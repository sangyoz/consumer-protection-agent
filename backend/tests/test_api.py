"""运行：在 backend 目录执行 python -m unittest discover -s tests -v。"""
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import main
from app.database import get_session


class ApiFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        self.original_engine, self.original_uploads = main.engine, main.UPLOAD_DIR
        main.engine = self.engine
        main.UPLOAD_DIR = Path(self.temp.name) / 'uploads'

        def session_override():
            with Session(self.engine, expire_on_commit=False) as session:
                yield session

        main.app.dependency_overrides[get_session] = session_override
        self.client_context = TestClient(main.app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        main.app.dependency_overrides.clear()
        main.engine, main.UPLOAD_DIR = self.original_engine, self.original_uploads
        self.engine.dispose()
        self.temp.cleanup()

    def create_case(self):
        response = self.client.post('/api/cases', json={'title': '耳机质量纠纷', 'summary': '购买的耳机右侧无声音，商家要求等待。', 'merchant': '示例数码店', 'amount': 399, 'goal': '协商退货退款'})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()['id']

    def test_complete_case_flow_and_confirmation(self):
        case_id = self.create_case()
        self.assertEqual(len(self.client.get('/api/cases').json()), 1)
        case = self.client.post(f'/api/cases/{case_id}/analysis').json()
        self.assertFalse(case['analysis']['legal']['verified'])
        response = self.client.post(f'/api/cases/{case_id}/messages', json={'content': '请耐心等待公司通知。'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['messages']), 2)
        case = self.client.post(f'/api/cases/{case_id}/complaint').json()
        self.assertIn('请耐心等待公司通知', case['complaint'])
        self.assertEqual(case['stage'], 'complaining')
        response = self.client.post(f'/api/cases/{case_id}/progress', json={'note': '商家口头同意', 'stage': 'resolved'})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(f'/api/cases/{case_id}/progress', json={'note': '退款已经到账', 'stage': 'resolved', 'confirmed': True})
        self.assertEqual(response.json()['stage'], 'resolved')
        self.assertEqual(self.client.post(f'/api/cases/{case_id}/analysis').status_code, 409)
        saved = self.client.get(f'/api/cases/{case_id}').json()
        self.assertEqual(saved['timeline'][-1]['text'], '退款已经到账')
        self.assertEqual(saved['amount'], 399)

    def test_upload_validation_and_storage(self):
        case_id = self.create_case()
        url = f'/api/cases/{case_id}/materials'
        response = self.client.post(url, files={'files': ('../../order.txt', b'order 399 CNY', 'text/plain')})
        self.assertEqual(response.status_code, 200, response.text)
        material = response.json()['materials'][0]
        self.assertEqual(material['name'], 'order.txt')
        self.assertEqual((main.UPLOAD_DIR / material['storageName']).read_bytes(), b'order 399 CNY')
        self.assertEqual(self.client.post(url, files={'files': ('run.exe', b'test', 'application/octet-stream')}).status_code, 400)
        # 整批校验失败时，不应保存前半批的材料。
        response = self.client.post(url, files=[('files', ('ok.txt', b'ok', 'text/plain')), ('files', ('bad.exe', b'bad', 'application/octet-stream'))])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(list(main.UPLOAD_DIR.iterdir())), 1)
        self.assertEqual(len(self.client.get(f'/api/cases/{case_id}').json()['materials']), 1)

    def test_invalid_requests(self):
        self.assertEqual(self.client.get('/api/cases/missing').status_code, 404)
        self.assertEqual(self.client.post('/api/cases', json={'summary': '   '}).status_code, 422)
        self.assertEqual(self.client.post('/api/cases', json={'summary': '测试', 'amount': -1}).status_code, 422)
        case_id = self.create_case()
        self.assertEqual(self.client.post(f'/api/cases/{case_id}/messages', json={'content': ' '}).status_code, 422)
        self.assertEqual(self.client.post(f'/api/cases/{case_id}/progress', json={'note': '更新', 'stage': 'invalid'}).status_code, 422)


if __name__ == '__main__':
    unittest.main()
