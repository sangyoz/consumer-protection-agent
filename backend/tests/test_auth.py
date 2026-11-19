import hashlib
import unittest
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import auth
from app.database import LoginSession, User
import test_api


class AccountTests(unittest.TestCase):
    def setUp(self):
        with auth._lock:
            auth._attempts.clear()
        test_api.ApiFlowTests.setUp(self)

    tearDown = test_api.ApiFlowTests.tearDown
    create_case = test_api.ApiFlowTests.create_case

    def test_registration_validation_duplicate_password_storage(self):
        response = self.client.post('/api/auth/register', json={'username': 'TEST_USER', 'password': 'other_password'})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.post('/api/auth/register', json={'username': 'x', 'password': 'short'}).status_code, 422)
        with Session(self.engine) as session:
            user = session.scalar(select(User))
            self.assertNotEqual(user.password_hash, 'test_password_123')
            self.assertTrue(auth.verify_password('test_password_123', user.password_hash))
            login = session.scalar(select(LoginSession))
            token = self.client.cookies.get(auth.COOKIE)
            self.assertNotEqual(login.token_hash, token)
            self.assertEqual(login.token_hash, hashlib.sha256(token.encode()).hexdigest())
        self.assertEqual(set(self.client.get('/api/auth/me').json()), {'id', 'username'})

    def test_login_logout_revocation_and_expiry(self):
        old = self.client.cookies.get(auth.COOKIE)
        self.assertEqual(self.client.post('/api/auth/logout').status_code, 200)
        self.assertEqual(self.client.get('/api/cases').status_code, 401)
        self.client.cookies.set(auth.COOKIE, old)
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)
        self.client.cookies.clear()
        self.assertEqual(self.client.post('/api/auth/login', json={'username': 'test_user', 'password': 'wrong_password'}).status_code, 401)
        response = self.client.post('/api/auth/login', json={'username': 'TEST_USER', 'password': 'test_password_123'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('HttpOnly', response.headers['set-cookie'])
        self.assertIn('SameSite=strict', response.headers['set-cookie'])
        with Session(self.engine) as session:
            login = session.scalar(select(LoginSession))
            login.expires_at = auth.utcnow() - timedelta(seconds=1)
            session.commit()
        self.assertEqual(self.client.get('/api/cases').status_code, 401)

    def test_case_isolation_for_all_case_routes(self):
        case_id = self.create_case()
        self.client.post('/api/auth/logout')
        self.client.post('/api/auth/register', json={'username': 'second_user', 'password': 'second_password'})
        self.assertEqual(self.client.get('/api/cases').json(), [])
        paths = [
            ('GET', '', None), ('DELETE', '', None), ('PUT', '', {'title': '越权'}),
            ('POST', '/analysis', None), ('POST', '/plan', None),
            ('POST', '/messages', {'content': '测试'}), ('POST', '/complaint', None),
            ('POST', '/evidence', {'key': 'payment', 'status': 'user_confirmed'}),
            ('POST', '/progress', {'note': '越权测试'}),
            ('POST', '/steps/evidence/feedback', {'status': 'failed', 'note': '测试'}),
            ('GET', '/materials/unknown/download', None), ('DELETE', '/materials/unknown', None),
            ('PATCH', '/materials/unknown', {'kind': 'order'}),
        ]
        for method, suffix, body in paths:
            with self.subTest(method=method, suffix=suffix):
                response = self.client.request(method, f'/api/cases/{case_id}{suffix}', json=body)
                self.assertEqual(response.status_code, 404, response.text)
        response = self.client.post(f'/api/cases/{case_id}/materials', files={'files': ('proof.txt', b'proof', 'text/plain')})
        self.assertEqual(response.status_code, 404)
        self.client.post('/api/auth/logout')
        self.client.post('/api/auth/login', json={'username': 'test_user', 'password': 'test_password_123'})
        self.assertEqual(self.client.get(f'/api/cases/{case_id}').status_code, 200)

    def test_untrusted_origin_and_rate_limit(self):
        response = self.client.post('/api/auth/login', json={'username': 'test_user', 'password': 'test_password_123'}, headers={'Origin': 'https://evil.example'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.post('/api/cases', json={'summary': '案件'}, headers={'Origin': 'https://evil.example'}).status_code, 403)
        with auth._lock:
            auth._attempts.clear()
        for _ in range(15):
            self.assertEqual(self.client.post('/api/auth/login', json={'username': 'unknown_user', 'password': 'wrong_password'}).status_code, 401)
        self.assertEqual(self.client.post('/api/auth/login', json={'username': 'unknown_user', 'password': 'wrong_password'}).status_code, 429)

    def test_legacy_cases_not_claimed_by_registration(self):
        # New accounts never receive existing users' records.
        self.create_case()
        self.client.post('/api/auth/register', json={'username': 'third_user', 'password': 'third_password'})
        self.assertEqual(self.client.get('/api/cases').json(), [])
