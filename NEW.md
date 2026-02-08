# LHIMS Docker Deployment Guide for DevOps

**Plan**: Create comprehensive Docker deployment guide for DevOps team to deploy LHIMS on Ubuntu with production-ready configuration.

This guide provides step-by-step instructions for DevOps team to deploy LHIMS using Docker with nginx reverse proxy, including security, monitoring, and maintenance procedures.

## 🎯 **Deployment Overview**

### ✅ **Architecture**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │   FastAPI      │    │     Nginx      │
│   Database      │◄──►│   Application   │◄──►│  Reverse Proxy   │
│   Port 5432    │    │   Port 8000    │    │  Ports 80/443   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        └───────────────────────┴───────────────────────┘
                    Docker Network: lhims_network
```

### ✅ **Deployment Components**
- **Database**: PostgreSQL 15 with performance tuning
- **Application**: FastAPI with Uvicorn workers
- **Proxy**: Nginx with SSL termination
- **Volumes**: Persistent data storage
- **Network**: Isolated Docker network
- **Monitoring**: Health checks and logging

## 📋 **Prerequisites**

### ✅ **System Requirements**
- **Ubuntu**: 20.04 LTS or later
- **RAM**: Minimum 4GB, Recommended 8GB
- **Storage**: Minimum 20GB free space
- **Network**: Static IP recommended
- **Access**: SSH with sudo privileges

### ✅ **Software Requirements**
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

## 🚀 **Deployment Steps**

### ✅ **Phase 1: Environment Setup**

#### **1.1 Clone Repository**
```bash
# Clone the repository
git clone <repository-url> lhims
cd lhims

# Verify Docker files exist
ls -la docker-compose.yml Dockerfile nginx.conf
```

#### **1.2 Configure Environment**
```bash
# Copy environment template
cp env.example .env

# Edit environment file
nano .env
```

#### **1.3 Environment Configuration**
```bash
# Database Configuration
POSTGRES_DB=lhims
POSTGRES_USER=lhims_user
POSTGRES_PASSWORD=SecurePassword123!  # Generate strong password
POSTGRES_PORT=5432

# Application Configuration
APP_TITLE=LHIMS Production
VERSION=2.0
DEBUG=False
SECRET_KEY=$(openssl rand -hex 32)  # Generate secure key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Port Configuration
APP_PORT=8000
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443

# Email Configuration (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=lhims@hospital.com
SMTP_PASSWORD=AppPassword123
SMTP_FROM=LHIMS <noreply@hospital.com>

# SMS Configuration (Optional - Ghana)
AFRICASTALKING_API_KEY=your_api_key_here
AFRICASTALKING_USERNAME=your_username
AFRICASTALKING_SENDER_ID=LHIMS
```

### ✅ **Phase 2: SSL Certificate Setup**

#### **2.1 Create SSL Directory**
```bash
# Create SSL directory
mkdir -p nginx/ssl

# Option A: Self-signed certificate (development)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/lhims.key \
  -out nginx/ssl/lhims.crt \
  -subj "/C=GH/ST=Greater Accra/L=Accra/O=Hospital/CN=lhims.local"

