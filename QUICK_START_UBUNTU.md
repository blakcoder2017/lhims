# ⚡ LHIMS Quick Start Guide - Ubuntu

**For experienced system administrators who want a quick deployment**

---

## 🚀 Quick Deployment (5 Minutes)

### 1. Run Setup Script

```bash
sudo bash setup_server.sh
```

Follow the prompts to set database password.

### 2. Deploy Application

```bash
# Copy files to /opt/lhims
sudo mkdir -p /opt/lhims
sudo chown $USER:$USER /opt/lhims
# Copy all application files here

cd /opt/lhims
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
nano .env
```

Add:

```env
SQLALCHEMY_DATABASE_URL=postgresql://lhims_user:YOUR_PASSWORD@localhost:5432/lhims
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DEBUG=False
```

### 4. Run Migrations

```bash
alembic upgrade head
```

### 5. Setup Nginx

```bash
sudo nano /etc/nginx/sites-available/lhims
```

Paste:

```nginx
server {
    listen 80;
    server_name _;
    client_max_body_size 100M;
    
    location /static {
        alias /opt/lhims/app/static;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Enable:

```bash
sudo ln -s /etc/nginx/sites-available/lhims /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Create Systemd Service

```bash
sudo nano /etc/systemd/system/lhims.service
```

Paste:

```ini
[Unit]
Description=LHIMS FastAPI Application
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/lhims
Environment="PATH=/opt/lhims/venv/bin"
ExecStart=/opt/lhims/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo chown -R www-data:www-data /opt/lhims
sudo systemctl daemon-reload
sudo systemctl enable lhims
sudo systemctl start lhims
```

### 7. Access Application

Open browser: `http://YOUR_SERVER_IP`

### 8. Create Admin User

```bash
cd /opt/lhims
source venv/bin/activate
python scripts/seed_admin.py
```

Or manually:

```python
python
>>> from app.db.database import SessionLocal
>>> from app.models.user_models import User, Role
>>> from app.core.security import get_password_hash
>>> db = SessionLocal()
>>> admin_role = db.query(Role).filter(Role.name == "Admin").first()
>>> admin = User(username="admin", email="admin@local", full_name="Admin", hashed_password=get_password_hash("admin123"), role_id=admin_role.id, is_active=True)
>>> db.add(admin)
>>> db.commit()
```

---

## ✅ Verify Installation

```bash
# Check services
sudo systemctl status lhims nginx postgresql

# Check logs
sudo journalctl -u lhims -f

# Test access
curl http://localhost
```

---

**For detailed instructions, see DEPLOYMENT_TUTORIAL_UBUNTU.md**

