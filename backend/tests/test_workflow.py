"""验证 LangGraph 路由和无 API Key 时的本地演示回退。"""
import os
import json
import tempfile
import unittest
from unittest.mock import patch

from app.agents import workflow
from app.services import agent, retrieval


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'DEEPSEEK_API_KEY': '', 'BOCHA_API_KEY': '',
                                           'LAW_CORPUS_PATH': '', 'LAW_DB_PATH': self.temp.name + '/law.sqlite3'})
        self.env.start()
        agent._model.cache_clear()
        self.case = {
            'id': 'case-test',
            'title': '耳机质量纠纷',
            'summary': '网购耳机右侧没有声音。',
            'merchant': '示例商家',
            'amount': 399,
            'goal': '退货退款',
            'messages': [],
        }

    def tearDown(self):
        self.env.stop()
        agent._model.cache_clear()
        self.temp.cleanup()

    def test_analysis_runs_graph_and_marks_legal_unverified(self):
        result = workflow.run_analysis(self.case)
        self.assertEqual(result['engine'], 'demo')
        self.assertEqual(result['summary'], self.case['summary'])
        self.assertFalse(result['legal']['verified'])
        self.assertTrue(result['missing'])
        self.assertTrue(result['evidence_checklist'])
        self.assertEqual(result['retrieval']['law_library'], 'empty')

    def test_invalid_citation_routes_through_one_correction(self):
        law = {'id': 'consumer-55', 'law_name': '中华人民共和国消费者权益保护法', 'article': '55', 'content': '经营者提供商品或者服务有欺诈行为的……', 'source': 'https://flk.npc.gov.cn/example', 'effective_from': '2024-07-01', 'effective_to': None, 'reviewed_at': '2025-01-01'}
        drafts = [
            {'category': '商品纠纷', 'missing': [], 'rights': '依据《消费者权益保护法》第88条。', 'strategy': '核对事实', 'script': '请回复。', 'engine': 'deepseek'},
            {'category': '商品纠纷', 'missing': [], 'rights': '相关条文待核验。', 'strategy': '核对事实', 'script': '请回复。', 'engine': 'deepseek'},
        ]
        with patch.object(retrieval, '_active_laws', return_value=[law]), \
             patch.object(retrieval, 'search', return_value={'laws': [law], 'cases': [], 'status': {'law_library': 'ok', 'law_search_mode': 'bm25', 'case_search': 'not_configured'}}), \
             patch.object(agent, 'generate', side_effect=drafts) as generate:
            result = workflow.run_analysis(self.case)
        self.assertEqual(generate.call_count, 2)
        self.assertTrue(result['audit']['valid'])
        self.assertEqual(result['audit']['correction_attempts'], 1)

    def test_still_invalid_after_retry_discards_model_text(self):
        law = {'id': 'consumer-55', 'law_name': '消费者权益保护法', 'article': '55', 'content': '经营者提供商品或者服务有欺诈行为的。', 'source': 'https://flk.npc.gov.cn/example', 'effective_from': '2024-07-01', 'effective_to': None, 'reviewed_at': '2025-01-01'}
        unsafe = {'category': '商品纠纷', 'missing': [], 'rights': '依据《消费者权益保护法》第88条。', 'strategy': '核对事实', 'script': '威胁商家并引用第88条。', 'engine': 'deepseek', 'citations': []}
        with patch.object(retrieval, '_active_laws', return_value=[law]), \
             patch.object(retrieval, 'search', return_value={'laws': [law], 'cases': [], 'status': {'law_library': 'ok', 'law_search_mode': 'bm25', 'case_search': 'not_configured'}}), \
             patch.object(agent, 'generate', side_effect=[unsafe, unsafe]):
            result = workflow.run_analysis(self.case)
        self.assertEqual(result['engine'], 'demo')
        self.assertEqual(result['fallback_reason'], 'citation_audit_failed')
        self.assertNotIn('第88条', result['rights'] + result['script'])
        self.assertTrue(result['audit']['safe_fallback'])

    def test_citation_audit_rejects_law_not_in_retrieval(self):
        audit = retrieval.audit_citations('依据《消费者权益保护法》第88条处理。', [])
        self.assertFalse(audit['valid'])
        self.assertIn('消费者权益保护法', audit['feedback'])

    def test_local_bm25_import_and_source_quote_audit(self):
        row = {'id': 'law-55', 'law_name': '消费者权益保护法', 'article': '五十五',
               'content': '经营者提供商品或者服务有欺诈行为的，应当按照消费者的要求增加赔偿其受到的损失。',
               'source': 'https://flk.npc.gov.cn/law/55', 'effective_from': '2024-07-01', 'reviewed_at': '2025-01-01'}
        corpus = os.path.join(self.temp.name, 'laws.jsonl')
        with open(corpus, 'w', encoding='utf-8') as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
        retrieval.import_laws(corpus)
        found = retrieval.search_local_law('商家欺诈消费赔偿')
        self.assertEqual(found['mode'], 'bm25')
        self.assertEqual(found['laws'][0]['article'], '55')
        quote = '应当按照消费者的要求增加赔偿其受到的损失。'
        audit = retrieval.audit_citations('依据《消费者权益保护法》第五十五条。', found['laws'],
                                          [{'law_id': 'law-55', 'quote': quote}])
        self.assertTrue(audit['valid'])

    def test_reply_runs_graph_with_full_case_context(self):
        result = workflow.run_reply(self.case, '请耐心等待公司通知。')
        self.assertIn('处理期限', result)
        self.assertIn('仅供参考', result)

    def test_opponent_wrong_article_is_reported_without_allowing_it_as_authority(self):
        law = {'id': 'consumer-10', 'law_name': '中华人民共和国消费者权益保护法', 'article': '10',
               'content': '第十条 测试条文正文。', 'source': 'https://flk.npc.gov.cn/test-only',
               'effective_from': '2020-01-01', 'effective_to': None, 'reviewed_at': '2025-01-01'}
        with patch.object(retrieval, '_active_laws', return_value=[law]):
            result = workflow.run_case('reply', self.case, '根据《消费者权益保护法》第88条，特价不退。')
            bad_audit = retrieval.audit_citations('依据《消费者权益保护法》第88条可以拒绝退款。', [law])
        self.assertEqual(result['merchant_claim_checks'][0]['status'], 'article_not_found')
        self.assertIn('未在本地已收录的该法律版本中找到', result['reply'])
        self.assertIn('retrieve_context', result['trace'])
        self.assertFalse(bad_audit['valid'])

    def test_missing_law_is_not_described_as_nonexistent(self):
        with patch.object(retrieval, '_active_laws', return_value=[]):
            checks = retrieval.check_merchant_claims('依据《尚未收录的测试法》第88条。')
        self.assertEqual(checks[0]['status'], 'law_not_in_library')
        self.assertIn('不能据此断言法条不存在', retrieval.format_merchant_checks(checks))

    def test_verbatim_quote_with_article_number_does_not_fail_bare_number_rule(self):
        law = {'id': 'consumer-10', 'law_name': '中华人民共和国消费者权益保护法', 'article': '10',
               'content': '第十条 测试条文正文。', 'source': 'https://flk.npc.gov.cn/test-only',
               'effective_from': '2020-01-01', 'effective_to': None, 'reviewed_at': '2025-01-01'}
        with patch.object(retrieval, '_active_laws', return_value=[law]):
            result = retrieval.audit_citations('检索原文：第十条 测试条文正文。', [law],
                                               [{'law_id': 'consumer-10', 'quote': law['content']}])
        self.assertTrue(result['valid'])

    def test_model_cannot_skip_local_search_when_opponent_cites_a_statute(self):
        decision = {'action': 'collect_evidence', 'reason': '先补证', 'tools': [], 'query': '商品退货'}
        state = {'operation': 'reply', 'case': self.case, 'merchant_reply': '根据《消费者权益保护法》第88条。',
                 'evidence_checklist': [], 'retrieval': {}, 'executed_tools': [], 'trace': [],
                 'merchant_claim_checks': [{'status': 'article_not_found'}]}
        with patch.object(agent, 'decide', return_value=decision):
            result = workflow.decide(state)
        self.assertIn('search_local_law', result['decision']['tools'])

    def test_reply_turn_can_negotiate_while_evidence_is_missing(self):
        decision = {'action': 'negotiate', 'reason': '先回应商家的拒绝理由', 'tools': [],
                    'query': '', 'confidence': 'medium', 'uncertainties': ['商品是否使用过'],
                    'user_questions': []}
        with patch.object(agent, '_json_call', return_value=decision):
            result = agent.decide('reply', self.case, '特价商品不能退。',
                                  [{'key': 'payment', 'status': 'missing', 'required': True}],
                                  {}, [])
        self.assertEqual(result['action'], 'negotiate')
        self.assertEqual(result['uncertainties'], ['商品是否使用过'])

    def test_initial_analysis_keeps_required_evidence_gate_and_complaint_is_explicit(self):
        decision = {'action': 'escalate', 'reason': '资料不足', 'tools': [], 'query': '',
                    'confidence': 'low', 'uncertainties': [], 'user_questions': []}
        inventory = [{'key': 'payment', 'status': 'missing', 'required': True}]
        with patch.object(agent, '_json_call', side_effect=[dict(decision), dict(decision)]):
            initial = agent.decide('analysis', self.case, '', inventory, {}, [])
            complaint = agent.decide('complaint', self.case, '', inventory, {}, [])
        self.assertEqual(initial['action'], 'collect_evidence')
        self.assertEqual(complaint['action'], 'complaint')

    def test_clarify_action_routes_to_a_bounded_user_question(self):
        decision = {'action': 'clarify_user', 'reason': '退款计算取决于剩余服务时长', 'tools': [],
                    'query': '', 'confidence': 'low', 'uncertainties': ['已使用的服务时长未知'],
                    'user_questions': ['会员服务已经使用了多长时间？']}
        with patch.object(agent, '_json_call', side_effect=[dict(decision), None]):
            result = workflow.run_case('reply', self.case, '可以退一半。')
        self.assertEqual(result['decision']['action'], 'clarify_user')
        self.assertIn('会员服务已经使用了多长时间', result['reply'])
        self.assertIn('clarify_user', result['trace'])


if __name__ == '__main__':
    unittest.main()
