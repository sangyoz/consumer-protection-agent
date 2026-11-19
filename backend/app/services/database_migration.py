"""One-time, non-destructive migration of the existing SQLite case store."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, CaseRecord
from .case_repository import load_case, store_case
from .schema_migration import upgrade_schema


def migrate_cases(source: Path, target, backup: Path) -> dict:
    if target.dialect.name != 'mysql':
        raise ValueError('迁移目标必须是 MySQL。')
    upgrade_schema(target)
    if not source.exists():
        return {'inserted': 0, 'existing': 0}
    backup.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)) as connection:
        with closing(sqlite3.connect(backup)) as snapshot:
            connection.backup(snapshot)
        rows = connection.execute('SELECT id, payload FROM cases ORDER BY id').fetchall()
    records = [{'id': key, 'payload': json.loads(payload)} for key, payload in rows]
    with Session(target) as session, session.begin():
        existing = {row.id: load_case(row) for row in session.scalars(select(CaseRecord))}
        conflicts = [row for row in records if row['id'] in existing and existing[row['id']] != row['payload']]
        if conflicts:
            raise ValueError(f'MySQL 有 {len(conflicts)} 个同 ID 但内容不同的案件；已中止迁移，未覆盖任何案件。')
        missing = [row for row in records if row['id'] not in existing]
        for row in missing:
            session.add(store_case(CaseRecord(id=row['id']), row['payload']))
        session.flush()
        session.expire_all()
        # JSON objects, Chinese text, evidence metadata and fixed plans must round-trip unchanged.
        verified = {row.id: load_case(row) for row in session.scalars(select(CaseRecord))}
        if any(verified.get(row['id']) != row['payload'] for row in records):
            raise ValueError('迁移后内容核对失败，事务已回滚。')
    return {'inserted': len(missing), 'existing': len(records) - len(missing)}
