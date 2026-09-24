"""
Production Deployment & Environment Configuration Verification Suite
Tests dynamic environment loading, ProxyFix HTTPS handling, WSGI entry, and Gunicorn configuration.
"""
import sys
import os
import unittest
import tempfile
import shutil

# Ensure scratch/lib is on sys.path
sys.path.insert(0, '/home/hd/.gemini/antigravity/scratch/lib')
sys.path.insert(0, '/home/hd/.gemini/antigravity/scratch/mat-vlab')

class TestProductionDeployment(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, 'custom_mount', 'test_production.db')
        os.environ['DATABASE_PATH'] = self.test_db_path
        os.environ['SECRET_KEY'] = 'test-production-secret-987654321'
        os.environ['FLASK_ENV'] = 'production'
        os.environ['ENABLE_PROXY_FIX'] = 'true'

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_dynamic_config_loading(self):
        from config import Config
        self.assertEqual(Config.DATABASE, self.test_db_path)
        self.assertEqual(Config.SECRET_KEY, 'test-production-secret-987654321')
        self.assertEqual(Config.FLASK_ENV, 'production')
        self.assertTrue(Config.ENABLE_PROXY_FIX)

    def test_database_auto_creation_in_custom_path(self):
        from models.database import init_db, get_all_materials, get_database_path
        self.assertEqual(get_database_path(), self.test_db_path)
        init_db()
        self.assertTrue(os.path.exists(self.test_db_path))
        materials = get_all_materials()
        self.assertGreaterEqual(len(materials), 5)

    def test_wsgi_entrypoint_import(self):
        import wsgi
        self.assertTrue(hasattr(wsgi, 'app'))
        self.assertIsNotNone(wsgi.app)

    def test_gunicorn_conf_parsing(self):
        gunicorn_conf_module = {}
        conf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gunicorn.conf.py')
        with open(conf_path, 'r', encoding='utf-8') as f:
            exec(f.read(), gunicorn_conf_module)
        self.assertIn('bind', gunicorn_conf_module)
        self.assertIn('workers', gunicorn_conf_module)
        self.assertIn('threads', gunicorn_conf_module)
        self.assertIn('timeout', gunicorn_conf_module)

    def test_proxy_fix_https_forwarding(self):
        from app import app
        client = app.test_client()
        with client:
            res = client.get('/', headers={
                'X-Forwarded-Proto': 'https',
                'X-Forwarded-For': '203.0.113.195',
                'X-Forwarded-Host': 'vlab.example.org'
            })
            self.assertEqual(res.status_code, 200)
            from flask import request, url_for
            self.assertEqual(request.scheme, 'https')
            self.assertEqual(request.host, 'vlab.example.org')
            self.assertTrue(url_for('tensile_hub', _external=True).startswith('https://vlab.example.org/experiments/tensile'))

    def test_relative_endpoints_in_frontend(self):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        forbidden = ['http://localhost', 'http://127.0.0.1', 'http://10.10.']
        scanned = 0
        for folder in ['templates', 'static']:
            target_dir = os.path.join(base_dir, folder)
            for root, dirs, files in os.walk(target_dir):
                for file in files:
                    if file.endswith(('.html', '.js', '.css')):
                        scanned += 1
                        with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            for bad in forbidden:
                                self.assertNotIn(bad, content, f"Found hardcoded address {bad} in {file}")
        self.assertGreater(scanned, 10)

if __name__ == '__main__':
    unittest.main()
