import sqlite3
import json
import os
import re
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

def get_database_path():
    path = os.environ.get('DATABASE_PATH')
    if not path:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, 'materials.db')
    return os.path.abspath(path)

DATABASE_PATH = get_database_path()

def get_database_url():
    """
    Returns normalized PostgreSQL DATABASE_URL if configured.
    Normalizes 'postgres://' to 'postgresql://' for SQLAlchemy/psycopg compatibility.
    """
    url = os.environ.get('DATABASE_URL')
    if url:
        url = url.strip()
        if url.startswith('postgres://'):
            url = 'postgresql://' + url[len('postgres://'):]
        if url:
            return url
    return None

def is_postgres():
    """Returns True if a PostgreSQL DATABASE_URL is configured."""
    return bool(get_database_url())

def convert_sql_placeholders(query: str) -> str:
    """
    Safely converts SQLite '?' parameter placeholders to PostgreSQL '%s'
    while preserving literal question marks inside single-quoted strings.
    """
    parts = []
    in_quote = False
    for char in query:
        if char == "'":
            in_quote = not in_quote
            parts.append(char)
        elif char == '?' and not in_quote:
            parts.append('%s')
        else:
            parts.append(char)
    return ''.join(parts)


class PgRow(dict):
    """
    Row wrapper that supports:
    - Case-insensitive string access: row['column_name']
    - Tuple/integer indexing: row[0], row[1]
    - Direct dict conversion: dict(row)
    - Dictionary methods: get(), keys(), values(), items()
    - Key containment check: 'col' in row
    """
    def __init__(self, description, tuple_row):
        self._col_names = [d[0].lower() if isinstance(d, (list, tuple)) else d.name.lower() for d in description] if description else []
        self._values = tuple_row
        d = {name: val for name, val in zip(self._col_names, tuple_row)} if description else {}
        super().__init__(d)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(str(key).lower())

    def get(self, key, default=None):
        if isinstance(key, int):
            try:
                return self._values[key]
            except IndexError:
                return default
        return super().get(str(key).lower(), default)

    def __contains__(self, key):
        if isinstance(key, int):
            return 0 <= key < len(self._values)
        return super().__contains__(str(key).lower())

    def keys(self):
        return self._col_names


