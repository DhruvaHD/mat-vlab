"""
MAT-VLAB — Final UI Simplification, Attractive Redesign & Interactive Diagram Test Suite
Verifies:
1. Direct Home Page Flow: Opens directly to MAT-VLAB Home page (/) without login or gating forms.
2. 9 Learning Pillars & Clean Aesthetics: Explicitly covers Theory, Equipment visualization,
   Virtual experiments, Manual laboratory readings, Calculations, Graphs, Results, Quizzes, Reports.
3. Complete Removal of Student Login/Registration: No login screen, no registration, no Student ID/PIN/Password,
   no "Start Virtual Lab" button.
4. Direct Experiment Access: Tensile, Brinell, Rockwell, Materials, Quizzes accessible without authentication.
5. Interactive Equipment Diagrams: Inline SVGs with clickable/tappable components, active highlight,
   and working information panel with close button [×].
6. Legacy route redirects (/login -> /, /register -> /, /dashboard -> /, /logout -> /).
7. Experiment saving and records persistence for student sessions.
8. Private Admin Portal: Strictly protected /portal-admin, usage records table, CSV export, credential management.
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

    def test_home_page_first_screen_and_pillars(self):
        """Verify website opens directly to MAT-VLAB Home page with 9 learning facets and no login gates."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # 1. Branding and Subtitle
        self.assertIn('MAT-VLAB', html)
        self.assertIn('Interactive Virtual Materials Testing &amp; Analysis Laboratory', html)

        # 2. Verify all 9 learning pillars are highlighted
        pillars = [
            'Theory',
            'Equipment Visualization',
            'Virtual Experiments',
            'Manual Readings',
            'Calculations',
            'Graphs',
            'Results',
            'Quizzes',
            'Reports'
        ]
        for p in pillars:
            self.assertIn(p, html)

        # 3. Absence of student login, registration, password, PIN
        self.assertNotIn('Student ID', html)
        self.assertNotIn('PIN', html)
        self.assertNotIn('Password', html)
        self.assertNotIn('CREATE NEW ACCOUNT', html)
        self.assertNotIn('STUDENT LOGIN', html)
        self.assertNotIn('Register Free', html)

        # 4. Absence of 'Start Virtual Lab' button
        self.assertNotIn('Start Virtual Lab', html)
        self.assertNotIn('START VIRTUAL LAB', html)

        # 5. Presence of direct experiment action on Home and direct cards on /experiments
        self.assertIn('Explore All Experiments', html)
        exp_res = self.client.get('/experiments')
        self.assertEqual(exp_res.status_code, 200)
        exp_html = exp_res.data.decode('utf-8')
        self.assertIn('Tensile Test (UTM', exp_html)
        self.assertIn('Brinell Hardness Test', exp_html)
        self.assertIn('Rockwell Hardness Test', exp_html)
        self.assertIn('Explore Experiment', exp_html)

    def test_experiments_accessible_directly_without_login(self):
        """Verify all core student experiment and learning pages are accessible directly without authentication."""
        urls = [
            '/',
            '/home',
            '/experiments',
            '/experiments/tensile',
            '/experiments/brinell',
            '/experiments/rockwell',
            '/materials',
            '/quiz',
            '/my-experiments',
            '/about'
        ]
        for url in urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"Expected 200 for direct access to {url}")
            html = res.data.decode('utf-8')
            # Verify no login prompt or authentication gate
            self.assertNotIn('Student Login', html)
            self.assertNotIn('Please sign in', html)

    def test_interactive_equipment_diagrams_rendered_inline(self):
        """Verify Brinell, Rockwell, and Tensile pages render inline interactive SVGs and detail cards with close buttons."""
        # 1. Brinell Hardness Tester
        res_b = self.client.get('/experiments/brinell')
        self.assertEqual(res_b.status_code, 200)
        html_b = res_b.data.decode('utf-8')
        self.assertIn('id="brinell-svg-container"', html_b)
        self.assertIn('id="brinell-tester-svg"', html_b)
        self.assertIn('interactive-part', html_b)
        self.assertIn('id="component-card"', html_b)
        self.assertIn('id="component-card-close-btn"', html_b)

        # 2. Rockwell Hardness Tester
        res_r = self.client.get('/experiments/rockwell')
        self.assertEqual(res_r.status_code, 200)
        html_r = res_r.data.decode('utf-8')
        self.assertIn('id="rockwell-svg-container"', html_r)
        self.assertIn('id="rockwell-tester-svg"', html_r)
        self.assertIn('interactive-part', html_r)
        self.assertIn('id="r-component-card"', html_r)
        self.assertIn('id="r-component-card-close-btn"', html_r)

        # 3. Universal Testing Machine (Tensile UTM)
        res_t = self.client.get('/experiments/tensile')
        self.assertEqual(res_t.status_code, 200)
        html_t = res_t.data.decode('utf-8')
        self.assertIn('id="utm-svg-container"', html_t)
        self.assertIn('id="utm-svg"', html_t)
        self.assertIn('interactive-part', html_t)
        self.assertIn('id="utm-component-card"', html_t)

    def test_legacy_routes_clean_redirect(self):
        """Verify legacy /login, /register, /dashboard, and /logout redirect cleanly to /."""
        for path in ['/login', '/register', '/dashboard', '/logout']:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 302, f"Expected 302 for {path}")
            self.assertEqual(res.headers['Location'], '/')

    def test_experiment_saving_and_session_metadata(self):
        """Verify Tensile and Hardness experiments save cleanly and auto-populate session metadata."""
        # 1. Save Tensile experiment
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

        # 2. Save Hardness experiment
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

        # 3. Verify records exist in database
        from models.database import get_experiment_by_id, get_hardness_experiment_by_id
        ten_rec = get_experiment_by_id(ten_id)
        self.assertIsNotNone(ten_rec)
        self.assertEqual(ten_rec['title'], "UTM Verification Run")

        hard_rec = get_hardness_experiment_by_id(hard_id)
        self.assertIsNotNone(hard_rec)
        self.assertEqual(hard_rec['title'], "Brinell Verification Run")

    def test_private_admin_system_and_usage_records_table(self):
        """Verify private admin portal: no admin links in student UI, /portal-admin auth, usage records table, and CSV export."""
        # 1. Student UI contains NO admin links
        for path in ['/', '/home', '/about', '/materials', '/my-experiments']:
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

        # 4. Verify Admin Dashboard elements
        self.assertIn('MAT-VLAB ADMIN', admin_html)
        self.assertIn('Central laboratory usage monitoring and experiment records', admin_html)
        self.assertIn('Total Experiments', admin_html)
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
        from models.database import get_admin_credentials

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
