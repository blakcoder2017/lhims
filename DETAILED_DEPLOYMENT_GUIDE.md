# 🏥 LHIMS - Complete Deployment Guide for Local Ubuntu Desktop (Server Mode)

**Version:** 2.1  
**Last Updated:** 2025-01-XX  
**Target:** Ubuntu Desktop 20.04/22.04/24.04 LTS OR macOS (with Docker)  
**Purpose:** Deploy LHIMS on a local computer (Ubuntu Desktop or Mac) configured as a server, accessible from all computers on your hospital network

**Note:** 
- **Ubuntu Desktop:** This guide configures Ubuntu Desktop to run as a server with native installation
- **macOS:** See the Docker Compose section for Mac deployment using containers (PostgreSQL + FastAPI + Nginx)

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
    - [Migration Troubleshooting](#migration-troubleshooting)
    - [Application Issues](#problem-application-wont-start)
    - [Network Issues](#problem-cant-access-from-network)
16. [Maintenance Procedures](#maintenance-procedures)
17. [Alternative: Docker Compose Deployment on Mac](#alternative-docker-compose-deployment-on-mac)

---

## 🎯 Introduction

This guide will walk you through deploying LHIMS (Local Health Information Management System) on an Ubuntu Desktop computer configured to act as a server, serving all computers on your hospital network. By the end, you'll have:

- ✅ A fully functional LHIMS server running on Ubuntu Desktop
- ✅ Auto-start on boot
- ✅ Accessible from any computer on your network
- ✅ Secure and production-ready setup
- ✅ Automated backups
- ✅ GUI available for easier management (optional)

**Estimated Time:** 2-3 hours for complete setup

**Ubuntu Desktop vs Server:**
- Ubuntu Desktop includes a graphical interface, which can be helpful for management
- All server functionality works identically on Desktop
- You can still use SSH and command line as you would with Server
- Desktop uses slightly more resources, but provides a familiar interface

**Prerequisites:**
- Ubuntu Desktop 20.04, 22.04, or 24.04 LTS installed
- Root or sudo access
- Physical or remote access to the computer
- Network connection (wired or wireless)
- Basic Linux command line knowledge (we'll guide you through everything)
- Terminal access (Press `Ctrl+Alt+T` to open terminal)

---

## ✅ Pre-Deployment Checklist

Before starting, gather this information:

- [ ] Computer IP address (or plan to set a static IP)
- [ ] Network gateway IP (usually 192.168.1.1 or 192.168.0.1)
- [ ] Network subnet mask (usually 255.255.255.0 or /24)
- [ ] DNS servers (usually 8.8.8.8 and 8.8.4.4 for Google DNS)
- [ ] PostgreSQL database password (choose a strong one)
- [ ] Application secret key (we'll generate this)
- [ ] Terminal access (Press `Ctrl+Alt+T` to open terminal)

**Computer Requirements:**
- Minimum: 2 CPU cores, 4GB RAM, 20GB free disk space
- Recommended: 4+ CPU cores, 8GB RAM, 50GB+ free disk space
- **Note:** Ubuntu Desktop uses more resources than Server, so ensure you have adequate RAM

---

## 🔧 Part 1: Computer Preparation

### Step 1.1: Initial Setup and System Update

1. **Log into your Ubuntu Desktop computer**

You can either:
- **Use the computer directly** (recommended for initial setup)
- **Use SSH from another computer** (if SSH is already configured)

```bash
# If using SSH from another computer:
ssh username@computer-ip-address

# Example:
ssh admin@192.168.1.100
```

**To open Terminal on Ubuntu Desktop:**
- Press `Ctrl+Alt+T` (quickest method)
- Or click the Activities button (top-left), type "Terminal", and press Enter
- Or right-click on desktop → "Open Terminal Here"

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

**Note on Ubuntu Desktop:** You'll see more processes running than on Server due to the graphical interface. This is normal.

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

**Ubuntu Desktop Note:** You can also create users through the GUI:
- Go to Settings → Users
- Click "Unlock" and enter your password
- Click "Add User" and follow the prompts

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

A static IP ensures your computer always has the same address, making it easier for other computers to connect.

**For Ubuntu Desktop, you have two options:**

**Option A: Using GUI (Easier for Desktop users)**

1. Click the network icon in the top-right corner (Wi-Fi or Ethernet icon)
2. Select "Wired Settings" (for Ethernet) or "Wi-Fi Settings" (for wireless)
3. Click the gear icon (⚙️) next to your active connection
4. Go to the "IPv4" tab
5. Change from "Automatic (DHCP)" to "Manual"
6. Enter:
   - **Address:** `192.168.1.100` (your desired static IP)
   - **Netmask:** `255.255.255.0` (or `/24`)
   - **Gateway:** `192.168.1.1` (your router/gateway IP)
   - **DNS:** `8.8.8.8, 8.8.4.4` (Google DNS)
7. Click "Apply"
8. You may need to disconnect and reconnect the network for changes to take effect

**Option B: Using Command Line (Netplan) - For Ubuntu 20.04/22.04:**

1. **Find your network interface name:**
```bash
ip link show
```

2. **Check existing Netplan configuration:**
```bash
ls /etc/netplan/
```

You'll see a file like `01-network-manager-all.yaml` or `50-cloud-init.yaml`

**Note:** On Ubuntu Desktop, NetworkManager is usually used. You may need to configure it differently.

3. **Backup the existing configuration:**
```bash
sudo cp /etc/netplan/01-network-manager-all.yaml /etc/netplan/01-network-manager-all.yaml.backup
```

4. **Edit the Netplan configuration:**
```bash
sudo nano /etc/netplan/01-network-manager-all.yaml
```

5. **Replace with your network configuration:**

**Example for typical home/office network (192.168.1.x) with NetworkManager:**
```yaml
network:
  version: 2
  renderer: NetworkManager
  ethernets:
    eth0:  # Replace 'eth0' with your interface name (use 'enp0s3', 'ens33', etc.)
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
  renderer: NetworkManager
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

**Important Note:** On Ubuntu Desktop, the renderer is usually `NetworkManager` (not `networkd`). If you're unsure, check your existing netplan file first.

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

**Ubuntu Desktop Note:** If you're using Wi-Fi, make sure you're connected to the same network as the other computers. For best performance and reliability, use a wired Ethernet connection if possible.

---

### Step 2.3: Configure Firewall

**Note:** Ubuntu Desktop may have a firewall GUI tool, but we'll use the command line for consistency.

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

**Test Nginx:** 
- On the Ubuntu Desktop computer: Open Firefox/Chrome and go to `http://localhost` - you should see the default Nginx welcome page
- From another computer: Open a web browser and go to `http://your-computer-ip`. You should see the default Nginx welcome page

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

**Expected output:** You should see migration messages like:

```
INFO  [alembic.runtime.migration] Context impl PostgreSQLImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade -> abc123, Initial migration
INFO  [alembic.runtime.migration] Running upgrade abc123 -> def456, Add users table
...
```

**Note:** The messages "Context impl PostgreSQLImpl" and "Will assume transactional DDL" are **NORMAL** - they indicate Alembic detected PostgreSQL and is using transactional DDL (which is correct for PostgreSQL).

**Verify migrations completed:**
```bash
# Check current migration version
alembic current

# Verify tables were created
sudo -u postgres psql -d lhims -c "\dt"

# Should show many tables (users, patients, encounters, etc.)
```

**Common Migration Errors and Solutions:**

See the [Migration Troubleshooting Section](#migration-troubleshooting) below for detailed solutions.

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
- From the Ubuntu Desktop computer: 
  - Terminal: `curl http://localhost:8000`
  - Browser: Open Firefox/Chrome and go to `http://localhost:8000`
- From another computer: Open browser to `http://computer-ip:8000`

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

Add the following configuration (replace `192.168.1.100` with your computer's IP address):

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

**Option A: Using Terminal**
```bash
# Test from computer itself
curl http://localhost
curl http://127.0.0.1:8000
```

**Option B: Using Browser (Ubuntu Desktop)**
1. Open Firefox or Chrome
2. Navigate to: `http://localhost` or `http://127.0.0.1:8000`
3. You should see the LHIMS application

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

### Step 9.1: Find Your Computer IP

**Option A: Using GUI (Ubuntu Desktop)**
1. Click the network icon in the top-right
2. Click on your connection name
3. The IP address will be displayed

**Option B: Using Command Line**

```bash
# On the computer, find the IP address
ip addr show | grep "inet "

# Or
hostname -I

# Or use the GUI-friendly command
ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}'
```

**Note the IP address** (e.g., 192.168.1.100)

### Step 9.2: Test from Another Computer on the Network

**From the Ubuntu Desktop Computer (Local Test):**
1. Open Firefox or Chrome
2. Navigate to: `http://localhost` or `http://192.168.1.100`
3. You should see the LHIMS login page

**From Windows:**
1. Open a web browser
2. Navigate to: `http://192.168.1.100` (replace with your computer's IP)
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

**On the Ubuntu Desktop Computer:**

**Option A: Using GUI**
1. Open Settings → About
2. Click on "Device Name"
3. Change it to something like "lhims-server"
4. Restart if prompted

**Option B: Using Command Line**

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

1. **From the Ubuntu Desktop computer:**
   - Open Firefox or Chrome
   - Navigate to: `http://localhost` or `http://lhims.local`
   - You should see the LHIMS login page

2. **From any other computer on the network:**
   - Open a web browser
   - Navigate to: `http://your-computer-ip` or `http://lhims.local`
   - You should see the LHIMS login page

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

### 🔄 Migration Troubleshooting

If you're getting errors when running migrations on another computer, follow these steps:

#### Error 1: Database Connection Error

**Symptoms:**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect to server
```

**Solutions:**

1. **Check .env file exists and is configured:**
   ```bash
   cd /opt/lhims
   cat .env | grep SQLALCHEMY_DATABASE_URL
   ```

2. **Verify database connection string format:**
   ```bash
   # Should be:
   # postgresql://username:password@host:port/database
   # Example:
   # postgresql://lhims_user:mypassword@localhost:5432/lhims
   ```

3. **Test database connection manually:**
   ```bash
   # On Ubuntu
   sudo -u postgres psql -d lhims -U lhims_user
   
   # If using Docker
   docker compose exec db psql -U lhims_user -d lhims
   ```

4. **Check PostgreSQL is running:**
   ```bash
   # On Ubuntu
   sudo systemctl status postgresql
   
   # If using Docker
   docker compose ps db
   ```

5. **Verify database exists:**
   ```bash
   # On Ubuntu
   sudo -u postgres psql -l | grep lhims
   
   # If using Docker
   docker compose exec db psql -U postgres -c "\l" | grep lhims
   ```

#### Error 2: Import Errors / Module Not Found

**Symptoms:**
```
ModuleNotFoundError: No module named 'app'
ImportError: cannot import name 'Base' from 'app.db.database'
```

**Solutions:**

1. **Ensure you're in the correct directory:**
   ```bash
   pwd
   # Should show: /opt/lhims (or your project directory)
   cd /opt/lhims
   ```

2. **Check Python path:**
   ```bash
   # Verify you're using the virtual environment
   which python
   # Should show: /opt/lhims/venv/bin/python
   
   # Activate virtual environment
   source venv/bin/activate
   ```

3. **Verify all dependencies are installed:**
   ```bash
   pip list | grep -E "(alembic|sqlalchemy|psycopg2|fastapi)"
   ```

4. **Reinstall dependencies if needed:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Check app directory structure:**
   ```bash
   ls -la app/
   ls -la app/db/
   ls -la app/models/
   ```

6. **Test imports manually:**
   ```bash
   python -c "from app.db.database import Base; print('OK')"
   python -c "from app.models import *; print('OK')"
   ```

#### Error 3: Multiple Migration Heads

**Symptoms:**
```
ERROR: Multiple heads detected
```

**Solutions:**

1. **Check current migration status:**
   ```bash
   alembic heads
   alembic current
   alembic history
   ```

2. **Merge multiple heads:**
   ```bash
   # Create a merge migration
   alembic merge -m "merge_heads" heads
   
   # Then upgrade
   alembic upgrade head
   ```

3. **If merge fails, check migration history:**
   ```bash
   alembic history --verbose
   ```

#### Error 4: Tables Already Exist

**Symptoms:**
```
ERROR: relation "users" already exists
```

**Solutions:**

**Option A: Drop and recreate (WARNING: Data Loss!)**
```bash
# Connect to database
sudo -u postgres psql -d lhims

# Drop all tables (WARNING: This deletes all data!)
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO lhims_user;
GRANT ALL ON SCHEMA public TO public;
\q

# Then run migrations
alembic upgrade head
```

**Option B: Mark migrations as complete (if tables already exist)**
```bash
# Check what migrations exist
alembic history

# Stamp database with current head (if tables already match)
alembic stamp head
```

**Option C: Create fresh database**
```bash
# Drop and recreate database
sudo -u postgres psql << EOF
DROP DATABASE lhims;
CREATE DATABASE lhims;
GRANT ALL PRIVILEGES ON DATABASE lhims TO lhims_user;
\c lhims
GRANT ALL ON SCHEMA public TO lhims_user;
\q
EOF

# Then run migrations
alembic upgrade head
```

#### Error 5: Permission Denied

**Symptoms:**
```
ERROR: permission denied for schema public
ERROR: must be owner of database lhims
```

**Solutions:**

1. **Grant proper permissions:**
   ```bash
   sudo -u postgres psql << EOF
   \c lhims
   GRANT ALL ON SCHEMA public TO lhims_user;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO lhims_user;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO lhims_user;
   \q
   EOF
   ```

2. **Verify user has correct privileges:**
   ```bash
   sudo -u postgres psql -d lhims -c "\du lhims_user"
   ```

#### Error 6: Path Issues (Windows/Mac)

**Symptoms:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'migrations'
```

**Solutions:**

1. **Ensure you're in the project root:**
   ```bash
   # Check current directory
   pwd
   ls -la | grep alembic.ini
   ```

2. **Use absolute paths if needed:**
   ```bash
   # On Mac/Windows, use full path
   alembic -c /full/path/to/lhims/alembic.ini upgrade head
   ```

3. **Check file permissions:**
   ```bash
   ls -la migrations/
   chmod -R 755 migrations/
   ```

#### Error 7: Environment Variables Not Loaded

**Symptoms:**
```
KeyError: 'SQLALCHEMY_DATABASE_URL'
```

**Solutions:**

1. **Verify .env file exists:**
   ```bash
   ls -la .env
   ```

2. **Check .env file location:**
   ```bash
   # .env should be in project root
   pwd
   ls -la .env
   ```

3. **Verify .env file format:**
   ```bash
   cat .env
   # Should have SQLALCHEMY_DATABASE_URL=postgresql://...
   ```

4. **Test environment loading:**
   ```bash
   python -c "from app.core.config import settings; print(settings.SQLALCHEMY_DATABASE_URL)"
   ```

#### Error 8: Migration File Conflicts / Missing Revision

**Symptoms:**
```
ERROR: Can't locate revision identified by '1b61f463c8c4'
FAILED: Can't locate revision identified by 'abc123'
```

**This happens when:**
- The database has a reference to a migration that doesn't exist in your `migrations/versions/` directory
- Migration files weren't copied to the new computer
- There's a mismatch between database state and migration files

**Solutions:**

**Solution 1: Check and Copy Missing Migration Files**

1. **Check what revision the database thinks it's at:**
   ```bash
   alembic current
   ```

2. **List all migration files you have:**
   ```bash
   ls -la migrations/versions/
   ```

3. **Check migration history:**
   ```bash
   alembic history
   ```

4. **Find the missing revision:**
   ```bash
   # The error shows the missing revision ID (e.g., '1b61f463c8c4')
   # Search for it in migration files
   grep -r "1b61f463c8c4" migrations/versions/
   ```

5. **If file is missing, copy from working installation:**
   ```bash
   # From your working computer, find the migration file
   # It should be named something like: 1b61f463c8c4_*.py
   # Copy it to the new computer's migrations/versions/ directory
   ```

**Solution 2: Reset Database Migration State (If Missing Files Can't Be Found)**

If you can't find the missing migration file, reset the migration state:

```bash
# 1. Check current database state
alembic current

# 2. Check what tables exist
sudo -u postgres psql -d lhims -c "\dt"

# 3. If tables exist and match your models, stamp the database
alembic stamp head

# 4. If tables don't exist or are incomplete, drop and recreate
```

**Solution 3: Complete Reset (Recommended for Fresh Install)**

If this is a fresh installation on a new computer:

```bash
# 1. Drop and recreate database
sudo -u postgres psql << EOF
DROP DATABASE IF EXISTS lhims;
CREATE DATABASE lhims;
GRANT ALL PRIVILEGES ON DATABASE lhims TO lhims_user;
\c lhims
GRANT ALL ON SCHEMA public TO lhims_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO lhims_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO lhims_user;
\q
EOF

# 2. Verify all migration files are present
ls -la migrations/versions/ | wc -l
# Should show all migration files (usually 50+ files)

# 3. Run migrations from scratch
cd /opt/lhims  # or your project path
source venv/bin/activate
alembic upgrade head
```

**Solution 4: Copy All Migration Files from Source**

If migration files are missing:

```bash
# On the working computer, copy all migration files
# Method 1: Using scp
scp -r /path/to/source/lhims/migrations/versions/* user@new-computer:/opt/lhims/migrations/versions/

# Method 2: Using rsync
rsync -av /path/to/source/lhims/migrations/versions/ user@new-computer:/opt/lhims/migrations/versions/

# Method 3: Copy entire migrations directory
scp -r /path/to/source/lhims/migrations user@new-computer:/opt/lhims/
```

**Solution 5: Clear Alembic Version Table and Restart**

If you want to keep existing tables but reset migration tracking:

```bash
# 1. Connect to database
sudo -u postgres psql -d lhims

# 2. Check alembic_version table
SELECT * FROM alembic_version;

# 3. Clear the version (WARNING: This resets migration tracking)
DELETE FROM alembic_version;

# 4. Exit
\q

# 5. Stamp with current head (if tables already exist)
alembic stamp head

# OR run migrations from beginning (if tables need to be created)
alembic upgrade head
```

**Solution 6: Verify Migration File Integrity**

```bash
# 1. Count migration files
ls migrations/versions/*.py | wc -l

# 2. Check for Python syntax errors
python -m py_compile migrations/versions/*.py

# 3. Verify migration chain
alembic history | head -20
alembic history | tail -20

# 4. Check for broken references
grep -r "down_revision" migrations/versions/ | sort
```

**Quick Fix for Specific Error '1b61f463c8c4':**

```bash
# 1. Check if this revision exists in files
find migrations/versions/ -name "*1b61f463c8c4*"

# 2. If not found, you need to:
#    a) Copy the missing migration file from source, OR
#    b) Reset the database (Solution 3 above)

# 3. If file exists but error persists, check the file content
grep -A 5 "revision = '1b61f463c8c4'" migrations/versions/*.py
```

#### Complete Migration Reset (Last Resort)

If nothing else works, perform a complete reset:

```bash
# 1. Backup existing data (if any)
sudo -u postgres pg_dump lhims > backup_before_reset.sql

# 2. Drop and recreate database
sudo -u postgres psql << EOF
DROP DATABASE lhims;
CREATE DATABASE lhims;
GRANT ALL PRIVILEGES ON DATABASE lhims TO lhims_user;
\c lhims
GRANT ALL ON SCHEMA public TO lhims_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO lhims_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO lhims_user;
\q
EOF

# 3. Ensure you're in project directory
cd /opt/lhims  # or your project path

# 4. Activate virtual environment
source venv/bin/activate

# 5. Verify environment
python -c "from app.core.config import settings; print('Config OK')"

# 6. Run migrations from scratch
alembic upgrade head

# 7. Verify tables created
sudo -u postgres psql -d lhims -c "\dt"
```

#### Migration Checklist for New Computer

Use this checklist when setting up on a new computer:

- [ ] All application files copied (including `migrations/` directory)
- [ ] Virtual environment created and activated
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created and configured
- [ ] Database exists and user has permissions
- [ ] PostgreSQL is running
- [ ] Can connect to database manually
- [ ] Python can import app modules
- [ ] `alembic.ini` file exists in project root
- [ ] `migrations/env.py` exists
- [ ] `migrations/versions/` directory has migration files
- [ ] Current directory is project root when running `alembic`

#### Quick Diagnostic Commands

Run these to diagnose migration issues:

```bash
# 1. Check current directory
pwd

# 2. Check virtual environment
which python
which alembic

# 3. Check environment variables
python -c "from app.core.config import settings; print(settings.SQLALCHEMY_DATABASE_URL)"

# 4. Check database connection
python -c "from app.db.database import engine; engine.connect(); print('DB OK')"

# 5. Check migration status
alembic current
alembic heads
alembic history

# 6. Check migration files
ls -la migrations/versions/ | wc -l  # Count migration files

# 7. Test imports
python -c "from app.models import *; print('Models OK')"
```

---

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
# Check computer IP
ip addr show
hostname -I

# Test local access (Terminal)
curl http://localhost
curl http://127.0.0.1:8000

# Test local access (Browser on Ubuntu Desktop)
# Open Firefox/Chrome and navigate to http://localhost

# Check listening ports
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :8000

# Or use ss command (more modern)
ss -tlnp | grep :80
ss -tlnp | grep :8000
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

### Computer Setup
- [ ] Ubuntu Desktop installed and updated
- [ ] Static IP address configured
- [ ] Firewall configured (ports 22, 80, 443 open)
- [ ] System packages updated
- [ ] Terminal access confirmed (Ctrl+Alt+T works)

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
- [ ] Services accessible from Ubuntu Desktop computer (localhost)
- [ ] Services accessible from network (other computers)
- [ ] Hostname configured (optional)
- [ ] Network connection stable (wired recommended)

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
- [ ] Application accessible from Ubuntu Desktop computer (localhost)
- [ ] Application accessible from network (other computers)
- [ ] Admin user can login
- [ ] All modules accessible
- [ ] Static files loading correctly
- [ ] Browser test successful on Desktop computer

---

## 🎉 Success!

If you've completed all steps, your LHIMS server running on Ubuntu Desktop should now be:

- ✅ Running and accessible from all computers on your network
- ✅ Auto-starting on boot
- ✅ Automatically restarting if it crashes
- ✅ Backed up regularly
- ✅ Secure and production-ready
- ✅ GUI available for easier management

**Access your application:**
- **From Ubuntu Desktop computer:** `http://localhost` or `http://lhims.local`
- **From other computers:** `http://your-computer-ip` or `http://lhims.local`
- **Default admin:** `admin` / `admin123` (change immediately!)

**Ubuntu Desktop Benefits:**
- Easy access to logs and files through GUI file manager
- Can use browser directly on the server computer for testing
- Visual monitoring of system resources
- Easier for non-technical staff to manage

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
- **Docker Deployment:** `DOCKER_SETUP.md`
- **User Manual:** `USER_MANUAL.md`

---

## 💡 Ubuntu Desktop Specific Tips

### Using GUI Tools

**File Manager:**
- Press `Super` (Windows key) and type "Files" to open the file manager
- Navigate to `/opt/lhims` to view application files
- Right-click files to edit with text editor

**System Monitor:**
- Press `Super` and type "System Monitor" to see CPU, RAM, and network usage
- Useful for monitoring server performance

**Terminal Shortcuts:**
- `Ctrl+Alt+T` - Open new terminal
- `Ctrl+Shift+T` - New tab in terminal
- `Ctrl+Alt+F1-F6` - Switch to virtual terminals (if GUI freezes)

**Network Manager:**
- Click network icon in top-right for quick network settings
- Useful for checking connection status

### Running in Background

If you want to keep the terminal free while services run:
- Use `systemctl` commands (services run in background automatically)
- Or use `screen` or `tmux` for terminal sessions:
  ```bash
  sudo apt install screen
  screen -S lhims
  # Run commands here
  # Press Ctrl+A then D to detach
  # screen -r lhims to reattach
  ```

### Auto-Start on Login (Alternative)

If you want the application to start when a specific user logs in (instead of system boot):
1. Press `Super` and type "Startup Applications"
2. Click "Add"
3. Name: "LHIMS Server"
4. Command: `sudo systemctl start lhims`
5. Save

**Note:** Systemd service (configured in Part 7) is better as it starts before login.

---

## 🍎 Alternative: Docker Compose Deployment on Mac

If you're deploying on a Mac (macOS) instead of Ubuntu, Docker Compose is the recommended approach. This method packages everything (PostgreSQL + FastAPI + Nginx) into containers, making it easy to deploy and manage.

### Prerequisites for Mac

- **macOS 10.15 (Catalina) or later**
- **Docker Desktop for Mac** installed
- **At least 8GB RAM** (16GB recommended)
- **At least 20GB free disk space**

### Step 1: Install Docker Desktop

1. **Download Docker Desktop:**
   - Visit: https://www.docker.com/products/docker-desktop
   - Download Docker Desktop for Mac (Apple Silicon or Intel)
   - Install the `.dmg` file

2. **Start Docker Desktop:**
   - Open Docker Desktop from Applications
   - Wait for it to start (whale icon in menu bar)
   - Verify installation:
   ```bash
   docker --version
   docker compose version
   ```

### Step 2: Prepare Application Files

1. **Clone or copy your LHIMS application:**
   ```bash
   cd ~/Documents
   # Copy your lhims folder here, or clone from repository
   cd lhims
   ```

2. **Verify Docker files exist:**
   ```bash
   ls -la | grep -E "(Dockerfile|docker-compose|nginx.conf|docker-entrypoint)"
   ```
   
   You should see:
   - `Dockerfile`
   - `docker-compose.yml`
   - `nginx.conf`
   - `docker-entrypoint.sh`
   - `env.example`

### Step 3: Configure Environment

1. **Create environment file:**
   ```bash
   cp env.example .env
   ```

2. **Edit `.env` file:**
   ```bash
   nano .env
   # Or use any text editor like VS Code, TextEdit, etc.
   ```

3. **Set required values:**
   ```env
   # Database
   POSTGRES_PASSWORD=your_secure_password_here
   POSTGRES_DB=lhims
   POSTGRES_USER=lhims_user
   
   # Application
   SECRET_KEY=$(openssl rand -hex 32)  # Generate and paste the output
   APP_TITLE=LHIMS
   VERSION=2.0
   DEBUG=False
   
   # Ports (adjust if needed)
   APP_PORT=8000
   NGINX_HTTP_PORT=80
   POSTGRES_PORT=5432
   ```

4. **Generate SECRET_KEY:**
   ```bash
   openssl rand -hex 32
   ```
   Copy the output and paste it as `SECRET_KEY` in your `.env` file.

### Step 4: Build and Start Services

1. **Build Docker images:**
   ```bash
   docker compose build
   ```
   This may take 5-10 minutes the first time.

2. **Start all services:**
   ```bash
   docker compose up -d
   ```

3. **Check service status:**
   ```bash
   docker compose ps
   ```
   
   All services should show "Up" status:
   - `lhims_db` (PostgreSQL)
   - `lhims_app` (FastAPI)
   - `lhims_nginx` (Nginx)

### Step 5: Run Database Migrations

Migrations run automatically on container start, but you can run manually:

```bash
# Wait for database to be ready (about 10 seconds)
sleep 10

# Run migrations
docker compose exec app alembic upgrade head
```

### Step 6: Seed Initial Data (Optional)

```bash
# Seed permissions
docker compose exec app python scripts/seed_permissions.py

# Seed admin user
docker compose exec app python scripts/seed_admin.py
```

### Step 7: Access the Application

**From Mac:**
- Open Safari, Chrome, or Firefox
- Navigate to: `http://localhost`
- You should see the LHIMS login page

**From Other Computers on Network:**
1. **Find your Mac's IP address:**
   ```bash
   # In Terminal on Mac
   ifconfig | grep "inet " | grep -v 127.0.0.1
   # Or
   ipconfig getifaddr en0  # For Wi-Fi
   ipconfig getifaddr en1  # For Ethernet
   ```

2. **From other computers:**
   - Open browser
   - Navigate to: `http://your-mac-ip-address`
   - Example: `http://192.168.1.105`

**Note:** If you can't access from network, check macOS Firewall settings:
- System Settings → Network → Firewall
- Make sure it's not blocking connections

### Step 8: Configure Network Access (Mac)

**Option A: Allow Docker through Firewall**

1. Open **System Settings** → **Network** → **Firewall**
2. Click **Options**
3. Ensure Docker is allowed, or add it if needed

**Option B: Configure Static IP (Optional)**

1. **System Settings** → **Network**
2. Select your connection (Wi-Fi or Ethernet)
3. Click **Details**
4. Go to **TCP/IP** tab
5. Change from "Using DHCP" to "Manually"
6. Enter:
   - IP Address: `192.168.1.100` (your desired IP)
   - Subnet Mask: `255.255.255.0`
   - Router: `192.168.1.1` (your router IP)
7. Click **Apply**

### Step 9: Auto-Start on Mac Boot

**Option A: Using Docker Desktop Settings**

1. Open **Docker Desktop**
2. Go to **Settings** → **General**
3. Check **"Start Docker Desktop when you log in"**
4. Docker will start automatically, but containers won't

**Option B: Create Launch Agent (Auto-start containers)**

1. **Create launch agent:**
   ```bash
   mkdir -p ~/Library/LaunchAgents
   nano ~/Library/LaunchAgents/com.lhims.docker.plist
   ```

2. **Add this content:**
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
       <key>Label</key>
       <string>com.lhims.docker</string>
       <key>ProgramArguments</key>
       <array>
           <string>/usr/local/bin/docker</string>
           <string>compose</string>
           <string>-f</string>
           <string>/Users/YOUR_USERNAME/Documents/lhims/docker-compose.yml</string>
           <string>up</string>
           <string>-d</string>
       </array>
       <key>RunAtLoad</key>
       <true/>
       <key>KeepAlive</key>
       <false/>
       <key>WorkingDirectory</key>
       <string>/Users/YOUR_USERNAME/Documents/lhims</string>
   </dict>
   </plist>
   ```
   
   **Replace `YOUR_USERNAME` with your Mac username:**
   ```bash
   whoami  # This shows your username
   ```

3. **Load the launch agent:**
   ```bash
   launchctl load ~/Library/LaunchAgents/com.lhims.docker.plist
   ```

4. **Test:**
   ```bash
   launchctl start com.lhims.docker
   ```

### Step 10: Management Commands (Mac)

**Start/Stop Services:**
```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart specific service
docker compose restart app

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f app
```

**Database Operations:**
```bash
# Access database shell
docker compose exec db psql -U lhims_user -d lhims

# Backup database
docker compose exec db pg_dump -U lhims_user lhims > backup_$(date +%Y%m%d).sql

# Restore database
cat backup.sql | docker compose exec -T db psql -U lhims_user lhims
```

**Application Commands:**
```bash
# Access app container shell
docker compose exec app bash

# Run migrations
docker compose exec app alembic upgrade head

# Run seed scripts
docker compose exec app python scripts/seed_admin.py
```

### Step 11: Backup Setup (Mac)

**Create backup script:**

```bash
nano ~/Documents/lhims/backup.sh
```

Add this content:

```bash
#!/bin/bash
BACKUP_DIR="$HOME/Documents/lhims/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
docker compose exec -T db pg_dump -U lhims_user lhims | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

Make executable:
```bash
chmod +x ~/Documents/lhims/backup.sh
```

**Schedule automatic backups:**

1. Open **Automator** (Applications → Automator)
2. Create new **Calendar Alarm**
3. Add "Run Shell Script" action
4. Enter:
   ```bash
   /Users/YOUR_USERNAME/Documents/lhims/backup.sh
   ```
5. Save as "LHIMS Backup"
6. Open **Calendar** app
7. Create new event, set to repeat daily at 2 AM
8. Add alert: "Run Script" → Select your Automator workflow

### Troubleshooting on Mac

**Docker won't start:**
- Check Docker Desktop is running (whale icon in menu bar)
- Restart Docker Desktop
- Check system resources (Docker needs adequate RAM)

**Can't access from network:**
- Check macOS Firewall: System Settings → Network → Firewall
- Verify Docker is allowed through firewall
- Check Mac's IP address hasn't changed
- Ensure other computers are on same network

**Port already in use:**
```bash
# Check what's using port 80
lsof -i :80

# Change port in .env file
NGINX_HTTP_PORT=8080
```

**High resource usage:**
- Docker Desktop → Settings → Resources
- Adjust CPU and Memory limits
- Close unnecessary applications

**Database connection errors:**
```bash
# Check database is running
docker compose ps db

# Check database logs
docker compose logs db

# Restart database
docker compose restart db
```

### Mac-Specific Tips

1. **Use Docker Desktop GUI:**
   - View containers, images, volumes
   - Monitor resource usage
   - View logs visually

2. **Terminal Alternatives:**
   - Use **iTerm2** for better terminal experience
   - Use **VS Code** with Docker extension

3. **File Access:**
   - Use Finder to navigate to `~/Documents/lhims`
   - Edit files with TextEdit, VS Code, or any editor

4. **Network Sharing:**
   - System Settings → General → Sharing
   - Enable "File Sharing" if needed
   - Enable "Remote Login" for SSH access

### Advantages of Docker on Mac

✅ **Easy Setup:** No need to install PostgreSQL, Python, Nginx separately  
✅ **Isolated Environment:** Everything runs in containers  
✅ **Easy Updates:** Just rebuild containers  
✅ **Portable:** Same setup works on any Mac  
✅ **Clean Uninstall:** Just remove Docker containers  
✅ **Resource Management:** Easy to adjust via Docker Desktop  

### Comparison: Docker vs Native Installation

| Feature | Docker (Mac) | Native (Ubuntu) |
|---------|-------------|-----------------|
| Setup Complexity | ⭐⭐ Easy | ⭐⭐⭐ Medium |
| Resource Usage | Higher | Lower |
| Isolation | ✅ Complete | ❌ None |
| Portability | ✅ Excellent | ⚠️ Limited |
| Auto-start | ⚠️ Requires setup | ✅ Built-in |
| Management | GUI + CLI | CLI |

---

**End of Detailed Deployment Guide**

For support or questions, refer to the troubleshooting section or check the application logs.

**Additional Resources:**
- **Docker Setup Guide:** `DOCKER_SETUP.md`
- **Deployment Alternatives:** `DEPLOYMENT_ALTERNATIVES.md`