# Option B: Let's Encrypt (production)
sudo apt install certbot
sudo certbot certonly --standalone -d lhims.hospital.com
sudo cp /etc/letsencrypt/live/lhims.hospital.com/fullchain.pem nginx/ssl/lhims.crt
sudo cp /etc/letsencrypt/live/lhims.hospital.com/privkey.pem nginx/ssl/lhims.key
```

#### **2.2 Update Nginx for SSL**
```bash
# Add SSL configuration to nginx.conf
cat >> nginx.conf << 'EOF'

    # HTTPS Server
    server {
        listen 443 ssl http2;
        server_name _;
        
        ssl_certificate /etc/nginx/ssl/lhims.crt;
        ssl_certificate_key /etc/nginx/ssl/lhims.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
        ssl_prefer_server_ciphers off;
        
        location / {
            proxy_pass http://lhims_app:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        location /static/ {
            alias /usr/share/nginx/html/static;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
EOF
```

### ✅ **Phase 3: Application Deployment**

#### **3.1 Build and Start Services**
```bash
# Build Docker images
docker-compose build

# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps
```

#### **3.2 Initialize Database**
```bash
# Wait for database to be ready
docker-compose logs -f db

# Run database migrations
docker-compose exec app alembic upgrade head

# Create admin user (optional)
docker-compose exec app python scripts/create_admin.py
```

#### **3.3 Verify Deployment**
```bash
# Check service health
docker-compose ps

# Check application logs
docker-compose logs -f app

# Test application locally
curl -f http://localhost:8000/health

# Test through nginx proxy
curl -f http://localhost/
```

### ✅ **Phase 4: Production Configuration**

#### **4.1 Firewall Setup**
```bash
# Configure UFW firewall
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

#### **4.2 Systemd Service (Optional)**
```bash
# Create systemd service for Docker Compose
sudo tee /etc/systemd/system/lhims-docker.service > /dev/null << 'EOF'
[Unit]
Description=LHIMS Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/lhims
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable lhims-docker.service
sudo systemctl start lhims-docker.service
```

## 🔧 **Configuration Management**

### ✅ **Environment Variables**
```bash
# Production .env file template
cat > .env << 'EOF'
# ============================================
# Database Configuration
# ============================================
POSTGRES_DB=lhims
POSTGRES_USER=lhims_user
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_PORT=5432

# ============================================
# Application Configuration
# ============================================
APP_TITLE=LHIMS Production
VERSION=2.0
DEBUG=False
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ============================================
# Port Configuration
# ============================================
APP_PORT=8000
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443

# ============================================
# Email Configuration
# ============================================
SMTP_HOST=smtp.hospital.com
SMTP_PORT=587
SMTP_USER=noreply@hospital.com
SMTP_PASSWORD=SecureEmailPassword
SMTP_FROM=LHIMS <noreply@hospital.com>

# ============================================
# SMS Configuration (Ghana)
# ============================================
AFRICASTALKING_API_KEY=production_api_key
AFRICASTALKING_USERNAME=hospital_sms
AFRICASTALKING_SENDER_ID=LHIMS
EOF
```

### ✅ **Docker Compose Production Config**
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: lhims_db_prod
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
      - ./logs/postgres:/var/log/postgresql
    restart: unless-stopped
    networks:
      - lhims_network

  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: lhims_app_prod
    environment:
      SQLALCHEMY_DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      SECRET_KEY: ${SECRET_KEY}
      DEBUG: ${DEBUG}
      PYTHONUNBUFFERED: 1
    volumes:
      - ./app/static:/app/app/static
      - ./app/static/uploads:/app/app/static/uploads
      - ./logs/app:/app/logs
    ports:
      - "${APP_PORT}:8000"
    depends_on:
      - db
    restart: unless-stopped
    networks:
      - lhims_network

  nginx:
    image: nginx:alpine
    container_name: lhims_nginx_prod
    ports:
      - "${NGINX_HTTP_PORT}:80"
      - "${NGINX_HTTPS_PORT}:443"
    volumes:
      - ./nginx.prod.conf:/etc/nginx/nginx.conf:ro
      - ./app/static:/usr/share/nginx/html/static:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - app
    restart: unless-stopped
    networks:
      - lhims_network

volumes:
  postgres_data:
  logs_postgres:
  logs_app:
  logs_nginx:

networks:
  lhims_network:
    driver: bridge
```

## 🔍 **Monitoring and Maintenance**

### ✅ **Health Checks**
```bash
# Check all services
docker-compose ps

# Check service health
docker-compose exec app curl -f http://localhost:8000/health

# Database health check
docker-compose exec db pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}

# Nginx health check
docker-compose exec nginx wget --quiet --tries=1 --spider http://localhost/
```

### ✅ **Log Management**
```bash
# View application logs
docker-compose logs -f app

# View database logs
docker-compose logs -f db

# View nginx logs
docker-compose logs -f nginx

# Log rotation setup
sudo tee /etc/logrotate.d/lhims-docker > /dev/null << 'EOF'
/opt/lhims/logs/app/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        docker-compose restart app
}

/opt/lhims/logs/nginx/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        docker-compose restart nginx
}
EOF
```

### ✅ **Backup Procedures**
```bash
# Database backup script
cat > backup-db.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/lhims/backups"
CONTAINER_NAME="lhims_db_prod"

# Create backup
docker exec $CONTAINER_NAME pg_dump -U lhims_user lhims > $BACKUP_DIR/lhims_backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/lhims_backup_$DATE.sql

