import copy
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app.services import planning


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.model = patch.object(planning.agent, '_json_call', return_value=None)
        self.model.start()
        self.addCleanup(self.model.stop)
        self.case = {'summary': '网购耳机无法使用', 'merchant': '耳机店', 'platform': '淘宝',
                     'goal': '退款', 'stage': 'collecting', 'materials': [], 'messages': []}

    def test_different_facts_produce_different_plans_and_other_is_last(self):
        shopping = copy.deepcopy(self.case)
        prepaid = {**self.case, 'summary': '健身房会员卡停业，剩余未消费', 'platform': ''}
        planning.refresh(shopping, 'initial')
        planning.refresh(prepaid, 'initial')
        a = [row['type'] for row in shopping['plan']['steps']]
        b = [row['type'] for row in prepaid['plan']['steps']]
        self.assertIn('platform', a)
        self.assertNotIn('calculation', a)
        self.assertIn('calculation', b)
        self.assertNotIn('platform', b)
        self.assertEqual(a[-1], 'other')
        self.assertEqual(b[-1], 'other')

    def test_code_deduplicates_steps_and_appends_other(self):
        proposal = {'reason': '选择必要步骤', 'steps': [
            {'type': 'other', 'reason': '末尾', 'completion_condition': '核对'},
            {'type': 'negotiation', 'reason': '沟通', 'completion_condition': '记录回复'},
            {'type': 'negotiation', 'reason': '重复', 'completion_condition': '记录回复'}], 'alternatives': []}
        with patch.object(planning.agent, '_json_call', return_value=proposal):
            planning.refresh(self.case)
        self.assertEqual([s['id'] for s in self.case['plan']['steps']], ['negotiation', 'other'])
        self.assertEqual(self.case['plan']['current_step_id'], 'negotiation')

    def test_failed_step_is_frozen_and_failed_channel_not_recommended(self):
        planning.refresh(self.case)
        step = next(row for row in self.case['plan']['steps'] if row['type'] == 'platform')
        step.update(status='failed', note='平台不支持处理此订单')
        proposal = {'reason': '调整路径', 'steps': [{'type': 'platform', 'reason': '重复', 'completion_condition': '再试'},
            {'type': 'complaint', 'reason': '整理材料', 'completion_condition': '核对草稿'}],
            'alternatives': [{'channel': 'platform', 'reason': '不能再推荐'},
                             {'channel': 'consumer_assoc', 'reason': '核对调解条件'}]}
        with patch.object(planning.agent, '_json_call', return_value=proposal):
            planning.refresh(self.case, 'step_failed')
        frozen = self.case['plan']['steps'][0]
        self.assertEqual(frozen['status'], 'failed')
        self.assertEqual(frozen['note'], '平台不支持处理此订单')
        self.assertEqual(self.case['plan']['current_step_id'], 'complaint')
        self.assertEqual([x['channel'] for x in self.case['plan']['alternatives']], ['consumer_assoc'])
        self.assertEqual(self.case['plan']['version'], 2)
        self.assertEqual(len(self.case['plan_history']), 1)

    def test_model_cannot_supply_executable_step_or_extra_channel(self):
        with self.assertRaises(ValidationError):
            planning.PlanProposal.model_validate({'reason': '测试', 'steps': [
                {'type': 'send_email', 'reason': '对外发送', 'completion_condition': '发送成功'}]})

    def test_fabricated_statute_in_plan_falls_back_to_rules(self):
        proposal = {'reason': '依据《消费者权益保护法》第88条', 'steps': [
            {'type': 'complaint', 'reason': '直接投诉', 'completion_condition': '核对'}], 'alternatives': []}
        with patch.object(planning.agent, '_json_call', return_value=proposal):
            planning.refresh(self.case)
        self.assertEqual(self.case['plan']['engine'], 'rules')
        self.assertNotIn('88', self.case['plan']['reason'])

    def test_resolved_case_keeps_plan_and_history(self):
        planning.refresh(self.case)
        old = copy.deepcopy(self.case['plan'])
        self.case['stage'] = 'resolved'
        planning.refresh(self.case, 'progress_feedback')
        self.assertEqual(self.case['plan'], old)

    def test_failed_negotiation_adds_complaint_and_preserves_history(self):
        planning.refresh(self.case)
        step = next(s for s in self.case['plan']['steps'] if s['type'] == 'negotiation')
        step.update(status='failed', note='商家拒绝退款')
        planning.refresh(self.case, 'step_failed')
        self.assertIn('complaint', [s['type'] for s in self.case['plan']['steps']])
        self.assertEqual(next(s for s in self.case['plan']['steps'] if s['type'] == 'negotiation')['status'], 'failed')

    def test_other_yields_to_newly_needed_steps(self):
        self.case['plan'] = {'version': 1, 'current_step_id': 'other', 'steps': [
            {'id': 'other', 'type': 'other', 'status': 'active'}]}
        planning.refresh(self.case)
        self.assertNotEqual(self.case['plan']['current_step_id'], 'other')
        self.assertEqual(self.case['plan']['steps'][-1]['type'], 'other')

    def test_confirming_evidence_does_not_remove_active_checklist(self):
        planning.refresh(self.case)
        self.case['evidence_checklist'] = [
            {'key': key, 'status': 'user_confirmed'} for key in ('transaction', 'payment')]
        planning.refresh(self.case, 'evidence_updated')
        self.assertEqual(self.case['plan']['current_step_id'], 'evidence')
        self.assertEqual(next(s for s in self.case['plan']['steps'] if s['type'] == 'evidence')['status'], 'active')
