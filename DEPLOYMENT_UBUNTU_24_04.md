# LHIMS Ubuntu 24.04.3 LTS Deployment Guide

## 🎯 Overview
Complete guide to deploy LHIMS on Ubuntu 24.04.3 LTS server at IP 192.168.0.130 for LAN access.

## 📋 Prerequisites

### System Requirements
- **OS**: Ubuntu 24.04.3 LTS
- **RAM**: Minimum 4GB (8GB recommended)
- **Storage**: Minimum 20GB free space
- **Network**: Static IP 192.168.0.130
- **Access**: SSH or direct terminal access

### Initial Server Setup

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y curl wget git vim htop unzip software-properties-common

# Set timezone (example: Africa/Accra)
sudo timedatectl set-timezone Africa/Accra

# Create application user (optional but recommended)
sudo useradd -m -s /bin/bash lhims
sudo usermod -aG sudo lhims
```

## 🐍 Python Environment Setup

### Option 1: System Python (Quick Setup)
```bash
# Install Python 3.12 and development tools
sudo apt install -y python3.12 python3.12-venv python3.12-dev python3-pip

# Verify installation
python3.12 --version
pip3 --version
```

### Option 2: Pyenv (Recommended for multiple versions)
```bash
# Install pyenv
curl https://pyenv.run | bash

# Add to shell
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc

# Reload shell
source ~/.bashrc

# Install Python 3.12
pyenv install 3.12.0
pyenv global 3.12.0
```

## 🗄️ Database Setup (PostgreSQL)

```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE lhims;
CREATE USER lhims_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE lhims TO lhims_user;
ALTER USER lhims_user CREATEDB;
\q
EOF

# Configure PostgreSQL for network access
sudo vim /etc/postgresql/16/main/postgresql.conf
# Uncomment and change: listen_addresses = 'localhost,192.168.0.130'

sudo vim /etc/postgresql/16/main/pg_hba.conf
# Add line: host    lhims    lhims_user    192.168.0.0/24    md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

## 🎨 Cairo Dependencies (Choose ONE option)

### Option A: Install Cairo Dependencies (Full PDF Support)
```bash
# Install Cairo and related libraries
sudo apt install -y libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev \
    libffi-dev libjpeg-dev libpng-dev libtiff-dev
```

### Option B: Remove Cairo Dependencies (Simpler Installation)
```bash
# Use the modified requirements file without Cairo
# This will be used in the Python setup step below
```

## 📁 Application Setup

```bash
# Create application directory
sudo mkdir -p /opt/lhims
sudo chown lhims:lhims /opt/lhims

# Switch to application user
sudo su - lhims

# Navigate to application directory
cd /opt/lhims

# Clone or copy your application files
# If using git:
git clone <your-repo-url> .

# Or copy from local machine (replace with your method)
# scp -r /path/to/lhims/* lhims@192.168.0.130:/opt/lhims/

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install Python dependencies
# Choose ONE of the following:

# Option A: With Cairo dependencies
pip install -r requirements.txt

# Option B: Without Cairo dependencies
pip install -r requirements_no_cairo.txt
```

## ⚙️ Environment Configuration

```bash
# Create environment file
cp .env.example .env
vim .env
```

**Configure these essential settings:**
```env
# Database
DATABASE_URL=postgresql://lhims_user:your_secure_password@localhost/lhims

# Security
SECRET_KEY=your_generated_secret_key_here
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"

# Network
HOST=0.0.0.0
PORT=8000

# Production
DEBUG=False
ENVIRONMENT=production

# Additional settings as needed
```

## 🗃️ Database Migration

```bash
# Activate virtual environment if not already active
source /opt/lhims/venv/bin/activate

# Run database migrations
cd /opt/lhims
alembic upgrade head

# Seed initial data (optional)
python scripts/seed_permissions.py
python scripts/seed_admin.py
```

## 🚀 Service Configuration

### Create Gunicorn Service

```bash
# Create systemd service file
sudo vim /etc/systemd/system/lhims.service
```

**Service configuration:**
```ini
[Unit]
Description=LHIMS FastAPI Application
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=exec
User=lhims
Group=lhims
WorkingDirectory=/opt/lhims
Environment=PATH=/opt/lhims/venv/bin
EnvironmentFile=/opt/lhims/.env
ExecStart=/opt/lhims/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Create Nginx configuration
sudo vim /etc/nginx/sites-available/lhims
```

