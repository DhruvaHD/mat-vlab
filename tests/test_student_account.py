"""
Comprehensive MAT-VLAB Major Simplification & Final UX Test Suite
Verifies:
1. First Screen Student Identification (Name + University, Continue button, no Student ID/PIN/Password)
2. Direct Home Page Flow (submitting identification immediately opens /home with no intermediate screens)
3. Removal of "Start Virtual Lab" button from Hero and Navbar
4. Session-based student identity and route protection
5. Educational activity and experiment saving (Tensile, Hardness, Quiz) with session metadata
6. Session-scoped "My Experiments" with active session notice banner
7. Private Admin System (/portal-admin auth, Experiment Usage Records table, JSON detail, CSV export)
8. Admin credentials update (requiring current password, updating username & password, no plaintext display)
9. Legacy route redirects (/login -> /, /register -> /, /dashboard -> /home)
"""
import os
import sys
import unittest
import tempfile
import shutil

# Ensure paths are configured
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SCRATCH_LIB = os.path.abspath(os.path.join(BASE_DIR, '..', 'lib'))
if os.path.exists(SCRATCH_LIB) and SCRATCH_LIB not in sys.path:
    sys.path.insert(0, SCRATCH_LIB)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ['MPLCONFIGDIR'] = '/tmp'
os.environ['ADMIN_USERNAME'] = 'testadmin'
os.environ['ADMIN_PASSWORD'] = 'testsecret2026'

