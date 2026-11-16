"""运行：在 backend 目录执行 python -m unittest discover -s tests -v。"""
import tempfile
import unittest
import os
from unittest.mock import patch
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import main
from app.database import get_session
from app.services import agent


class ApiFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'DEEPSEEK_API_KEY': '', 'BOCHA_API_KEY': '',
                                           'LAW_CORPUS_PATH': '', 'LAW_DB_PATH': str(Path(self.temp.name) / 'legal.sqlite3')})
        self.env.start()
        agent._model.cache_clear()
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
        self.env.stop()
        agent._model.cache_clear()
        self.temp.cleanup()

    def create_case(self):
        response = self.client.post('/api/cases', json={'title': '耳机质量纠纷', 'summary': '购买的耳机右侧无声音，商家要求等待。', 'merchant': '示例数码店', 'amount': 399, 'goal': '协商退货退款'})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()['id']

    def test_create_case_default_title_uses_goal_and_product(self):
        response = self.client.post('/api/cases', json={'summary': '台灯插上电就不亮。', 'goal': '退货退款', 'product': '护眼台灯'})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()['title'], '退货退款 · 护眼台灯')
        fallback = self.client.post('/api/cases', json={'summary': '商家一直推脱，希望帮忙看看怎么维权。', 'goal': '', 'product': ''}).json()
        self.assertEqual(fallback['title'], '商家一直推脱，希望帮忙看看怎么维权。')

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

    def test_create_case_with_extra_facts(self):
        payload = {
            'summary': '网购台灯收到后无法点亮，商家尚未回应。',
            'merchant': '示例灯具店',
            'amount': 199,
            'tradeTime': '2026-11-01',
            'platform': '某电商平台',
            'product': '护眼台灯',
            'payee': '示例贸易有限公司',
            'creditCode': '91370100MA3XXXXXX1X',
        }
        case_id = self.client.post('/api/cases', json=payload).json()['id']
        saved = self.client.get(f'/api/cases/{case_id}').json()
        self.assertEqual(saved['platform'], '某电商平台')
        self.assertEqual(saved['product'], '护眼台灯')
        self.assertEqual(saved['payee'], '示例贸易有限公司')
        self.assertEqual(saved['creditCode'], '91370100MA3XXXXXX1X')

    def test_update_case_facts(self):
        case_id = self.create_case()
        response = self.client.put(f'/api/cases/{case_id}', json={'product': '蓝牙耳机', 'platform': '某电商平台', 'payee': '示例收款方'})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['product'], '蓝牙耳机')
        self.assertEqual(body['platform'], '某电商平台')
        self.assertEqual(body['payee'], '示例收款方')
        # 未传的字段保持不变
        self.assertEqual(body['merchant'], '示例数码店')

    def test_update_case_rejects_empty_summary(self):
        case_id = self.create_case()
        response = self.client.put(f'/api/cases/{case_id}', json={'summary': '   '})
        self.assertEqual(response.status_code, 422)

    def test_material_download_and_delete(self):
        case_id = self.create_case()
        url = f'/api/cases/{case_id}/materials'
        self.client.post(url, files={'files': ('order.txt', b'order 399 CNY', 'text/plain')})
        case = self.client.get(f'/api/cases/{case_id}').json()
        material = case['materials'][0]
        download = self.client.get(f"/api/cases/{case_id}/materials/{material['id']}/download")
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.content, b'order 399 CNY')
        delete = self.client.delete(f"/api/cases/{case_id}/materials/{material['id']}")
        self.assertEqual(delete.status_code, 200)
        self.assertEqual(len(delete.json()['materials']), 0)
        self.assertFalse((main.UPLOAD_DIR / material['storageName']).exists())
        # 再次删除应 404
        self.assertEqual(self.client.delete(f"/api/cases/{case_id}/materials/{material['id']}").status_code, 404)

    def test_update_case_goal_plan_and_attachments(self):
        case_id = self.create_case()
        plan = {'basic': '退货退款', 'further': '赔偿运费', 'negotiable': '优惠券补偿', 'targetAmount': 399, 'basis': '商品全额', 'confirmed': True, 'evidence': ''}
        response = self.client.put(f'/api/cases/{case_id}', json={'goalPlan': plan, 'complaintAttachments': ['e1']})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['goalPlan']['basic'], '退货退款')
        self.assertTrue(body['goalPlan']['confirmed'])
        self.assertEqual(body['complaintAttachments'], ['e1'])

    def test_material_kind_patch(self):
        case_id = self.create_case()
        url = f'/api/cases/{case_id}/materials'
        self.client.post(url, files={'files': ('note.txt', b'chat record', 'text/plain')})
        material = self.client.get(f'/api/cases/{case_id}').json()['materials'][0]
        response = self.client.patch(f"/api/cases/{case_id}/materials/{material['id']}", json={'kind': 'chat'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['materials'][0]['kind'], 'chat')
        # 非法材料类型应被拒绝
        self.assertEqual(self.client.patch(f"/api/cases/{case_id}/materials/{material['id']}", json={'kind': 'video'}).status_code, 422)

    def test_progress_structured_followup(self):
        case_id = self.create_case()
        payload = {
            'note': '已在 12315 平台提交投诉',
            'stage': 'complaining',
            'channel': 'market_12315',
            'caseNo': '12315-2026-0001',
            'acceptStatus': 'pending',
            'deadline': '2026-11-20',
        }
        response = self.client.post(f'/api/cases/{case_id}/progress', json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        followup = response.json()['followups'][0]
        self.assertEqual(followup['channel'], 'market_12315')
        self.assertEqual(followup['caseNo'], '12315-2026-0001')
        self.assertEqual(followup['acceptStatus'], 'pending')
        self.assertEqual(followup['deadline'], '2026-11-20')
        self.assertIn('market_12315', response.json()['timeline'][-1]['text'])
        self.assertIn('12315-2026-0001', response.json()['timeline'][-1]['text'])

    def test_progress_resolution_on_close(self):
        case_id = self.create_case()
        resolution = {'resolvedWay': 'negotiation', 'actualAmount': 399, 'expectedMet': 'yes', 'summary': '全额退款到账', 'closedAt': '2026-11-13T00:00:00+00:00'}
        response = self.client.post(f'/api/cases/{case_id}/progress', json={'note': '退款已经到账', 'stage': 'resolved', 'confirmed': True, 'resolution': resolution})
        self.assertEqual(response.status_code, 200, response.text)
        saved = response.json()['resolution']
        self.assertEqual(saved['resolvedWay'], 'negotiation')
        self.assertEqual(saved['actualAmount'], 399)
        self.assertEqual(saved['expectedMet'], 'yes')

    def test_extract_fields_from_description(self):
        text = '我在淘宝花 399 元买了个蓝牙耳机，昨天收到后发现右侧没声音，商家让我等通知，我希望能退货退款。'
        response = self.client.post('/api/extract', json={'text': text})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['fields']['platform'], '淘宝')
        self.assertEqual(body['fields']['amount'], 399)
        self.assertEqual(body['fields']['product'], '蓝牙耳机')
        self.assertEqual(body['fields']['goal'], '退货退款')
        self.assertIn('tradeTime', body['fields'])
        # 每条识别结果都必须能在原文里定位到，这是不编造字段的底线。
        for item in body['evidence']:
            self.assertEqual(text[item['start']:item['end']], item['snippet'], item)
        self.assertEqual([item['field'] for item in body['missing']], ['merchant'])

    def test_extract_reports_missing_and_rejects_blank(self):
        response = self.client.post('/api/extract', json={'text': '商家一直不处理，我要投诉。'})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['fields'], {})
        self.assertEqual([item['field'] for item in body['missing']], ['merchant', 'amount', 'product', 'tradeTime'])
        self.assertEqual(self.client.post('/api/extract', json={'text': '   '}).status_code, 422)

    def test_delete_case_removes_record_and_files(self):
        case_id = self.create_case()
        material = self.client.post(f'/api/cases/{case_id}/materials', files={'files': ('order.txt', b'order 399 CNY', 'text/plain')}).json()['materials'][0]
        stored = main.UPLOAD_DIR / material['storageName']
        self.assertTrue(stored.exists())
        response = self.client.delete(f'/api/cases/{case_id}')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['id'], case_id)
        self.assertEqual(self.client.get('/api/cases').json(), [])
        self.assertEqual(self.client.get(f'/api/cases/{case_id}').status_code, 404)
        self.assertFalse(stored.exists())
        # 重复删除同一个案件应 404
        self.assertEqual(self.client.delete(f'/api/cases/{case_id}').status_code, 404)

    def test_invalid_requests(self):
        self.assertEqual(self.client.get('/api/cases/missing').status_code, 404)
        self.assertEqual(self.client.post('/api/cases', json={'summary': '   '}).status_code, 422)
        self.assertEqual(self.client.post('/api/cases', json={'summary': '测试', 'amount': -1}).status_code, 422)
        case_id = self.create_case()
        self.assertEqual(self.client.post(f'/api/cases/{case_id}/messages', json={'content': ' '}).status_code, 422)
        self.assertEqual(self.client.post(f'/api/cases/{case_id}/progress', json={'note': '更新', 'stage': 'invalid'}).status_code, 422)

    def test_evidence_confirmation_is_recorded_as_user_claim(self):
        case_id = self.create_case()
        response = self.client.post(f'/api/cases/{case_id}/evidence', json={'key': 'transaction', 'status': 'user_confirmed', 'note': '已核对订单号'})
        self.assertEqual(response.status_code, 200)
        entry = next(row for row in response.json()['evidence_checklist'] if row['key'] == 'transaction')
        self.assertEqual(entry['status'], 'user_confirmed')
        self.assertFalse(entry['content_verified'])
        self.assertEqual(self.client.post(f'/api/cases/{case_id}/evidence', json={'key': 'payment', 'status': 'not_applicable'}).status_code, 400)


if __name__ == '__main__':
    unittest.main()
