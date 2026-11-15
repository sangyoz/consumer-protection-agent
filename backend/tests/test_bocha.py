"""Bocha contract and failure tests; all network requests are mocked."""
import os
import unittest
from unittest.mock import patch

import httpx

from app.services import retrieval


class BochaTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'BOCHA_API_KEY': 'test-key',
                                          'BOCHA_BASE_URL': 'https://api.bochaai.com/v1/web-search'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def response(self, body, status=200):
        return httpx.Response(status, json=body, request=httpx.Request('POST',
                              'https://api.bochaai.com/v1/web-search'))

    def test_unconfigured_does_not_send_request(self):
        with patch.dict(os.environ, {'BOCHA_API_KEY': ''}), patch.object(retrieval.httpx, 'post') as post:
            self.assertEqual(retrieval.search_web_experience('退货退款')['status'], 'not_configured')
        post.assert_not_called()

    def test_contract_whitelist_and_query_minimization(self):
        rows = [
            {'name': '投诉记录', 'url': 'https://tousu.sina.com.cn/complaint/view/1', 'summary': '消费者陈述'},
            {'name': '裁判案例', 'url': 'https://anli.court.gov.cn/case/1', 'snippet': '案例摘要'},
            {'url': 'https://tousu.sina.com.cn.evil.example/1'},
            {'url': 'https://evil.example/?to=tousu.sina.com.cn'},
            {'url': 'https://user:pass@tousu.sina.com.cn/1'},
            {'url': 'http://tousu.sina.com.cn/1'},
            {'url': None}, None,
        ]
        rows.append(rows[0])
        response = self.response({'code': 200, 'data': {'webPages': {'value': rows}}})
        with patch.object(retrieval.httpx, 'post', return_value=response) as post:
            result = retrieval.search_web_experience('退货退款 商品质量 姓名张三 电话13800000000 订单123')
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(len(result['cases']), 2)
        self.assertEqual([c['kind'] for c in result['cases']], ['consumer_report', 'court_case'])
        payload = post.call_args.kwargs['json']
        self.assertEqual(set(payload['include'].split('|')), retrieval.ALLOWED_CASE_HOSTS)
        self.assertIsInstance(payload['include'], str)
        self.assertEqual(payload['query'], '商品质量 退货退款')
        self.assertEqual(post.call_args.kwargs['headers']['Authorization'], 'Bearer test-key')

    def test_http_failures_have_safe_distinct_statuses(self):
        statuses = {400: 'invalid_request', 401: 'unauthorized', 402: 'payment_required',
                    403: 'forbidden', 429: 'rate_limited', 500: 'provider_error'}
        for code, expected in statuses.items():
            with self.subTest(code=code), patch.object(retrieval.httpx, 'post',
                    return_value=self.response({'msg': 'test-key'}, status=code)):
                result = retrieval.search_web_experience('退货退款')
                self.assertEqual(result, {'cases': [], 'status': expected})

    def test_business_error_is_not_treated_as_empty_results(self):
        with patch.object(retrieval.httpx, 'post', return_value=self.response({'code': 401, 'msg': 'test-key'})):
            self.assertEqual(retrieval.search_web_experience('退货退款')['status'], 'unauthorized')

    def test_empty_or_filtered_results_are_valid_responses(self):
        for data in [{}, {'webPages': None}, {'webPages': {'value': []}},
                     {'webPages': {'value': [{'url': 'https://example.com/1'}]}}]:
            with self.subTest(data=data), patch.object(retrieval.httpx, 'post',
                    return_value=self.response({'code': 200, 'data': data})):
                self.assertEqual(retrieval.search_web_experience('退货退款')['status'], 'no_results')

    def test_malformed_payload_is_not_no_results(self):
        for body in [[], {}, {'data': []}, {'data': {'webPages': []}},
                     {'data': {'webPages': {'value': 'bad'}}}]:
            with self.subTest(body=body), patch.object(retrieval.httpx, 'post', return_value=self.response(body)):
                self.assertEqual(retrieval.search_web_experience('退货退款')['status'], 'invalid_response')

    def test_timeout_and_network_failure(self):
        for error, expected in [(httpx.ReadTimeout('secret'), 'timeout'),
                                (httpx.ConnectError('secret'), 'unavailable')]:
            with self.subTest(expected=expected), patch.object(retrieval.httpx, 'post', side_effect=error):
                self.assertEqual(retrieval.search_web_experience('退货退款'), {'cases': [], 'status': expected})


if __name__ == '__main__':
    unittest.main()