**Nginx configuration:**
```nginx
server {
    listen 80;
    server_name 192.168.0.130;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /static/ {
        alias /opt/lhims/app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
```

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/lhims /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Start and enable services
sudo systemctl daemon-reload
sudo systemctl start lhims
sudo systemctl enable lhims
sudo systemctl start nginx
sudo systemctl enable nginx
```

## 🔥 Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Check firewall status
sudo ufw status
```

## 📊 Monitoring and Logs

```bash
# Check service status
sudo systemctl status lhims
sudo systemctl status nginx
sudo systemctl status postgresql

# View logs
sudo journalctl -u lhims -f
sudo journalctl -u nginx -f

# Application logs (if configured)
tail -f /opt/lhims/logs/app.log
```

## 🔄 Backup Setup

```bash
# Create backup script
sudo vim /usr/local/bin/lhims-backup.sh
```

**Backup script:**
```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/lhims"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U lhims_user -h localhost lhims | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Application files backup
tar -czf $BACKUP_DIR/app_$DATE.tar.gz -C /opt lhims --exclude='venv' --exclude='*.pyc' --exclude='__pycache__'

# Keep only last 7 days
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

```bash
# Make script executable
sudo chmod +x /usr/local/bin/lhims-backup.sh

# Add to crontab (daily at 2 AM)
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/lhims-backup.sh
```

## 🌐 Network Access

### Access from LAN Computers
- **URL**: `http://192.168.0.130`
- **Default Admin**: Username: `admin`, Password: `admin123` (change immediately!)

### Test the Application
```bash
# Test locally
curl http://localhost

# Test from server
curl http://192.168.0.130

# Check health endpoint
curl http://192.168.0.130/health
```

## 🔧 Troubleshooting

### Common Issues

1. **Port 80 already in use:**
```bash
sudo lsof -i :80
sudo systemctl stop apache2  # or other service using port 80
```

2. **Database connection failed:**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -U lhims_user -h localhost -d lhims
```

3. **Permission denied errors:**
```bash
# Fix ownership
sudo chown -R lhims:lhims /opt/lhims

# Fix permissions
sudo chmod -R 755 /opt/lhims
```

4. **Cairo installation issues:**
```bash
# If Cairo fails, use the no-Cairo requirements
pip install -r requirements_no_cairo.txt
```

### Performance Optimization

```bash
# Optimize PostgreSQL
sudo vim /etc/postgresql/16/main/postgresql.conf
# Adjust: shared_buffers, effective_cache_size, work_mem

# Optimize Gunicorn workers
# Formula: (2 * CPU cores) + 1
# Edit /etc/systemd/system/lhims.service
# Change: -w 4 to appropriate number
```

## 📱 SSL/HTTPS Setup (Optional)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d 192.168.0.130

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## ✅ Deployment Checklist

- [ ] System updated and prerequisites installed
- [ ] PostgreSQL installed and configured
- [ ] Python environment set up
- [ ] Cairo dependencies resolved (chosen option)
- [ ] Application files deployed
- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] Systemd services created and enabled
- [ ] Nginx configured and running
- [ ] Firewall configured
- [ ] Backup script set up
- [ ] Application accessible from LAN
- [ ] Admin password changed
- [ ] SSL configured (if needed)

## 🚀 Quick Commands Reference

```bash
# Start services
sudo systemctl start lhims nginx postgresql

# Stop services
sudo systemctl stop lhims nginx postgresql

# Restart services
sudo systemctl restart lhims nginx

# View logs
sudo journalctl -u lhims -f

# Database access
sudo -u postgres psql lhims

# Run migrations
cd /opt/lhims && source venv/bin/activate && alembic upgrade head

# Update application
cd /opt/lhims && git pull && source venv/bin/activate && pip install -r requirements.txt && sudo systemctl restart lhims
```

## 📞 Support

For issues:
1. Check logs: `sudo journalctl -u lhims -f`
2. Verify services: `sudo systemctl status lhims nginx postgresql`
3. Test database: `psql -U lhims_user -h localhost -d lhims`
4. Check network: `curl http://192.168.0.130`

---

**Deployment Complete!** Your LHIMS should now be accessible at `http://192.168.0.130` from any computer on your LAN.
