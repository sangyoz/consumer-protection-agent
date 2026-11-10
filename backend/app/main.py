import copy
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import BACKEND_DIR, Base, CaseRecord, engine, get_session
from .schemas import CaseInput, MessageInput, ProgressInput
from .services import agent, complaint

UPLOAD_DIR = BACKEND_DIR / 'uploads'
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_SUFFIXES = {'.pdf', '.docx', '.png', '.jpg', '.jpeg', '.txt'}


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    UPLOAD_DIR.mkdir(exist_ok=True)
    yield


app = FastAPI(title='有理消费维权助手 API', version='0.1.0', lifespan=lifespan, description='双人开发骨架；Agent 使用模拟规则，未接入真实法律检索与投诉提交。')
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')], allow_credentials=False, allow_methods=['GET', 'POST'], allow_headers=['*'])


def now():
    return datetime.now(timezone.utc).isoformat()


def get_case(case_id: str, session: Session) -> tuple[CaseRecord, dict]:
    record = session.get(CaseRecord, case_id)
    if record is None:
        raise HTTPException(404, '案件不存在')
    return record, copy.deepcopy(record.payload)


def ensure_open(case: dict):
    if case['stage'] == 'resolved':
        raise HTTPException(409, '案件已解决；如需继续处理，请先在处理跟进中更新状态')


def record_event(case: dict, text: str):
    case['updatedAt'] = now()
    case['timeline'].append({'id': str(uuid4()), 'text': text, 'createdAt': case['updatedAt']})


def save(record: CaseRecord, case: dict, session: Session):
    record.payload = case
    session.commit()
    return case


@app.get('/api/health')
def health():
    return {'status': 'ok', 'agentMode': 'demo'}


@app.get('/api/cases')
def list_cases(session: Session = Depends(get_session)):
    return sorted([record.payload for record in session.scalars(select(CaseRecord))], key=lambda item: item['updatedAt'], reverse=True)


@app.post('/api/cases', status_code=201)
def create_case(input: CaseInput, session: Session = Depends(get_session)):
    case_id, created_at = str(uuid4()), now()
    case = {'id': case_id, 'title': input.title.strip() or input.summary[:24], 'summary': input.summary, 'merchant': input.merchant.strip(), 'amount': input.amount, 'goal': input.goal.strip() or '希望协助梳理合理诉求', 'stage': 'collecting', 'createdAt': created_at, 'updatedAt': created_at, 'analysis': None, 'messages': [], 'materials': [], 'complaint': '', 'timeline': [{'id': str(uuid4()), 'text': '案件已创建，等待补充信息', 'createdAt': created_at}]}
    session.add(CaseRecord(id=case_id, payload=case))
    session.commit()
    return case


@app.get('/api/cases/{case_id}')
def read_case(case_id: str, session: Session = Depends(get_session)):
    return get_case(case_id, session)[1]


@app.post('/api/cases/{case_id}/analysis')
def analyze_case(case_id: str, session: Session = Depends(get_session)):
    record, case = get_case(case_id, session)
    ensure_open(case)
    case['analysis'] = agent.analyze(case)
    if case['stage'] == 'collecting':
        case['stage'] = 'analyzing'
    record_event(case, '已生成演示案情分析，法律依据待核验')
    return save(record, case, session)


@app.post('/api/cases/{case_id}/messages')
def send_message(case_id: str, input: MessageInput, session: Session = Depends(get_session)):
    record, case = get_case(case_id, session)
    ensure_open(case)
    created_at = now()
    case['messages'].append({'id': str(uuid4()), 'role': 'merchant', 'content': input.content, 'createdAt': created_at})
    case['messages'].append({'id': str(uuid4()), 'role': 'assistant', 'content': agent.reply(case, input.content), 'createdAt': created_at})
    case['stage'] = 'negotiating'
    record_event(case, '记录商家回复并生成演示沟通建议')
    return save(record, case, session)


@app.post('/api/cases/{case_id}/complaint')
def generate_complaint(case_id: str, session: Session = Depends(get_session)):
    record, case = get_case(case_id, session)
    ensure_open(case)
    case['complaint'] = complaint.generate(case)
    case['stage'] = 'complaining'
    record_event(case, '生成投诉草稿，尚未向任何平台提交')
    return save(record, case, session)


@app.post('/api/cases/{case_id}/materials')
async def upload_materials(case_id: str, files: list[UploadFile] = File(...), session: Session = Depends(get_session)):
    record, case = get_case(case_id, session)
    ensure_open(case)
    if not 1 <= len(files) <= 5:
        raise HTTPException(400, '每次上传 1 至 5 份材料')
    pending = []
    written = []
    try:
        # 先验证整批文件，再写入；存储名独立生成，绝不使用用户提供的路径。
        for upload in files:
            filename = (upload.filename or '').replace('\\', '/').rsplit('/', 1)[-1]
            suffix = Path(filename).suffix.lower()
            if suffix not in ALLOWED_SUFFIXES:
                raise HTTPException(400, '仅支持 PDF、DOCX、PNG、JPG、TXT')
            content = await upload.read(MAX_FILE_SIZE + 1)
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(413, '单个文件不能超过 10 MB')
            if not content:
                raise HTTPException(400, '不能上传空文件')
            material_id = str(uuid4())
            storage_name = material_id + suffix
            pending.append(({'id': material_id, 'name': filename, 'size': len(content), 'status': 'uploaded', 'storageName': storage_name}, content))
        for material, content in pending:
            target = UPLOAD_DIR / material['storageName']
            target.write_bytes(content)
            written.append(target)
            case['materials'].append(material)
        record_event(case, '附件已保存，内容解析待接入')
        return save(record, case, session)
    except Exception:
        session.rollback()
        for path in written:
            path.unlink(missing_ok=True)
        raise
    finally:
        for upload in files:
            await upload.close()


@app.post('/api/cases/{case_id}/progress')
def update_progress(case_id: str, input: ProgressInput, session: Session = Depends(get_session)):
    record, case = get_case(case_id, session)
    if input.stage == 'resolved' and not input.confirmed:
        raise HTTPException(400, '请确认退款到账或其他诉求已实际履行，再结束案件')
    if input.stage:
        case['stage'] = input.stage
    record_event(case, input.note)
    return save(record, case, session)