class PgCursor:
    """
    Cursor adapter for PostgreSQL wrapping a raw psycopg2 cursor.
    Translates '?' placeholders to '%s' and intercepts INSERT queries to populate lastrowid via RETURNING id.
    """
    def __init__(self, raw_cursor):
        self._cursor = raw_cursor
        self.lastrowid = None

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def execute(self, sql, params=None):
        adapted_sql = convert_sql_placeholders(sql)
        stripped = adapted_sql.strip()
        is_insert = stripped.upper().startswith("INSERT INTO")
        has_returning = "RETURNING" in stripped.upper()
        
        auto_returning = False
        if is_insert and not has_returning:
            adapted_sql = adapted_sql.rstrip().rstrip(';') + " RETURNING id"
            auto_returning = True

        if params is None:
            self._cursor.execute(adapted_sql)
        else:
            if isinstance(params, (list, tuple)):
                self._cursor.execute(adapted_sql, tuple(params))
            else:
                self._cursor.execute(adapted_sql, params)

        if auto_returning:
            try:
                ret = self._cursor.fetchone()
                if ret is not None:
                    self.lastrowid = ret[0]
            except Exception:
                self.lastrowid = None
        else:
            self.lastrowid = None

        return self

    def executemany(self, sql, seq_of_parameters):
        adapted_sql = convert_sql_placeholders(sql)
        return self._cursor.executemany(adapted_sql, seq_of_parameters)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return PgRow(self._cursor.description, row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []
        desc = self._cursor.description
        return [PgRow(desc, r) for r in rows]

    def fetchmany(self, size=None):
        rows = self._cursor.fetchmany(size) if size is not None else self._cursor.fetchmany()
        if not rows:
            return []
        desc = self._cursor.description
        return [PgRow(desc, r) for r in rows]

    def __iter__(self):
        desc = self._cursor.description
        for r in self._cursor:
            yield PgRow(desc, r)

    def close(self):
        return self._cursor.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class PgConnection:
    """
    Connection adapter for PostgreSQL wrapping a raw psycopg2 connection.
    Implements conn.execute(), conn.cursor(), conn.commit(), conn.rollback(), and conn.close().
    """
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        return PgCursor(self._conn.cursor())

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()


def get_db_connection():
    """
    Returns an active database connection.
    Connects to PostgreSQL if DATABASE_URL is set; otherwise falls back to SQLite.
    """
    pg_url = get_database_url()
    if pg_url:
        try:
            import psycopg2
        except ImportError:
            try:
                import psycopg as psycopg2
            except ImportError:
                raise ImportError(
                    "PostgreSQL DATABASE_URL is configured, but 'psycopg2' (or 'psycopg') is not installed. "
                    "Please ensure 'psycopg2-binary' is in requirements.txt and installed."
                )
        raw_conn = psycopg2.connect(pg_url)
        return PgConnection(raw_conn)
    else:
        db_path = get_database_path()
        parent_dir = os.path.dirname(db_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn


def sync_all_postgres_sequences(pg_conn):
    """
    Synchronizes PostgreSQL auto-increment sequences (SERIAL) to COALESCE(MAX(id), 1)
    to prevent unique key constraint violations after inserting records with explicit IDs.
    """
    tables = [
        'materials', 'students', 'admin_credentials', 'quiz_questions',
        'experiments', 'experiment_readings', 'experiment_results',
        'hardness_experiments', 'hardness_readings', 'quiz_results',
        'login_activity', 'activity_logs'
    ]
    cur = pg_conn.cursor()
    for table in tables:
        try:
            sql = f"""
            SELECT setval(
                pg_get_serial_sequence('{table}', 'id'),
                COALESCE((SELECT MAX(id) FROM {table}), 1)
            )
            """
            cur.execute(sql)
        except Exception:
            pass


def auto_migrate_sqlite_to_postgres_if_empty(pg_conn):
    """
    If PostgreSQL is connected and 'students' table has 0 rows, checks if a local
    SQLite materials.db exists with existing student records.
    If so, automatically copies all existing records into PostgreSQL and synchronizes
    sequences so that production deployments on Render never lose previous student data.
    """
    try:
        cur = pg_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM students")
        pg_student_count = cur.fetchone()[0]
        if pg_student_count > 0:
            return  # Already populated in PostgreSQL; do not overwrite.

        # Look for local SQLite database
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidate_paths = [
            os.environ.get('DATABASE_PATH'),
            os.path.join(base_dir, 'materials.db'),
            os.path.join(base_dir, 'materials_backup.db'),
            '/home/hd/.gemini/antigravity/scratch/materials_backup.db'
        ]
        sqlite_path = None
        for p in candidate_paths:
            if p and os.path.exists(p) and os.path.isfile(p):
                sqlite_path = p
                break

        if not sqlite_path:
            return

        src_conn = sqlite3.connect(sqlite_path)
        src_conn.row_factory = sqlite3.Row
        src_cur = src_conn.cursor()

        src_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='students'")
        if not src_cur.fetchone():
            src_conn.close()
            return
        
        src_cur.execute("SELECT COUNT(*) FROM students")
        src_student_count = src_cur.fetchone()[0]
        if src_student_count == 0:
            src_conn.close()
            return

        print(f"[*] MAT-VLAB Auto-Migration: Migrating {src_student_count} students and experiment data from {sqlite_path} to PostgreSQL...")
        
        tables = [
            'materials', 'students', 'admin_credentials', 'quiz_questions',
            'experiments', 'experiment_readings', 'experiment_results',
            'hardness_experiments', 'hardness_readings', 'quiz_results',
            'login_activity', 'activity_logs'
        ]

        for table in tables:
            src_cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not src_cur.fetchone():
                continue
            
            src_cur.execute(f"SELECT * FROM {table}")
            rows = src_cur.fetchall()
            if not rows:
                continue

            cols = [d[0] for d in src_cur.description]
            col_str = ', '.join([f'"{c}"' for c in cols])
            val_placeholders = ', '.join(['%s' for _ in cols])
            
            for row in rows:
                val_tuple = tuple(row[c] for c in cols)
                cur.execute(f"INSERT INTO {table} ({col_str}) VALUES ({val_placeholders}) ON CONFLICT DO NOTHING", val_tuple)

        sync_all_postgres_sequences(pg_conn)
        pg_conn.commit()
        src_conn.close()
        print("[+] MAT-VLAB Auto-Migration: Successfully migrated student accounts to PostgreSQL!")
    except Exception as e:
        print(f"[!] Warning: Auto-migration to PostgreSQL encountered an issue: {e}")


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    if is_postgres():
        # PostgreSQL Schema Initialization
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            density_g_cm3 DOUBLE PRECISION NOT NULL,
            youngs_modulus_gpa DOUBLE PRECISION NOT NULL,
            yield_strength_mpa DOUBLE PRECISION NOT NULL,
            uts_mpa DOUBLE PRECISION NOT NULL,
            elongation_pct DOUBLE PRECISION NOT NULL,
            reduction_area_pct DOUBLE PRECISION,
            poisson_ratio DOUBLE PRECISION,
            standard_ref TEXT,
            description TEXT,
            applications TEXT,
            is_reference INTEGER DEFAULT 1
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiments (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            experiment_type TEXT NOT NULL,
            mode TEXT NOT NULL,
            material_name TEXT NOT NULL,
            original_diameter DOUBLE PRECISION NOT NULL,
            original_gauge_length DOUBLE PRECISION NOT NULL,
            final_gauge_length DOUBLE PRECISION,
            final_diameter DOUBLE PRECISION,
            notes TEXT,
            student_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiment_readings (
            id SERIAL PRIMARY KEY,
            experiment_id INTEGER NOT NULL REFERENCES experiments (id) ON DELETE CASCADE,
            reading_number INTEGER NOT NULL,
            load_n DOUBLE PRECISION NOT NULL,
            extension_mm DOUBLE PRECISION NOT NULL,
            stress_mpa DOUBLE PRECISION,
            strain DOUBLE PRECISION
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiment_results (
            id SERIAL PRIMARY KEY,
            experiment_id INTEGER UNIQUE NOT NULL REFERENCES experiments (id) ON DELETE CASCADE,
            cross_sectional_area DOUBLE PRECISION NOT NULL,
            youngs_modulus_gpa DOUBLE PRECISION,
            yield_strength_mpa DOUBLE PRECISION,
            uts_mpa DOUBLE PRECISION,
            max_load_n DOUBLE PRECISION,
            elongation_pct DOUBLE PRECISION,
            reduction_area_pct DOUBLE PRECISION,
            modulus_of_resilience_mj_m3 DOUBLE PRECISION,
            toughness_mj_m3 DOUBLE PRECISION,
            conclusion TEXT
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id SERIAL PRIMARY KEY,
            experiment_type TEXT NOT NULL,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option TEXT NOT NULL,
            explanation TEXT NOT NULL,
            difficulty TEXT DEFAULT 'Intermediate'
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_results (
            id SERIAL PRIMARY KEY,
            experiment_id INTEGER REFERENCES experiments (id) ON DELETE SET NULL,
            experiment_type TEXT NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            percentage DOUBLE PRECISION NOT NULL,
            student_id TEXT,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id SERIAL PRIMARY KEY,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            course TEXT NOT NULL,
            university TEXT NOT NULL,
            pin_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS login_activity (
            id SERIAL PRIMARY KEY,
            student_id TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id SERIAL PRIMARY KEY,
            student_id TEXT,
            activity_type TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_credentials (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS hardness_experiments (
            id SERIAL PRIMARY KEY,
            student_id TEXT NOT NULL,
            title TEXT NOT NULL,
            method TEXT NOT NULL,
            mode TEXT NOT NULL,
            material_name TEXT NOT NULL,
            data_origin TEXT NOT NULL,
            parameters_json TEXT,
            mean_hardness DOUBLE PRECISION NOT NULL,
            hardness_unit TEXT NOT NULL,
            num_readings INTEGER NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS hardness_readings (
            id SERIAL PRIMARY KEY,
            experiment_id INTEGER NOT NULL REFERENCES hardness_experiments (id) ON DELETE CASCADE,
            trial_number INTEGER NOT NULL,
            d1_mm DOUBLE PRECISION,
            d2_mm DOUBLE PRECISION,
            mean_d_mm DOUBLE PRECISION,
            depth_mm DOUBLE PRECISION,
            hardness_value DOUBLE PRECISION NOT NULL
        )
        ''')

        cursor.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS pin_hash TEXT")
        cursor.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP")
        cursor.execute("ALTER TABLE experiments ADD COLUMN IF NOT EXISTS student_id TEXT")
        cursor.execute("ALTER TABLE experiments ADD COLUMN IF NOT EXISTS student_name TEXT")
        cursor.execute("ALTER TABLE experiments ADD COLUMN IF NOT EXISTS university TEXT")
        cursor.execute("ALTER TABLE experiments ADD COLUMN IF NOT EXISTS session_id TEXT")
        cursor.execute("ALTER TABLE quiz_results ADD COLUMN IF NOT EXISTS student_id TEXT")
        cursor.execute("ALTER TABLE quiz_results ADD COLUMN IF NOT EXISTS student_name TEXT")
        cursor.execute("ALTER TABLE quiz_results ADD COLUMN IF NOT EXISTS university TEXT")
        cursor.execute("ALTER TABLE quiz_results ADD COLUMN IF NOT EXISTS session_id TEXT")
        cursor.execute("ALTER TABLE hardness_experiments ADD COLUMN IF NOT EXISTS student_name TEXT")
        cursor.execute("ALTER TABLE hardness_experiments ADD COLUMN IF NOT EXISTS university TEXT")
        cursor.execute("ALTER TABLE hardness_experiments ADD COLUMN IF NOT EXISTS session_id TEXT")
        cursor.execute("ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS student_name TEXT")
        cursor.execute("ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS university TEXT")
        cursor.execute("ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS session_id TEXT")

        # Auto-migrate SQLite data if this is a fresh PostgreSQL instance
        auto_migrate_sqlite_to_postgres_if_empty(conn)

    else:
        # SQLite Schema Initialization
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            density_g_cm3 REAL NOT NULL,
            youngs_modulus_gpa REAL NOT NULL,
            yield_strength_mpa REAL NOT NULL,
            uts_mpa REAL NOT NULL,
            elongation_pct REAL NOT NULL,
            reduction_area_pct REAL,
            poisson_ratio REAL,
            standard_ref TEXT,
            description TEXT,
            applications TEXT,
            is_reference INTEGER DEFAULT 1
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            experiment_type TEXT NOT NULL,
            mode TEXT NOT NULL, -- 'VIRTUAL_SIMULATION' or 'MANUAL_ENTRY'
            material_name TEXT NOT NULL,
            original_diameter REAL NOT NULL,
            original_gauge_length REAL NOT NULL,
            final_gauge_length REAL,
            final_diameter REAL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiment_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id INTEGER NOT NULL,
            reading_number INTEGER NOT NULL,
            load_n REAL NOT NULL,
            extension_mm REAL NOT NULL,
            stress_mpa REAL,
            strain REAL,
            FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE CASCADE
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiment_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id INTEGER UNIQUE NOT NULL,
            cross_sectional_area REAL NOT NULL,
            youngs_modulus_gpa REAL,
            yield_strength_mpa REAL,
            uts_mpa REAL,
            max_load_n REAL,
            elongation_pct REAL,
            reduction_area_pct REAL,
            modulus_of_resilience_mj_m3 REAL,
            toughness_mj_m3 REAL,
            conclusion TEXT,
            FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE CASCADE
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_type TEXT NOT NULL,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option TEXT NOT NULL, -- 'A', 'B', 'C', or 'D'
            explanation TEXT NOT NULL,
            difficulty TEXT DEFAULT 'Intermediate'
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id INTEGER,
            experiment_type TEXT NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            percentage REAL NOT NULL,
            student_id TEXT,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE SET NULL
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL COLLATE NOCASE,
            name TEXT NOT NULL,
            course TEXT NOT NULL,
            university TEXT NOT NULL,
            pin_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP
        )
        ''')

        cursor.execute("PRAGMA table_info(students)")
        student_cols = [col['name'] for col in cursor.fetchall()]
        if 'pin_hash' not in student_cols:
            cursor.execute("ALTER TABLE students ADD COLUMN pin_hash TEXT")
        if 'last_login_at' not in student_cols:
            cursor.execute("ALTER TABLE students ADD COLUMN last_login_at TIMESTAMP")

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS login_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            activity_type TEXT NOT NULL, -- 'EXPERIMENT_START', 'EXPERIMENT_SAVE', 'QUIZ_ATTEMPT', 'REPORT_DOWNLOAD'
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute("PRAGMA table_info(experiments)")
        columns = [col['name'] for col in cursor.fetchall()]
        if 'student_id' not in columns:
            cursor.execute("ALTER TABLE experiments ADD COLUMN student_id TEXT")
        if 'student_name' not in columns:
            cursor.execute("ALTER TABLE experiments ADD COLUMN student_name TEXT")
        if 'university' not in columns:
            cursor.execute("ALTER TABLE experiments ADD COLUMN university TEXT")
        if 'session_id' not in columns:
            cursor.execute("ALTER TABLE experiments ADD COLUMN session_id TEXT")

        cursor.execute("PRAGMA table_info(quiz_results)")
        quiz_cols = [col['name'] for col in cursor.fetchall()]
        if 'student_id' not in quiz_cols:
            cursor.execute("ALTER TABLE quiz_results ADD COLUMN student_id TEXT")
        if 'student_name' not in quiz_cols:
            cursor.execute("ALTER TABLE quiz_results ADD COLUMN student_name TEXT")
        if 'university' not in quiz_cols:
            cursor.execute("ALTER TABLE quiz_results ADD COLUMN university TEXT")
        if 'session_id' not in quiz_cols:
            cursor.execute("ALTER TABLE quiz_results ADD COLUMN session_id TEXT")

        cursor.execute("PRAGMA table_info(activity_logs)")
        act_cols = [col['name'] for col in cursor.fetchall()]
        if 'student_name' not in act_cols:
            cursor.execute("ALTER TABLE activity_logs ADD COLUMN student_name TEXT")
        if 'university' not in act_cols:
            cursor.execute("ALTER TABLE activity_logs ADD COLUMN university TEXT")
        if 'session_id' not in act_cols:
            cursor.execute("ALTER TABLE activity_logs ADD COLUMN session_id TEXT")

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS hardness_experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            student_name TEXT,
            university TEXT,
            session_id TEXT,
            title TEXT NOT NULL,
            method TEXT NOT NULL, -- 'BRINELL' or 'ROCKWELL'
            mode TEXT NOT NULL, -- 'VIRTUAL_SIMULATION' or 'MANUAL_ENTRY'
            material_name TEXT NOT NULL,
            data_origin TEXT NOT NULL, -- 'SIMULATION / DEMONSTRATION DATA' or 'USER-ENTERED LABORATORY DATA'
            parameters_json TEXT,
            mean_hardness REAL NOT NULL,
            hardness_unit TEXT NOT NULL, -- 'HBW', 'HRB', 'HRC', 'HRA'
            num_readings INTEGER NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute("PRAGMA table_info(hardness_experiments)")
        h_cols = [col['name'] for col in cursor.fetchall()]
        if 'student_name' not in h_cols:
            cursor.execute("ALTER TABLE hardness_experiments ADD COLUMN student_name TEXT")
        if 'university' not in h_cols:
            cursor.execute("ALTER TABLE hardness_experiments ADD COLUMN university TEXT")
        if 'session_id' not in h_cols:
            cursor.execute("ALTER TABLE hardness_experiments ADD COLUMN session_id TEXT")

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS hardness_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id INTEGER NOT NULL,
            trial_number INTEGER NOT NULL,
            d1_mm REAL,
            d2_mm REAL,
            mean_d_mm REAL,
            depth_mm REAL,
            hardness_value REAL NOT NULL,
            FOREIGN KEY (experiment_id) REFERENCES hardness_experiments (id) ON DELETE CASCADE
        )
        ''')

    # Synchronize Administrator Credentials (works identically on SQLite & PostgreSQL)
    env_user = os.environ.get('ADMIN_USERNAME')
    env_hash = os.environ.get('ADMIN_PASSWORD_HASH')
    env_pass = os.environ.get('ADMIN_PASSWORD')

    cursor.execute('SELECT COUNT(*) as count FROM admin_credentials')
    cred_count = cursor.fetchone()['count']

    if env_user and (env_hash or env_pass):
        final_hash = env_hash if env_hash else generate_password_hash(env_pass)
        if cred_count == 0:
            cursor.execute('INSERT INTO admin_credentials (username, password_hash) VALUES (?, ?)', (env_user.strip(), final_hash))
        else:
            cursor.execute('UPDATE admin_credentials SET username = ?, password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = (SELECT id FROM admin_credentials ORDER BY id ASC LIMIT 1)', (env_user.strip(), final_hash))
    elif cred_count == 0:
        cursor.execute('''
        INSERT INTO admin_credentials (username, password_hash)
        VALUES (?, ?)
        ''', ('admin', generate_password_hash('matvlab_admin_2024')))

    conn.commit()

    # Seed data if tables are empty
    seed_materials(conn)
    seed_quiz_questions(conn)

    conn.close()

def seed_materials(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM materials')
    if cursor.fetchone()['count'] == 0:
        seed_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'materials_seed.json')
        if os.path.exists(seed_file):
            with open(seed_file, 'r') as f:
                materials = json.load(f)
                for m in materials:
                    cursor.execute('''
                    INSERT INTO materials (
                        name, slug, category, density_g_cm3, youngs_modulus_gpa,
                        yield_strength_mpa, uts_mpa, elongation_pct, reduction_area_pct,
                        poisson_ratio, standard_ref, description, applications, is_reference
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        m['name'], m['slug'], m['category'], m['density_g_cm3'],
                        m['youngs_modulus_gpa'], m['yield_strength_mpa'], m['uts_mpa'],
                        m['elongation_pct'], m.get('reduction_area_pct'), m.get('poisson_ratio'),
                        m.get('standard_ref'), m.get('description'), m.get('applications'), m.get('is_reference', 1)
                    ))
            conn.commit()

def seed_quiz_questions(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM quiz_questions')
    if cursor.fetchone()['count'] == 0:
        questions = [
            {
                "experiment_type": "tensile",
                "question": "What cross-sectional area is used to calculate Engineering Stress in a tensile test?",
                "option_a": "Instantaneous cross-sectional area under load",
                "option_b": "Original undeformed cross-sectional area (A₀)",
                "option_c": "Final cross-sectional area at fracture",
                "option_d": "Average of original and final cross-sectional areas",
                "correct_option": "B",
                "explanation": "Engineering stress (nominal stress) is defined strictly as applied load divided by the original undeformed cross-sectional area (σ = P / A₀), unlike True Stress which uses the instantaneous area (σ_T = P / A_i).",
                "difficulty": "Basic"
            },
            {
                "experiment_type": "tensile",
                "question": "Young's modulus (Modulus of Elasticity) represents which fundamental characteristic of a material?",
                "option_a": "Resistance to plastic deformation (Hardness)",
                "option_b": "Maximum load capacity before fracture (Tensile Strength)",
                "option_c": "Atomic bond stiffness / resistance to elastic deformation",
                "option_d": "Total energy absorbed before fracture (Toughness)",
                "correct_option": "C",
                "explanation": "Young's modulus (E = Δσ / Δε) is the slope of the linear elastic region. It reflects interatomic bond strength and measures the elastic stiffness of the material.",
                "difficulty": "Basic"
            },
            {
                "experiment_type": "tensile",
                "question": "For materials like Aluminium alloys that do not show a distinct yield point, how is yield strength conventionally determined?",
                "option_a": "By taking 50% of the Ultimate Tensile Strength",
                "option_b": "Using the 0.2% (0.002) plastic strain offset method",
                "option_c": "By identifying the point of necking inception",
                "option_d": "By extrapolating the fracture stress back to the origin",
                "correct_option": "B",
                "explanation": "In continuous yielding materials without a sharp yield drop (such as aluminum, copper, and austenitic stainless steel), the standard ASTM/ISO procedure is to draw a line parallel to the elastic slope starting at 0.2% (0.002) strain. Its intersection defines the 0.2% proof stress / yield strength.",
                "difficulty": "Intermediate"
            },
            {
                "experiment_type": "tensile",
                "question": "What phenomenon occurs immediately when a ductile tensile specimen reaches its Ultimate Tensile Strength (UTS)?",
                "option_a": "Catastrophic cleavage fracture across crystallographic planes",
                "option_b": "Complete recovery of all accumulated elastic strain",
                "option_c": "Onset of localized necking (non-uniform cross-sectional reduction)",
                "option_d": "Sudden increase in load-bearing cross-sectional area",
                "correct_option": "C",
                "explanation": "At UTS (dσ/dε = σ), the rate of strain hardening can no longer compensate for geometric cross-sectional reduction. Plastic deformation localizes into a 'neck', causing nominal engineering stress to drop until ductile rupture.",
                "difficulty": "Intermediate"
            },
            {
                "experiment_type": "tensile",
                "question": "Which component in a Universal Testing Machine (UTM) is responsible for converting mechanical force into an electrical measurement signal?",
                "option_a": "Extensometer",
                "option_b": "Crosshead lead screw",
                "option_c": "Strain gauge load cell",
                "option_d": "Hydraulic wedge grip",
                "correct_option": "C",
                "explanation": "The load cell houses strain gauge Wheatstone bridges attached to an elastic sensing element. As load is applied, the minute deflection alters electrical resistance proportional to the applied tensile force.",
                "difficulty": "Basic"
            },
            {
                "experiment_type": "tensile",
                "question": "What is the standard fracture morphology typically observed in a ductile cylindrical tensile specimen (e.g., Mild Steel)?",
                "option_a": "Flat, granular cleavage fracture at 90° to the tensile axis",
                "option_b": "Cup-and-cone fracture with central fibrous tear and 45° shear lips",
                "option_c": "Helical spiral fracture along torsion planes",
                "option_d": "Multiple fragmented shattered segments",
                "correct_option": "B",
                "explanation": "Ductile metals fail via void nucleation, growth, and coalescence in the triaxial stress core of the neck, forming a fibrous flat tear, followed by final shear separation along 45° maximum shear planes, yielding the classic 'cup-and-cone' morphology.",
                "difficulty": "Intermediate"
            },
            {
                "experiment_type": "tensile",
                "question": "The total area under the entire engineering stress-strain curve up to the fracture point represents which mechanical property?",
                "option_a": "Modulus of Resilience",
                "option_b": "Tensile Toughness (energy absorbed per unit volume)",
                "option_c": "Hardness number",
                "option_d": "Poisson's Ratio",
                "correct_option": "B",
                "explanation": "The area under the entire stress-strain curve (∫ σ dε) equals the total work or energy absorbed per unit volume before fracture, known as Tensile Toughness (measured in MJ/m³ or J/cm³). The area under only the elastic portion is the Modulus of Resilience.",
                "difficulty": "Advanced"
            },
            {
                "experiment_type": "tensile",
                "question": "Why does the engineering stress-strain curve show a descending curve after UTS, while the True stress-strain curve continues to rise?",
                "option_a": "The material loses atomic bond strength after UTS",
                "option_b": "Engineering stress divides load by constant A₀, ignoring necking shrinkage",
                "option_c": "Extensometers slip after reaching the yield point",
                "option_d": "Friction in the UTM crosshead decreases at higher strains",
                "correct_option": "B",
                "explanation": "Because engineering stress uses fixed A₀, the rapid reduction in the local neck area (A_i) causes the required force to drop, creating an apparent decrease in engineering stress. True stress (P / A_i) continues to climb due to ongoing strain hardening until rupture.",
                "difficulty": "Advanced"
            },
            {
                "experiment_type": "tensile",
                "question": "In ASTM E8 standard cylindrical specimens, what is the standard gauge length-to-diameter ratio (L₀ / d₀)?",
                "option_a": "1 : 1",
                "option_b": "2 : 1",
                "option_c": "4 : 1 or 5 : 1 (typically 50 mm gauge length for 10 mm or 12.5 mm diameter)",
                "option_d": "10 : 1",
                "correct_option": "C",
                "explanation": "ASTM E8 and ISO 6892 specify proportional test specimens with a standard gauge length L₀ = 5 × d₀ (e.g., 50 mm gauge length for a 10 mm diameter or 62.5 mm for 12.5 mm diameter) to ensure comparable percentage elongation results.",
                "difficulty": "Intermediate"
            },
            {
                "experiment_type": "tensile",
                "question": "Which of the following units is equivalent to 1 Megapascal (1 MPa)?",
                "option_a": "1 N / m²",
                "option_b": "1 N / mm²",
                "option_c": "1 kN / cm²",
                "option_d": "10⁶ N / mm²",
                "correct_option": "B",
                "explanation": "1 MPa = 10⁶ Pa = 10⁶ N/m² = 1 N / (10⁻³ m)² = 1 N / mm². This 1 MPa = 1 N/mm² equivalence is standard in materials testing calculations.",
                "difficulty": "Basic"
            }
        ]
        for q in questions:
            cursor.execute('''
            INSERT INTO quiz_questions (
                experiment_type, question, option_a, option_b, option_c, option_d,
                correct_option, explanation, difficulty
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                q['experiment_type'], q['question'], q['option_a'], q['option_b'],
                q['option_c'], q['option_d'], q['correct_option'], q['explanation'], q['difficulty']
            ))
        conn.commit()

    # Seed Brinell and Rockwell quiz questions if not already present
    cursor.execute("SELECT COUNT(*) as count FROM quiz_questions WHERE experiment_type IN ('brinell', 'rockwell')")
    if cursor.fetchone()['count'] == 0:
        hardness_questions = [
            # BRINELL QUESTIONS
            {
                "experiment_type": "brinell",
                "question": "In the Brinell hardness test (ASTM E10 / ISO 6506), what physical parameter is measured to calculate the Brinell Hardness Number (HBW)?",
                "option_a": "Net vertical penetration depth of the indenter under major load",
                "option_b": "Arithmetic mean of two perpendicular indentation diameters (d1 and d2) measured using an optical microscope",
                "option_c": "Time taken for the indenter ball to stop penetrating the specimen",
                "option_d": "Rebound velocity of the tungsten carbide indenter",
                "correct_option": "B",
                "explanation": "Brinell hardness measures the spherical contact area of the impression. The indentation diameter is measured along two perpendicular axes (d1 and d2) using an optical measuring microscope, and the average d is used in the HBW formula.",
                "difficulty": "Basic"
            },
            {
                "experiment_type": "brinell",
                "question": "What indenter is standard in modern Brinell hardness testing according to ASTM E10 and ISO 6506?",
                "option_a": "Diamond square-based pyramid (136° apex angle)",
                "option_b": "Spheroconical diamond cone with 120° included angle",
                "option_c": "Tungsten carbide (WC) spherical ball (typically 10 mm, 5 mm, or 2.5 mm diameter)",
                "option_d": "Hardened sapphire chisel",
                "correct_option": "C",
                "explanation": "Modern ASTM E10 and ISO 6506 designate the test as HBW ('W' standing for Wolfram Carbide / Tungsten Carbide), utilizing precision ground tungsten carbide balls to prevent indenter deformation at higher hardness levels.",
                "difficulty": "Basic"
            },
            {
                "experiment_type": "brinell",
                "question": "Why must the load-to-diameter-squared ratio (P / D²) be maintained constant when testing a given class of alloy in Brinell testing?",
                "option_a": "To maintain geometric similarity of spherical indentations (0.24 <= d/D <= 0.60) and ensure comparable hardness values",
                "option_b": "To prevent electrical short-circuiting in the load cell",
                "option_c": "To ensure the dwell time reaches exactly 60 seconds",
                "option_d": "To convert compressive stress into tensile stress",
                "correct_option": "A",
                "explanation": "Because a spherical indenter is not geometrically self-similar at varying depths, Meyer's law dictates that the ratio P/D² (e.g., 30 for steels, 10 for copper/brass, 5 for aluminium) must be preserved so that the indentation angle and constraint factor remain constant.",
                "difficulty": "Intermediate"
            },
            {
                "experiment_type": "brinell",
                "question": "Which mathematical formula correctly calculates the Brinell Hardness Number (HBW) for load P (kgf), ball diameter D (mm), and mean indentation diameter d (mm)?",
                "option_a": "HBW = P / (pi * D * d)",
                "option_b": "HBW = 2P / [pi * D * (D - sqrt(D² - d²))]",
                "option_c": "HBW = 100 - (d / 0.002)",
                "option_d": "HBW = P / (0.7854 * d²)",
                "correct_option": "B",
                "explanation": "The Brinell formula divides load P by the curved spherical surface area of the indentation cap A = pi*D*h = (pi*D/2)*(D - sqrt(D² - d²)), yielding HBW = 2P / [pi * D * (D - sqrt(D² - d²))].",
                "difficulty": "Intermediate"
            },
            {
                "experiment_type": "brinell",
                "question": "To avoid the 'anvil effect' (where hard support anvil artificially elevates hardness reading), what is the minimum required specimen thickness in a Brinell test?",
                "option_a": "Equal to the indentation diameter (t >= d)",
                "option_b": "At least 8 to 10 times the indentation depth (t >= 8h)",
                "option_c": "Exactly 1.0 mm regardless of load",
                "option_d": "Twice the ball diameter (t >= 2D)",
                "correct_option": "B",
                "explanation": "ASTM E10 mandates that the test piece thickness must be at least 8 times (preferably 10 times) the indentation depth h = (D - sqrt(D² - d²))/2. If the specimen is too thin, the plastic zone reaches the support anvil, distorting the reading.",
                "difficulty": "Advanced"
            },
            {
                "experiment_type": "brinell",
                "question": "Why is the Brinell test specifically preferred over micro-indentation tests when evaluating coarse-grained or heterogeneous metals like Grey Cast Iron?",
                "option_a": "Brinell testing is faster and leaves no visible impression",
                "option_b": "The large 10 mm indenter ball and heavy 3000 kgf load average over multiple grains and graphite flakes, providing a representative bulk hardness",
                "option_c": "Brinell hardness can test materials up to 1000 HBW without indenter damage",
                "option_d": "Brinell tests do not require surface preparation",
                "correct_option": "B",
                "explanation": "Because cast irons contain structural heterogeneities (such as graphite flakes in pearlite/ferrite matrix), a large 10 mm ball produces an impression across multiple constituent phases, yielding a reliable macroscopic average.",
                "difficulty": "Intermediate"
            },
            # ROCKWELL QUESTIONS
            {
                "experiment_type": "rockwell",
                "question": "Unlike the optical diameter measurement in Brinell, how does the Rockwell hardness test determine material hardness?",
                "option_a": "By measuring electrical resistivity under acoustic vibration",
                "option_b": "By measuring the net permanent increase in indentation depth (e) between preliminary minor load and total major load",
                "option_c": "By calculating ultrasonic rebound frequency of an oscillating rod",
                "option_d": "By measuring the mass of metal displaced into a pile-up ridge",
                "correct_option": "B",
                "explanation": "Rockwell testing is a differential-depth indentation method. It measures the net permanent depth increase e = h2 - h0 after removing the major load while maintaining the minor load, enabling direct dial/digital readout without optical imaging.",
                "difficulty": "Basic"
            },
            {
                "experiment_type": "rockwell",
                "question": "In the Rockwell testing cycle, what is the primary purpose of applying the 10 kgf preliminary minor load (F0) prior to zeroing the gauge?",
                "option_a": "To initiate rapid work hardening in the core of the specimen",
                "option_b": "To break through slight surface roughness, mill scale, and seating clearances to establish a reliable depth datum",
                "option_c": "To plastically fracture the surface layer",
                "option_d": "To measure the elastic limit of the indenter",
                "correct_option": "B",
                "explanation": "The 10 kgf minor load seats the indenter firmly through minor surface irregularities, dust, and mechanical play. The depth gauge is zeroed at this datum (h0), drastically improving accuracy on ground industrial surfaces.",
                "difficulty": "Intermediate"
            },
            {
                "experiment_type": "rockwell",
                "question": "Which combination of indenter and total test load defines the Rockwell C scale (HRC) for hardened steels?",
                "option_a": "1/16\" steel ball with 100 kgf total load",
                "option_b": "120° spheroconical diamond Brale cone with 150 kgf total load",
                "option_c": "1/8\" steel ball with 60 kgf total load",
                "option_d": "10 mm tungsten carbide ball with 3000 kgf total load",
                "correct_option": "B",
                "explanation": "Scale C (HRC) utilizes the 120° spheroconical diamond Brale indenter with a 0.2 mm spherical tip radius under a 10 kgf minor load + 140 kgf major load = 150 kgf total load, read on the black dial scale (useful range 20–70 HRC).",
                "difficulty": "Basic"
            },
            {
                "experiment_type": "rockwell",
                "question": "Which indenter and dial scale are specified for Rockwell Scale B (HRB), typically used for brasses and soft steels?",
                "option_a": "1/16\" (1.588 mm) diameter ball indenter, 100 kgf total load, read on the Red scale",
                "option_b": "120° diamond cone, 150 kgf total load, read on the Black scale",
                "option_c": "1/2\" ball indenter, 60 kgf total load, read on the Yellow scale",
                "option_d": "Diamond pyramid indenter, 30 kgf total load",
                "correct_option": "A",
                "explanation": "Rockwell B uses a 1/16\" (1.588 mm) hardened ball indenter under 10 kgf minor + 90 kgf major = 100 kgf total load, evaluated against HRB = 130 - (e / 0.002) on the red scale (useful range 20–100 HRB).",
                "difficulty": "Intermediate"
            },
            {
                "experiment_type": "rockwell",
                "question": "In standard Rockwell scales (A, B, C), each single division (1 unit) on the hardness dial gauge corresponds to what vertical indentation depth penetration?",
                "option_a": "0.100 mm (100 µm)",
                "option_b": "0.010 mm (10 µm)",
                "option_c": "0.002 mm (2 µm)",
                "option_d": "0.0005 mm (0.5 µm)",
                "correct_option": "C",
                "explanation": "According to ASTM E18 / ISO 6508, each scale unit on standard Rockwell testers corresponds precisely to 0.002 mm (2 µm) of vertical indentation depth.",
                "difficulty": "Intermediate"
            },
            {
                "experiment_type": "rockwell",
                "question": "Which of the following is a key operational advantage of the Rockwell test over the Brinell test in industrial quality control?",
                "option_a": "Rockwell testing requires high-power optical microscopes to read indents",
                "option_b": "Rockwell testing produces direct numerical readouts in seconds with minimal surface blemish, suitable for finished parts",
                "option_c": "Rockwell testing can accurately measure coarse grey cast iron",
                "option_d": "Rockwell testing does not require any minor load",
                "correct_option": "B",
                "explanation": "Because Rockwell reads depth automatically via a dial indicator or LVDT sensor, testing takes under 10 seconds without subjective optical diameter measurement. Furthermore, the indentation is tiny compared to a 10 mm Brinell impression, preserving finished component integrity.",
                "difficulty": "Basic"
            }
        ]
        for q in hardness_questions:
            cursor.execute('''
            INSERT INTO quiz_questions (
                experiment_type, question, option_a, option_b, option_c, option_d,
                correct_option, explanation, difficulty
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                q['experiment_type'], q['question'], q['option_a'], q['option_b'],
                q['option_c'], q['option_d'], q['correct_option'], q['explanation'], q['difficulty']
            ))
        conn.commit()

# Material helper functions
def get_all_materials():
    conn = get_db_connection()
    materials = conn.execute('SELECT * FROM materials ORDER BY name ASC').fetchall()
    conn.close()
    return [dict(m) for m in materials]

def get_material_by_slug(slug):
    conn = get_db_connection()
    material = conn.execute('SELECT * FROM materials WHERE slug = ?', (slug,)).fetchone()
    conn.close()
    return dict(material) if material else None

def get_material_by_id(material_id):
    conn = get_db_connection()
    material = conn.execute('SELECT * FROM materials WHERE id = ?', (material_id,)).fetchone()
    conn.close()
    return dict(material) if material else None

# Experiment CRUD functions
def save_experiment(data, student_id=None, student_name=None, university=None, session_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    sid = student_id or data.get('student_id')
    s_name = student_name or data.get('student_name')
    uni = university or data.get('university')
    sess_id = session_id or data.get('session_id')

    cursor.execute('''
    INSERT INTO experiments (
        title, experiment_type, mode, material_name,
        original_diameter, original_gauge_length,
        final_gauge_length, final_diameter, notes,
        student_id, student_name, university, session_id
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('title', 'Tensile Test Experiment'),
        data.get('experiment_type', 'tensile'),
        data.get('mode', 'MANUAL_ENTRY'),
        data.get('material_name', 'Mild Steel'),
        float(data.get('original_diameter', 10.0)),
        float(data.get('original_gauge_length', 50.0)),
        float(data['final_gauge_length']) if data.get('final_gauge_length') else None,
        float(data['final_diameter']) if data.get('final_diameter') else None,
        data.get('notes', ''),
        sid, s_name, uni, sess_id
    ))

    experiment_id = cursor.lastrowid

    # Insert readings
    readings = data.get('readings', [])
    for idx, r in enumerate(readings, start=1):
        cursor.execute('''
        INSERT INTO experiment_readings (
            experiment_id, reading_number, load_n, extension_mm, stress_mpa, strain
        ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            experiment_id,
            idx,
            float(r.get('load_n', 0.0)),
            float(r.get('extension_mm', 0.0)),
            float(r.get('stress_mpa')) if r.get('stress_mpa') is not None else None,
            float(r.get('strain')) if r.get('strain') is not None else None
        ))

    # Insert results
    res = data.get('results', {})
    cursor.execute('''
    INSERT INTO experiment_results (
        experiment_id, cross_sectional_area, youngs_modulus_gpa,
        yield_strength_mpa, uts_mpa, max_load_n, elongation_pct,
        reduction_area_pct, modulus_of_resilience_mj_m3, toughness_mj_m3, conclusion
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        experiment_id,
        float(res.get('cross_sectional_area', 0.0)),
        float(res['youngs_modulus_gpa']) if res.get('youngs_modulus_gpa') is not None else None,
        float(res['yield_strength_mpa']) if res.get('yield_strength_mpa') is not None else None,
        float(res['uts_mpa']) if res.get('uts_mpa') is not None else None,
        float(res['max_load_n']) if res.get('max_load_n') is not None else None,
        float(res['elongation_pct']) if res.get('elongation_pct') is not None else None,
        float(res['reduction_area_pct']) if res.get('reduction_area_pct') is not None else None,
        float(res['modulus_of_resilience_mj_m3']) if res.get('modulus_of_resilience_mj_m3') is not None else None,
        float(res['toughness_mj_m3']) if res.get('toughness_mj_m3') is not None else None,
        res.get('conclusion', '')
    ))

    conn.commit()
    conn.close()
    return experiment_id

def get_experiment_by_id(experiment_id):
    conn = get_db_connection()
    exp = conn.execute('SELECT * FROM experiments WHERE id = ?', (experiment_id,)).fetchone()
    if not exp:
        conn.close()
        return None

    exp_dict = dict(exp)
    readings = conn.execute('SELECT * FROM experiment_readings WHERE experiment_id = ? ORDER BY reading_number ASC', (experiment_id,)).fetchall()
    exp_dict['readings'] = [dict(r) for r in readings]

    result = conn.execute('SELECT * FROM experiment_results WHERE experiment_id = ?', (experiment_id,)).fetchone()
    exp_dict['results'] = dict(result) if result else {}

    quiz = conn.execute('SELECT * FROM quiz_results WHERE experiment_id = ? ORDER BY completed_at DESC LIMIT 1', (experiment_id,)).fetchone()
    exp_dict['quiz'] = dict(quiz) if quiz else None

    conn.close()
    return exp_dict

def get_all_experiments(student_id=None, session_id=None, student_name=None):
    conn = get_db_connection()
    query = '''
    SELECT e.*, r.uts_mpa, r.youngs_modulus_gpa, r.elongation_pct,
           (SELECT COUNT(*) FROM experiment_readings WHERE experiment_id = e.id) as readings_count
    FROM experiments e
    LEFT JOIN experiment_results r ON e.id = r.experiment_id
    WHERE 1=1
    '''
    params = []
    if session_id:
        query += ' AND e.session_id = ?'
        params.append(session_id.strip())
    elif student_id:
        query += ' AND LOWER(e.student_id) = LOWER(?)'
        params.append(student_id.strip())
    elif student_name:
        query += ' AND LOWER(e.student_name) = LOWER(?)'
        params.append(student_name.strip())

    query += ' ORDER BY e.created_at DESC'
    experiments = conn.execute(query, tuple(params)).fetchall()
    conn.close()
    return [dict(e) for e in experiments]

def delete_experiment(experiment_id, student_id=None):
    conn = get_db_connection()
    if student_id:
        # Check ownership
        exp = conn.execute('SELECT id, student_id FROM experiments WHERE id = ?', (experiment_id,)).fetchone()
        if not exp:
            conn.close()
            return False
        if exp['student_id'] and exp['student_id'].lower() != student_id.lower():
            conn.close()
            return False

    conn.execute('DELETE FROM experiment_readings WHERE experiment_id = ?', (experiment_id,))
    conn.execute('DELETE FROM experiment_results WHERE experiment_id = ?', (experiment_id,))
    conn.execute('DELETE FROM quiz_results WHERE experiment_id = ?', (experiment_id,))
    conn.execute('DELETE FROM experiments WHERE id = ?', (experiment_id,))
    conn.commit()
    conn.close()
    return True

# Quiz helpers
def get_quiz_questions(experiment_type='tensile', limit=10):
    conn = get_db_connection()
    questions = conn.execute('''
    SELECT * FROM quiz_questions WHERE experiment_type = ? ORDER BY id ASC LIMIT ?
    ''', (experiment_type, limit)).fetchall()
    conn.close()
    return [dict(q) for q in questions]

def save_quiz_result(experiment_id, experiment_type, score, total_questions, student_id=None, student_name=None, university=None, session_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    pct = round((score / total_questions) * 100.0, 1) if total_questions > 0 else 0.0
    cursor.execute('''
    INSERT INTO quiz_results (experiment_id, experiment_type, score, total_questions, percentage, student_id, student_name, university, session_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (experiment_id, experiment_type, score, total_questions, pct, student_id, student_name, university, session_id))
    result_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return result_id

# ==========================================
# STUDENT ACCOUNT SYSTEM
# ==========================================

def validate_student_id(student_id):
    """
    Validates student ID rules:
    - Unique (checked via is_student_id_available)
    - Allow letters and numbers
    - Do not allow spaces
    - Keep it reasonably short (3 to 20 characters)
    """
    if not student_id or not isinstance(student_id, str):
        return False, "Student ID cannot be empty."

    sid = student_id.strip()
    if ' ' in sid or ' ' in student_id:
        return False, "Spaces are not allowed in Student ID. Use only letters and numbers."

    if not re.match(r'^[a-zA-Z0-9]+$', sid):
        return False, "Student ID can only contain letters and numbers (no spaces or special symbols)."

    if len(sid) < 3:
        return False, "Student ID must be at least 3 characters long."

    if len(sid) > 20:
        return False, "Student ID must be reasonably short (maximum 20 characters)."

    return True, ""

def is_student_id_available(student_id):
    """
    Checks if a student ID is valid and not already taken.
    Returns (bool, message).
    """
    is_valid, err_msg = validate_student_id(student_id)
    if not is_valid:
        return False, err_msg

    sid = student_id.strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM students WHERE LOWER(student_id) = LOWER(?)', (sid,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return False, f"The Student ID '{sid}' is already taken. Please choose another ID."
    return True, f"The Student ID '{sid}' is available!"

def register_student(name, course, university, student_id, pin=None):
    """
    Registers a new student.
    REGISTRATION FIELDS:
    - Name
    - Course
    - University / College
    - Student ID (chosen by student, unique, letters + numbers, no spaces, 3-20 chars)
    - PIN (4-6 digits, hashed securely with werkzeug)
    """
    name = (name or '').strip()
    course = (course or '').strip()
    university = (university or '').strip()
    student_id = (student_id or '').strip()

    if not name:
        raise ValueError("Please enter your Full Name.")
    if not course:
        raise ValueError("Please enter your Course / Degree Program.")
    if not university:
        raise ValueError("Please enter your University / College.")
    if not student_id:
        raise ValueError("Please choose a Student ID.")

    is_avail, msg = is_student_id_available(student_id)
    if not is_avail:
        raise ValueError(msg)

    if pin is not None and str(pin).strip() != '':
        pin_str = str(pin).strip()
        if not re.match(r'^\d{4,6}$', pin_str):
            raise ValueError("Security PIN must be 4 to 6 digits (numbers only).")
        pin_hash = generate_password_hash(pin_str)
    else:
        # Default fallback for programmatic creation if pin omitted
        pin_hash = generate_password_hash('1234')

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO students (student_id, name, course, university, pin_hash)
        VALUES (?, ?, ?, ?, ?)
        ''', (student_id, name, course, university, pin_hash))
        conn.commit()
        cursor.execute('SELECT * FROM students WHERE id = ?', (cursor.lastrowid,))
        student = dict(cursor.fetchone())
        conn.close()
        return student
    except Exception as e:
        conn.close()
        err_msg = str(e).lower()
        if 'unique' in err_msg or 'integrity' in err_msg or 'already exists' in err_msg:
            raise ValueError(f"The Student ID '{student_id}' is already taken. Please choose another ID.")
        raise

def authenticate_student(student_id, pin=None, university=None, ip_address=None, user_agent=None):
    """
    Logs in an existing student using Student ID and 4-6 digit PIN.
    LOGIN FIELDS:
    - Student ID
    - PIN (4-6 digits)
    (Does NOT require student name during login)
    Also supports university verification for backward-compatibility.
    Records login in login_activity and updates last_login_at.
    """
    student_id = (student_id or '').strip()
    if not student_id:
        raise ValueError("Please enter your Student ID.")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students WHERE LOWER(student_id) = LOWER(?)', (student_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise ValueError(f"Student ID '{student_id}' was not found. Please verify your ID or create a free student account.")

    student = dict(row)

    if pin is not None and str(pin).strip() != '':
        pin_str = str(pin).strip()
        if not student.get('pin_hash') or not check_password_hash(student['pin_hash'], pin_str):
            conn.close()
            raise ValueError("Invalid Security PIN. Please enter your correct 4-6 digit PIN.")
    elif university is not None and str(university).strip() != '':
        if student['university'].strip().lower() != str(university).strip().lower():
            conn.close()
            raise ValueError("The University / College entered does not match our records for this Student ID.")
    else:
        conn.close()
        raise ValueError("Please enter your 4-6 digit PIN to log in.")

    # Record login activity
    try:
        cursor.execute('''
        INSERT INTO login_activity (student_id, ip_address, user_agent, login_time)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (student['student_id'], ip_address, user_agent))
    except Exception:
        pass

    # Update last_login_at
    try:
        cursor.execute('''
        UPDATE students SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?
        ''', (student['id'],))
    except Exception:
        pass

    conn.commit()
    conn.close()

    return student

def log_activity(student_id=None, activity_type='GENERAL', details=None, student_name=None, university=None, session_id=None):
    """
    Records student action in activity_logs table:
    EXPERIMENT_START, EXPERIMENT_SAVE, QUIZ_ATTEMPT, REPORT_DOWNLOAD
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO activity_logs (student_id, activity_type, details, student_name, university, session_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (student_id, activity_type, str(details) if details else None, student_name, university, session_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging activity: {e}")

def get_student_by_id(student_id):
    """
    Retrieves student account details by student_id.
    """
    if not student_id:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students WHERE LOWER(student_id) = LOWER(?)', (student_id.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_student_dashboard_stats(student_id):
    """
    Returns summary statistics for a student's dashboard:
    - Experiments Completed (total)
    - Virtual Experiments
    - Manual Experiments
    - Quiz Attempts
    - Saved Experiments
    """
    if not student_id:
        return {
            'total_experiments': 0,
            'simulation_count': 0,
            'manual_count': 0,
            'quiz_attempts': 0,
            'saved_experiments': 0,
            'last_experiment_at': None
        }

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT 
        COUNT(*) as total_experiments,
        SUM(CASE WHEN mode = 'VIRTUAL_SIMULATION' THEN 1 ELSE 0 END) as simulation_count,
        SUM(CASE WHEN mode = 'MANUAL_ENTRY' THEN 1 ELSE 0 END) as manual_count,
        MAX(created_at) as last_experiment_at
    FROM experiments
    WHERE LOWER(student_id) = LOWER(?)
    ''', (student_id.strip(),))
    row = cursor.fetchone()

    cursor.execute('''
    SELECT 
        COUNT(*) as total_experiments,
        SUM(CASE WHEN mode = 'VIRTUAL_SIMULATION' THEN 1 ELSE 0 END) as simulation_count,
        SUM(CASE WHEN mode = 'MANUAL_ENTRY' THEN 1 ELSE 0 END) as manual_count,
        MAX(created_at) as last_experiment_at
    FROM hardness_experiments
    WHERE LOWER(student_id) = LOWER(?)
    ''', (student_id.strip(),))
    h_row = cursor.fetchone()

    cursor.execute('''
    SELECT COUNT(*) as quiz_count
    FROM quiz_results
    WHERE LOWER(student_id) = LOWER(?)
    ''', (student_id.strip(),))
    q_row = cursor.fetchone()
    quiz_attempts = q_row['quiz_count'] if q_row else 0

    conn.close()
    
    t_total = (row['total_experiments'] or 0) if row else 0
    t_sim = (row['simulation_count'] or 0) if row else 0
    t_man = (row['manual_count'] or 0) if row else 0
    t_last = row['last_experiment_at'] if row else None

    h_total = (h_row['total_experiments'] or 0) if h_row else 0
    h_sim = (h_row['simulation_count'] or 0) if h_row else 0
    h_man = (h_row['manual_count'] or 0) if h_row else 0
    h_last = h_row['last_experiment_at'] if h_row else None

    total_exp = t_total + h_total
    sim_count = t_sim + h_sim
    man_count = t_man + h_man
    last_dates = [d for d in [t_last, h_last] if d]
    last_at = max(last_dates) if last_dates else None

    return {
        'total_experiments': total_exp,
        'simulation_count': sim_count,
        'manual_count': man_count,
        'quiz_attempts': quiz_attempts,
        'saved_experiments': total_exp,
        'last_experiment_at': last_at
    }

def get_student_stats(student_id):
    """Alias for backwards compatibility."""
    return get_student_dashboard_stats(student_id)

# ==========================================
# ADMIN & ROSTER MANAGEMENT
# ==========================================

def get_all_students(search_query=None, university=None, course=None):
    """
    Retrieves all registered students with experiment and quiz counts.
    Supports optional search query and university/course filters.
    """
    conn = get_db_connection()
    query = '''
    SELECT s.id, s.student_id, s.name, s.course, s.university, s.created_at, s.last_login_at,
           ((SELECT COUNT(*) FROM experiments WHERE LOWER(student_id) = LOWER(s.student_id)) +
            (SELECT COUNT(*) FROM hardness_experiments WHERE LOWER(student_id) = LOWER(s.student_id))) as experiment_count,
           (SELECT COUNT(*) FROM quiz_results WHERE LOWER(student_id) = LOWER(s.student_id)) as quiz_count
    FROM students s
    WHERE 1=1
    '''
    params = []
    if search_query:
        query += ''' AND (
            s.name LIKE ? OR 
            s.student_id LIKE ? OR 
            s.course LIKE ? OR 
            s.university LIKE ?
        )'''
        term = f"%{search_query.strip()}%"
        params.extend([term, term, term, term])

    if university and university.strip() and university.strip() != 'ALL':
        query += " AND s.university = ?"
        params.append(university.strip())

    if course and course.strip() and course.strip() != 'ALL':
        query += " AND s.course = ?"
        params.append(course.strip())

    query += " ORDER BY s.id ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_admin_stats():
    """
    Returns administrative summary statistics for MAT-VLAB ADMIN.
    """
    conn = get_db_connection()
    
    total_students = conn.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    total_universities = conn.execute('SELECT COUNT(DISTINCT university) FROM students').fetchone()[0]
    total_courses = conn.execute('SELECT COUNT(DISTINCT course) FROM students').fetchone()[0]
    total_experiments = conn.execute('SELECT COUNT(*) FROM experiments').fetchone()[0]
    sim_count = conn.execute("SELECT COUNT(*) FROM experiments WHERE mode = 'VIRTUAL_SIMULATION'").fetchone()[0]
    manual_count = conn.execute("SELECT COUNT(*) FROM experiments WHERE mode = 'MANUAL_ENTRY'").fetchone()[0]
    total_quizzes = conn.execute('SELECT COUNT(*) FROM quiz_results').fetchone()[0]
    
    universities = [r[0] for r in conn.execute('SELECT DISTINCT university FROM students ORDER BY university ASC').fetchall() if r[0]]
    courses = [r[0] for r in conn.execute('SELECT DISTINCT course FROM students ORDER BY course ASC').fetchall() if r[0]]

    conn.close()
    return {
        'total_students': total_students,
        'total_universities': total_universities,
        'total_courses': total_courses,
        'total_experiments': total_experiments,
        'sim_count': sim_count,
        'manual_count': manual_count,
        'total_quizzes': total_quizzes,
        'universities': universities,
        'courses': courses
    }

def get_admin_dashboard_data(search_query=None, university=None, exp_type=None, mode=None, date_query=None):
    """
    Returns full admin dashboard telemetry for experiment usage records:
    - Overview counts (total experiments, total students, total universities, sim vs manual, total quizzes)
    - Filtered experiment usage records (Tensile and Hardness)
    - Recent Activity Logs (last 20)
    - Available universities list for filtering
    """
    stats = get_admin_usage_stats()
    conn = get_db_connection()

    # Recent activity logs (last 20)
    recent_act = conn.execute('''
    SELECT a.id, a.student_id, 
           COALESCE(a.student_name, s.name, a.student_id, 'Anonymous Student') as name,
           COALESCE(a.university, s.university, 'General Session') as university,
           a.activity_type, a.details, a.created_at
    FROM activity_logs a
    LEFT JOIN students s ON LOWER(a.student_id) = LOWER(s.student_id)
    ORDER BY a.id DESC LIMIT 20
    ''').fetchall()
    stats['recent_activity_logs'] = [dict(r) for r in recent_act]
    conn.close()

    records = get_admin_usage_records(
        search_query=search_query,
        exp_type=exp_type,
        mode=mode,
        university=university,
        date_query=date_query
    )
    stats['records'] = records
    stats['total_records_count'] = len(records)
    stats['students'] = []
    return stats

def delete_student_account(student_id):
    """
    Deletes a student account by student_id.
    """
    if not student_id:
        return False
    conn = get_db_connection()
    conn.execute('DELETE FROM students WHERE LOWER(student_id) = LOWER(?)', (student_id.strip(),))
    conn.commit()
    conn.close()
    return True

def _sync_admin_record(username, password_hash):
    """Internal helper to ensure the database admin_credentials row matches the active credentials."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM admin_credentials ORDER BY id DESC LIMIT 1')
        existing = cursor.fetchone()
        if existing:
            cursor.execute('UPDATE admin_credentials SET username = ?, password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (username, password_hash, existing['id']))
        else:
            cursor.execute('INSERT INTO admin_credentials (username, password_hash) VALUES (?, ?)', (username, password_hash))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_admin_credentials():
    """
    Returns the active admin credentials dictionary or None.
    """
    conn = get_db_connection()
    row = conn.execute('SELECT id, username, password_hash, updated_at FROM admin_credentials ORDER BY id DESC LIMIT 1').fetchone()
    conn.close()
    
    if row:
        return dict(row)
    
    # Fallback to env or defaults if database table is empty
    env_user = os.environ.get('ADMIN_USERNAME')
    if env_user:
        env_hash = os.environ.get('ADMIN_PASSWORD_HASH')
        env_pass = os.environ.get('ADMIN_PASSWORD', 'matvlab_admin_2024')
        return {
            'id': 1,
            'username': env_user.strip(),
            'password_hash': env_hash or generate_password_hash(env_pass),
            'updated_at': datetime.utcnow()
        }
    return None

def verify_admin_login(username, password):
    """
    Verifies administrator credentials.
    Priority:
    1. Database record in admin_credentials
    2. Environment variables ADMIN_USERNAME + (ADMIN_PASSWORD_HASH or ADMIN_PASSWORD)
       (Enables instant recovery of forgotten administrator passwords via Render Environment tab)
    3. Default fallback (admin / matvlab_admin_2024) if no custom settings exist
    Returns (True, "success") or (False, "error message").
    """
    if not username or not password:
        return False, "Username and password are required."
    
    clean_user = username.strip().lower()
    env_user = os.environ.get('ADMIN_USERNAME')
    env_hash = os.environ.get('ADMIN_PASSWORD_HASH')
    env_pass = os.environ.get('ADMIN_PASSWORD')

    # 1. Database Record Match
    cred = get_admin_credentials()
    if cred:
        if clean_user == cred['username'].strip().lower() and check_password_hash(cred['password_hash'], password):
            return True, "Login successful."
        # If database record didn't match, check if ADMIN_PASSWORD_HASH is set to override:
        if env_hash and clean_user == (env_user or 'admin').strip().lower() and check_password_hash(env_hash, password):
            _sync_admin_record(env_user or 'admin', env_hash)
            return True, "Login successful."
        return False, "Invalid administrator credentials."

    # 2. Environment Variable Match (when database table has no credentials)
    if env_user and clean_user == env_user.strip().lower():
        if env_hash and check_password_hash(env_hash, password):
            _sync_admin_record(env_user.strip(), env_hash)
            return True, "Login successful."
        if env_pass and (password == env_pass or check_password_hash(generate_password_hash(env_pass), password)):
            _sync_admin_record(env_user.strip(), generate_password_hash(env_pass))
            return True, "Login successful."
        return False, "Invalid administrator credentials."

    # 3. Default Fallback
    if clean_user == 'admin' and password == 'matvlab_admin_2024':
        return True, "Login successful."

    return False, "Invalid administrator credentials."

def update_admin_credentials(new_username, new_password, current_password=None):
    """
    Updates the admin username and password from the Admin Portal.
    If current_password is provided, verifies it first against active credentials.
    Returns (True, "Success message") or (False, "Error message").
    """
    if not new_username or not new_username.strip():
        return False, "New admin username cannot be empty."
    if not new_password or len(new_password) < 4:
        return False, "New admin password must be at least 4 characters long."
    
    new_username = new_username.strip()
    cred = get_admin_credentials()
    
    if current_password is not None:
        valid_current = False
        if cred and check_password_hash(cred['password_hash'], current_password):
            valid_current = True
        else:
            env_pass = os.environ.get('ADMIN_PASSWORD', 'matvlab_admin_2024')
            env_hash = os.environ.get('ADMIN_PASSWORD_HASH')
            if env_hash and check_password_hash(env_hash, current_password):
                valid_current = True
            elif current_password == env_pass:
                valid_current = True
        if not valid_current:
            return False, "Current administrator password is incorrect."

    conn = get_db_connection()
    cursor = conn.cursor()
    new_hash = generate_password_hash(new_password)
    
    cursor.execute('SELECT id FROM admin_credentials ORDER BY id DESC LIMIT 1')
    existing = cursor.fetchone()
    if existing:
        cursor.execute('''
        UPDATE admin_credentials 
        SET username = ?, password_hash = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''', (new_username, new_hash, existing['id']))
    else:
        cursor.execute('''
        INSERT INTO admin_credentials (username, password_hash)
        VALUES (?, ?)
        ''', (new_username, new_hash))
    conn.commit()
    conn.close()

    return True, "Administrator credentials successfully updated."

# ==========================================
# HARDNESS EXPERIMENTS OPERATIONS (BRINELL & ROCKWELL)
# ==========================================

def save_hardness_experiment(data, student_id=None, student_name=None, university=None, session_id=None):
    """
    Saves a completed Brinell or Rockwell hardness experiment.
    Parameters in data:
    - title: str
    - method: 'BRINELL' or 'ROCKWELL'
    - mode: 'VIRTUAL_SIMULATION' or 'MANUAL_ENTRY'
    - material_name: str
    - data_origin: 'SIMULATION / DEMONSTRATION DATA' or 'USER-ENTERED LABORATORY DATA'
    - parameters: dict (stored as JSON)
    - mean_hardness: float
    - hardness_unit: str ('HBW', 'HRB', 'HRC', 'HRA')
    - num_readings: int
    - readings: list of trial dicts
    - notes: str
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    sid = student_id or data.get('student_id')
    s_name = student_name or data.get('student_name')
    uni = university or data.get('university')
    sess_id = session_id or data.get('session_id')

    method = (data.get('method') or 'BRINELL').upper().strip()
    mode = data.get('mode', 'MANUAL_ENTRY')
    data_origin = data.get('data_origin')
    if not data_origin:
        data_origin = 'SIMULATION / DEMONSTRATION DATA' if mode == 'VIRTUAL_SIMULATION' else 'USER-ENTERED LABORATORY DATA'

    params = data.get('parameters', {})
    params_json = json.dumps(params) if isinstance(params, dict) else str(params)
    readings = data.get('readings', [])
    num_readings = len(readings) if readings else int(data.get('num_readings', 1))

    mean_h = float(data.get('mean_hardness', 0.0))
    h_unit = data.get('hardness_unit', 'HBW' if method == 'BRINELL' else 'HRB')
    title = data.get('title') or f"{method.capitalize()} Hardness Test — {data.get('material_name', 'Specimen')}"

    cursor.execute('''
    INSERT INTO hardness_experiments (
        student_id, title, method, mode, material_name, data_origin,
        parameters_json, mean_hardness, hardness_unit, num_readings, notes,
        student_name, university, session_id
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        sid, title, method, mode, data.get('material_name', 'Unknown Material'),
        data_origin, params_json, mean_h, h_unit, num_readings, data.get('notes', ''),
        s_name, uni, sess_id
    ))

    exp_id = cursor.lastrowid

    # Insert individual trial readings
    for idx, r in enumerate(readings, start=1):
        t_num = r.get('trial_number', idx)
        d1 = float(r['d1_mm']) if r.get('d1_mm') is not None else (float(r['d1']) if r.get('d1') is not None else None)
        d2 = float(r['d2_mm']) if r.get('d2_mm') is not None else (float(r['d2']) if r.get('d2') is not None else None)
        mean_d = float(r['mean_d_mm']) if r.get('mean_d_mm') is not None else (float(r['d_mm']) if r.get('d_mm') is not None else None)
        depth = float(r['depth_mm']) if r.get('depth_mm') is not None else (float(r['depth_e_mm']) if r.get('depth_e_mm') is not None else None)
        h_val = float(r.get('hardness_value', r.get('hbw', r.get('hardness_reading', mean_h))))

        cursor.execute('''
        INSERT INTO hardness_readings (
            experiment_id, trial_number, d1_mm, d2_mm, mean_d_mm, depth_mm, hardness_value
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (exp_id, t_num, d1, d2, mean_d, depth, h_val))

    conn.commit()
    conn.close()

    # Log activity
    log_activity(
        student_id=sid,
        activity_type='EXPERIMENT_SAVE',
        details=f"Hardness {method} experiment #{exp_id} saved ({mode})",
        student_name=s_name,
        university=uni,
        session_id=sess_id
    )

    return exp_id

def get_hardness_experiment_by_id(exp_id):
    """
    Retrieves full details of a hardness experiment including parameters, trials, and associated quiz.
    """
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM hardness_experiments WHERE id = ?', (exp_id,)).fetchone()
    if not row:
        conn.close()
        return None
    exp = dict(row)
    if exp.get('parameters_json'):
        try:
            exp['parameters'] = json.loads(exp['parameters_json'])
        except Exception:
            exp['parameters'] = {}
    else:
        exp['parameters'] = {}

    readings = conn.execute('SELECT * FROM hardness_readings WHERE experiment_id = ? ORDER BY trial_number ASC', (exp_id,)).fetchall()
    exp['readings'] = [dict(r) for r in readings]

    quiz_res = conn.execute('''
    SELECT * FROM quiz_results 
    WHERE experiment_id = ? OR (experiment_type = LOWER(?) AND (student_id = ? OR student_name = ?))
    ORDER BY completed_at DESC LIMIT 1
    ''', (exp_id, exp['method'], exp.get('student_id'), exp.get('student_name'))).fetchone()
    exp['quiz'] = dict(quiz_res) if quiz_res else None

    conn.close()
    return exp

def get_all_hardness_experiments(student_id=None, method=None, session_id=None, student_name=None):
    """
    Retrieves all hardness experiments, optionally filtered by session_id, student_id, student_name, and/or method.
    """
    conn = get_db_connection()
    query = 'SELECT * FROM hardness_experiments WHERE 1=1'
    params = []
    if session_id:
        query += ' AND session_id = ?'
        params.append(session_id.strip())
    elif student_id:
        query += ' AND LOWER(student_id) = LOWER(?)'
        params.append(student_id.strip())
    elif student_name:
        query += ' AND LOWER(student_name) = LOWER(?)'
        params.append(student_name.strip())

    if method:
        query += ' AND UPPER(method) = UPPER(?)'
        params.append(method.strip())

    query += ' ORDER BY created_at DESC'
    rows = conn.execute(query, tuple(params)).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        if d.get('parameters_json'):
            try:
                d['parameters'] = json.loads(d['parameters_json'])
            except Exception:
                d['parameters'] = {}
        else:
            d['parameters'] = {}
        result.append(d)
    return result

def delete_hardness_experiment(exp_id, student_id=None):
    """
    Deletes a hardness experiment by id, verifying student ownership if student_id is provided.
    """
    conn = get_db_connection()
    if student_id:
        row = conn.execute('SELECT student_id FROM hardness_experiments WHERE id = ?', (exp_id,)).fetchone()
        if not row or (row['student_id'] and row['student_id'].lower() != student_id.lower()):
            conn.close()
            return False
    conn.execute('DELETE FROM hardness_readings WHERE experiment_id = ?', (exp_id,))
    conn.execute('DELETE FROM hardness_experiments WHERE id = ?', (exp_id,))
    conn.commit()
    conn.close()
    return True

# ==========================================
# ADMIN EXPERIMENT USAGE TELEMETRY & RECORDS
# ==========================================

def get_admin_usage_stats():
    """
    Returns administrative summary statistics for MAT-VLAB ADMIN:
    - total_experiments (Tensile + Hardness)
    - total_students (unique user names across experiments and registered students)
    - total_universities (unique institutions)
    - sim_count (Virtual Simulation count across all experiments)
    - manual_count (Manual Data Entry count across all experiments)
    - total_quizzes
    - universities list for filtering
    """
    conn = get_db_connection()
    t_count = conn.execute('SELECT COUNT(*) FROM experiments').fetchone()[0]
    h_count = conn.execute('SELECT COUNT(*) FROM hardness_experiments').fetchone()[0]
    total_experiments = t_count + h_count

    t_sim = conn.execute("SELECT COUNT(*) FROM experiments WHERE mode = 'VIRTUAL_SIMULATION'").fetchone()[0]
    h_sim = conn.execute("SELECT COUNT(*) FROM hardness_experiments WHERE mode = 'VIRTUAL_SIMULATION'").fetchone()[0]
    sim_count = t_sim + h_sim

    t_man = conn.execute("SELECT COUNT(*) FROM experiments WHERE mode = 'MANUAL_ENTRY'").fetchone()[0]
    h_man = conn.execute("SELECT COUNT(*) FROM hardness_experiments WHERE mode = 'MANUAL_ENTRY'").fetchone()[0]
    manual_count = t_man + h_man

    total_quizzes = conn.execute('SELECT COUNT(*) FROM quiz_results').fetchone()[0]

    names_query = '''
    SELECT DISTINCT name FROM (
        SELECT student_name as name FROM experiments WHERE student_name IS NOT NULL AND student_name != ''
        UNION
        SELECT student_name as name FROM hardness_experiments WHERE student_name IS NOT NULL AND student_name != ''
        UNION
        SELECT name FROM students WHERE name IS NOT NULL AND name != ''
    )
    '''
    student_names = [r[0] for r in conn.execute(names_query).fetchall() if r[0]]
    total_students = len(student_names)

    uni_query = '''
    SELECT DISTINCT university FROM (
        SELECT university FROM experiments WHERE university IS NOT NULL AND university != ''
        UNION
        SELECT university FROM hardness_experiments WHERE university IS NOT NULL AND university != ''
        UNION
        SELECT university FROM students WHERE university IS NOT NULL AND university != ''
    ) ORDER BY university ASC
    '''
    universities = [r[0] for r in conn.execute(uni_query).fetchall() if r[0]]
    total_universities = len(universities)

    conn.close()
    return {
        'total_experiments': total_experiments,
        'total_students': total_students,
        'total_universities': total_universities,
        'sim_count': sim_count,
        'manual_count': manual_count,
        'total_quizzes': total_quizzes,
        'universities': universities
    }

def get_admin_usage_records(search_query=None, exp_type=None, mode=None, university=None, date_query=None):
    """
    Returns aggregated experiment usage records from both Tensile and Hardness experiments
    with flexible filtering for the admin dashboard.
    """
    conn = get_db_connection()
    records = []

    # 1. Fetch Tensile Experiments
    if not exp_type or exp_type.upper() in ['ALL', 'TENSILE']:
        t_query = '''
        SELECT e.id, 'tensile' as exp_table, 'TENSILE' as exp_type,
               e.title, e.mode, e.material_name,
               COALESCE(e.student_name, s.name, e.student_id, 'Anonymous Student') as student_name,
               COALESCE(e.university, s.university, 'General Session') as university,
               e.session_id, e.created_at,
               r.uts_mpa, r.youngs_modulus_gpa, r.yield_strength_mpa, r.elongation_pct,
               (SELECT COUNT(*) FROM experiment_readings WHERE experiment_id = e.id) as readings_count
        FROM experiments e
        LEFT JOIN experiment_results r ON e.id = r.experiment_id
        LEFT JOIN students s ON LOWER(e.student_id) = LOWER(s.student_id)
        WHERE 1=1
        '''
        t_params = []
        if mode and mode.upper() != 'ALL':
            t_query += ' AND e.mode = ?'
            t_params.append(mode)
        if university and university.upper() != 'ALL':
            t_query += ' AND (e.university = ? OR s.university = ?)'
            t_params.extend([university, university])
        if date_query:
            t_query += ' AND e.created_at LIKE ?'
            t_params.append(f"{date_query.strip()}%")

        t_rows = conn.execute(t_query, tuple(t_params)).fetchall()
        for r in t_rows:
            d = dict(r)
            uts = d.get('uts_mpa')
            key_res = f"UTS: {round(uts, 1)} MPa" if uts is not None else "Completed"
            records.append({
                'id': d['id'],
                'table': 'tensile',
                'exp_type': 'Tensile (UTM)',
                'title': d['title'],
                'mode': d['mode'],
                'material_name': d['material_name'],
                'student_name': d['student_name'],
                'university': d['university'],
                'session_id': d.get('session_id'),
                'created_at': str(d.get('created_at', ''))[:19],
                'key_result': key_res,
                'readings_count': d.get('readings_count', 0),
                'report_url': f"/api/download-report/{d['id']}"
            })

    # 2. Fetch Hardness Experiments
    if not exp_type or exp_type.upper() in ['ALL', 'BRINELL', 'ROCKWELL', 'HARDNESS']:
        h_query = '''
        SELECT h.id, 'hardness' as exp_table, UPPER(h.method) as method,
               h.title, h.mode, h.material_name,
               COALESCE(h.student_name, s.name, h.student_id, 'Anonymous Student') as student_name,
               COALESCE(h.university, s.university, 'General Session') as university,
               h.session_id, h.created_at,
               h.mean_hardness, h.hardness_unit, h.num_readings
        FROM hardness_experiments h
        LEFT JOIN students s ON LOWER(h.student_id) = LOWER(s.student_id)
        WHERE 1=1
        '''
        h_params = []
        if exp_type and exp_type.upper() in ['BRINELL', 'ROCKWELL']:
            h_query += ' AND UPPER(h.method) = ?'
            h_params.append(exp_type.upper())
        if mode and mode.upper() != 'ALL':
            h_query += ' AND h.mode = ?'
            h_params.append(mode)
        if university and university.upper() != 'ALL':
            h_query += ' AND (h.university = ? OR s.university = ?)'
            h_params.extend([university, university])
        if date_query:
            h_query += ' AND h.created_at LIKE ?'
            h_params.append(f"{date_query.strip()}%")

        h_rows = conn.execute(h_query, tuple(h_params)).fetchall()
        for r in h_rows:
            d = dict(r)
            m_val = d.get('mean_hardness')
            m_unit = d.get('hardness_unit', '')
            key_res = f"{round(m_val, 1)} {m_unit}" if m_val is not None else "Completed"
            records.append({
                'id': d['id'],
                'table': 'hardness',
                'exp_type': f"{d['method'].capitalize()} Hardness",
                'title': d['title'],
                'mode': d['mode'],
                'material_name': d['material_name'],
                'student_name': d['student_name'],
                'university': d['university'],
                'session_id': d.get('session_id'),
                'created_at': str(d.get('created_at', ''))[:19],
                'key_result': key_res,
                'readings_count': d.get('num_readings', 0),
                'report_url': f"/hardness/report/{d['id']}"
            })

    conn.close()

    # Search filtering
    if search_query:
        sq = search_query.lower().strip()
        records = [
            r for r in records
            if sq in (r['student_name'] or '').lower()
            or sq in (r['university'] or '').lower()
            or sq in (r['material_name'] or '').lower()
            or sq in (r['title'] or '').lower()
            or sq in (r['exp_type'] or '').lower()
        ]

    # Sort descending by created_at
    records.sort(key=lambda x: x['created_at'], reverse=True)
    return records

def get_admin_record_by_id(table, record_id):
    """
    Fetches complete experiment record for admin modal inspection.
    """
    if table == 'tensile':
        return get_experiment_by_id(record_id)
    elif table == 'hardness':
        return get_hardness_experiment_by_id(record_id)
    return None
