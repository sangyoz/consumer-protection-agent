"""默认 SQLite；通过 DATABASE_URL 切换到 MySQL。"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import JSON, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / '.env')
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{(BACKEND_DIR / "youli.db").as_posix()}')
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class CaseRecord(Base):
    """骨架阶段使用 JSON 保存案件聚合；后续可拆分案件、消息、证据等表。"""
    __tablename__ = 'cases'
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)


def get_session():
    with SessionLocal() as session:
        yield session
