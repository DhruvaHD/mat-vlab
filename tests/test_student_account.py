"""
Student Account System Verification Test Suite
Tests student registration, custom student ID rules (unique, letters/numbers, no spaces, short),
login with Student ID + University (no name entry), and dashboard data retrieval.
"""
import os
import sys
import unittest
import tempfile
import shutil

# Ensure scratch/lib is on sys.path
sys.path.insert(0, '/home/hd/.gemini/antigravity/scratch/lib')
sys.path.insert(0, '/home/hd/Desktop/MATERIAL_PROJECT')

class TestStudentAccountSystem(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.temp_dir, 'test_students.db')
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

        # Valid examples given in specification
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

        # Invalid: Too short (< 3 chars)
        is_valid, msg = validate_student_id('D1')
        self.assertFalse(is_valid)
        self.assertIn("at least 3", msg)

        # Invalid: Too long (> 20 chars)
        is_valid, msg = validate_student_id('DhruvaVeryLongStudentIdentifier12345')
        self.assertFalse(is_valid)
        self.assertIn("20", msg)

    def test_registration_and_uniqueness(self):
        """Verify registration and clear error message when chosen ID is already taken."""
        from models.database import register_student, is_student_id_available

        # 1. Pre-seeded Dhruva01 check
        avail, msg = is_student_id_available('Dhruva01')
        self.assertFalse(avail)
        self.assertEqual(msg, "The Student ID 'Dhruva01' is already taken. Please choose another ID.")

        # 2. Case-insensitive collision check
        avail_lower, msg_lower = is_student_id_available('dhruva01')
        self.assertFalse(avail_lower)
        self.assertIn("already taken", msg_lower)

        # 3. Attempt duplicate registration on taken ID must raise ValueError with clear message
        with self.assertRaises(ValueError) as ctx:
            register_student(
                name='Another Student',
                course='Mechanical Engineering',
                university='Another University',
                student_id='Dhruva01'
            )
        self.assertIn("already taken", str(ctx.exception))

        # 4. Register a new unique student
        st = register_student(
            name='Tanvi Sharma',
            course='B.Tech Materials Science',
            university='Delhi Technological University',
            student_id='Tanvi88'
        )
        self.assertEqual(st['student_id'], 'Tanvi88')
        self.assertEqual(st['name'], 'Tanvi Sharma')
        self.assertEqual(st['course'], 'B.Tech Materials Science')
        self.assertEqual(st['university'], 'Delhi Technological University')

        # Now Tanvi88 is taken
        avail_new, _ = is_student_id_available('Tanvi88')
        self.assertFalse(avail_new)

    def test_login_without_requiring_name(self):
        """Verify login requires ONLY Student ID and University (does NOT require name)."""
        from models.database import authenticate_student

        # 1. Login with pre-seeded Dhruva01 + Pondicherry University (NO NAME)
        student = authenticate_student(student_id='Dhruva01', university='Pondicherry University')
        self.assertIsNotNone(student)
        self.assertEqual(student['name'], 'Dhruva H D')
        self.assertEqual(student['course'], 'B.Tech')
        self.assertEqual(student['university'], 'Pondicherry University')

        # 2. Login with pre-seeded Rahul25 + XYZ University (NO NAME)
        student_rahul = authenticate_student(student_id='Rahul25', university='XYZ University')
        self.assertIsNotNone(student_rahul)
        self.assertEqual(student_rahul['name'], 'Rahul K')
        self.assertEqual(student_rahul['course'], 'B.Tech')
        self.assertEqual(student_rahul['university'], 'XYZ University')

        # 3. Wrong university rejects login
        with self.assertRaises(ValueError) as ctx:
            authenticate_student(student_id='Dhruva01', university='Other College')
        self.assertIn("does not match", str(ctx.exception))

        # 4. Unknown Student ID rejects login
        with self.assertRaises(ValueError) as ctx:
            authenticate_student(student_id='Unknown99', university='Pondicherry University')
        self.assertIn("not found", str(ctx.exception))

    def test_web_routes_registration_and_dashboard_display(self):
        """Verify web registration, session login, and automatic display of student data on dashboard."""
        # 1. Register via Web POST
        res = self.client.post('/register', data={
            'name': 'Arjun Mehta',
            'course': 'B.Tech Mechanical Engineering',
            'university': 'IIT Madras',
            'student_id': 'Arjun99'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        content = res.data.decode('utf-8')

        # Verify student details are automatically retrieved and displayed on the dashboard
        self.assertIn('Arjun Mehta', content)
        self.assertIn('Arjun99', content)
        self.assertIn('B.Tech Mechanical Engineering', content)
        self.assertIn('IIT Madras', content)
        self.assertIn('Active Student Account', content)

        # 2. Log out
        res_logout = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn('logged out', res_logout.data.decode('utf-8'))

        # 3. Log back in with ONLY Student ID and University (NO name)
        res_login = self.client.post('/login', data={
            'student_id': 'Arjun99',
            'university': 'IIT Madras'
        }, follow_redirects=True)

        self.assertEqual(res_login.status_code, 200)
        dashboard_content = res_login.data.decode('utf-8')

        # Verify student details retrieved from account and displayed automatically
        self.assertIn('Arjun Mehta', dashboard_content)
        self.assertIn('Arjun99', dashboard_content)
        self.assertIn('B.Tech Mechanical Engineering', dashboard_content)
        self.assertIn('IIT Madras', dashboard_content)

    def test_api_check_student_id(self):
        """Verify the real-time ID availability endpoint /api/student/check-id."""
        from models.database import register_student
        register_student('Dhruva H D', 'Materials', 'NITK', 'Dhruva123')

        # Check available ID
        res = self.client.get('/api/student/check-id?student_id=AvailableID99')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['available'])
        self.assertIn("available", data['message'].lower())

        # Check taken ID
        res = self.client.get('/api/student/check-id?student_id=Dhruva123')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data['available'])
        self.assertIn("already taken", data['message'])

        # Check ID with spaces
        res = self.client.get('/api/student/check-id?student_id=Dhruva%20123')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data['available'])
        self.assertIn("spaces", data['message'].lower())

    def test_admin_portal_and_students_roster(self):
        """Verify MAT-VLAB ADMIN dashboard, Total Students: 247, and students table."""
        res = self.client.get('/admin')
        self.assertEqual(res.status_code, 200)
        content = res.data.decode('utf-8')

        # 1. Headline & Total Students count
        self.assertIn('MAT-VLAB ADMIN', content)
        self.assertIn('Total Students', content)
        self.assertIn('247', content)

        # 2. Key students from specification
        self.assertIn('Dhruva H D', content)
        self.assertIn('Dhruva01', content)
        self.assertIn('Pondicherry University', content)

        self.assertIn('Rahul K', content)
        self.assertIn('Rahul25', content)
        self.assertIn('XYZ University', content)

        # 3. CSV Roster Export endpoint
        res_csv = self.client.get('/admin/export-csv')
        self.assertEqual(res_csv.status_code, 200)
        csv_text = res_csv.data.decode('utf-8')
        self.assertIn('Student ID,Name,Course,University', csv_text)
        self.assertIn('Dhruva01,Dhruva H D,B.Tech,Pondicherry University', csv_text)
        self.assertIn('Rahul25,Rahul K,B.Tech,XYZ University', csv_text)

        # 4. Search and filter query
        res_search = self.client.get('/admin?q=Dhruva01')
        self.assertEqual(res_search.status_code, 200)
        search_content = res_search.data.decode('utf-8')
        self.assertIn('Dhruva H D', search_content)

if __name__ == '__main__':
    unittest.main()
