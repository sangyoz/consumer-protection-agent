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

    def test_failed_step_keeps_order_and_filters_failed_channel(self):
        planning.refresh(self.case)
        before = [row['id'] for row in self.case['plan']['steps']]
        step = next(row for row in self.case['plan']['steps'] if row['type'] == 'platform')
        step.update(status='failed', note='平台不支持处理此订单')
        self.case['plan']['alternatives'] = [{'channel': 'platform'}, {'channel': 'consumer_assoc'}]
        with patch.object(planning.agent, '_json_call') as model:
            planning.refresh(self.case, 'step_failed')
        model.assert_not_called()
        self.assertEqual([row['id'] for row in self.case['plan']['steps']], before)
        saved = next(row for row in self.case['plan']['steps'] if row['type'] == 'platform')
        self.assertEqual(saved['note'], '平台不支持处理此订单')
        self.assertEqual(saved['status'], 'failed')
        self.assertEqual([row['channel'] for row in self.case['plan']['alternatives']], ['consumer_assoc'])
        self.assertEqual(self.case['plan']['version'], 1)
        self.assertFalse(self.case.get('plan_history'))

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

    def test_failed_negotiation_does_not_add_or_reorder_steps(self):
        planning.refresh(self.case)
        before = [s['id'] for s in self.case['plan']['steps']]
        step = next(s for s in self.case['plan']['steps'] if s['type'] == 'negotiation')
        step.update(status='failed', note='商家拒绝退款')
        planning.refresh(self.case, 'step_failed')
        self.assertEqual([s['id'] for s in self.case['plan']['steps']], before)
        self.assertNotIn('complaint', before)
        self.assertEqual(step['status'], 'failed')

    def test_existing_terminal_other_does_not_gain_new_steps(self):
        self.case['plan'] = {'version': 1, 'current_step_id': 'other', 'steps': [
            {'id': 'other', 'type': 'other', 'status': 'active'}]}
        planning.refresh(self.case)
        self.assertEqual([s['id'] for s in self.case['plan']['steps']], ['other'])

    def test_every_automatic_update_keeps_initial_plan_without_model_calls(self):
        planning.refresh(self.case)
        original = copy.deepcopy(self.case['plan'])
        self.case.update(summary='健身房协商失败，需要核算未消费余额', merchant='', platform='线下门店')
        for trigger in ('initial', 'facts_updated', 'merchant_reply', 'materials_updated', 'evidence_updated', 'progress_feedback'):
            with self.subTest(trigger=trigger), patch.object(planning.agent, '_json_call') as model:
                planning.refresh(self.case, trigger)
                model.assert_not_called()
                self.assertEqual(self.case['plan'], original)

    def test_manual_refresh_updates_alternatives_only(self):
        planning.refresh(self.case)
        original = copy.deepcopy(self.case['plan'])
        proposal = {'reason': '结合新反馈核对调解条件', 'alternatives': [
            {'channel': 'consumer_assoc', 'reason': '核对当地受理条件'}]}
        with patch.object(planning.agent, '_json_call', return_value=proposal) as model:
            planning.refresh(self.case, 'manual')
        self.assertIs(model.call_args.args[-1], planning.AlternativeProposal)
        for key in ('steps', 'version', 'reason', 'current_step_id', 'updated_at'):
            self.assertEqual(self.case['plan'][key], original[key])
        self.assertEqual(self.case['plan']['alternatives_engine'], 'deepseek')
        self.assertEqual([row['channel'] for row in self.case['plan']['alternatives']], ['consumer_assoc'])

    def test_step_result_advances_within_initial_order(self):
        planning.refresh(self.case)
        rows = self.case['plan']['steps']
        rows[0].update(status='completed', note='已整理')
        planning.refresh(self.case, 'step_completed')
        self.assertEqual(self.case['plan']['current_step_id'], rows[1]['id'])
        self.assertEqual(rows[1]['status'], 'active')
        self.assertEqual(rows[0]['status'], 'completed')

    def test_confirming_evidence_does_not_remove_active_checklist(self):
        planning.refresh(self.case)
        self.case['evidence_checklist'] = [
            {'key': key, 'status': 'user_confirmed'} for key in ('transaction', 'payment')]
        planning.refresh(self.case, 'evidence_updated')
        self.assertEqual(self.case['plan']['current_step_id'], 'evidence')
        self.assertEqual(next(s for s in self.case['plan']['steps'] if s['type'] == 'evidence')['status'], 'active')
