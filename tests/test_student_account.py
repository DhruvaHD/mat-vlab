"""
Comprehensive MAT-VLAB Student Authentication & Private Admin Test Suite
Verifies:
1. First Page Authentication Landing (no direct access to Home until login)
2. Main Laboratory Navigation hidden until login
3. Student Registration with Course dropdown, College, custom Student ID, and 4-6 digit PIN hashing
4. Post-Registration Confirmation Screen (Name, Student ID, Course, University, LOGIN button)
5. Student Login with Student ID + PIN (no name required, auto-retrieves student details)
6. Login Activity & Timestamp Recording
7. Protected Laboratory Routes (@login_required)
8. Student Dashboard (Welcome name, Course, University, Student ID, 5 stats, 5 buttons)
9. Educational Activity Logging (EXPERIMENT_START, EXPERIMENT_SAVE, QUIZ_ATTEMPT, REPORT_DOWNLOAD)
10. Private Admin System (no admin links on student pages, /portal-admin auth, roster & CSV export)
"""
import os
import sys
import unittest
import tempfile
import shutil
import re

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

from werkzeug.security import check_password_hash

class TestStudentAuthAndPrivateAdmin(unittest.TestCase):

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

    def test_student_id_validation_rules(self):
        """Verify student ID formatting rules: letters + numbers, no spaces, 3-20 chars."""
        from models.database import validate_student_id

        # Valid examples
        for valid_id in ['Dhruva01', 'Dhruva123', 'Sindhu07', 'Rahul25', 'MAT2026', 'student1']:
            is_valid, msg = validate_student_id(valid_id)
            self.assertTrue(is_valid, f"Expected {valid_id} to be valid, got: {msg}")

        # Invalid: Contains spaces
        for space_id in ['Dhruva 01', 'Dhruva 123', ' Rahul25', 'Sindhu07 ']:
            is_valid, msg = validate_student_id(space_id)
            self.assertFalse(is_valid, f"Expected {space_id} to be rejected for spaces")
            self.assertIn("space", msg.lower())

        # Invalid: Special characters
        for special_id in ['Dhruva@01', 'Dhruva-123', 'Rahul_25', 'user#1']:
            is_valid, msg = validate_student_id(special_id)
            self.assertFalse(is_valid, f"Expected {special_id} to be rejected for special characters")

        # Invalid: Length constraints (< 3 chars or > 20 chars)
        self.assertFalse(validate_student_id('D1')[0])
        self.assertFalse(validate_student_id('DhruvaVeryLongStudentIdentifier12345')[0])

    def test_registration_with_pin_hashing_and_uniqueness(self):
        """Verify student registration securely hashes the 4-6 digit PIN and enforces unique ID."""
        from models.database import register_student, is_student_id_available, get_db_connection

        # Register Dhruva01 with 4-digit PIN '1234'
        st = register_student(
            name='Dhruva H D',
            course='B.Tech / B.E.',
            university='Pondicherry University',
            student_id='Dhruva01',
            pin='1234'
        )
        self.assertEqual(st['student_id'], 'Dhruva01')
        self.assertEqual(st['name'], 'Dhruva H D')
        self.assertEqual(st['course'], 'B.Tech / B.E.')
        self.assertEqual(st['university'], 'Pondicherry University')

        # Verify PIN is hashed in database and NOT plain text
        conn = get_db_connection()
        row = conn.execute("SELECT pin_hash FROM students WHERE student_id = 'Dhruva01'").fetchone()
        conn.close()
        self.assertIsNotNone(row['pin_hash'])
        self.assertNotEqual(row['pin_hash'], '1234')
        self.assertTrue(check_password_hash(row['pin_hash'], '1234'))

        # Check duplicate ID rejection
        avail, msg = is_student_id_available('Dhruva01')
        self.assertFalse(avail)
        self.assertIn("already taken", msg)

        with self.assertRaises(ValueError) as ctx:
            register_student('Another Person', 'M.Tech / M.E.', 'Another Uni', 'Dhruva01', '5678')
        self.assertIn("already taken", str(ctx.exception))

        # Check PIN validation (must be 4-6 numeric digits)
        with self.assertRaises(ValueError) as ctx:
            register_student('Invalid PIN User', 'B.Tech', 'Uni', 'ValidID99', '12')  # too short
        self.assertIn("4 to 6 digits", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            register_student('Invalid PIN User 2', 'B.Tech', 'Uni', 'ValidID88', '1234567')  # too long
        self.assertIn("4 to 6 digits", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            register_student('Invalid PIN User 3', 'B.Tech', 'Uni', 'ValidID77', 'abcd')  # non-numeric
        self.assertIn("4 to 6 digits", str(ctx.exception))

    def test_login_with_pin_and_activity_tracking(self):
        """Verify login requires ONLY Student ID and PIN, records login activity, and updates timestamp."""
        from models.database import register_student, authenticate_student, get_db_connection

        register_student(
            name='Sindhu K',
            course='B.Tech / B.E.',
            university='NIT Karnataka',
            student_id='Sindhu07',
            pin='5678'
        )

        # 1. Login with Student ID + PIN (no name)
        student = authenticate_student(
            student_id='Sindhu07',
            pin='5678',
            ip_address='192.168.1.100',
            user_agent='TestBrowser/1.0'
        )
        self.assertIsNotNone(student)
        self.assertEqual(student['name'], 'Sindhu K')
        self.assertEqual(student['course'], 'B.Tech / B.E.')
        self.assertEqual(student['university'], 'NIT Karnataka')

        # 2. Check login_activity table recording
        conn = get_db_connection()
        activity = conn.execute("SELECT * FROM login_activity WHERE student_id = 'Sindhu07'").fetchone()
        self.assertIsNotNone(activity)
        self.assertEqual(activity['ip_address'], '192.168.1.100')
        self.assertEqual(activity['user_agent'], 'TestBrowser/1.0')

        # 3. Check last_login_at in students table
        st_row = conn.execute("SELECT last_login_at FROM students WHERE student_id = 'Sindhu07'").fetchone()
        conn.close()
        self.assertIsNotNone(st_row['last_login_at'])

        # 4. Wrong PIN rejection
        with self.assertRaises(ValueError) as ctx:
            authenticate_student(student_id='Sindhu07', pin='9999')
        self.assertIn("Invalid", str(ctx.exception))

        # 5. Unknown Student ID rejection
        with self.assertRaises(ValueError) as ctx:
            authenticate_student(student_id='NonExistentID', pin='5678')
        self.assertIn("not found", str(ctx.exception))

    def test_first_page_auth_landing_and_route_protection(self):
        """Verify first page is authentication landing, lab nav is hidden, and lab routes require login."""
        # 1. Visiting '/' unauthenticated shows the professional landing page
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        content = res.data.decode('utf-8')

        self.assertIn('MAT-VLAB', content)
        self.assertIn('Interactive Virtual Materials Testing & Analysis Laboratory', content)
        self.assertIn('Learn. Simulate. Experiment. Analyze.', content)
        self.assertIn('STUDENT LOGIN', content)
        self.assertIn('CREATE NEW ACCOUNT', content)

        # 2. Main laboratory navigation must NOT be visible when unauthenticated
        self.assertNotIn('href="/simulation"', content)
        self.assertNotIn('href="/manual"', content)
        self.assertNotIn('href="/experiments"', content)
        self.assertNotIn('href="/materials"', content)

        # 3. Accessing laboratory routes unauthenticated must redirect to /login
        for protected_path in ['/dashboard', '/experiments', '/simulation', '/manual', '/materials', '/compare', '/my-experiments', '/quizzes', '/about']:
            res_prot = self.client.get(protected_path)
            self.assertEqual(res_prot.status_code, 302, f"Expected 302 redirect for unauthenticated {protected_path}")
            self.assertIn('/login', res_prot.headers['Location'])

    def test_registration_confirmation_screen_and_login_flow(self):
        """Verify web registration shows confirmation screen and subsequent login retrieves full details."""
        # 1. Register through web POST form
        res = self.client.post('/register', data={
            'name': 'Rahul K',
            'course': 'B.Tech / B.E.',
            'university': 'XYZ University',
            'student_id': 'Rahul25',
            'pin': '4321'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        confirm_content = res.data.decode('utf-8')

        # Verify confirmation screen displays all student details and [ LOGIN ] button
        self.assertIn('Rahul K', confirm_content)
        self.assertIn('Rahul25', confirm_content)
        self.assertIn('B.Tech / B.E.', confirm_content)
        self.assertIn('XYZ University', confirm_content)
        self.assertIn('LOGIN TO MAT-VLAB', confirm_content)

        # 2. Login with Student ID and PIN (NO name required)
        res_login = self.client.post('/login', data={
            'student_id': 'Rahul25',
            'pin': '4321'
        }, follow_redirects=True)

        self.assertEqual(res_login.status_code, 200)
        dash_content = res_login.data.decode('utf-8')

        # 3. Dashboard displays student name, course, university, and ID automatically
        self.assertIn('Welcome, Rahul K!', dash_content)
        self.assertIn('Rahul25', dash_content)
        self.assertIn('B.Tech / B.E.', dash_content)
        self.assertIn('XYZ University', dash_content)

        # 4. Check all 5 required dashboard buttons
        self.assertIn('START VIRTUAL LAB', dash_content)
        self.assertIn('EXPERIMENTS', dash_content)
        self.assertIn('MATERIALS', dash_content)
        self.assertIn('QUIZZES', dash_content)
        self.assertIn('MY EXPERIMENTS', dash_content)

        # 5. Check all 5 required statistics
        self.assertIn('Experiments Completed', dash_content)
        self.assertIn('Virtual Experiments', dash_content)
        self.assertIn('Manual Experiments', dash_content)
        self.assertIn('Quiz Attempts', dash_content)
        self.assertIn('Saved Experiments', dash_content)

        # 6. Now authenticated: visiting '/' redirects to '/dashboard'
        res_index = self.client.get('/')
        self.assertEqual(res_index.status_code, 302)
        self.assertIn('/dashboard', res_index.headers['Location'])

    def test_activity_logging_system(self):
        """Verify educational activity logs for EXPERIMENT_START, EXPERIMENT_SAVE, QUIZ_ATTEMPT, REPORT_DOWNLOAD."""
        from models.database import register_student, get_db_connection

        register_student('Arjun M', 'B.Tech / B.E.', 'IIT Madras', 'Arjun99', '2026')

        # Log in student
        self.client.post('/login', data={'student_id': 'Arjun99', 'pin': '2026'}, follow_redirects=True)

        # 1. Trigger EXPERIMENT_START via /simulation
        self.client.get('/simulation')

        # 2. Trigger EXPERIMENT_SAVE via /api/save
        save_payload = {
            "title": "Tensile Verification Run",
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
        res_save = self.client.post('/api/save', json=save_payload)
        self.assertEqual(res_save.status_code, 200)
        exp_id = res_save.get_json()['experiment_id']

        # 3. Trigger QUIZ_ATTEMPT via /api/quiz/submit
        res_quiz = self.client.post('/api/quiz/submit', json={
            "experiment_id": exp_id,
            "experiment_type": "tensile",
            "score": 9,
            "total_questions": 10
        })
        self.assertEqual(res_quiz.status_code, 200)

        # 4. Trigger REPORT_DOWNLOAD via /api/download-report/<id>
        res_rep = self.client.get(f'/api/download-report/{exp_id}')
        self.assertEqual(res_rep.status_code, 200)

        # Verify activity_logs table in database
        conn = get_db_connection()
        logs = conn.execute("SELECT activity_type FROM activity_logs WHERE student_id = 'Arjun99'").fetchall()
        conn.close()

        act_types = [l['activity_type'] for l in logs]
        self.assertIn('EXPERIMENT_START', act_types)
        self.assertIn('EXPERIMENT_SAVE', act_types)
        self.assertIn('QUIZ_ATTEMPT', act_types)
        self.assertIn('REPORT_DOWNLOAD', act_types)

    def test_private_admin_system_and_no_admin_links_in_student_ui(self):
        """Verify strict private admin: no admin links in student UI, /portal-admin protected with auth."""
        from models.database import register_student
        register_student('Dhruva H D', 'B.Tech / B.E.', 'Pondicherry University', 'Dhruva01', '1234')

        # 1. Log in as student
        res_stud = self.client.post('/login', data={'student_id': 'Dhruva01', 'pin': '1234'}, follow_redirects=True)
        student_ui = res_stud.data.decode('utf-8')

        # Verify NO Admin link anywhere in student UI
        self.assertNotIn('/admin', student_ui)
        self.assertNotIn('/portal-admin', student_ui)
        self.assertNotIn('Admin Portal', student_ui)
        self.assertNotIn('MAT-VLAB Admin', student_ui)

        # 2. Check footer and other pages do NOT contain admin links
        for page in ['/about', '/materials', '/quizzes', '/my-experiments']:
            content = self.client.get(page).data.decode('utf-8')
            self.assertNotIn('MAT-VLAB Admin', content)
            self.assertNotIn('/portal-admin', content)

        # 3. Unauthenticated access to /portal-admin redirects to /portal-admin/login
        res_admin_unauth = self.client.get('/portal-admin')
        self.assertEqual(res_admin_unauth.status_code, 302)
        self.assertIn('admin/login', res_admin_unauth.headers['Location'])

        # 4. Log in with admin credentials
        res_admin_login = self.client.post('/portal-admin/login', data={
            'username': 'testadmin',
            'password': 'testsecret2026'
        }, follow_redirects=True)
        self.assertEqual(res_admin_login.status_code, 200)
        admin_dashboard = res_admin_login.data.decode('utf-8')

        # 5. Admin dashboard contains required administrative telemetry
        self.assertIn('MAT-VLAB ADMIN', admin_dashboard)
        self.assertIn('Total Students', admin_dashboard)
        self.assertIn('Dhruva01', admin_dashboard)
        self.assertIn('Dhruva H D', admin_dashboard)
        self.assertIn('Pondicherry University', admin_dashboard)
        self.assertTrue('Institution &amp; Degree Cohorts' in admin_dashboard or 'Institution & Degree Cohorts' in admin_dashboard)

        # 6. CSV Roster Export
        res_csv = self.client.get('/portal-admin/export-csv')
        self.assertEqual(res_csv.status_code, 200)
        csv_text = res_csv.data.decode('utf-8')
        self.assertIn('Student ID,Name,Course,University', csv_text)
        self.assertIn('Dhruva01,Dhruva H D,B.Tech / B.E.,Pondicherry University', csv_text)

        # 7. Admin Logout
        res_logout = self.client.get('/portal-admin/logout', follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn('Administrative Console', res_logout.data.decode('utf-8'))

    def test_no_examples_in_login_or_create_page(self):
        """Verify that login and create account pages do NOT show any examples in placeholders, buttons, or suggestions."""
        # 1. Check Register Page
        res_reg = self.client.get('/register')
        self.assertEqual(res_reg.status_code, 200)
        reg_html = res_reg.data.decode('utf-8')

        self.assertNotIn('e.g.', reg_html)
        self.assertNotIn('Dhruva01', reg_html)
        self.assertNotIn('Rahul25', reg_html)
        self.assertNotIn('Sindhu07', reg_html)
        self.assertNotIn('example-id-btn', reg_html)
        self.assertNotIn('universitySuggestions', reg_html)

        # 2. Check Login Page
        res_login = self.client.get('/login')
        self.assertEqual(res_login.status_code, 200)
        login_html = res_login.data.decode('utf-8')

        self.assertNotIn('e.g.', login_html)
        self.assertNotIn('Dhruva01', login_html)
        self.assertNotIn('Rahul25', login_html)
        self.assertNotIn('Sindhu07', login_html)

if __name__ == '__main__':
    unittest.main()
