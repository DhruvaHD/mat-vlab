"""
WSGI Entry Point for MAT-VLAB Production Servers (Gunicorn / uWSGI / Waitress).
Used by container runtimes and PaaS clouds (Render, Railway, Fly.io, Heroku, AWS, GCP).
"""
import os
import sys

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SCRATCH_LIB = os.path.abspath(os.path.join(BASE_DIR, '..', 'lib'))
if os.path.exists(SCRATCH_LIB) and SCRATCH_LIB not in sys.path:
    sys.path.insert(0, SCRATCH_LIB)

from app import app

if __name__ == "__main__":
    app.run()
