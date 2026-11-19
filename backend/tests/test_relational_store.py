import json
from datetime import datetime
from pathlib import Path
import tempfile
import unittest

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.database import Base, CaseRecord, Message, Material, CaseStep, CaseEvent, User
from app.services.case_repository import load_case, store_case
from app.services.schema_migration import upgrade_schema


def example():
    return {'id': 'case-one', 'title': '退货📦', 'summary': '耳机有质量问题', 'amount': 299.25,
            'stage': 'collecting', 'createdAt': '2026-11-19T00:00:00+00:00', 'updatedAt': '2026-11-19T00:00:00+00:00',
            'messages': [{'id': 'msg', 'role': 'merchant', 'content': '正在核对', 'createdAt': '2026-11-19'}],
            'materials': [{'id': 'file', 'name': '订单.txt', 'size': 50, 'kind': 'order', 'storageName': 'file.txt'}],
            'evidence_checklist': [{'key': 'payment', 'status': 'user_confirmed', 'content_verified': False, 'materials': ['file']}],
            'plan': {'version': 1, 'locked': True, 'reason': '首次规划', 'current_step_id': 'evidence',
                     'alternatives': [{'channel': 'consumer_assoc', 'reason': '核对受理范围'}],
                     'steps': [{'id': 'evidence', 'type': 'evidence', 'status': 'active'}, {'id': 'other', 'type': 'other', 'status': 'pending'}]},
            'followups': [{'id': 'followup', 'note': '补充材料', 'caseNo': None, 'confirmed': False}],
            'timeline': [{'id': 'event', 'text': '案件已创建', 'createdAt': '2026-11-19'}],
            'analysis': {'citations': [{'id': 'law'}]}, 'agent_state': {'trace': ['audit']},
            'complaint': '', 'goalPlan': None, 'resolution': None, 'extension': {'future': True}}


class RelationalStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.engine = create_engine('sqlite:///' + str(Path(self.temp.name) / 'test.db'))

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def test_round_trip_updates_delete_and_rollback(self):
        Base.metadata.create_all(self.engine)
        case = example()
        with Session(self.engine) as session, session.begin():
            session.add(store_case(CaseRecord(id=case['id']), case))
        with Session(self.engine) as session:
            record = session.get(CaseRecord, case['id'])
            self.assertEqual(load_case(record), case)
            self.assertEqual(session.scalar(select(Message.content)), '正在核对')
            case['messages'].append({'id': 'reply', 'role': 'assistant', 'content': '建议保留证据'})
            case['materials'] = []
            case['plan']['steps'][0]['status'] = 'completed'
            store_case(record, case)
            session.commit()
        with Session(self.engine) as session:
            record = session.get(CaseRecord, case['id'])
            self.assertEqual(load_case(record), case)
            self.assertEqual(session.scalars(select(Material)).all(), [])
            revised = load_case(record)
            revised['messages'] = []
            store_case(record, revised)
            session.flush()
            session.rollback()
        with Session(self.engine) as session:
            record = session.get(CaseRecord, case['id'])
            self.assertEqual(load_case(record), case)
            session.delete(record)
            session.commit()
            for model in (Message, Material, CaseStep, CaseEvent):
                self.assertEqual(session.scalars(select(model)).all(), [])

    def test_upgrade_preserves_payload_and_owner_and_is_idempotent(self):
        case = example()
        # Old schema, including a real owner, before relational tables exist.
        User.__table__.create(self.engine)
        with self.engine.begin() as connection:
            connection.execute(User.__table__.insert().values(id='owner', username='existing_owner',
                               password_hash='existing_hash', created_at=datetime(2026, 11, 19)))
            connection.execute(text('CREATE TABLE cases (id VARCHAR(50) PRIMARY KEY, user_id VARCHAR(50), payload JSON NOT NULL)'))
            connection.execute(text('INSERT INTO cases VALUES (:id, :owner, :payload)'),
                               {'id': case['id'], 'owner': 'owner', 'payload': json.dumps(case)})
        result = upgrade_schema(self.engine, Path(self.temp.name) / 'backups')
        self.assertEqual(result['migrated'], 1)
        self.assertTrue(Path(result['backup']).exists())
        self.assertNotIn('payload', {col['name'] for col in inspect(self.engine).get_columns('cases')})
        with Session(self.engine) as session:
            record = session.get(CaseRecord, case['id'])
            self.assertEqual(load_case(record), case)
            self.assertEqual(record.user_id, 'owner')
        self.assertEqual(upgrade_schema(self.engine)['migrated'], 0)

    def test_optional_null_empty_and_unknown_fields_survive(self):
        Base.metadata.create_all(self.engine)
        for index, case in enumerate(({'plan': None}, {'plan': {'steps': None}}, {'messages': None}, {'plan': {}, 'messages': []})):
            document = {'id': f'case-{index}', **case}
            with Session(self.engine) as session, session.begin():
                session.add(store_case(CaseRecord(id=document['id']), document))
            with Session(self.engine) as session:
                self.assertEqual(load_case(session.get(CaseRecord, document['id'])), document)
