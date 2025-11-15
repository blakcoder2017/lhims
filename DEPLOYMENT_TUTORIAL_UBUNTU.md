# 🚀 LHIMS Deployment Tutorial - Ubuntu Local Network

**Version:** 1.0  
**Last Updated:** 2025-11-11  
**Target:** Ubuntu Server 20.04/22.04 LTS  
**Network:** Local Area Network (LAN)

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [System Requirements](#system-requirements)
3. [Step 1: Initial Server Setup](#step-1-initial-server-setup)
4. [Step 2: Install System Dependencies](#step-2-install-system-dependencies)
5. [Step 3: Install and Configure PostgreSQL](#step-3-install-and-configure-postgresql)
6. [Step 4: Install Python and Create Virtual Environment](#step-4-install-python-and-create-virtual-environment)
7. [Step 5: Deploy Application Code](#step-5-deploy-application-code)
8. [Step 6: Configure Application](#step-6-configure-application)
9. [Step 7: Run Database Migrations](#step-7-run-database-migrations)
10. [Step 8: Install and Configure Apache](#step-8-install-and-configure-apache)
11. [Step 9: Create Systemd Service](#step-9-create-systemd-service)
12. [Step 10: Configure Network Access](#step-10-configure-network-access)
13. [Step 11: Initial Setup and Testing](#step-11-initial-setup-and-testing)
14. [Troubleshooting](#troubleshooting)
15. [Security Considerations](#security-considerations)
16. [Maintenance](#maintenance)

---

## 📦 Prerequisites

Before starting, ensure you have:
- ✅ Ubuntu Server 20.04 or 22.04 LTS installed
- ✅ Root or sudo access
- ✅ Network connectivity
- ✅ At least 4GB RAM (8GB recommended)
- ✅ At least 20GB free disk space
- ✅ Static IP address assigned to server (recommended)

---

## 💻 System Requirements

### Minimum Requirements
- **CPU:** 2 cores
- **RAM:** 4GB
- **Storage:** 20GB free space
- **Network:** 100Mbps LAN connection

### Recommended Requirements
- **CPU:** 4+ cores
- **RAM:** 8GB+
- **Storage:** 50GB+ SSD
- **Network:** 1Gbps LAN connection

---

## 🔧 Step 1: Initial Server Setup

### 1.1 Update System Packages

```bash
sudo apt update
sudo apt upgrade -y
```

### 1.2 Set Static IP Address (Optional but Recommended)

Edit network configuration:

```bash
sudo nano /etc/netplan/00-installer-config.yaml
```

Example configuration:

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      dhcp4: no
      addresses:
        - 192.168.1.100/24
      gateway4: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

Apply changes:

```bash
sudo netplan apply
```

### 1.3 Configure Firewall

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS (if using SSL)
sudo ufw enable
```

---

## 📥 Step 2: Install System Dependencies

### 2.1 Install Essential Packages

```bash
sudo apt install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    postgresql \
    postgresql-contrib \
    apache2 \
    libapache2-mod-wsgi-py3 \
    git \
    curl \
    build-essential \
    libpq-dev \
    python3-dev \
    nginx
```

**Note:** If Python 3.12 is not available in your Ubuntu version, use Python 3.10 or 3.11:

```bash
sudo apt install -y python3.10 python3.10-venv python3-pip
```

### 2.2 Verify Installations

```bash
python3 --version
postgresql --version
apache2 -v
nginx -v
```

---

## 🗄️ Step 3: Install and Configure PostgreSQL

### 3.1 Start PostgreSQL Service

```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 3.2 Create Database and User

Switch to postgres user:

```bash
sudo -u postgres psql
```

Run the following SQL commands:

```sql
-- Create database
CREATE DATABASE lhims;

-- Create user
CREATE USER lhims_user WITH PASSWORD 'your_secure_password_here';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE lhims TO lhims_user;

-- Connect to database and grant schema privileges
\c lhims
GRANT ALL ON SCHEMA public TO lhims_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO lhims_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO lhims_user;

-- Exit
\q
```

**Important:** Replace `your_secure_password_here` with a strong password!

### 3.3 Configure PostgreSQL for Network Access (Optional)

Edit PostgreSQL configuration:

```bash
sudo nano /etc/postgresql/14/main/postgresql.conf
```

Find and uncomment/modify:

```
listen_addresses = 'localhost'
```

Edit pg_hba.conf:

```bash
sudo nano /etc/postgresql/14/main/pg_hba.conf
```

Add at the end:

```
# Local network access (adjust IP range as needed)
host    lhims    lhims_user    192.168.1.0/24    md5
```

Restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

---

## 🐍 Step 4: Install Python and Create Virtual Environment

### 4.1 Create Application Directory

```bash
sudo mkdir -p /opt/lhims
sudo chown $USER:$USER /opt/lhims
cd /opt/lhims
```

### 4.2 Create Virtual Environment

```bash
python3.12 -m venv venv
# OR if using Python 3.10:
# python3.10 -m venv venv

source venv/bin/activate
```

### 4.3 Upgrade pip

```bash
pip install --upgrade pip setuptools wheel
```

---

## 📦 Step 5: Deploy Application Code

### 5.1 Clone or Copy Application Files

**Option A: Using Git (if repository is available)**

```bash
cd /opt/lhims
git clone <your-repository-url> .
```

**Option B: Copy Files Manually**

```bash
# Copy all application files to /opt/lhims
# Ensure the following structure:
# /opt/lhims/
#   ├── app/
#   ├── migrations/
#   ├── alembic.ini
#   ├── requirements.txt (create if not exists)
#   └── ...
```

### 5.2 Create requirements.txt

If it doesn't exist, create it:

```bash
cd /opt/lhims
cat > requirements.txt << EOF
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.12.1
pydantic==2.5.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
jinja2==3.1.2
python-dotenv==1.0.0
email-validator==2.1.0
EOF
```

### 5.3 Install Python Dependencies

```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

## ⚙️ Step 6: Configure Application

### 6.1 Create .env File

```bash
cd /opt/lhims
nano .env
```

Add the following configuration:

```env
# Application Settings
APP_TITLE=LHIMS
VERSION=2.0
DEBUG=False

# Database Configuration
SQLALCHEMY_DATABASE_URL=postgresql://lhims_user:your_secure_password_here@localhost:5432/lhims

# Security Settings
SECRET_KEY=your-very-secret-key-change-this-in-production-min-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Optional: Email Configuration (for password reset)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com

# Optional: SMS Configuration (for Ghana - AfricasTalking)
AFRICASTALKING_API_KEY=your-api-key
AFRICASTALKING_USERNAME=your-username
AFRICASTALKING_SENDER_ID=LHIMS
```

**Important:** 
- Replace `your_secure_password_here` with the PostgreSQL password you set earlier
- Replace `your-very-secret-key-change-this-in-production-min-32-characters` with a strong random string (use `openssl rand -hex 32` to generate)

### 6.2 Set Proper Permissions

```bash
chmod 600 .env
chown $USER:$USER .env
```

---

## 🗃️ Step 7: Run Database Migrations

### 7.1 Initialize Database Schema

```bash
cd /opt/lhims
source venv/bin/activate

# Run migrations
alembic upgrade head
```

### 7.2 Seed Initial Data (Optional)

If you have seed scripts:

```bash
python scripts/seed_admin.py
python scripts/seed_permissions.py
```

### 7.3 Verify Database

```bash
sudo -u postgres psql -d lhims -c "\dt"
```

You should see all tables created.

---

## 🌐 Step 8: Install and Configure Apache

### 8.1 Install Apache and mod_wsgi (Alternative: Use Nginx + Gunicorn)

**Option A: Using Apache with mod_wsgi (Simpler for LAMP-like setup)**

```bash
sudo apt install -y apache2 libapache2-mod-wsgi-py3
```

**Option B: Using Nginx as Reverse Proxy (Recommended for Production)**

We'll use Nginx as it's better for FastAPI applications.

### 8.2 Configure Nginx (Recommended)

Create Nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/lhims
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name lhims.local 192.168.1.100;  # Replace with your server IP or domain

    # Increase timeouts for large file uploads (PACS images)
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

    # Proxy all other requests to FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/lhims /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 8.3 Alternative: Apache Configuration (if using Apache)

If you prefer Apache, create configuration:

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
    </Directory>

    # Proxy to FastAPI
    ProxyPreserveHost On
    ProxyPass /static !
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    # Increase upload size for PACS images
    LimitRequestBody 104857600
</VirtualHost>
```

Enable modules and site:

```bash
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod headers
sudo a2ensite lhims
sudo systemctl restart apache2
```

---

## 🔄 Step 9: Create Systemd Service

### 9.1 Create Service File

```bash
sudo nano /etc/systemd/system/lhims.service
```

Add the following:

```ini
[Unit]
Description=LHIMS FastAPI Application
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/lhims
Environment="PATH=/opt/lhims/venv/bin"
ExecStart=/opt/lhims/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**Note:** Adjust `--workers 4` based on your CPU cores (recommended: number of cores)

### 9.2 Set Permissions

```bash
sudo chown -R www-data:www-data /opt/lhims
sudo chmod -R 755 /opt/lhims
sudo chmod 600 /opt/lhims/.env
```

### 9.3 Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable lhims
sudo systemctl start lhims
sudo systemctl status lhims
```

### 9.4 Check Logs

```bash
sudo journalctl -u lhims -f
```

---

## 🌍 Step 10: Configure Network Access

### 10.1 Configure Firewall

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload
```

### 10.2 Test Local Access

```bash
curl http://localhost
# Should return HTML content
```

### 10.3 Test Network Access

From another computer on the network:

```
http://192.168.1.100
```

Replace `192.168.1.100` with your server's IP address.

### 10.4 Configure Hostname (Optional)

Edit hosts file on client machines:

**Windows:** `C:\Windows\System32\drivers\etc\hosts`
**Linux/Mac:** `/etc/hosts`

Add:

```
192.168.1.100    lhims.local
```

Then access via: `http://lhims.local`

---

## ✅ Step 11: Initial Setup and Testing

### 11.1 Access the Application

Open a web browser and navigate to:

```
http://192.168.1.100
# or
http://lhims.local
```

### 11.2 Create Admin User

If seed script didn't run, create admin user manually:

```bash
cd /opt/lhims
source venv/bin/activate
python
```

```python
from app.db.database import SessionLocal
from app.models.user_models import User, Role
from app.core.security import get_password_hash

db = SessionLocal()

# Get Admin role
admin_role = db.query(Role).filter(Role.name == "Admin").first()

# Create admin user
admin = User(
    username="admin",
    email="admin@hospital.local",
    full_name="System Administrator",
    hashed_password=get_password_hash("admin123"),  # Change this!
    role_id=admin_role.id,
    is_active=True
)
db.add(admin)
db.commit()
db.close()
```

**Important:** Change the password immediately after first login!

### 11.3 Login and Configure

1. Login with admin credentials
2. Navigate to **System Admin → Hospital Settings**
3. Configure hospital name, logo, address, etc.
4. Navigate to **System Admin → Service Pricing**
5. Set up service prices
6. Create additional users as needed

### 11.4 Verify All Modules

Test access to:
- ✅ Dashboard
- ✅ Patient Registration
- ✅ Appointments
- ✅ Clinical Encounters
- ✅ Lab Dashboard
- ✅ Pharmacy Dashboard
- ✅ Radiology Dashboard
- ✅ Billing
- ✅ Reports

---

## 🔧 Troubleshooting

### Issue: Application won't start

**Check service status:**
```bash
sudo systemctl status lhims
```

**Check logs:**
```bash
sudo journalctl -u lhims -n 50
```

**Common causes:**
- Database connection error → Check `.env` database URL
- Missing dependencies → Run `pip install -r requirements.txt`
- Port 8000 already in use → Change port in service file

### Issue: Database connection error

**Test database connection:**
```bash
sudo -u postgres psql -d lhims -U lhims_user
```

**Check PostgreSQL is running:**
```bash
sudo systemctl status postgresql
```

**Verify .env file:**
```bash
cat /opt/lhims/.env | grep SQLALCHEMY_DATABASE_URL
```

### Issue: 502 Bad Gateway

**Check if FastAPI is running:**
```bash
curl http://127.0.0.1:8000
```

**Check Nginx/Apache error logs:**
```bash
sudo tail -f /var/log/nginx/error.log
# or
sudo tail -f /var/log/apache2/error.log
```

**Check service:**
```bash
sudo systemctl restart lhims
```

### Issue: Static files not loading

**Check permissions:**
```bash
sudo chown -R www-data:www-data /opt/lhims/app/static
```

**Check Nginx/Apache configuration:**
- Verify `/static` alias path is correct
- Check file permissions (755 for directories, 644 for files)

### Issue: Can't access from network

**Check firewall:**
```bash
sudo ufw status
```

**Check server IP:**
```bash
ip addr show
```

**Test from server:**
```bash
curl http://localhost
```

**Check Nginx/Apache is listening:**
```bash
sudo netstat -tlnp | grep :80
```

### Issue: Migration errors

**Check Alembic version:**
```bash
cd /opt/lhims
source venv/bin/activate
alembic current
```

**Check for multiple heads:**
```bash
alembic heads
```

**If multiple heads, create merge:**
```bash
alembic merge -m "merge_heads" heads
alembic upgrade head
```

---

## 🔒 Security Considerations

### 1. Change Default Passwords

- ✅ Change PostgreSQL password
- ✅ Change admin user password
- ✅ Change SECRET_KEY in .env

### 2. File Permissions

```bash
# Application files
sudo chown -R www-data:www-data /opt/lhims
sudo chmod -R 755 /opt/lhims
sudo chmod 600 /opt/lhims/.env

# Static files
sudo chmod -R 644 /opt/lhims/app/static/*
sudo find /opt/lhims/app/static -type d -exec chmod 755 {} \;
```

### 3. Firewall Configuration

```bash
# Only allow necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS (if using SSL)
sudo ufw enable
```

### 4. SSL/HTTPS (Recommended for Production)

Install Certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
```

Get SSL certificate:

```bash
sudo certbot --nginx -d lhims.local
```

Auto-renewal is set up automatically.

### 5. Database Security

- ✅ Use strong passwords
- ✅ Limit network access if not needed
- ✅ Regular backups
- ✅ Don't expose PostgreSQL port to internet

### 6. Application Security

- ✅ Keep dependencies updated
- ✅ Regular security updates: `sudo apt update && sudo apt upgrade`
- ✅ Monitor logs for suspicious activity
- ✅ Use strong SECRET_KEY
- ✅ Enable HTTPS in production

---

## 🔄 Maintenance

### Daily Tasks

**Check service status:**
```bash
sudo systemctl status lhims
sudo systemctl status nginx
sudo systemctl status postgresql
```

**Check disk space:**
```bash
df -h
```

### Weekly Tasks

**Update system:**
```bash
sudo apt update
sudo apt upgrade
```

**Check logs:**
```bash
sudo journalctl -u lhims --since "1 week ago"
```

**Database backup:**
```bash
sudo -u postgres pg_dump lhims > /backups/lhims_$(date +%Y%m%d).sql
```

### Monthly Tasks

**Review and rotate logs:**
```bash
sudo journalctl --vacuum-time=30d
```

**Check application updates:**
```bash
cd /opt/lhims
git pull  # If using git
source venv/bin/activate
pip install -r requirements.txt --upgrade
alembic upgrade head
sudo systemctl restart lhims
```

### Backup Strategy

**Create backup script:**

```bash
sudo nano /opt/lhims/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/backups/lhims"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
sudo -u postgres pg_dump lhims > $BACKUP_DIR/db_$DATE.sql

# Backup application files (excluding venv)
tar -czf $BACKUP_DIR/app_$DATE.tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    /opt/lhims

# Keep only last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

Make executable:

```bash
chmod +x /opt/lhims/backup.sh
```

Add to crontab (daily at 2 AM):

```bash
crontab -e
```

Add:

```
0 2 * * * /opt/lhims/backup.sh
```

---

## 📝 Quick Reference Commands

### Service Management

```bash
# Start/Stop/Restart LHIMS
sudo systemctl start lhims
sudo systemctl stop lhims
sudo systemctl restart lhims
sudo systemctl status lhims

# View logs
sudo journalctl -u lhims -f
sudo journalctl -u lhims --since "1 hour ago"

# Nginx
sudo systemctl restart nginx
sudo nginx -t

# PostgreSQL
sudo systemctl restart postgresql
```

### Database Management

```bash
# Connect to database
sudo -u postgres psql -d lhims

# Run migrations
cd /opt/lhims
source venv/bin/activate
alembic upgrade head

# Check migration status
alembic current
alembic history
```

### Application Management

```bash
# Activate virtual environment
cd /opt/lhims
source venv/bin/activate

# Update dependencies
pip install -r requirements.txt --upgrade

# Check application
curl http://localhost:8000
```

---

## 🌐 Network Configuration Examples

### For Small Clinic (10-20 users)

**Server IP:** 192.168.1.100  
**Access:** `http://192.168.1.100`  
**Workers:** 2-4

### For Medium Hospital (50-100 users)

**Server IP:** 192.168.1.100  
**Access:** `http://lhims.hospital.local` (configure DNS)  
**Workers:** 4-8  
**Database:** Consider separate database server

### For Large Hospital (100+ users)

**Server IP:** 192.168.1.100  
**Load Balancer:** Consider multiple application servers  
**Database:** Separate PostgreSQL server  
**Workers:** 8+ per server

---

## 📞 Support & Resources

### Log Locations

- **Application logs:** `sudo journalctl -u lhims`
- **Nginx logs:** `/var/log/nginx/access.log` and `/var/log/nginx/error.log`
- **PostgreSQL logs:** `/var/log/postgresql/postgresql-14-main.log`
- **System logs:** `/var/log/syslog`

### Useful Commands

```bash
# Check all services
sudo systemctl status lhims nginx postgresql

# Check disk usage
df -h
du -sh /opt/lhims

# Check memory
free -h

# Check network
ip addr show
netstat -tlnp
```

---

## ✅ Deployment Checklist

- [ ] System updated and configured
- [ ] PostgreSQL installed and database created
- [ ] Python virtual environment created
- [ ] Application code deployed
- [ ] .env file configured
- [ ] Database migrations run
- [ ] Nginx/Apache configured
- [ ] Systemd service created and running
- [ ] Firewall configured
- [ ] Network access tested
- [ ] Admin user created
- [ ] Hospital settings configured
- [ ] All modules tested
- [ ] Backup strategy implemented
- [ ] SSL certificate installed (if using HTTPS)
- [ ] Monitoring set up

---

## 🎉 Success!

Once all steps are completed, your LHIMS system should be:
- ✅ Running on the local network
- ✅ Accessible from all client computers
- ✅ Fully functional with all modules
- ✅ Secure and properly configured
- ✅ Ready for production use

**Default Access:**
- URL: `http://192.168.1.100` (replace with your server IP)
- Admin Login: Use the admin credentials you created

---

**End of Deployment Tutorial**

