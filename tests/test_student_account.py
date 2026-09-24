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

        # 1. Register Dhruva01
        st = register_student(
            name='Dhruva H D',
            course='B.Tech Materials Science & Technology',
            university='National Institute of Technology',
            student_id='Dhruva01'
        )
        self.assertEqual(st['student_id'], 'Dhruva01')
        self.assertEqual(st['name'], 'Dhruva H D')
        self.assertEqual(st['course'], 'B.Tech Materials Science & Technology')
        self.assertEqual(st['university'], 'National Institute of Technology')

        # 2. Availability check on taken ID
        avail, msg = is_student_id_available('Dhruva01')
        self.assertFalse(avail)
        self.assertEqual(msg, "The Student ID 'Dhruva01' is already taken. Please choose another ID.")

        # 3. Case-insensitive collision check
        avail_lower, msg_lower = is_student_id_available('dhruva01')
        self.assertFalse(avail_lower)
        self.assertIn("already taken", msg_lower)

        # 4. Attempt duplicate registration must raise ValueError with clear message
        with self.assertRaises(ValueError) as ctx:
            register_student(
                name='Another Student',
                course='Mechanical Engineering',
                university='Another University',
                student_id='Dhruva01'
            )
        self.assertIn("already taken", str(ctx.exception))

    def test_login_without_requiring_name(self):
        """Verify login requires ONLY Student ID and University (does NOT require name)."""
        from models.database import register_student, authenticate_student

        # Register Sindhu07
        register_student(
            name='Sindhu K',
            course='M.Tech Metallurgical Engineering',
            university='IISc Bangalore',
            student_id='Sindhu07'
        )

        # Login with Student ID + University (NO NAME)
        student = authenticate_student(student_id='Sindhu07', university='IISc Bangalore')
        self.assertIsNotNone(student)
        self.assertEqual(student['name'], 'Sindhu K')
        self.assertEqual(student['course'], 'M.Tech Metallurgical Engineering')
        self.assertEqual(student['university'], 'IISc Bangalore')

        # Wrong university rejects login
        with self.assertRaises(ValueError) as ctx:
            authenticate_student(student_id='Sindhu07', university='Other College')
        self.assertIn("does not match", str(ctx.exception))

        # Unknown Student ID rejects login
        with self.assertRaises(ValueError) as ctx:
            authenticate_student(student_id='Unknown99', university='IISc Bangalore')
        self.assertIn("not found", str(ctx.exception))

    def test_web_routes_registration_and_dashboard_display(self):
        """Verify web registration, session login, and automatic display of student data on dashboard."""
        # 1. Register via Web POST
        res = self.client.post('/register', data={
            'name': 'Rahul Sharma',
            'course': 'B.Tech Mechanical Engineering',
            'university': 'IIT Madras',
            'student_id': 'Rahul25'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        content = res.data.decode('utf-8')

        # Verify student details are automatically retrieved and displayed on the dashboard
        self.assertIn('Rahul Sharma', content)
        self.assertIn('Rahul25', content)
        self.assertIn('B.Tech Mechanical Engineering', content)
        self.assertIn('IIT Madras', content)
        self.assertIn('Active Student Account', content)

        # 2. Log out
        res_logout = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn('logged out', res_logout.data.decode('utf-8'))

        # 3. Log back in with ONLY Student ID and University (NO name)
        res_login = self.client.post('/login', data={
            'student_id': 'Rahul25',
            'university': 'IIT Madras'
        }, follow_redirects=True)

        self.assertEqual(res_login.status_code, 200)
        dashboard_content = res_login.data.decode('utf-8')

        # Verify student details retrieved from account and displayed automatically
        self.assertIn('Rahul Sharma', dashboard_content)
        self.assertIn('Rahul25', dashboard_content)
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

if __name__ == '__main__':
    unittest.main()
