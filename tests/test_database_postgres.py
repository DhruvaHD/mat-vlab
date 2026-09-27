"""
Unit Tests for MAT-VLAB Dual PostgreSQL/SQLite Database Engine & Admin Login Recovery
Tests:
1. Placeholder conversion (SQLite ? to PostgreSQL %s)
2. PgRow dict-like and index-based access
3. PgCursor adapter and RETURNING id handling
4. PostgreSQL URL normalization (postgres:// -> postgresql://)
5. Admin authentication with ADMIN_PASSWORD_HASH environment variable
6. Admin authentication with ADMIN_PASSWORD environment variable
7. Admin UI credential updating
8. Student unique registration error handling across SQLite and PostgreSQL
"""
import os
import sys
import unittest
import tempfile
import shutil
from unittest.mock import MagicMock

# Configure paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SCRATCH_LIB = os.path.abspath(os.path.join(BASE_DIR, '..', 'lib'))
if os.path.exists(SCRATCH_LIB) and SCRATCH_LIB not in sys.path:
    sys.path.insert(0, SCRATCH_LIB)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from werkzeug.security import generate_password_hash
from models.database import (
    convert_sql_placeholders,
    PgRow,
    PgCursor,
    PgConnection,
    get_database_url,
    is_postgres,
    verify_admin_login,
    get_admin_credentials,
    update_admin_credentials,
    register_student,
    init_db
)

