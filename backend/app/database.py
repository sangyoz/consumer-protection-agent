"""MySQL case store; explicit SQLite URLs remain available for tests/offline use."""
import os
from pathlib import Path

from dotenv import load_dotenv
from datetime import datetime
from sqlalchemy import JSON, String, Text, Float, Integer, Boolean, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, relationship

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / '.env')
DATABASE_URL = os.getenv('DATABASE_URL') or 'mysql+pymysql://youli:youli_dev_password@127.0.0.1:3306/youli?charset=utf8mb4'
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class DocumentFields:
    """Only extension fields stay JSON; normal business fields are SQL columns.

    field_names preserves absent vs null fields during lossless legacy migration.
    """
    field_names: Mapped[list | None] = mapped_column(JSON, nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class CaseRecord(DocumentFields, Base):
    __tablename__ = 'cases'
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(50), ForeignKey('users.id'), index=True, nullable=True)
    title: Mapped[str | None] = mapped_column(String(100))
    summary: Mapped[str | None] = mapped_column(Text)
    merchant: Mapped[str | None] = mapped_column(String(200))
    amount: Mapped[float | None] = mapped_column(Float)
    goal: Mapped[str | None] = mapped_column(Text)
    trade_time: Mapped[str | None] = mapped_column(String(40))
    platform: Mapped[str | None] = mapped_column(String(100))
    product: Mapped[str | None] = mapped_column(String(200))
    payee: Mapped[str | None] = mapped_column(String(200))
    credit_code: Mapped[str | None] = mapped_column(String(30))
    stage: Mapped[str | None] = mapped_column(String(32), index=True)
    created_at: Mapped[str | None] = mapped_column(String(40))
    updated_at: Mapped[str | None] = mapped_column(String(40), index=True)
    messages: Mapped[list['Message']] = relationship(cascade='all, delete-orphan', lazy='selectin', order_by='Message.position')
    materials: Mapped[list['Material']] = relationship(cascade='all, delete-orphan', lazy='selectin', order_by='Material.position')
    evidence_items: Mapped[list['EvidenceItem']] = relationship(cascade='all, delete-orphan', lazy='selectin', order_by='EvidenceItem.position')
    steps: Mapped[list['CaseStep']] = relationship(cascade='all, delete-orphan', lazy='selectin', order_by='CaseStep.position')
    progress_records: Mapped[list['ProgressRecord']] = relationship(cascade='all, delete-orphan', lazy='selectin', order_by='ProgressRecord.position')
    events: Mapped[list['CaseEvent']] = relationship(cascade='all, delete-orphan', lazy='selectin', order_by='CaseEvent.position')
    plan: Mapped['CasePlan | None'] = relationship(cascade='all, delete-orphan', lazy='selectin', uselist=False)
    analysis_record: Mapped['CaseAnalysis | None'] = relationship(cascade='all, delete-orphan', lazy='selectin', uselist=False)


class CaseRow(DocumentFields):
    case_id: Mapped[str] = mapped_column(String(50), ForeignKey('cases.id', ondelete='CASCADE'), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, primary_key=True)


class Message(CaseRow, Base):
    __tablename__ = 'messages'
    id: Mapped[str | None] = mapped_column(String(50), index=True)
    role: Mapped[str | None] = mapped_column(String(32))
    content: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(String(40))


class Material(CaseRow, Base):
    __tablename__ = 'materials'
    id: Mapped[str | None] = mapped_column(String(50), index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    size: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String(32))
    storage_name: Mapped[str | None] = mapped_column(String(100))
    kind: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str | None] = mapped_column(String(32))
    uploaded_at: Mapped[str | None] = mapped_column(String(40))


class EvidenceItem(CaseRow, Base):
    __tablename__ = 'evidence_items'
    key: Mapped[str | None] = mapped_column(String(50))
    label: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str | None] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(Text)
    content_verified: Mapped[bool | None] = mapped_column(Boolean)


class CaseStep(CaseRow, Base):
    __tablename__ = 'case_steps'
    id: Mapped[str | None] = mapped_column(String(50), index=True)
    type: Mapped[str | None] = mapped_column(String(32))
    title: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str | None] = mapped_column(String(32))
    reason: Mapped[str | None] = mapped_column(Text)
    completion_condition: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    feedback_at: Mapped[str | None] = mapped_column(String(40))


class ProgressRecord(CaseRow, Base):
    __tablename__ = 'progress_records'
    id: Mapped[str | None] = mapped_column(String(50), index=True)
    step_id: Mapped[str | None] = mapped_column(String(50))
    note: Mapped[str | None] = mapped_column(Text)
    stage: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str | None] = mapped_column(String(32))
    confirmed: Mapped[bool | None] = mapped_column(Boolean)
    channel: Mapped[str | None] = mapped_column(String(100))
    case_no: Mapped[str | None] = mapped_column(String(200))
    accept_status: Mapped[str | None] = mapped_column(String(32))
    deadline: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[str | None] = mapped_column(String(40))


class CaseEvent(CaseRow, Base):
    __tablename__ = 'case_events'
    id: Mapped[str | None] = mapped_column(String(50), index=True)
    text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(String(40))


class CasePlan(DocumentFields, Base):
    __tablename__ = 'case_plans'
    case_id: Mapped[str] = mapped_column(String(50), ForeignKey('cases.id', ondelete='CASCADE'), primary_key=True)
    version: Mapped[int | None] = mapped_column(Integer)
    locked: Mapped[bool | None] = mapped_column(Boolean)
    engine: Mapped[str | None] = mapped_column(String(32))
    reason: Mapped[str | None] = mapped_column(Text)
    current_step_id: Mapped[str | None] = mapped_column(String(50))
    updated_at: Mapped[str | None] = mapped_column(String(40))


class CaseAnalysis(DocumentFields, Base):
    """AI output/variable schemas remain JSON, outside relational business rows."""
    __tablename__ = 'case_analyses'
    case_id: Mapped[str] = mapped_column(String(50), ForeignKey('cases.id', ondelete='CASCADE'), primary_key=True)
    analysis: Mapped[dict | None] = mapped_column(JSON)
    agent_state: Mapped[dict | None] = mapped_column(JSON)
    complaint: Mapped[str | None] = mapped_column(Text)
    complaint_attachments: Mapped[list | None] = mapped_column(JSON)
    goal_plan: Mapped[dict | None] = mapped_column(JSON)
    resolution: Mapped[dict | None] = mapped_column(JSON)


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime)


class LoginSession(Base):
    __tablename__ = 'user_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey('users.id'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


def get_session():
    with SessionLocal() as session:
        yield session
