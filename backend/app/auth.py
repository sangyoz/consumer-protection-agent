"""Password hashing, opaque revocable sessions and per-user case ownership."""
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import threading
import time
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, inspect, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import BACKEND_DIR, CaseRecord, LoginSession, User, get_session

router = APIRouter(prefix='/api/auth', tags=['账号'])
COOKIE = 'youli_session'
TTL = 7 * 24 * 60 * 60
_attempts = defaultdict(deque)
_lock = threading.Lock()


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return f'scrypt${salt}${digest}'


def verify_password(password, encoded):
    try:
        algorithm, salt, expected = encoded.split('$')
        if algorithm != 'scrypt':
            return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


# Unknown users still perform the same expensive password check.
DUMMY_HASH = hash_password(secrets.token_urlsafe(24))


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)

    @field_validator('username')
    @classmethod
    def username_format(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[a-z0-9_]{3,32}', value):
            raise ValueError('账号需为 3–32 位英文字母、数字或下划线')
        return value


def public_user(user):
    return {'id': user.id, 'username': user.username}


def check_origin(request: Request):
    """Only same-origin browser writes; allow the two local Vite entry points."""
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return
    origin = request.headers.get('origin')
    allowed = {str(request.base_url).rstrip('/'), *[x.strip() for x in os.getenv(
        'CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')]}
    if origin and origin not in allowed:
        raise HTTPException(403, '请求来源不受信任')
    if request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403, '不接受跨站请求')


def current_user(request: Request, session: Session = Depends(get_session)):
    check_origin(request)
    token = request.cookies.get(COOKIE, '')
    record = session.get(LoginSession, hashlib.sha256(token.encode()).hexdigest()) if token else None
    if not record or record.expires_at <= utcnow():
        raise HTTPException(401, '请先登录，或登录已过期')
    user = session.get(User, record.user_id)
    if not user:
        raise HTTPException(401, '登录已失效，请重新登录')
    return user


def authenticated_session(session: Session = Depends(get_session), user: User = Depends(current_user)):
    session.info['user_id'] = user.id
    return session


def rate_limit(request, username):
    ip = request.client.host if request.client else 'unknown'
    now = time.monotonic()
    with _lock:
        # Bound memory even when random usernames/IPs are submitted.
        for key in list(_attempts):
            if not _attempts[key] or _attempts[key][-1] < now - 600:
                del _attempts[key]
        for key, limit in ((f'ip:{ip}', 40), (f'user:{username}', 15)):
            bucket = _attempts[key]
            while bucket and bucket[0] < now - 600:
                bucket.popleft()
            if len(bucket) >= limit:
                raise HTTPException(429, '尝试过于频繁，请 10 分钟后再试', headers={'Retry-After': '600'})
        _attempts[f'ip:{ip}'].append(now)
        _attempts[f'user:{username}'].append(now)


def issue_session(user, response, request, session):
    token = secrets.token_urlsafe(32)
    session.execute(delete(LoginSession).where(LoginSession.expires_at <= utcnow()))
    session.add(LoginSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id,
                             expires_at=utcnow() + timedelta(seconds=TTL)))
    session.commit()
    response.set_cookie(COOKIE, token, httponly=True, samesite='strict', max_age=TTL,
                        secure=request.url.scheme == 'https', path='/api')
    response.headers['Cache-Control'] = 'no-store'
    return public_user(user)


@router.post('/register', status_code=201)
def register(input: Credentials, request: Request, response: Response, session: Session = Depends(get_session)):
    check_origin(request)
    rate_limit(request, input.username)
    user = User(id=str(uuid4()), username=input.username, password_hash=hash_password(input.password), created_at=utcnow())
    session.add(user)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, '该账号已被使用，请换一个账号') from None
    return issue_session(user, response, request, session)


@router.post('/login')
def login(input: Credentials, request: Request, response: Response, session: Session = Depends(get_session)):
    check_origin(request)
    rate_limit(request, input.username)
    user = session.scalar(select(User).where(User.username == input.username))
    valid = verify_password(input.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, '账号或密码不正确')
    return issue_session(user, response, request, session)


@router.get('/me')
def me(response: Response, user: User = Depends(current_user)):
    response.headers['Cache-Control'] = 'no-store'
    return public_user(user)


@router.post('/logout')
def logout(request: Request, response: Response, session: Session = Depends(get_session)):
    check_origin(request)
    token = request.cookies.get(COOKIE, '')
    if token:
        session.execute(delete(LoginSession).where(LoginSession.token_hash == hashlib.sha256(token.encode()).hexdigest()))
        session.commit()
    response.delete_cookie(COOKIE, path='/api', httponly=True, samesite='strict')
    return {'ok': True}


def upgrade_ownership(engine):
    """Add ownership to existing installations; never assign legacy cases to a public registrant."""
    columns = {c['name'] for c in inspect(engine).get_columns('cases')}
    if 'user_id' not in columns:
        with engine.begin() as connection:
            connection.execute(text('ALTER TABLE cases ADD COLUMN user_id VARCHAR(50) NULL'))
            connection.execute(text('CREATE INDEX ix_cases_user_id ON cases (user_id)'))
    with Session(engine) as session:
        unowned = session.scalar(select(CaseRecord.id).where(CaseRecord.user_id.is_(None)).limit(1))
        if not unowned:
            return
        username = 'owner_' + secrets.token_hex(4)
        password = secrets.token_urlsafe(18)
        user = User(id=str(uuid4()), username=username, password_hash=hash_password(password), created_at=utcnow())
        session.add(user)
        session.flush()
        # Local handover file is ignored by Git; no credentials appear in logs/API.
        folder = BACKEND_DIR.parent / '.run'
        folder.mkdir(exist_ok=True)
        path = folder / 'initial-account.txt'
        with path.open('x', encoding='utf-8') as output:
            output.write(f'旧案件初始账号\n账号：{username}\n密码：{password}\n请妥善保管，不要上传此文件。\n')
        session.execute(update(CaseRecord).where(CaseRecord.user_id.is_(None)).values(user_id=user.id))
        session.commit()
