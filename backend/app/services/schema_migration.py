"""Idempotent upgrade from cases.payload to relational module tables.

Run with application writers stopped. MySQL DDL commits implicitly: the payload
column is removed only after a committed round-trip verification. On failure it
stays available for retry; a local backup is written before the first DDL.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import MetaData, Table, inspect, select, text
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateColumn

from app.database import BACKEND_DIR, Base, CaseRecord
from .case_repository import load_case, store_case


def upgrade_schema(engine, backup_dir: Path | None = None):
    inspector = inspect(engine)
    if 'cases' not in inspector.get_table_names():
        Base.metadata.create_all(engine)
        return {'migrated': 0}
    columns = {column['name'] for column in inspector.get_columns('cases')}
    if 'payload' not in columns:
        Base.metadata.create_all(engine)
        return {'migrated': 0}

    backup_dir = backup_dir or BACKEND_DIR.parent / '.run' / 'backups'
    backup_dir.mkdir(parents=True, exist_ok=True)
    path = backup_dir / f'relational-before-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")}.json'
    metadata = MetaData()
    metadata.reflect(engine)
    with engine.connect() as connection:
        # Includes existing users and hashed sessions, so ownership is recoverable.
        snapshot = {table.name: [dict(row) for row in connection.execute(select(table)).mappings()]
                    for table in metadata.sorted_tables}
    with path.open('x', encoding='utf-8') as output:
        json.dump(snapshot, output, ensure_ascii=False, default=str)

    # All added columns are nullable, so an interrupted migration can be retried.
    with engine.begin() as connection:
        for column in CaseRecord.__table__.columns:
            if column.name not in columns:
                definition = str(CreateColumn(column).compile(dialect=engine.dialect))
                # SQLite cannot ALTER ADD a REFERENCES constraint with legacy data;
                # existing installations already had user_id from the auth upgrade.
                connection.execute(text(f'ALTER TABLE cases ADD COLUMN {definition}'))
    Base.metadata.create_all(engine)
    for index in CaseRecord.__table__.indexes:
        index.create(engine, checkfirst=True)
    if engine.dialect.name == 'mysql' and not any(
            fk['constrained_columns'] == ['user_id'] for fk in inspect(engine).get_foreign_keys('cases')):
        with engine.begin() as connection:
            connection.execute(text('ALTER TABLE cases ADD CONSTRAINT fk_cases_user_id FOREIGN KEY (user_id) REFERENCES users(id)'))
    legacy = Table('cases', MetaData(), autoload_with=engine)
    with engine.connect() as connection:
        originals = connection.execute(select(legacy.c.id, legacy.c.payload)).all()
    documents = [(key, json.loads(value) if isinstance(value, str) else value) for key, value in originals]
    with Session(engine) as session:
        for key, document in documents:
            record = session.get(CaseRecord, key)
            store_case(record, document)
        session.commit()
    # New session forces a true read from the split tables instead of ORM cache.
    with Session(engine) as session:
        for key, document in documents:
            if load_case(session.get(CaseRecord, key)) != document:
                raise ValueError('拆表后数据核对失败；旧 payload 和本机备份已保留，未删除旧字段。')
    with engine.begin() as connection:
        connection.execute(text('ALTER TABLE cases DROP COLUMN payload'))
    return {'migrated': len(documents), 'backup': str(path)}