class TestDatabasePostgresAbstraction(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.temp_dir, 'test_pg_materials.db')
        os.environ['DATABASE_PATH'] = self.test_db
        # Ensure DATABASE_URL is not set for SQLite tests
        self.old_db_url = os.environ.pop('DATABASE_URL', None)
        self.old_admin_user = os.environ.pop('ADMIN_USERNAME', None)
        self.old_admin_pass = os.environ.pop('ADMIN_PASSWORD', None)
        self.old_admin_hash = os.environ.pop('ADMIN_PASSWORD_HASH', None)
        init_db()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        if self.old_db_url is not None:
            os.environ['DATABASE_URL'] = self.old_db_url
        else:
            os.environ.pop('DATABASE_URL', None)

        if self.old_admin_user is not None:
            os.environ['ADMIN_USERNAME'] = self.old_admin_user
        else:
            os.environ.pop('ADMIN_USERNAME', None)

        if self.old_admin_pass is not None:
            os.environ['ADMIN_PASSWORD'] = self.old_admin_pass
        else:
            os.environ.pop('ADMIN_PASSWORD', None)

        if self.old_admin_hash is not None:
            os.environ['ADMIN_PASSWORD_HASH'] = self.old_admin_hash
        else:
            os.environ.pop('ADMIN_PASSWORD_HASH', None)

    def test_sql_placeholder_conversion(self):
        """Verify ? placeholders convert to %s in SQL, preserving string literals."""
        # Simple query
        sql1 = "SELECT * FROM students WHERE student_id = ? AND course = ?"
        self.assertEqual(
            convert_sql_placeholders(sql1),
            "SELECT * FROM students WHERE student_id = %s AND course = %s"
        )

        # Query with question mark inside a string literal
        sql2 = "SELECT * FROM quiz_questions WHERE question = 'What is the young\\'s modulus?' AND id = ?"
        # In SQL, string literals are delimited by single quotes
        sql3 = "SELECT * FROM quiz WHERE q = 'Is this true?' AND student_id = ?"
        converted3 = convert_sql_placeholders(sql3)
        self.assertEqual(converted3, "SELECT * FROM quiz WHERE q = 'Is this true?' AND student_id = %s")

    def test_pg_row_semantics(self):
        """Verify PgRow matches sqlite3.Row behavior (case-insensitivity, index access, dict conversion)."""
        description = [
            MagicMock(name='id'),
            MagicMock(name='student_id'),
            MagicMock(name='name'),
            MagicMock(name='course')
        ]
        # Simulate psycopg2 column description where each element has .name or tuple[0]
        desc = [('id',), ('student_id',), ('Name',), ('Course',)]
        values = (42, 'Dhruva01', 'Dhruva H D', 'B.Tech')

        row = PgRow(desc, values)

        # 1. Dict-like string key access (case-insensitive)
        self.assertEqual(row['id'], 42)
        self.assertEqual(row['student_id'], 'Dhruva01')
        self.assertEqual(row['STUDENT_ID'], 'Dhruva01')
        self.assertEqual(row['name'], 'Dhruva H D')
        self.assertEqual(row['NAME'], 'Dhruva H D')
        self.assertEqual(row['course'], 'B.Tech')

        # 2. Tuple integer index access
        self.assertEqual(row[0], 42)
        self.assertEqual(row[1], 'Dhruva01')
        self.assertEqual(row[2], 'Dhruva H D')
        self.assertEqual(row[3], 'B.Tech')

        # 3. .get() method
        self.assertEqual(row.get('student_id'), 'Dhruva01')
        self.assertEqual(row.get('non_existent', 'default_val'), 'default_val')
        self.assertEqual(row.get(1), 'Dhruva01')
        self.assertEqual(row.get(99, 'out_of_bounds'), 'out_of_bounds')

        # 4. Containment check
        self.assertIn('student_id', row)
        self.assertIn('STUDENT_ID', row)
        self.assertIn(0, row)
        self.assertNotIn('unknown_column', row)

        # 5. dict(row) conversion
        d = dict(row)
        self.assertIsInstance(d, dict)
        self.assertEqual(d['id'], 42)
        self.assertEqual(d['student_id'], 'Dhruva01')

    def test_pg_cursor_insert_lastrowid_handling(self):
        """Verify PgCursor automatically appends RETURNING id on INSERT and populates lastrowid."""
        mock_raw_cursor = MagicMock()
        mock_raw_cursor.fetchone.return_value = (101,)
        mock_raw_cursor.description = [('id',)]

        pg_cur = PgCursor(mock_raw_cursor)
        pg_cur.execute("INSERT INTO students (student_id, name) VALUES (?, ?)", ('Hardness01', 'Tester'))

        # Check that RETURNING id was appended and %s used
        executed_sql = mock_raw_cursor.execute.call_args[0][0]
        executed_params = mock_raw_cursor.execute.call_args[0][1]

        self.assertIn("RETURNING id", executed_sql)
        self.assertIn("%s", executed_sql)
        self.assertNotIn("?", executed_sql)
        self.assertEqual(executed_params, ('Hardness01', 'Tester'))
        self.assertEqual(pg_cur.lastrowid, 101)

    def test_database_url_normalization(self):
        """Verify postgres:// is normalized to postgresql:// for SQLAlchemy/psycopg2."""
        os.environ['DATABASE_URL'] = 'postgres://testuser:secret@localhost:5432/testdb'
        self.assertEqual(
            get_database_url(),
            'postgresql://testuser:secret@localhost:5432/testdb'
        )
        self.assertTrue(is_postgres())

        os.environ['DATABASE_URL'] = 'postgresql://testuser:secret@localhost:5432/testdb'
        self.assertEqual(
            get_database_url(),
            'postgresql://testuser:secret@localhost:5432/testdb'
        )
        self.assertTrue(is_postgres())

        del os.environ['DATABASE_URL']
        self.assertIsNone(get_database_url())
        self.assertFalse(is_postgres())

    def test_admin_login_with_env_password_hash(self):
        """Verify forgotten admin login can be overridden with ADMIN_PASSWORD_HASH."""
        # Set environment variables for admin
        os.environ['ADMIN_USERNAME'] = 'cloud_admin'
        raw_pass = 'SecretPass2026!'
        pass_hash = generate_password_hash(raw_pass)
        os.environ['ADMIN_PASSWORD_HASH'] = pass_hash

        # Attempt login with correct password
        success, msg = verify_admin_login('cloud_admin', raw_pass)
        self.assertTrue(success, f"Expected login success, got: {msg}")

        # Attempt login with incorrect password
        success_bad, msg_bad = verify_admin_login('cloud_admin', 'WrongPassword')
        self.assertFalse(success_bad)
        self.assertIn("Invalid", msg_bad)

        # Check get_admin_credentials returns active username
        creds = get_admin_credentials()
        self.assertIsNotNone(creds)
        self.assertEqual(creds['username'], 'cloud_admin')

    def test_admin_login_with_env_plain_password(self):
        """Verify forgotten admin login can be overridden with ADMIN_PASSWORD."""
        os.environ['ADMIN_USERNAME'] = 'master_admin'
        os.environ['ADMIN_PASSWORD'] = 'SimplePass999'
        init_db()

        success, msg = verify_admin_login('master_admin', 'SimplePass999')
        self.assertTrue(success, f"Expected login success, got: {msg}")

        success_bad, _ = verify_admin_login('master_admin', 'Wrong')
        self.assertFalse(success_bad)

    def test_admin_update_credentials_via_ui(self):
        """Verify updating credentials updates the database credentials."""
        # Default credentials
        success, _ = update_admin_credentials('new_admin_user', 'new_secure_pass_2026', current_password='matvlab_admin_2024')
        self.assertTrue(success)

        # Verify old password fails
        old_success, _ = verify_admin_login('new_admin_user', 'matvlab_admin_2024')
        self.assertFalse(old_success)

        # Verify new password succeeds
        new_success, _ = verify_admin_login('new_admin_user', 'new_secure_pass_2026')
        self.assertTrue(new_success)

    def test_student_duplicate_id_error_handling(self):
        """Verify unique student ID validation rejects duplicates gracefully."""
        st1 = register_student('Dhruva H D', 'B.Tech', 'Pondicherry University', 'UniqueStudent01', '1234')
        self.assertEqual(st1['student_id'], 'UniqueStudent01')

        # Attempt duplicate registration
        with self.assertRaises(ValueError) as ctx:
            register_student('Another Name', 'B.Tech', 'XYZ University', 'UniqueStudent01', '5678')
        self.assertIn("already taken", str(ctx.exception).lower())

if __name__ == '__main__':
    unittest.main()