# Remove old backups (keep last 7 days)
find $BACKUP_DIR -name "lhims_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: lhims_backup_$DATE.sql.gz"
EOF

chmod +x backup-db.sh

# Setup cron job for daily backups at 2 AM
echo "0 2 * * * /opt/lhims/backup-db.sh" | sudo crontab -
```

## 🚨 **Troubleshooting**

### ✅ **Common Issues**

#### **Database Connection Issues**
```bash
# Check database container
docker-compose logs db

# Test database connection
docker-compose exec db psql -U lhims_user -d lhims -c "SELECT version();"

# Restart database
docker-compose restart db
```

#### **Application Issues**
```bash
# Check application logs
docker-compose logs app

# Restart application
docker-compose restart app

# Rebuild application
docker-compose up -d --build app
```

#### **Nginx Issues**
```bash
# Check nginx configuration
docker-compose exec nginx nginx -t

# Check nginx logs
docker-compose logs nginx

# Restart nginx
docker-compose restart nginx
```

#### **Port Conflicts**
```bash
# Check port usage
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :443

# Kill conflicting processes
sudo kill -9 <PID>

# Change ports in .env
sed -i 's/NGINX_HTTP_PORT=80/NGINX_HTTP_PORT=8080/' .env
```

## 📊 **Performance Optimization**

### ✅ **Database Optimization**
```sql
-- PostgreSQL performance settings in docker-compose.yml
-- Already configured for production:
max_connections=200
shared_buffers=256MB
effective_cache_size=1GB
maintenance_work_mem=64MB
```

### ✅ **Application Optimization**
```yaml
# Docker Compose optimizations:
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
    restart_policy: unless-stopped
```

### ✅ **Nginx Optimization**
```nginx
# Already configured in nginx.conf:
worker_processes auto;
client_max_body_size 100M;
gzip on;
keepalive_timeout 65;
```

## 🔒 **Security Hardening**

### ✅ **Container Security**
```bash
# Run containers as non-root user
# Already configured in Dockerfile

# Use read-only volumes where possible
# Already configured in docker-compose.yml

# Remove unnecessary packages
# Already configured in multi-stage Dockerfile
```

### ✅ **Network Security**
```bash
# Isolate containers in custom network
# Already configured: lhims_network

# Use internal communication
# App connects to db via container name

# Firewall rules
sudo ufw allow from 10.0.0.0/8 to any port 80
sudo ufw allow from 10.0.0.0/8 to any port 443
```

## 📋 **Deployment Checklist**

### ✅ **Pre-Deployment**
- [ ] Ubuntu server updated and secured
- [ ] Docker and Docker Compose installed
- [ ] SSH keys configured
- [ ] Firewall rules configured
- [ ] SSL certificates obtained
- [ ] Environment variables configured
- [ ] Repository cloned and updated

### ✅ **Deployment**
- [ ] Environment file created and secured
- [ ] Docker images built successfully
- [ ] All containers started without errors
- [ ] Database migrations completed
- [ ] Health checks passing
- [ ] Nginx proxy working
- [ ] SSL certificates configured

### ✅ **Post-Deployment**
- [ ] Application accessible via HTTP/HTTPS
- [ ] Database connectivity verified
- [ ] Static files serving correctly
- [ ] Logs being collected
- [ ] Backup procedures tested
- [ ] Monitoring configured
- [ ] Performance baseline established

## 🎯 **Production Access**

### ✅ **URLs**
- **HTTP**: http://<server-ip>/
- **HTTPS**: https://<server-ip>/
- **API**: http://<server-ip>/docs
- **Health**: http://<server-ip>/health

### ✅ **Admin Access**
- **Default Admin**: Created via seed script
- **Username**: admin
- **Password**: Set during deployment
- **Access**: http://<server-ip>/login

## 🚀 **Go-Live Commands**

### ✅ **Quick Deployment**
```bash
# Complete deployment in 5 commands
git clone <repo> lhims && cd lhims
cp env.example .env && nano .env  # Configure
docker-compose up -d --build
docker-compose exec app alembic upgrade head
docker-compose exec app python scripts/create_admin.py
```

### ✅ **Production Monitoring**
```bash
# Monitor all services
watch docker-compose ps

# Monitor logs
docker-compose logs -f

# Check resource usage
docker stats
```

This guide provides DevOps team with complete production-ready deployment procedures for LHIMS using Docker on Ubuntu.
