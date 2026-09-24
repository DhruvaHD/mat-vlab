# MAT-VLAB — Production Cloud Deployment Guide

This guide describes how to deploy the **MAT-VLAB (Interactive Virtual Materials Testing & Analysis Laboratory)** application to the public Internet with full **HTTPS / SSL encryption**, high availability, and zero hardcoded local network dependencies.

---

## 1. Cloud-Ready Architecture Overview

MAT-VLAB has been engineered following the **12-Factor App methodology**:
1. **Dynamic Network Binding**: Binds to `0.0.0.0` with the port assigned by the hosting environment via `$PORT`.
2. **Environment-Driven Configuration**: Database location, secret keys, upload directory, and proxy headers are all governed by environment variables (`config.py`).
3. **Automatic HTTPS Reverse Proxy Compatibility**: Integrated `ProxyFix` middleware from Werkzeug ensures that when running behind cloud load balancers or reverse proxies (Cloudflare, AWS ALB, Nginx, Render, Railway), all redirect URLs, cookies, and resource references generate proper `https://` schemes.
4. **Zero Local IP Dependencies**: All frontend AJAX requests (`fetch()`) and navigation links use relative URLs (e.g. `/api/simulation-data`, `/api/calculate`), so the app works automatically under any custom domain, subdomain, or IP.
5. **Production WSGI Server**: Uses **Gunicorn** (`gunicorn.conf.py` & `wsgi.py`) with multi-threaded worker pools and automatic process recycling.
6. **Containerized**: Pre-configured `Dockerfile` with non-root security permissions and `docker-compose.yml`.

---

## 2. Option A: Free/Managed Cloud PaaS (Recommended for Portfolio & Fast Deployment)

Managed cloud platforms provide **free automatic SSL/HTTPS**, continuous deployment directly from Git, and zero server maintenance.

### 🌐 Deploying to Render.com (Easiest & Free)

1. Push your MAT-VLAB repository to GitHub or GitLab.
2. Sign in to [Render.com](https://render.com) and click **New +** $\rightarrow$ **Web Service**.
3. Connect your MAT-VLAB repository.
4. Configure the service:
   - **Name**: `mat-vlab` (or your choice)
   - **Region**: Choose the closest region (e.g. Singapore, Frankfurt, Oregon)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -c gunicorn.conf.py wsgi:app`
5. In the **Environment Variables** section, add:
   - `SECRET_KEY`: *(Generate a 32-character random string)*
   - `FLASK_ENV`: `production`
   - `ENABLE_PROXY_FIX`: `true`
6. Click **Deploy Web Service**.
7. Render will build and deploy the application, giving you an immediate public HTTPS URL:
   `https://mat-vlab.onrender.com`

---

### 🚂 Deploying to Railway.app

1. Sign in to [Railway.app](https://railway.app).
2. Click **New Project** $\rightarrow$ **Deploy from GitHub repo**.
3. Select your MAT-VLAB repository.
4. Railway automatically detects `Procfile` and `requirements.txt`.
5. Under **Variables**, add:
   - `SECRET_KEY`: *(Secure random string)*
   - `ENABLE_PROXY_FIX`: `true`
6. Under **Settings**, click **Generate Domain**.
7. Your app is instantly live at:
   `https://mat-vlab-production.up.railway.app`

---

## 3. Option B: Docker Container Deployment (Any Cloud Provider)

MAT-VLAB includes a production-grade `Dockerfile` using `python:3.12-slim` and a non-root user.

### Build and Run with Docker

```bash
# 1. Build the Docker image
docker build -t mat-vlab:latest .

# 2. Run the container
docker run -d \
  --name mat-vlab-app \
  -p 5000:5000 \
  -e SECRET_KEY="your-production-secret-key" \
  -e FLASK_ENV="production" \
  -e ENABLE_PROXY_FIX="true" \
  -v matvlab_data:/app/data \
  mat-vlab:latest
```

### Run with Docker Compose

```bash
docker compose up -d
```

---

## 4. Option C: VPS / Dedicated Server (Ubuntu/Debian) with Nginx + Let's Encrypt SSL

For self-hosted virtual private servers (DigitalOcean Droplet, AWS EC2, Linode, Hetzner, etc.):

### 1. System Packages Setup
```bash
sudo apt update && sudo apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx
```

### 2. Clone and Setup Virtual Environment
```bash
cd /var/www
sudo git clone <your-repo-url> mat-vlab
sudo chown -R $USER:$USER /var/www/mat-vlab
cd /var/www/mat-vlab

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Systemd Service Configuration
Create `/etc/systemd/system/matvlab.service`:
```ini
[Unit]
Description=MAT-VLAB Gunicorn Application Server
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/mat-vlab
Environment="PATH=/var/www/mat-vlab/venv/bin"
Environment="SECRET_KEY=your-production-random-secret-key"
Environment="FLASK_ENV=production"
Environment="ENABLE_PROXY_FIX=true"
Environment="PORT=5000"
ExecStart=/var/www/mat-vlab/venv/bin/gunicorn -c gunicorn.conf.py wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable matvlab
sudo systemctl start matvlab
```

### 4. Nginx Reverse Proxy Configuration
Create `/etc/nginx/sites-available/matvlab`:
```nginx
server {
    server_name vlab.yourdomain.com;

    client_max_body_size 16M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_read_timeout 90;
    }

    location /static {
        alias /var/www/mat-vlab/static;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/matvlab /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5. Obtain Free Let's Encrypt SSL/HTTPS Certificate
```bash
sudo certbot --nginx -d vlab.yourdomain.com
```
Certbot will automatically install the certificate, configure HTTP $\rightarrow$ HTTPS redirection, and set up automatic renewal.

---

## 5. Environment Variables Reference

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `SECRET_KEY` | *(Built-in dev key)* | Cryptographic key for session signing. Set to a 32+ character random string in production. |
| `FLASK_ENV` | `production` | Set to `production` in live environments or `development` locally. |
| `HOST` | `0.0.0.0` | IP interface to bind. `0.0.0.0` allows connections from all network interfaces. |
| `PORT` | `5000` | Port to listen on. Most cloud platforms (Render, Railway, Heroku) inject this automatically. |
| `DATABASE_PATH` | `materials.db` | Absolute or relative path to SQLite database. Can point to persistent disk mounts. |
| `DATA_DIR` | `data` | Directory storing sample CSV files. |
| `UPLOAD_FOLDER` | `data/uploads` | Directory for uploaded datasets. |
| `ENABLE_PROXY_FIX` | `true` | Activates Werkzeug ProxyFix middleware to respect `X-Forwarded-Proto` for HTTPS generation. |
| `PREFERRED_URL_SCHEME` | `https` | Default scheme when generating absolute URLs. |
| `WEB_CONCURRENCY` | `(CPU * 2)` | Number of Gunicorn worker processes. |
| `PYTHON_THREADS` | `2` | Number of worker threads per process. |
| `TIMEOUT` | `60` | Worker timeout in seconds. |

---

## 6. Pre-Flight Verification Checklist

Before publishing your link:
- [x] Run unit tests: `python3 tests/test_tensile.py` (8/8 passing).
- [x] Run responsive audit: `python3 tests/audit_responsive.py` (27/27 passing).
- [x] Verify zero hardcoded IPs (`127.0.0.1` or `localhost`) in frontend JavaScript.
- [x] Verify `ProxyFix` is active so redirects use `https://`.
- [x] Verify SQLite data folder is mounted or persisted if saving long-term experiment records.
- [x] Open on an iPhone and Android device to verify responsive touch interaction.
