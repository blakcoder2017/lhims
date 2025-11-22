# 🚀 LHIMS Deployment Alternatives - Ubuntu Local Network

**Version:** 1.0  
**Last Updated:** 2025-01-XX  
**Target:** Ubuntu Server 20.04/22.04 LTS  
**Network:** Local Area Network (LAN) - Hospital Environment

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Deployment Options Comparison](#deployment-options-comparison)
3. [Option 1: Systemd + Uvicorn (Recommended)](#option-1-systemd--uvicorn-recommended)
4. [Option 2: Supervisor + Uvicorn](#option-2-supervisor--uvicorn)
5. [Option 3: Docker + Docker Compose](#option-3-docker--docker-compose)
6. [Option 4: Nginx + Gunicorn](#option-4-nginx--gunicorn)
7. [Option 5: Apache + mod_wsgi](#option-5-apache--mod_wsgi)
8. [Option 6: PM2 (Node.js Process Manager)](#option-6-pm2-nodejs-process-manager)
9. [Quick Decision Guide](#quick-decision-guide)
10. [Migration Between Options](#migration-between-options)

---

## 🎯 Overview

This document provides multiple deployment alternatives for running LHIMS on an Ubuntu server accessible across your hospital network. Each option includes:

- ✅ Auto-start on boot
- ✅ Automatic restart on failure
- ✅ Process management
- ✅ Network accessibility
- ✅ Production-ready configuration

**Common Prerequisites (All Options):**
- Ubuntu Server 20.04/22.04 LTS
- PostgreSQL database (see main deployment tutorial)
- Python 3.10+ with virtual environment
- Application code deployed to `/opt/lhims`
- Network access configured

---

## 📊 Deployment Options Comparison

| Option | Complexity | Performance | Auto-Start | Resource Usage | Best For |
|--------|-----------|-------------|------------|----------------|----------|
| **Systemd + Uvicorn** | ⭐⭐ Low | ⭐⭐⭐⭐⭐ Excellent | ✅ Yes | Low | **Recommended - Most hospitals** |
| **Supervisor + Uvicorn** | ⭐⭐⭐ Medium | ⭐⭐⭐⭐⭐ Excellent | ✅ Yes | Low | Multiple apps, easy management |
| **Docker + Compose** | ⭐⭐⭐⭐ High | ⭐⭐⭐⭐ Very Good | ✅ Yes | Medium | Isolated environments, scaling |
| **Nginx + Gunicorn** | ⭐⭐⭐ Medium | ⭐⭐⭐⭐ Very Good | ✅ Yes | Medium | High-traffic, load balancing |
| **Apache + mod_wsgi** | ⭐⭐⭐ Medium | ⭐⭐⭐ Good | ✅ Yes | Medium | Traditional LAMP stack |
| **PM2** | ⭐⭐ Low | ⭐⭐⭐⭐ Very Good | ✅ Yes | Low | Node.js background, simple setup |

---

## 🔧 Option 1: Systemd + Uvicorn (Recommended)

**Best for:** Most hospital deployments - Simple, reliable, built into Ubuntu

### Advantages
- ✅ Built into Ubuntu (no extra software)
- ✅ Excellent auto-start and restart capabilities
- ✅ Integrated with system logging (`journalctl`)
- ✅ Low resource overhead
- ✅ Easy to manage with standard systemctl commands

### Disadvantages
- ⚠️ Less flexible than Docker for complex setups
- ⚠️ Requires root/sudo for service management

### Setup Instructions

#### 1. Create Systemd Service File

```bash
sudo nano /etc/systemd/system/lhims.service
```

Add the following content:

```ini
[Unit]
Description=LHIMS FastAPI Application
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/lhims
Environment="PATH=/opt/lhims/venv/bin"
EnvironmentFile=/opt/lhims/.env
ExecStart=/opt/lhims/venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 4 \
    --log-level info
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/lhims

[Install]
WantedBy=multi-user.target
```

**Note:** Adjust `--workers 4` based on CPU cores (recommended: number of cores)

#### 2. Set Permissions

```bash
sudo chown -R www-data:www-data /opt/lhims
sudo chmod -R 755 /opt/lhims
sudo chmod 600 /opt/lhims/.env
```

#### 3. Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable lhims
sudo systemctl start lhims
sudo systemctl status lhims
```

#### 4. View Logs

```bash
# Real-time logs
sudo journalctl -u lhims -f

# Last 100 lines
sudo journalctl -u lhims -n 100

# Logs since boot
sudo journalctl -u lhims --since boot
```

#### 5. Management Commands

```bash
# Start/Stop/Restart
sudo systemctl start lhims
sudo systemctl stop lhims
sudo systemctl restart lhims

# Check status
sudo systemctl status lhims

# Enable/Disable auto-start
sudo systemctl enable lhims
sudo systemctl disable lhims
```

### Nginx Configuration (Reverse Proxy)

Create Nginx config:

```bash
sudo nano /etc/nginx/sites-available/lhims
```

```nginx
server {
    listen 80;
    server_name lhims.local 192.168.1.100;  # Replace with your server IP

    client_max_body_size 100M;
    proxy_read_timeout 300s;
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;

    # Static files
    location /static {
        alias /opt/lhims/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Proxy to FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable and restart:

```bash
sudo ln -s /etc/nginx/sites-available/lhims /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔧 Option 2: Supervisor + Uvicorn

**Best for:** Managing multiple applications or when you need a web-based management interface

### Advantages
- ✅ Web-based management UI (optional)
- ✅ Easy to manage multiple processes
- ✅ Simple configuration files
- ✅ Good logging capabilities
- ✅ No root access needed for management

### Disadvantages
- ⚠️ Requires additional software installation
- ⚠️ Less integrated with system than systemd

### Setup Instructions

#### 1. Install Supervisor

```bash
sudo apt update
sudo apt install -y supervisor
```

#### 2. Create Supervisor Configuration

```bash
sudo nano /etc/supervisor/conf.d/lhims.conf
```

Add the following:

```ini
[program:lhims]
command=/opt/lhims/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
directory=/opt/lhims
user=www-data
autostart=true
autorestart=true
startretries=3
stderr_logfile=/var/log/lhims/error.log
stdout_logfile=/var/log/lhims/access.log
environment=PATH="/opt/lhims/venv/bin"
```

#### 3. Create Log Directory

```bash
sudo mkdir -p /var/log/lhims
sudo chown www-data:www-data /var/log/lhims
```

#### 4. Reload and Start

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start lhims
sudo supervisorctl status
```

#### 5. Management Commands

```bash
# Start/Stop/Restart
sudo supervisorctl start lhims
sudo supervisorctl stop lhims
sudo supervisorctl restart lhims

# View status
sudo supervisorctl status lhims

# View logs
sudo tail -f /var/log/lhims/access.log
sudo tail -f /var/log/lhims/error.log

# Reload configuration
sudo supervisorctl reread
sudo supervisorctl update
```

#### 6. Enable Auto-Start (Systemd Integration)

Supervisor itself needs to start on boot:

```bash
sudo systemctl enable supervisor
sudo systemctl start supervisor
```

---

## 🐳 Option 3: Docker + Docker Compose

**Best for:** Isolated deployments, easy scaling, consistent environments

### Advantages
- ✅ Complete isolation from host system
- ✅ Easy to replicate across servers
- ✅ Simple scaling with multiple containers
- ✅ Version control for entire environment
- ✅ Easy rollback and updates

### Disadvantages
- ⚠️ Higher resource usage
- ⚠️ More complex initial setup
- ⚠️ Requires Docker knowledge
- ⚠️ Additional layer of abstraction

### Setup Instructions

#### 1. Install Docker and Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y docker-compose-plugin

# Start Docker
sudo systemctl enable docker
sudo systemctl start docker
```

#### 2. Create Dockerfile

```bash
cd /opt/lhims
nano Dockerfile
```

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### 3. Create docker-compose.yml

```bash
nano docker-compose.yml
```

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    container_name: lhims_db
    environment:
      POSTGRES_DB: lhims
      POSTGRES_USER: lhims_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: always
    networks:
      - lhims_network

  app:
    build: .
    container_name: lhims_app
    environment:
      - SQLALCHEMY_DATABASE_URL=postgresql://lhims_user:${DB_PASSWORD}@db:5432/lhims
      - SECRET_KEY=${SECRET_KEY}
      - ALGORITHM=HS256
      - ACCESS_TOKEN_EXPIRE_MINUTES=1440
    volumes:
      - ./app/static:/app/app/static
      - ./app/uploads:/app/app/static/uploads
    ports:
      - "8000:8000"
    depends_on:
      - db
    restart: always
    networks:
      - lhims_network

  nginx:
    image: nginx:alpine
    container_name: lhims_nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./app/static:/usr/share/nginx/html/static:ro
    depends_on:
      - app
    restart: always
    networks:
      - lhims_network

volumes:
  postgres_data:

networks:
  lhims_network:
    driver: bridge
```

#### 4. Create .env file for Docker

```bash
nano .env
```

```env
DB_PASSWORD=your_secure_password_here
SECRET_KEY=your-secret-key-here
```

#### 5. Create Nginx Configuration for Docker

```bash
nano nginx.conf
```

```nginx
events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:8000;
    }

    server {
        listen 80;
        client_max_body_size 100M;

        location /static {
            alias /usr/share/nginx/html/static;
        }

        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

#### 6. Build and Start

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

#### 7. Run Database Migrations

```bash
docker-compose exec app alembic upgrade head
```

#### 8. Auto-Start on Boot

Docker Compose services automatically restart on boot if `restart: always` is set (already configured above).

To ensure Docker starts on boot:

```bash
sudo systemctl enable docker
```

---

## 🔧 Option 4: Nginx + Gunicorn

**Best for:** High-traffic scenarios, when you need more control over worker processes

### Advantages
- ✅ Better for high-concurrency workloads
- ✅ More control over worker processes
- ✅ Better resource management
- ✅ Can handle more simultaneous connections

### Disadvantages
- ⚠️ Requires Gunicorn installation
- ⚠️ More complex configuration
- ⚠️ Gunicorn doesn't support WebSockets natively (need additional setup)

### Setup Instructions

#### 1. Install Gunicorn

```bash
cd /opt/lhims
source venv/bin/activate
pip install gunicorn
```

#### 2. Create Gunicorn Configuration

```bash
nano /opt/lhims/gunicorn_config.py
```

```python
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
accesslog = "/var/log/lhims/gunicorn_access.log"
errorlog = "/var/log/lhims/gunicorn_error.log"
loglevel = "info"
```

#### 3. Create Systemd Service

```bash
sudo nano /etc/systemd/system/lhims.service
```

```ini
[Unit]
Description=LHIMS Gunicorn Application Server
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/lhims
Environment="PATH=/opt/lhims/venv/bin"
EnvironmentFile=/opt/lhims/.env
ExecStart=/opt/lhims/venv/bin/gunicorn -c /opt/lhims/gunicorn_config.py app.main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 4. Create Log Directory

```bash
sudo mkdir -p /var/log/lhims
sudo chown www-data:www-data /var/log/lhims
```

#### 5. Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable lhims
sudo systemctl start lhims
```

#### 6. Nginx Configuration

Same as Option 1, but ensure proxy settings are optimized:

```nginx
upstream lhims {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name lhims.local 192.168.1.100;

    client_max_body_size 100M;
    proxy_read_timeout 300s;

    location /static {
        alias /opt/lhims/app/static;
    }

    location / {
        proxy_pass http://lhims;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 🔧 Option 5: Apache + mod_wsgi

**Best for:** Traditional LAMP stack environments, existing Apache infrastructure

### Advantages
- ✅ Familiar to many system administrators
- ✅ Good integration with existing Apache setups
- ✅ Mature and stable

### Disadvantages
- ⚠️ mod_wsgi is less optimal for ASGI (FastAPI uses ASGI)
- ⚠️ More complex configuration
- ⚠️ Higher resource usage than Nginx
- ⚠️ Less performant for FastAPI applications

### Setup Instructions

#### 1. Install Apache and mod_wsgi

```bash
sudo apt install -y apache2 libapache2-mod-wsgi-py3
```

**Note:** For FastAPI (ASGI), you'll need to use a different approach since mod_wsgi is for WSGI. Use Apache as reverse proxy instead.

#### 2. Enable Required Modules

```bash
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod headers
sudo a2enmod rewrite
```

#### 3. Create Apache Virtual Host

```bash
sudo nano /etc/apache2/sites-available/lhims.conf
```

```apache
<VirtualHost *:80>
    ServerName lhims.local
    ServerAlias 192.168.1.100

    # Static files
    Alias /static /opt/lhims/app/static
    <Directory /opt/lhims/app/static>
        Require all granted
        Options -Indexes
    </Directory>

    # Proxy to FastAPI (running via systemd)
    ProxyPreserveHost On
    ProxyPass /static !
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    # Increase upload size for PACS images
    LimitRequestBody 104857600

    # Logging
    ErrorLog ${APACHE_LOG_DIR}/lhims_error.log
    CustomLog ${APACHE_LOG_DIR}/lhims_access.log combined
</VirtualHost>
```

#### 4. Enable Site and Restart

```bash
sudo a2ensite lhims
sudo a2dissite 000-default
sudo systemctl restart apache2
sudo systemctl enable apache2
```

#### 5. Use Systemd for FastAPI (Recommended)

Run FastAPI via systemd (Option 1) and use Apache as reverse proxy only.

---

## 🔧 Option 6: PM2 (Node.js Process Manager)

**Best for:** Simple process management, when you're familiar with Node.js tools

### Advantages
- ✅ Very simple configuration
- ✅ Built-in monitoring dashboard
- ✅ Easy process management
- ✅ Good logging

### Disadvantages
- ⚠️ Requires Node.js (even though app is Python)
- ⚠️ Less standard for Python applications
- ⚠️ Additional dependency

### Setup Instructions

#### 1. Install Node.js and PM2

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2
```

#### 2. Create PM2 Configuration

```bash
cd /opt/lhims
nano ecosystem.config.js
```

```javascript
module.exports = {
  apps: [{
    name: 'lhims',
    script: '/opt/lhims/venv/bin/uvicorn',
    args: 'app.main:app --host 127.0.0.1 --port 8000 --workers 4',
    cwd: '/opt/lhims',
    interpreter: '/opt/lhims/venv/bin/python',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production'
    },
    error_file: '/var/log/lhims/pm2_error.log',
    out_file: '/var/log/lhims/pm2_out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
  }]
};
```

#### 3. Create Log Directory

```bash
sudo mkdir -p /var/log/lhims
sudo chown $USER:$USER /var/log/lhims
```

#### 4. Start Application

```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

The last command will generate a systemd service for PM2 itself.

#### 5. Management Commands

```bash
# Start/Stop/Restart
pm2 start lhims
pm2 stop lhims
pm2 restart lhims

# Status
pm2 status
pm2 info lhims

# Logs
pm2 logs lhims
pm2 logs lhims --lines 100

# Monitor
pm2 monit
```

---

## 🎯 Quick Decision Guide

### Choose **Systemd + Uvicorn** if:
- ✅ You want the simplest, most standard solution
- ✅ You're deploying to a single server
- ✅ You want built-in Ubuntu integration
- ✅ You prefer standard Linux tools

### Choose **Supervisor** if:
- ✅ You're managing multiple applications
- ✅ You want a web-based management interface
- ✅ You need process management without root access

### Choose **Docker** if:
- ✅ You want complete environment isolation
- ✅ You plan to scale horizontally
- ✅ You want easy replication across servers
- ✅ You're comfortable with containerization

### Choose **Gunicorn** if:
- ✅ You have high-traffic requirements
- ✅ You need fine-grained worker control
- ✅ You're running on a powerful server

### Choose **Apache** if:
- ✅ You have existing Apache infrastructure
- ✅ Your team is familiar with Apache
- ✅ You need Apache-specific features

### Choose **PM2** if:
- ✅ You're familiar with Node.js tools
- ✅ You want a simple process manager
- ✅ You need built-in monitoring dashboard

---

## 🔄 Migration Between Options

### From Systemd to Supervisor

1. Stop systemd service: `sudo systemctl stop lhims`
2. Disable systemd: `sudo systemctl disable lhims`
3. Follow Supervisor setup (Option 2)
4. Remove systemd file: `sudo rm /etc/systemd/system/lhims.service`

### From Any Option to Docker

1. Stop current service
2. Follow Docker setup (Option 3)
3. Test thoroughly before removing old setup
4. Keep old setup as backup for 1-2 weeks

### From Uvicorn to Gunicorn

1. Install Gunicorn: `pip install gunicorn`
2. Update service configuration (Option 4)
3. Restart service
4. Monitor performance

---

## 📝 Common Configuration for All Options

### Environment Variables (.env)

All options should use this `.env` file structure:

```env
# Application
APP_TITLE=LHIMS
VERSION=2.0
DEBUG=False

# Database
SQLALCHEMY_DATABASE_URL=postgresql://lhims_user:password@localhost:5432/lhims

# Security
SECRET_KEY=your-secret-key-here-min-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Optional: Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Firewall Configuration

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### Network Access

Ensure the server has a static IP or DHCP reservation:

```bash
# Check current IP
ip addr show

# Configure static IP (Ubuntu 20.04+)
sudo nano /etc/netplan/00-installer-config.yaml
```

---

## 🔒 Security Best Practices (All Options)

1. **Change Default Passwords**
   - PostgreSQL password
   - Admin user password
   - SECRET_KEY in .env

2. **File Permissions**
   ```bash
   sudo chown -R www-data:www-data /opt/lhims
   sudo chmod -R 755 /opt/lhims
   sudo chmod 600 /opt/lhims/.env
   ```

3. **SSL/HTTPS** (Recommended for Production)
   ```bash
   sudo apt install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d lhims.local
   ```

4. **Regular Updates**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

5. **Backup Strategy**
   - Daily database backups
   - Weekly application backups
   - Test restore procedures

---

## 📞 Troubleshooting

### Service Won't Start

1. Check logs (varies by option):
   - Systemd: `sudo journalctl -u lhims -n 50`
   - Supervisor: `sudo supervisorctl tail -f lhims stderr`
   - Docker: `docker-compose logs app`
   - PM2: `pm2 logs lhims`

2. Check database connection:
   ```bash
   sudo -u postgres psql -d lhims -U lhims_user
   ```

3. Verify environment variables:
   ```bash
   cat /opt/lhims/.env
   ```

### Can't Access from Network

1. Check firewall: `sudo ufw status`
2. Check service is running
3. Verify Nginx/Apache is running
4. Test locally: `curl http://localhost`

### High Memory Usage

1. Reduce worker count
2. Check for memory leaks
3. Monitor with: `htop` or `free -h`
4. Consider upgrading server RAM

---

## ✅ Recommended Setup for Hospital Environment

**For Most Hospitals (10-200 users):**

1. **Option 1: Systemd + Uvicorn** (Primary recommendation)
   - Simple and reliable
   - Built into Ubuntu
   - Easy to maintain
   - Good performance

2. **Nginx as Reverse Proxy**
   - Better than Apache for FastAPI
   - Lower resource usage
   - Better static file handling

3. **PostgreSQL on Same Server**
   - Sufficient for most hospitals
   - Simpler setup
   - Can migrate to separate server later if needed

**For Large Hospitals (200+ users):**

1. **Option 3: Docker + Compose**
   - Better isolation
   - Easier scaling
   - Can add more app containers later

2. **Separate Database Server**
   - Better performance
   - Easier backups
   - Can scale independently

---

## 🎉 Summary

All deployment options provide:
- ✅ Auto-start on boot
- ✅ Automatic restart on failure
- ✅ Network accessibility
- ✅ Production-ready configuration

**Choose based on:**
- Your team's expertise
- Server resources
- Expected traffic
- Future scaling plans

**Most Recommended:** Option 1 (Systemd + Uvicorn) for simplicity and reliability.

---

**End of Deployment Alternatives Guide**
