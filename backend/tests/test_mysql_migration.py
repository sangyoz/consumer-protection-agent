"""Optional MySQL integration tests; MYSQL_TEST_URL must name a disposable youli_test_* schema."""
import json
import os
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base, CaseRecord
from app.services.database_migration import migrate_cases
from app.services.case_repository import load_case, store_case


@unittest.skipUnless(os.getenv('MYSQL_TEST_URL'), '未配置独立 MySQL 测试库')
class MySQLMigrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(os.environ['MYSQL_TEST_URL'])
        if not (self.engine.url.database or '').startswith('youli_test_'):
            raise RuntimeError('只允许操作 youli_test_* 临时测试库。')
        Base.metadata.drop_all(self.engine)
        self.temp = tempfile.TemporaryDirectory()
        self.source = Path(self.temp.name) / 'source.db'
        self.backup = Path(self.temp.name) / 'backup.db'
        self.payload = {'id': 'test-case', 'summary': '中文案件📦', 'messages': [{'content': '订单已保留'}],
                        'plan': {'locked': True, 'steps': [{'id': 'evidence'}, {'id': 'other'}]}}
        with closing(sqlite3.connect(self.source)) as connection, connection:
            connection.execute('CREATE TABLE cases (id TEXT PRIMARY KEY, payload JSON)')
            connection.execute('INSERT INTO cases VALUES (?, ?)', ('test-case', json.dumps(self.payload)))

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        self.temp.cleanup()

    def test_json_round_trip_backup_and_repeat(self):
        self.assertEqual(migrate_cases(self.source, self.engine, self.backup), {'inserted': 1, 'existing': 0})
        with Session(self.engine) as session:
            self.assertEqual(load_case(session.get(CaseRecord, 'test-case')), self.payload)
        with closing(sqlite3.connect(self.backup)) as connection:
            self.assertEqual(json.loads(connection.execute('SELECT payload FROM cases').fetchone()[0]), self.payload)
        self.assertEqual(migrate_cases(self.source, self.engine, self.backup), {'inserted': 0, 'existing': 1})

    def test_conflicting_destination_is_never_overwritten(self):
        migrate_cases(self.source, self.engine, self.backup)
        changed = {**self.payload, 'summary': 'MySQL 上的新进度'}
        with Session(self.engine) as session, session.begin():
            store_case(session.get(CaseRecord, 'test-case'), changed)
        with self.assertRaisesRegex(ValueError, '未覆盖'):
            migrate_cases(self.source, self.engine, self.backup)
        with Session(self.engine) as session:
            self.assertEqual(load_case(session.get(CaseRecord, 'test-case')), changed)

    def test_fresh_install_creates_empty_schema(self):
        result = migrate_cases(Path(self.temp.name) / 'absent.db', self.engine, self.backup)
        self.assertEqual(result, {'inserted': 0, 'existing': 0})
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(select(CaseRecord.id)).all(), [])
