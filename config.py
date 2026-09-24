import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Environment & Secrets
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mat-vlab-materials-testing-laboratory-key-2026')

    # Configurable Storage Paths
    DATABASE = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'materials.db'))
    DATA_DIR = os.environ.get('DATA_DIR', os.path.join(BASE_DIR, 'data'))
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'data', 'uploads'))

    # Upload & Security Limits
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16 MB max upload
    ALLOWED_EXTENSIONS = {'csv', 'txt'}

    # HTTPS & Reverse Proxy Handling
    PREFERRED_URL_SCHEME = os.environ.get('PREFERRED_URL_SCHEME', 'https')
    ENABLE_PROXY_FIX = os.environ.get('ENABLE_PROXY_FIX', 'true').lower() in ('1', 'true', 'yes')