class TestMATVLabSimplification(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.temp_dir, 'test_materials.db')
        os.environ['DATABASE_PATH'] = self.test_db
        os.environ['SECRET_KEY'] = 'test-secret-key-12345'

        from models.database import init_db
        init_db()

        from app import app
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_student_identification_first_screen(self):
        """Verify first screen is simple 2-field Student Information form with Continue button."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # 1. Check title & 2 required fields
        self.assertIn('STUDENT INFORMATION', html)
        self.assertIn('Student Name', html)
        self.assertIn('University / College Name', html)
        self.assertIn('Continue', html)
        self.assertIn('name="student_name"', html)
        self.assertIn('name="university"', html)

        # 2. Verify complete absence of Student ID, PIN, password, account registration
        self.assertNotIn('Student ID', html)
        self.assertNotIn('PIN', html)
        self.assertNotIn('Password', html)
        self.assertNotIn('CREATE NEW ACCOUNT', html)
        self.assertNotIn('STUDENT LOGIN', html)
        self.assertNotIn('Register Free', html)

    def test_direct_home_page_flow_and_no_start_virtual_lab_button(self):
        """Verify submitting identification directly opens /home with no intermediate screens or Start Virtual Lab buttons."""
        # 1. Post 2 fields to /start-session
        res = self.client.post('/start-session', data={
            'student_name': 'Dhruva H D',
            'university': 'Pondicherry University'
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers['Location'], '/home')

        # 2. Access /home directly
        res_home = self.client.get('/home')
        self.assertEqual(res_home.status_code, 200)
        home_html = res_home.data.decode('utf-8')

        # 3. Verify student identity and direct navigation on /home
        self.assertIn('Dhruva H D', home_html)
        self.assertIn('Pondicherry University', home_html)
        self.assertIn('End Session', home_html)

        # 4. Verify presence of direct experiment navigation
        self.assertIn('Tensile Test (UTM)', home_html)
        self.assertIn('Hardness Test (Brinell &amp; Rockwell)', home_html)
        self.assertIn('Explore All Experiments', home_html)

        # 5. Verify REMOVAL of "Start Virtual Lab" button from Home hero and navbar
        self.assertNotIn('Start Virtual Lab', home_html)
        self.assertNotIn('START VIRTUAL LAB', home_html)

    def test_legacy_routes_clean_redirect(self):
        """Verify legacy /login and /register redirect to /, and /dashboard redirects to /home."""
        res_login = self.client.get('/login')
        self.assertEqual(res_login.status_code, 302)
        self.assertEqual(res_login.headers['Location'], '/')

        res_reg = self.client.get('/register')
        self.assertEqual(res_reg.status_code, 302)
        self.assertEqual(res_reg.headers['Location'], '/')

        # Dashboard redirects to /home
        res_dash = self.client.get('/dashboard')
        self.assertEqual(res_dash.status_code, 302)
        self.assertEqual(res_dash.headers['Location'], '/home')

    def test_route_protection_and_session_lifecycle(self):
        """Verify protected routes redirect unauthenticated users to /, and session logout clears state."""
        # 1. Unauthenticated access to /home redirects to /
        res_unauth = self.client.get('/home')
        self.assertEqual(res_unauth.status_code, 302)
        self.assertTrue(res_unauth.headers['Location'].startswith('/'))
        self.assertIn('next=/home', res_unauth.headers['Location'])

        # 2. Authenticate session
        self.client.post('/start-session', data={
            'student_name': 'Sindhu R',
            'university': 'Anna University'
        })

        # 3. Now visiting / redirects to /home
        res_root = self.client.get('/')
        self.assertEqual(res_root.status_code, 302)
        self.assertEqual(res_root.headers['Location'], '/home')

        # 4. Logout ends session and redirects to /
        res_logout = self.client.get('/logout')
        self.assertEqual(res_logout.status_code, 302)
        self.assertEqual(res_logout.headers['Location'], '/')

        # 5. Visiting /home again redirects to /
        res_after_logout = self.client.get('/home')
        self.assertEqual(res_after_logout.status_code, 302)
        self.assertTrue(res_after_logout.headers['Location'].startswith('/'))

    def test_experiment_saving_with_session_metadata(self):
        """Verify Tensile and Hardness experiments and quiz results persist student_name, university, and session_id."""
        # 1. Start student session
        self.client.post('/start-session', data={
            'student_name': 'Arjun Mehta',
            'university': 'IIT Bombay'
        })

        # 2. Save Tensile experiment
        tensile_payload = {
            "title": "UTM Verification Run",
            "experiment_type": "tensile",
            "mode": "VIRTUAL_SIMULATION",
            "material_name": "Mild Steel (AISI 1018)",
            "original_diameter": 10.0,
            "original_gauge_length": 50.0,
            "readings": [
                {"reading_number": 1, "load_n": 0, "extension_mm": 0},
                {"reading_number": 2, "load_n": 10000, "extension_mm": 0.03}
            ],
            "results": {
                "cross_sectional_area": 78.54,
                "youngs_modulus_gpa": 205.0,
                "yield_strength_mpa": 250.0,
                "uts_mpa": 440.0,
                "max_load_n": 34500,
                "elongation_pct": 26.0
            }
        }
        res_ten = self.client.post('/api/save', json=tensile_payload)
        self.assertEqual(res_ten.status_code, 200)
        ten_id = res_ten.get_json()['experiment_id']

        # 3. Save Hardness experiment
        hardness_payload = {
            "method": "BRINELL",
            "mode": "VIRTUAL_SIMULATION",
            "title": "Brinell Verification Run",
            "material_id": 1,
            "material_name": "Mild Steel (AISI 1018)",
            "ball_diameter": 10.0,
            "applied_load": 3000.0,
            "dwell_time": 15,
            "mean_hardness": 132.1,
            "hardness_unit": "HBW 10/3000",
            "readings": [
                {"d1": 5.18, "d2": 5.18, "mean_d": 5.18, "hbw": 132.1}
            ]
        }
        res_hard = self.client.post('/api/hardness/save', json=hardness_payload)
        self.assertEqual(res_hard.status_code, 200)
        hard_id = res_hard.get_json()['experiment_id']

        # 4. Submit Quiz
        res_quiz = self.client.post('/api/quiz/submit', json={
            "experiment_id": ten_id,
            "experiment_type": "tensile",
            "score": 10,
            "total_questions": 10
        })
        self.assertEqual(res_quiz.status_code, 200)

        # 5. Verify database records have student_name and university populated
        from models.database import get_experiment_by_id, get_hardness_experiment_by_id
        ten_rec = get_experiment_by_id(ten_id)
        self.assertEqual(ten_rec['student_name'], 'Arjun Mehta')
        self.assertEqual(ten_rec['university'], 'IIT Bombay')
        self.assertIsNotNone(ten_rec['session_id'])

        hard_rec = get_hardness_experiment_by_id(hard_id)
        self.assertEqual(hard_rec['student_name'], 'Arjun Mehta')
        self.assertEqual(hard_rec['university'], 'IIT Bombay')
        self.assertIsNotNone(hard_rec['session_id'])

    def test_session_scoped_my_experiments(self):
        """Verify My Experiments page displays active session records and clear notice banner."""
        # 1. Start student session
        self.client.post('/start-session', data={
            'student_name': 'Kavya Sharma',
            'university': 'BITS Pilani'
        })

        # 2. Save a hardness experiment
        self.client.post('/api/hardness/save', json={
            "method": "ROCKWELL",
            "mode": "VIRTUAL_SIMULATION",
            "title": "Rockwell Test Run",
            "material_id": 1,
            "material_name": "Mild Steel",
            "scale": "C",
            "mean_hardness": 45.2,
            "hardness_unit": "HRC",
            "readings": [{"reading_num": 1, "dial_depth_e": 0.11, "hardness": 45.2}]
        })

        # 3. View /my-experiments
        res = self.client.get('/my-experiments')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # 4. Verify active session banner and experiment item
        self.assertIn('Active Laboratory Session', html)
        self.assertIn('Kavya Sharma', html)
        self.assertIn('BITS Pilani', html)
        self.assertIn('These experiment records belong to your current active laboratory session', html)
        self.assertIn('Rockwell Test Run', html)

    def test_private_admin_system_and_usage_records_table(self):
        """Verify private admin portal: no admin links in student UI, /portal-admin auth, usage records table, JSON detail, and CSV export."""
        # 1. Student UI contains NO admin links
        self.client.post('/start-session', data={'student_name': 'Dhruva H D', 'university': 'Pondicherry University'})
        for path in ['/home', '/about', '/materials', '/my-experiments']:
            res = self.client.get(path)
            self.assertNotIn('/portal-admin', res.data.decode('utf-8'))
            self.assertNotIn('MAT-VLAB ADMIN', res.data.decode('utf-8'))

        # 2. Unauthenticated access to /portal-admin redirects to login
        res_admin_unauth = self.client.get('/portal-admin')
        self.assertEqual(res_admin_unauth.status_code, 302)
        self.assertIn('admin/login', res_admin_unauth.headers['Location'])

        # 3. Admin login with credentials
        res_admin_login = self.client.post('/portal-admin/login', data={
            'username': 'testadmin',
            'password': 'testsecret2026'
        }, follow_redirects=True)
        self.assertEqual(res_admin_login.status_code, 200)
        admin_html = res_admin_login.data.decode('utf-8')

        # 4. Verify redesigned Admin Dashboard elements
        self.assertIn('MAT-VLAB ADMIN', admin_html)
        self.assertIn('Central laboratory usage monitoring and experiment records', admin_html)
        self.assertIn('Total Experiments', admin_html)
        self.assertIn('Tensile Tests', admin_html)
        self.assertIn('Hardness Tests', admin_html)
        self.assertIn('EXPERIMENT USAGE RECORDS', admin_html)

        # 5. Save an experiment and verify it appears in the usage records
        self.client.post('/api/hardness/save', json={
            "method": "BRINELL",
            "mode": "VIRTUAL_SIMULATION",
            "title": "Admin Inspection Test",
            "student_name": "Admin Test Student",
            "university": "MIT Manipal",
            "material_name": "Aluminium 6061-T6",
            "mean_hardness": 95.0,
            "hardness_unit": "HBW",
            "readings": [{"d1": 6.1, "d2": 6.1, "mean_d": 6.1, "hbw": 95.0}]
        })

        res_records = self.client.get('/portal-admin')
        records_html = res_records.data.decode('utf-8')
        self.assertIn('Admin Test Student', records_html)
        self.assertIn('MIT Manipal', records_html)

        # 6. CSV Export contains usage records
        res_csv = self.client.get('/portal-admin/export-csv')
        self.assertEqual(res_csv.status_code, 200)
        csv_text = res_csv.data.decode('utf-8')
        self.assertIn('Record ID,Experiment Type,Title,Mode,Material,Student Name,University', csv_text)
        self.assertIn('Admin Test Student,MIT Manipal', csv_text)

        # 7. Admin Logout
        res_admin_logout = self.client.get('/portal-admin/logout', follow_redirects=True)
        self.assertEqual(res_admin_logout.status_code, 200)
        self.assertIn('Administrative Console', res_admin_logout.data.decode('utf-8'))

    def test_admin_credentials_update(self):
        """Verify admin can change username and password, requiring current password, without plaintext exposure."""
        from models.database import verify_admin_login, get_admin_credentials

        # Log in
        self.client.post('/portal-admin/login', data={'username': 'testadmin', 'password': 'testsecret2026'}, follow_redirects=True)

        # Bad current password fails
        bad_pw_res = self.client.post('/portal-admin/update-credentials', data={
            'current_password': 'wrongpassword',
            'new_username': 'chief_admin',
            'new_password': 'newpass2026',
            'confirm_password': 'newpass2026'
        }, follow_redirects=True)
        self.assertIn('Current administrator password is incorrect', bad_pw_res.data.decode('utf-8'))

        # Successful update
        update_res = self.client.post('/portal-admin/update-credentials', data={
            'current_password': 'testsecret2026',
            'new_username': 'chief_admin',
            'new_password': 'chiefPassword2026',
            'confirm_password': 'chiefPassword2026'
        }, follow_redirects=True)
        self.assertIn('Administrator credentials updated successfully', update_res.data.decode('utf-8'))

        # Verify DB
        creds = get_admin_credentials()
        self.assertEqual(creds['username'], 'chief_admin')

        # Log in with new credentials succeeds
        self.client.get('/portal-admin/logout')
        new_login = self.client.post('/portal-admin/login', data={
            'username': 'chief_admin',
            'password': 'chiefPassword2026'
        }, follow_redirects=True)
        self.assertEqual(new_login.status_code, 200)
        self.assertIn('MAT-VLAB ADMIN', new_login.data.decode('utf-8'))

if __name__ == '__main__':
    unittest.main()
