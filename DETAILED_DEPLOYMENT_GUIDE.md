# 🏥 LHIMS - Complete Deployment Guide for Local Ubuntu Server

**Version:** 2.0  
**Last Updated:** 2025-01-XX  
**Target:** Ubuntu Server 20.04/22.04 LTS  
**Purpose:** Deploy LHIMS on a local Ubuntu server accessible from all computers on your hospital network

---

## 📋 Table of Contents

1. [Introduction](#introduction)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Part 1: Server Preparation](#part-1-server-preparation)
4. [Part 2: Network Configuration](#part-2-network-configuration)
5. [Part 3: System Dependencies](#part-3-system-dependencies)
6. [Part 4: Database Setup](#part-4-database-setup)
7. [Part 5: Application Deployment](#part-5-application-deployment)
8. [Part 6: Web Server Configuration](#part-6-web-server-configuration)
9. [Part 7: Auto-Start Configuration](#part-7-auto-start-configuration)
10. [Part 8: Network Access Setup](#part-8-network-access-setup)
11. [Part 9: Testing from Other Computers](#part-9-testing-from-other-computers)
12. [Part 10: Initial Configuration](#part-10-initial-configuration)
13. [Part 11: Security Hardening](#part-11-security-hardening)
14. [Part 12: Backup Setup](#part-12-backup-setup)
15. [Troubleshooting Guide](#troubleshooting-guide)
16. [Maintenance Procedures](#maintenance-procedures)

---

## 🎯 Introduction

This guide will walk you through deploying LHIMS (Local Health Information Management System) on an Ubuntu server that will serve all computers on your hospital network. By the end, you'll have:

- ✅ A fully functional LHIMS server
- ✅ Auto-start on boot
- ✅ Accessible from any computer on your network
- ✅ Secure and production-ready setup
- ✅ Automated backups

**Estimated Time:** 2-3 hours for complete setup

**Prerequisites:**
- Ubuntu Server 20.04 or 22.04 LTS installed
- Root or sudo access
- Physical or remote access to the server
- Network connection
- Basic Linux command line knowledge (we'll guide you through everything)

---

## ✅ Pre-Deployment Checklist

Before starting, gather this information:

- [ ] Server IP address (or plan to set a static IP)
- [ ] Network gateway IP (usually 192.168.1.1 or 192.168.0.1)
- [ ] Network subnet mask (usually 255.255.255.0 or /24)
- [ ] DNS servers (usually 8.8.8.8 and 8.8.4.4 for Google DNS)
- [ ] PostgreSQL database password (choose a strong one)
- [ ] Application secret key (we'll generate this)

**Server Requirements:**
- Minimum: 2 CPU cores, 4GB RAM, 20GB disk space
- Recommended: 4+ CPU cores, 8GB RAM, 50GB+ disk space

---

## 🔧 Part 1: Server Preparation

### Step 1.1: Initial Login and System Update

1. **Log into your Ubuntu server** (via SSH or directly)

```bash
# If using SSH from another computer:
ssh username@server-ip-address

# Example:
ssh admin@192.168.1.100
```

2. **Update the system packages**

```bash
# Update package list
sudo apt update

# Upgrade all installed packages
sudo apt upgrade -y

# Install essential tools
sudo apt install -y curl wget git nano vim
```

**What this does:** Ensures your server has the latest security updates and essential tools.

3. **Check system information**

```bash
# Check Ubuntu version
lsb_release -a

# Check available disk space
df -h

# Check memory
free -h

# Check CPU
lscpu | grep "CPU(s)"
```

**Expected output:** You should see your Ubuntu version, available disk space (should be at least 20GB free), and system resources.

---

### Step 1.2: Create Deployment User (Optional but Recommended)

For security, create a dedicated user for the application:

```bash
# Create a new user
sudo adduser lhims

# Add user to sudo group (if needed)
sudo usermod -aG sudo lhims

# Switch to the new user
su - lhims
```

**Note:** You can also use your existing user account. The important part is having sudo access.

---

## 🌐 Part 2: Network Configuration

### Step 2.1: Check Current Network Configuration

First, let's see what network interface you're using:

```bash
# List network interfaces
ip addr show

# Or use the older command
ifconfig
```

**What to look for:**
- Interface name (usually `eth0`, `ens33`, `enp0s3`, or `wlan0` for wireless)
- Current IP address
- Network mask

### Step 2.2: Set Static IP Address (Highly Recommended)

A static IP ensures your server always has the same address, making it easier for other computers to connect.

**For Ubuntu 20.04/22.04 (using Netplan):**

1. **Find your network interface name:**
```bash
ip link show
```

2. **Check existing Netplan configuration:**
```bash
ls /etc/netplan/
```

You'll see a file like `00-installer-config.yaml` or `50-cloud-init.yaml`

3. **Backup the existing configuration:**
```bash
sudo cp /etc/netplan/00-installer-config.yaml /etc/netplan/00-installer-config.yaml.backup
```

4. **Edit the Netplan configuration:**
```bash
sudo nano /etc/netplan/00-installer-config.yaml
```

5. **Replace with your network configuration:**

**Example for typical home/office network (192.168.1.x):**
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:  # Replace 'eth0' with your interface name
      dhcp4: no
      addresses:
        - 192.168.1.100/24  # Your desired static IP
      gateway4: 192.168.1.1  # Your router/gateway IP
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

**Example for network using 192.168.0.x:**
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      dhcp4: no
      addresses:
        - 192.168.0.100/24
      gateway4: 192.168.0.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

**Important:** 
- Replace `eth0` with your actual interface name
- Replace `192.168.1.100` with an IP that's not in use on your network
- Replace `192.168.1.1` with your actual gateway/router IP
- The `/24` means subnet mask 255.255.255.0

6. **Apply the configuration:**
```bash
# Test the configuration first
sudo netplan try

# If test is successful (press Enter), or apply directly:
sudo netplan apply
```

7. **Verify the new IP:**
```bash
ip addr show
```

You should see your new static IP address.

8. **Test network connectivity:**
```bash
# Ping your gateway
ping -c 4 192.168.1.1

# Ping external server (Google DNS)
ping -c 4 8.8.8.8
```

**If ping fails:** Check your gateway IP and network settings. You may need to check your router's configuration.

---

### Step 2.3: Configure Firewall

Ubuntu comes with UFW (Uncomplicated Firewall). Let's configure it:

```bash
# Check firewall status
sudo ufw status

# Allow SSH (important - do this first!)
sudo ufw allow 22/tcp

# Allow HTTP
sudo ufw allow 80/tcp

# Allow HTTPS (for future SSL setup)
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status again
sudo ufw status verbose
```

**What this does:** Opens ports 22 (SSH), 80 (HTTP), and 443 (HTTPS) while blocking everything else.

**Important:** Always allow SSH before enabling the firewall, or you might lock yourself out!

---

## 📦 Part 3: System Dependencies

### Step 3.1: Install Python and Development Tools

```bash
# Update package list
sudo apt update

# Install Python 3.12 (or 3.10/3.11 if 3.12 not available)
sudo apt install -y python3.12 python3.12-venv python3-pip

# If Python 3.12 is not available, use:
# sudo apt install -y python3.10 python3.10-venv python3-pip

# Install build tools (needed for some Python packages)
sudo apt install -y build-essential

# Install Python development headers
sudo apt install -y python3-dev

# Verify Python installation
python3 --version
```

**Expected output:** `Python 3.12.x` or similar

### Step 3.2: Install PostgreSQL

```bash
# Install PostgreSQL and additional modules
sudo apt install -y postgresql postgresql-contrib

# Install PostgreSQL development libraries (needed for psycopg2)
sudo apt install -y libpq-dev

# Start PostgreSQL service
sudo systemctl start postgresql

# Enable PostgreSQL to start on boot
sudo systemctl enable postgresql

# Check PostgreSQL status
sudo systemctl status postgresql
```

**Expected output:** PostgreSQL should be "active (running)"

### Step 3.3: Install Web Server (Nginx)

Nginx will act as a reverse proxy, handling requests and forwarding them to the FastAPI application.

```bash
# Install Nginx
sudo apt install -y nginx

# Start Nginx
sudo systemctl start nginx

# Enable Nginx to start on boot
sudo systemctl enable nginx

# Check Nginx status
sudo systemctl status nginx
```

**Test Nginx:** Open a web browser on another computer and go to `http://your-server-ip`. You should see the default Nginx welcome page.

### Step 3.4: Install Additional Tools

```bash
# Install Git (for cloning repositories if needed)
sudo apt install -y git

# Install other useful tools
sudo apt install -y curl wget unzip
```

---

## 🗄️ Part 4: Database Setup

### Step 4.1: Access PostgreSQL

```bash
# Switch to postgres user
sudo -u postgres psql
```

You should see a prompt like: `postgres=#`

### Step 4.2: Create Database and User

In the PostgreSQL prompt, run these commands (replace `your_secure_password` with a strong password):

```sql
-- Create the database
CREATE DATABASE lhims;

-- Create a user for the application
CREATE USER lhims_user WITH PASSWORD 'your_secure_password';

-- Grant privileges on the database
GRANT ALL PRIVILEGES ON DATABASE lhims TO lhims_user;

-- Connect to the lhims database
\c lhims

-- Grant privileges on the schema
GRANT ALL ON SCHEMA public TO lhims_user;

-- Grant privileges on all tables (for future tables)
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO lhims_user;

-- Grant privileges on all sequences (for auto-increment IDs)
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO lhims_user;

-- Exit PostgreSQL
\q
```

**Important:** 
- Write down the password you set - you'll need it later
- Use a strong password (mix of letters, numbers, special characters)
- Example: `Lh1ms@2025!Secure#Pass`

### Step 4.3: Verify Database Creation

```bash
# Test connection to the database
sudo -u postgres psql -d lhims -U lhims_user

# If it asks for a password, enter the one you set
# You should see: lhims=>

# Exit
\q
```

### Step 4.4: Configure PostgreSQL for Local Access (Optional)

By default, PostgreSQL only accepts connections from localhost. If you need to connect from other servers later, you can configure it:

```bash
# Find PostgreSQL version
sudo -u postgres psql -c "SELECT version();"

# Edit PostgreSQL configuration (replace 14 with your version if different)
sudo nano /etc/postgresql/14/main/postgresql.conf
```

Find the line:
```
#listen_addresses = 'localhost'
```

Change to:
```
listen_addresses = 'localhost'
```

(Keep it as localhost for security - the application will connect locally)

```bash
# Restart PostgreSQL
sudo systemctl restart postgresql
```

---

## 📥 Part 5: Application Deployment

### Step 5.1: Create Application Directory

```bash
# Create directory for the application
sudo mkdir -p /opt/lhims

# Set ownership (replace 'lhims' with your username if different)
sudo chown -R $USER:$USER /opt/lhims

# Navigate to the directory
cd /opt/lhims
```

### Step 5.2: Copy Application Files

You have several options to get your application files to the server:

**Option A: Using SCP (from your development machine)**

From your local machine (Mac/Windows/Linux):
```bash
# From your local machine, copy files to server
scp -r /path/to/lhims/* username@server-ip:/opt/lhims/

# Example:
scp -r ~/Documents/seproject/python_projects/lhims/* admin@192.168.1.100:/opt/lhims/
```

**Option B: Using Git (if your code is in a repository)**

```bash
cd /opt/lhims
git clone https://your-repository-url.git .
```

**Option C: Using USB Drive or Network Share**

1. Copy files to USB drive
2. Mount USB on server
3. Copy files to `/opt/lhims`

**Option D: Manual File Transfer**

Use tools like WinSCP (Windows) or FileZilla to transfer files.

### Step 5.3: Verify Application Structure

After copying files, verify the structure:

```bash
cd /opt/lhims
ls -la
```

You should see:
- `app/` directory
- `migrations/` directory
- `requirements.txt`
- `alembic.ini`
- Other application files

### Step 5.4: Create Python Virtual Environment

```bash
cd /opt/lhims

# Create virtual environment
python3.12 -m venv venv
# OR if using Python 3.10:
# python3.10 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Verify you're using the virtual environment
which python
# Should show: /opt/lhims/venv/bin/python
```

### Step 5.5: Install Python Dependencies

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# This may take several minutes
```

**If you encounter errors:**
- Missing system libraries: Install them with `sudo apt install -y <package-name>`
- Compilation errors: Make sure `build-essential` and `python3-dev` are installed

### Step 5.6: Create Environment Configuration File

```bash
cd /opt/lhims
nano .env
```

Add the following content (replace with your actual values):

```env
# Application Settings
APP_TITLE=LHIMS
VERSION=2.0
DEBUG=False

# Database Configuration
# Replace 'your_secure_password' with the password you set in Step 4.2
SQLALCHEMY_DATABASE_URL=postgresql://lhims_user:your_secure_password@localhost:5432/lhims

# Security Settings
# Generate a secret key (see command below)
SECRET_KEY=your-secret-key-here-minimum-32-characters-long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Optional: Email Configuration (for password reset)
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your-email@gmail.com
# SMTP_PASSWORD=your-app-password
# SMTP_FROM=your-email@gmail.com
```

**Generate a secure SECRET_KEY:**

```bash
# Generate a random secret key
openssl rand -hex 32
```

Copy the output and paste it as the `SECRET_KEY` value in your `.env` file.

**Important:** 
- Replace `your_secure_password` with the PostgreSQL password from Step 4.2
- Replace `your-secret-key-here...` with the generated key
- Save the file: `Ctrl+O`, then `Enter`, then `Ctrl+X`

### Step 5.7: Set File Permissions

```bash
cd /opt/lhims

# Set permissions for .env file (sensitive data)
chmod 600 .env

# Set permissions for application directory
chmod -R 755 /opt/lhims

# Verify permissions
ls -la .env
# Should show: -rw------- (read/write for owner only)
```

### Step 5.8: Run Database Migrations

```bash
cd /opt/lhims

# Activate virtual environment
source venv/bin/activate

# Run migrations to create database tables
alembic upgrade head
```

**Expected output:** You should see migration messages indicating tables are being created.

**If you see errors:**
- Database connection error: Check your `.env` file and PostgreSQL password
- Permission errors: Make sure the database user has proper privileges

### Step 5.9: Verify Database Tables

```bash
# Connect to database
sudo -u postgres psql -d lhims

# List all tables
\dt

# You should see many tables like: users, patients, encounters, etc.

# Exit
\q
```

### Step 5.10: Seed Initial Data (Optional)

If you have seed scripts:

```bash
cd /opt/lhims
source venv/bin/activate

# Seed admin user
python scripts/seed_admin.py

# Seed permissions
python scripts/seed_permissions.py
```

**Note:** If seed scripts don't exist, we'll create an admin user manually later.

### Step 5.11: Test Application Locally

Before setting up the web server, test that the application runs:

```bash
cd /opt/lhims
source venv/bin/activate

# Start the application
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Expected output:** You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Test it:**
- From the server: `curl http://localhost:8000`
- From another computer: Open browser to `http://server-ip:8000`

**Stop the server:** Press `Ctrl+C`

---

## 🌐 Part 6: Web Server Configuration

### Step 6.1: Remove Default Nginx Site

```bash
# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Or disable it
sudo rm /etc/nginx/sites-enabled/default
```

### Step 6.2: Create Nginx Configuration

```bash
# Create configuration file
sudo nano /etc/nginx/sites-available/lhims
```

Add the following configuration (replace `192.168.1.100` with your server IP):

```nginx
server {
    listen 80;
    server_name 192.168.1.100 lhims.local;  # Replace with your server IP

    # Increase timeouts for large file uploads (PACS images, documents)
    client_max_body_size 100M;
    proxy_read_timeout 300s;
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;

    # Logging
    access_log /var/log/nginx/lhims_access.log;
    error_log /var/log/nginx/lhims_error.log;

    # Serve static files directly (CSS, JS, images)
    location /static {
        alias /opt/lhims/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
        
        # Security headers
        add_header X-Content-Type-Options "nosniff";
        add_header X-Frame-Options "SAMEORIGIN";
    }

    # Proxy all other requests to FastAPI application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed in future)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

**Save the file:** `Ctrl+O`, `Enter`, `Ctrl+X`

### Step 6.3: Enable the Site

```bash
# Create symbolic link to enable the site
sudo ln -s /etc/nginx/sites-available/lhims /etc/nginx/sites-enabled/

# Test Nginx configuration
sudo nginx -t
```

**Expected output:** 
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### Step 6.4: Set Static Files Permissions

```bash
# Set proper permissions for static files
sudo chown -R www-data:www-data /opt/lhims/app/static
sudo chmod -R 755 /opt/lhims/app/static
```

### Step 6.5: Restart Nginx

```bash
# Restart Nginx
sudo systemctl restart nginx

# Check status
sudo systemctl status nginx
```

**Expected output:** Nginx should be "active (running)"

---

## 🔄 Part 7: Auto-Start Configuration

### Step 7.1: Create Systemd Service File

Systemd will manage the FastAPI application, ensuring it starts on boot and restarts if it crashes.

```bash
# Create service file
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
ExecStart=/opt/lhims/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
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

**Important:** 
- Adjust `--workers 4` based on your CPU cores (recommended: number of CPU cores)
- Check CPU cores: `nproc` or `lscpu | grep "^CPU(s)"`

**Save the file:** `Ctrl+O`, `Enter`, `Ctrl+X`

### Step 7.2: Set Application Permissions

```bash
# Set ownership for application directory
sudo chown -R www-data:www-data /opt/lhims

# Set permissions
sudo chmod -R 755 /opt/lhims

# Keep .env file private
sudo chmod 600 /opt/lhims/.env
sudo chown www-data:www-data /opt/lhims/.env
```

### Step 7.3: Enable and Start the Service

```bash
# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable lhims

# Start the service
sudo systemctl start lhims

# Check status
sudo systemctl status lhims
```

**Expected output:** Service should be "active (running)"

### Step 7.4: View Service Logs

```bash
# View real-time logs
sudo journalctl -u lhims -f

# View last 50 lines
sudo journalctl -u lhims -n 50

# View logs since boot
sudo journalctl -u lhims --since boot
```

**Press `Ctrl+C` to exit log view**

### Step 7.5: Test Service Management

```bash
# Stop the service
sudo systemctl stop lhims

# Start the service
sudo systemctl start lhims

# Restart the service
sudo systemctl restart lhims

# Check status
sudo systemctl status lhims
```

---

## 🌍 Part 8: Network Access Setup

### Step 8.1: Verify Firewall Rules

```bash
# Check firewall status
sudo ufw status verbose
```

You should see:
- `22/tcp` ALLOW
- `80/tcp` ALLOW
- `443/tcp` ALLOW

### Step 8.2: Test Local Access

```bash
# Test from server itself
curl http://localhost
curl http://127.0.0.1:8000
```

**Expected output:** HTML content from the application

### Step 8.3: Verify Services Are Running

```bash
# Check all services
sudo systemctl status lhims
sudo systemctl status nginx
sudo systemctl status postgresql
```

All should be "active (running)"

### Step 8.4: Check Listening Ports

```bash
# Check what's listening on port 80
sudo netstat -tlnp | grep :80

# Check what's listening on port 8000
sudo netstat -tlnp | grep :8000
```

**Expected output:**
- Port 80: nginx should be listening
- Port 8000: uvicorn (lhims service) should be listening on 127.0.0.1

---

## 🖥️ Part 9: Testing from Other Computers

### Step 9.1: Find Your Server IP

```bash
# On the server, find the IP address
ip addr show | grep "inet "

# Or
hostname -I
```

**Note the IP address** (e.g., 192.168.1.100)

### Step 9.2: Test from Another Computer on the Network

**From Windows:**
1. Open a web browser
2. Navigate to: `http://192.168.1.100` (replace with your server IP)
3. You should see the LHIMS login page

**From Mac/Linux:**
```bash
# Test with curl
curl http://192.168.1.100

# Or open in browser
# http://192.168.1.100
```

**From Mobile Device:**
1. Connect to the same Wi-Fi network
2. Open browser
3. Navigate to: `http://192.168.1.100`

### Step 9.3: Configure Hostname (Optional but Recommended)

Instead of using IP addresses, you can use a hostname like `lhims.local`.

**On the Server:**

```bash
# Edit hosts file
sudo nano /etc/hosts
```

Add this line:
```
192.168.1.100    lhims.local
```

**On Client Computers (Windows):**

1. Open Notepad as Administrator
2. Open file: `C:\Windows\System32\drivers\etc\hosts`
3. Add line: `192.168.1.100    lhims.local`
4. Save

**On Client Computers (Mac/Linux):**

```bash
sudo nano /etc/hosts
```

Add line:
```
192.168.1.100    lhims.local
```

**Now access via:** `http://lhims.local`

### Step 9.4: Troubleshoot Network Access Issues

**If you can't access from other computers:**

1. **Check firewall:**
```bash
sudo ufw status
```

2. **Check if services are running:**
```bash
sudo systemctl status lhims nginx
```

3. **Check Nginx logs:**
```bash
sudo tail -f /var/log/nginx/lhims_error.log
```

4. **Test from server:**
```bash
curl http://localhost
```

5. **Check network connectivity:**
```bash
# From client computer, ping server
ping 192.168.1.100
```

---

## ⚙️ Part 10: Initial Configuration

### Step 10.1: Access the Application

1. Open a web browser on any computer on the network
2. Navigate to: `http://your-server-ip` or `http://lhims.local`
3. You should see the LHIMS login page

### Step 10.2: Create Admin User

If you didn't run seed scripts, create an admin user manually:

**Option A: Using Python Script**

```bash
cd /opt/lhims
source venv/bin/activate
python
```

In Python:
```python
from app.db.database import SessionLocal
from app.models.user_models import User, Role
from app.core.security import get_password_hash

db = SessionLocal()

# Get Admin role
admin_role = db.query(Role).filter(Role.name == "Admin").first()

if not admin_role:
    print("Admin role not found. Run seed_permissions.py first.")
    exit()

# Create admin user
admin = User(
    username="admin",
    email="admin@hospital.local",
    full_name="System Administrator",
    hashed_password=get_password_hash("admin123"),  # CHANGE THIS PASSWORD!
    role_id=admin_role.id,
    is_active=True
)

db.add(admin)
db.commit()
print(f"Admin user created: {admin.username}")
db.close()
```

**Option B: Using Seed Script**

```bash
cd /opt/lhims
source venv/bin/activate
python scripts/seed_admin.py
```

### Step 10.3: Login and Configure

1. **Login:**
   - Username: `admin`
   - Password: `admin123` (or the password you set)
   - **IMPORTANT:** Change this password immediately after first login!

2. **Configure Hospital Settings:**
   - Navigate to: **System Admin → Hospital Settings**
   - Enter hospital name, address, contact information
   - Upload hospital logo (optional)
   - Save settings

3. **Set Up Service Pricing:**
   - Navigate to: **System Admin → Service Pricing**
   - Configure prices for services
   - Save

4. **Create Additional Users:**
   - Navigate to: **System Admin → Users**
   - Create users for doctors, nurses, etc.
   - Assign appropriate roles

### Step 10.4: Verify All Modules

Test access to key modules:
- ✅ Dashboard
- ✅ Patient Registration
- ✅ Appointments
- ✅ Clinical Encounters
- ✅ Lab Dashboard
- ✅ Pharmacy Dashboard
- ✅ Billing
- ✅ Reports

---

## 🔒 Part 11: Security Hardening

### Step 11.1: Change Default Passwords

**Change PostgreSQL password (if needed):**
```bash
sudo -u postgres psql
ALTER USER lhims_user WITH PASSWORD 'new_secure_password';
\q
```

Then update `.env` file with the new password.

**Change admin user password:**
- Login to the application
- Go to user profile
- Change password

### Step 11.2: Secure File Permissions

```bash
# Ensure proper permissions
sudo chown -R www-data:www-data /opt/lhims
sudo chmod -R 755 /opt/lhims
sudo chmod 600 /opt/lhims/.env
```

### Step 11.3: Configure SSL/HTTPS (Recommended for Production)

**Install Certbot:**
```bash
sudo apt install -y certbot python3-certbot-nginx
```

**Get SSL Certificate:**
```bash
# If you have a domain name
sudo certbot --nginx -d yourdomain.com

# For local network (self-signed certificate)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/lhims-selfsigned.key \
  -out /etc/ssl/certs/lhims-selfsigned.crt
```

**Update Nginx for HTTPS:**
```nginx
server {
    listen 443 ssl;
    server_name lhims.local;
    
    ssl_certificate /etc/ssl/certs/lhims-selfsigned.crt;
    ssl_certificate_key /etc/ssl/private/lhims-selfsigned.key;
    
    # ... rest of configuration
}
```

### Step 11.4: Regular Security Updates

```bash
# Set up automatic security updates
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Step 11.5: Disable Root Login (SSH)

```bash
# Edit SSH configuration
sudo nano /etc/ssh/sshd_config
```

Find and change:
```
PermitRootLogin no
```

Restart SSH:
```bash
sudo systemctl restart sshd
```

---

## 💾 Part 12: Backup Setup

### Step 12.1: Create Backup Directory

```bash
# Create backup directory
sudo mkdir -p /backups/lhims
sudo chown $USER:$USER /backups/lhims
```

### Step 12.2: Create Backup Script

```bash
# Create backup script
nano /opt/lhims/backup.sh
```

Add the following:

```bash
#!/bin/bash
# LHIMS Backup Script

BACKUP_DIR="/backups/lhims"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Backup database
echo "Backing up database..."
sudo -u postgres pg_dump lhims > $BACKUP_DIR/db_$DATE.sql

# Compress database backup
gzip $BACKUP_DIR/db_$DATE.sql

# Backup application files (excluding venv and cache)
echo "Backing up application files..."
tar -czf $BACKUP_DIR/app_$DATE.tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    /opt/lhims

# Remove backups older than retention period
echo "Cleaning old backups..."
find $BACKUP_DIR -type f -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $DATE"
```

Make it executable:
```bash
chmod +x /opt/lhims/backup.sh
```

### Step 12.3: Test Backup

```bash
# Run backup manually
/opt/lhims/backup.sh

# Verify backup was created
ls -lh /backups/lhims/
```

### Step 12.4: Schedule Automatic Backups

```bash
# Edit crontab
crontab -e
```

Add this line (runs daily at 2 AM):
```
0 2 * * * /opt/lhims/backup.sh >> /var/log/lhims_backup.log 2>&1
```

### Step 12.5: Test Restore (Important!)

**Test database restore:**
```bash
# Create a test database
sudo -u postgres createdb lhims_test

# Restore from backup
gunzip -c /backups/lhims/db_YYYYMMDD_HHMMSS.sql.gz | sudo -u postgres psql lhims_test

# Verify
sudo -u postgres psql -d lhims_test -c "\dt"
```

---

## 🔧 Troubleshooting Guide

### Problem: Application Won't Start

**Symptoms:** `sudo systemctl status lhims` shows failed

**Solutions:**

1. **Check logs:**
```bash
sudo journalctl -u lhims -n 50
```

2. **Common causes:**
   - Database connection error → Check `.env` file and PostgreSQL password
   - Missing dependencies → Run `pip install -r requirements.txt`
   - Port 8000 already in use → Change port in service file
   - Permission errors → Check file ownership

3. **Test manually:**
```bash
cd /opt/lhims
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Problem: 502 Bad Gateway

**Symptoms:** Browser shows "502 Bad Gateway" error

**Solutions:**

1. **Check if FastAPI is running:**
```bash
sudo systemctl status lhims
curl http://127.0.0.1:8000
```

2. **Check Nginx error logs:**
```bash
sudo tail -f /var/log/nginx/lhims_error.log
```

3. **Restart services:**
```bash
sudo systemctl restart lhims
sudo systemctl restart nginx
```

### Problem: Can't Access from Network

**Symptoms:** Can access from server but not from other computers

**Solutions:**

1. **Check firewall:**
```bash
sudo ufw status
sudo ufw allow 80/tcp
```

2. **Check server IP:**
```bash
ip addr show
```

3. **Test connectivity:**
```bash
# From client computer
ping 192.168.1.100
telnet 192.168.1.100 80
```

4. **Check Nginx is listening:**
```bash
sudo netstat -tlnp | grep :80
```

### Problem: Database Connection Error

**Symptoms:** Application logs show database connection errors

**Solutions:**

1. **Check PostgreSQL is running:**
```bash
sudo systemctl status postgresql
```

2. **Test database connection:**
```bash
sudo -u postgres psql -d lhims -U lhims_user
```

3. **Verify .env file:**
```bash
cat /opt/lhims/.env | grep SQLALCHEMY_DATABASE_URL
```

4. **Check database exists:**
```bash
sudo -u postgres psql -l | grep lhims
```

### Problem: Static Files Not Loading

**Symptoms:** CSS/JS/images don't load, page looks broken

**Solutions:**

1. **Check permissions:**
```bash
sudo chown -R www-data:www-data /opt/lhims/app/static
sudo chmod -R 755 /opt/lhims/app/static
```

2. **Check Nginx configuration:**
```bash
sudo nginx -t
```

3. **Check static file path in Nginx config:**
```bash
sudo cat /etc/nginx/sites-available/lhims | grep static
```

### Problem: High Memory Usage

**Symptoms:** Server becomes slow, high memory usage

**Solutions:**

1. **Check memory usage:**
```bash
free -h
htop
```

2. **Reduce worker count:**
```bash
sudo nano /etc/systemd/system/lhims.service
# Change --workers 4 to --workers 2
sudo systemctl restart lhims
```

3. **Check for memory leaks:**
```bash
sudo journalctl -u lhims | grep -i memory
```

---

## 🔄 Maintenance Procedures

### Daily Tasks

```bash
# Check service status
sudo systemctl status lhims nginx postgresql

# Check disk space
df -h

# Check logs for errors
sudo journalctl -u lhims --since "1 day ago" | grep -i error
```

### Weekly Tasks

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Check application logs
sudo journalctl -u lhims --since "1 week ago"

# Verify backups
ls -lh /backups/lhims/
```

### Monthly Tasks

```bash
# Review and rotate logs
sudo journalctl --vacuum-time=30d

# Check for application updates
cd /opt/lhims
git pull  # If using git
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Run database migrations if needed
alembic upgrade head

# Restart application
sudo systemctl restart lhims
```

### Update Application

```bash
# Stop service
sudo systemctl stop lhims

# Backup current version
/opt/lhims/backup.sh

# Update code (method depends on how you deployed)
cd /opt/lhims
# git pull OR copy new files

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Restart service
sudo systemctl start lhims

# Verify
sudo systemctl status lhims
```

---

## 📞 Quick Reference Commands

### Service Management

```bash
# Start/Stop/Restart LHIMS
sudo systemctl start lhims
sudo systemctl stop lhims
sudo systemctl restart lhims
sudo systemctl status lhims

# View logs
sudo journalctl -u lhims -f
sudo journalctl -u lhims -n 100

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

### Network Testing

```bash
# Check server IP
ip addr show
hostname -I

# Test local access
curl http://localhost
curl http://127.0.0.1:8000

# Check listening ports
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :8000
```

### File Permissions

```bash
# Fix permissions
sudo chown -R www-data:www-data /opt/lhims
sudo chmod -R 755 /opt/lhims
sudo chmod 600 /opt/lhims/.env
```

---

## ✅ Deployment Checklist

Use this checklist to ensure everything is set up correctly:

### Server Setup
- [ ] Ubuntu Server installed and updated
- [ ] Static IP address configured
- [ ] Firewall configured (ports 22, 80, 443 open)
- [ ] System packages updated

### Dependencies
- [ ] Python 3.10+ installed
- [ ] PostgreSQL installed and running
- [ ] Nginx installed and running
- [ ] All system dependencies installed

### Database
- [ ] PostgreSQL database `lhims` created
- [ ] Database user `lhims_user` created
- [ ] Permissions granted
- [ ] Connection tested

### Application
- [ ] Application files copied to `/opt/lhims`
- [ ] Virtual environment created
- [ ] Python dependencies installed
- [ ] `.env` file configured
- [ ] Database migrations run
- [ ] Initial data seeded (optional)

### Web Server
- [ ] Nginx configuration created
- [ ] Nginx site enabled
- [ ] Static files permissions set
- [ ] Nginx tested and restarted

### Auto-Start
- [ ] Systemd service file created
- [ ] Service enabled for auto-start
- [ ] Service started and running
- [ ] Logs accessible

### Network Access
- [ ] Firewall allows port 80
- [ ] Services accessible from server
- [ ] Services accessible from network
- [ ] Hostname configured (optional)

### Security
- [ ] Default passwords changed
- [ ] File permissions set correctly
- [ ] SSL/HTTPS configured (optional)
- [ ] Security updates enabled

### Backup
- [ ] Backup script created
- [ ] Backup tested
- [ ] Automatic backups scheduled
- [ ] Restore procedure tested

### Testing
- [ ] Application accessible from server
- [ ] Application accessible from network
- [ ] Admin user can login
- [ ] All modules accessible
- [ ] Static files loading correctly

---

## 🎉 Success!

If you've completed all steps, your LHIMS server should now be:

- ✅ Running and accessible from all computers on your network
- ✅ Auto-starting on boot
- ✅ Automatically restarting if it crashes
- ✅ Backed up regularly
- ✅ Secure and production-ready

**Access your application:**
- URL: `http://your-server-ip` or `http://lhims.local`
- Default admin: `admin` / `admin123` (change immediately!)

**Next Steps:**
1. Change default admin password
2. Configure hospital settings
3. Create user accounts for staff
4. Set up service pricing
5. Train staff on using the system

---

## 📚 Additional Resources

- **Main Deployment Tutorial:** `DEPLOYMENT_TUTORIAL_UBUNTU.md`
- **Deployment Alternatives:** `DEPLOYMENT_ALTERNATIVES.md`
- **User Manual:** `USER_MANUAL.md`

---

**End of Detailed Deployment Guide**

For support or questions, refer to the troubleshooting section or check the application logs.

