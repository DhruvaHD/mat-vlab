"""
Gunicorn Production Server Configuration for MAT-VLAB
Optimized for containers, cloud PaaS (Render, Railway, Heroku, Fly.io), and reverse proxies.
"""
import os
import multiprocessing

# Network Binding: dynamic host and port
host = os.environ.get('HOST', '0.0.0.0')
port = os.environ.get('PORT', '5000')
bind = f"{host}:{port}"

# Worker Concurrency & Threading
# Allows override via WEB_CONCURRENCY or defaults safely to 2-4 workers
cpu_count = multiprocessing.cpu_count() or 2
default_workers = min(max(cpu_count * 2, 2), 4)
workers = int(os.environ.get('WEB_CONCURRENCY', default_workers))
threads = int(os.environ.get('PYTHON_THREADS', 2))
worker_class = 'gthread'

# Request Timeouts & Worker Recycling
timeout = int(os.environ.get('TIMEOUT', 60))
keepalive = int(os.environ.get('KEEPALIVE', 5))
max_requests = int(os.environ.get('MAX_REQUESTS', 1000))
max_requests_jitter = int(os.environ.get('MAX_REQUESTS_JITTER', 50))

# Logging: Direct to stdout/stderr for Docker & cloud log collectors
accesslog = '-'
errorlog = '-'
loglevel = os.environ.get('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(a)s"'
