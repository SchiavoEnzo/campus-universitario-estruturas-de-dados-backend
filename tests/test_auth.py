import os
import unittest
from datetime import timedelta
from unittest.mock import patch
import mongomock
from fastapi.testclient import TestClient
from app import app
from campus.auth import auth_db, password_hash, digest, now
from campus.controllers import repository
from test_api import MemoryGraph

class TestAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hashed = password_hash.hash('temporary-password-123')
    def setUp(self):
        self.db = mongomock.MongoClient(tz_aware=True).campus_viva
        self.db.users.insert_one({'_id':'enzo','username':'enzo','name':'Enzo','role':'admin',
            'password_hash':self.hashed,'auth_version':1,'must_change_password':True})
        app.dependency_overrides[auth_db] = lambda: self.db
        app.dependency_overrides[repository] = lambda: MemoryGraph()
        self.db_patch = patch('campus.controllers.auth_db', return_value=self.db)
        self.db_patch.start()
        self.env = patch.dict(os.environ, {'CORS_ORIGINS':'https://campus.example','VERCEL':'1'})
        self.env.start()
        self.client = TestClient(app, base_url='https://campus.example')
        self.origin = {'Origin':'https://campus.example'}
    def tearDown(self):
        self.client.close();self.env.stop();self.db_patch.stop();app.dependency_overrides.clear()
    def login(self, username='Enzo', password='temporary-password-123'):
        return self.client.post('/api/auth/login',json={'username':username,'password':password},headers=self.origin)
    def test_login_errors_origin_rate_limit(self):
        self.assertEqual(self.client.post('/api/auth/login',json={'username':'Enzo','password':'x'}).status_code,403)
        for _ in range(10):
            result=self.login(password='wrong');self.assertEqual(result.status_code,401)
        self.assertEqual(self.login().status_code,429)
        self.assertEqual(self.login(username='missing').json()['detail'],result.json()['detail'])
    def test_password_csrf_rotation_permissions_logout(self):
        login=self.login();self.assertEqual(login.status_code,200)
        for flag in ['HttpOnly','Secure','SameSite=lax','__Host-campus_session']:
            self.assertIn(flag,login.headers['set-cookie'])
        self.assertNotIn('password_hash',str(login.json()))
        token=self.client.cookies.get('__Host-campus_session')
        self.assertIsNotNone(self.db.auth_sessions.find_one({'_id':digest(token)}))
        self.assertNotIn(token,str(list(self.db.auth_sessions.find())))
        headers={**self.origin,'X-CSRF-Token':login.json()['csrf_token']}
        self.assertEqual(self.client.get('/api/auth/me').status_code,200)
        self.assertEqual(self.client.post('/api/points',json={'name':'x'},headers=headers).status_code,403)
        payload={'current_password':'temporary-password-123','new_password':'new-password-for-enzo'}
        self.assertEqual(self.client.post('/api/auth/password',json=payload,headers=self.origin).status_code,403)
        self.assertEqual(self.client.post('/api/auth/password',json={**payload,'current_password':'wrong'},headers=headers).status_code,400)
        changed=self.client.post('/api/auth/password',json=payload,headers=headers)
        self.assertEqual(changed.status_code,200)
        self.assertFalse(changed.json()['user']['must_change_password'])
        self.assertIsNone(self.db.auth_sessions.find_one({'_id':digest(token)}))
        headers['X-CSRF-Token']=changed.json()['csrf_token']
        self.assertEqual(self.client.post('/api/points',json={'name':'x'},headers=self.origin).status_code,403)
        self.assertEqual(self.client.post('/api/points',json={'name':'x'},headers={**headers,'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.client.post('/api/points',json={'name':'x'},headers=headers).status_code,201)
        self.assertEqual(self.client.post('/api/auth/logout',headers=headers).status_code,204)
        self.assertEqual(self.client.get('/api/auth/me').status_code,401)
        self.assertEqual(self.login().status_code,401)
        self.assertEqual(self.login(password=payload['new_password']).status_code,200)
    def test_normalization_viewer_disabled_expired_version(self):
        self.db.users.update_one({'_id':'enzo'},{'$set':{'username':'verissimo','name':'Veríssimo','role':'viewer','must_change_password':False}})
        response=self.login(username=' VERÍSSIMO ');self.assertEqual(response.status_code,200)
        headers={**self.origin,'X-CSRF-Token':response.json()['csrf_token']}
        self.assertEqual(self.client.post('/api/points',json={'name':'x'},headers=headers).status_code,403)
        self.db.users.update_one({'_id':'enzo'},{'$inc':{'auth_version':1}})
        self.assertEqual(self.client.get('/api/auth/me').status_code,401)
        self.assertEqual(self.login(username='verissimo').status_code,200)
        self.db.auth_sessions.update_many({},{'$set':{'expires_at':now()-timedelta(seconds=1)}})
        self.assertEqual(self.client.get('/api/auth/me').status_code,401)
        self.db.users.update_one({'_id':'enzo'},{'$set':{'disabled':True}})
        self.assertEqual(self.login(username='verissimo').status_code,401)
