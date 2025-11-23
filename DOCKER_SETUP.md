# 🐳 LHIMS Docker Deployment Guide

Complete guide for deploying LHIMS using Docker and Docker Compose.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Setup](#detailed-setup)
4. [Configuration](#configuration)
5. [Management Commands](#management-commands)
6. [Troubleshooting](#troubleshooting)
7. [Production Deployment](#production-deployment)

---

## ✅ Prerequisites

Before starting, ensure you have:

- **Docker** (version 20.10 or later)
- **Docker Compose** (version 2.0 or later)
- **At least 4GB RAM** (8GB recommended)
- **At least 20GB free disk space**

### Install Docker and Docker Compose

**On Ubuntu/Debian:**

```bash
# Update package index
sudo apt update

# Install prerequisites
sudo apt install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add your user to docker group (to run without sudo)
sudo usermod -aG docker $USER

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Verify installation
docker --version
docker compose version
```

**On macOS:**

```bash
# Install Docker Desktop from:
# https://www.docker.com/products/docker-desktop
```

**On Windows:**

```bash
# Install Docker Desktop from:
# https://www.docker.com/products/docker-desktop
```

---

## 🚀 Quick Start

### Step 1: Clone/Copy Application

```bash
# Navigate to your project directory
cd /path/to/lhims
```

### Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit environment file
nano .env
```

**Important:** Update these values in `.env`:
- `POSTGRES_PASSWORD` - Strong password for database
- `SECRET_KEY` - Generate with: `openssl rand -hex 32`

### Step 3: Build and Start

```bash
# Build and start all services
docker compose up -d

# View logs
docker compose logs -f
```

### Step 4: Access Application

Open your browser and navigate to:
- **Local:** `http://localhost`
- **Network:** `http://your-server-ip`

**Default Admin:**
- Username: `admin`
- Password: `admin123` (change immediately!)

---

## 📝 Detailed Setup

### Step 1: Prepare Environment File

```bash
# Copy example file
cp .env.example .env

# Generate secret key
openssl rand -hex 32
```

Edit `.env` file with your values:

```env
POSTGRES_PASSWORD=your_secure_password_here
SECRET_KEY=your_generated_secret_key_here
```

### Step 2: Build Docker Images

```bash
# Build all images
docker compose build

# Or build specific service
docker compose build app
```

### Step 3: Start Services

```bash
# Start all services in detached mode
docker compose up -d

# Start specific service
docker compose up -d db
docker compose up -d app
docker compose up -d nginx
```

### Step 4: Run Database Migrations

Migrations run automatically on container start, but you can run manually:

```bash
# Run migrations
docker compose exec app alembic upgrade head

# Check migration status
docker compose exec app alembic current
```

### Step 5: Seed Initial Data (Optional)

```bash
# Seed permissions
docker compose exec app python scripts/seed_permissions.py

# Seed admin user
docker compose exec app python scripts/seed_admin.py
```

### Step 6: Verify Services

```bash
# Check all services are running
docker compose ps

# Check logs
docker compose logs

# Check specific service logs
docker compose logs app
docker compose logs db
docker compose logs nginx
```

---

## ⚙️ Configuration

### Environment Variables

All configuration is done through the `.env` file. Key variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | Database password | **Required** |
| `SECRET_KEY` | Application secret key | **Required** |
| `APP_PORT` | Application port | 8000 |
| `NGINX_HTTP_PORT` | HTTP port | 80 |
| `POSTGRES_PORT` | Database port | 5432 |
| `DEBUG` | Debug mode | False |

### Port Configuration

Default ports:
- **80** - HTTP (Nginx)
- **443** - HTTPS (Nginx, if configured)
- **8000** - FastAPI application (internal)
- **5432** - PostgreSQL (internal)

To change ports, edit `.env`:
```env
NGINX_HTTP_PORT=8080
APP_PORT=8001
```

### Database Configuration

Database is automatically created on first start. Data persists in Docker volume `postgres_data`.

**Access database directly:**
```bash
docker compose exec db psql -U lhims_user -d lhims
```

### Static Files

Static files are mounted as volumes:
- `./app/static` → `/app/app/static` (read-only)
- `./app/static/uploads` → `/app/app/static/uploads` (read-write)

### Backups

Backup directory is mounted:
- `./backups` → `/app/backups`

---

## 🛠️ Management Commands

### Start/Stop Services

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Stop and remove volumes (WARNING: deletes database!)
docker compose down -v

# Restart specific service
docker compose restart app

# Restart all services
docker compose restart
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f app
docker compose logs -f db
docker compose logs -f nginx

# Last 100 lines
docker compose logs --tail=100 app

# Since specific time
docker compose logs --since 30m app
```

### Execute Commands

```bash
# Run command in app container
docker compose exec app <command>

# Examples:
docker compose exec app python scripts/seed_admin.py
docker compose exec app alembic upgrade head
docker compose exec app python -c "from app.db.database import SessionLocal; print('DB OK')"

# Access shell
docker compose exec app bash
docker compose exec db psql -U lhims_user -d lhims
```

### Update Application

```bash
# Pull latest code (if using git)
git pull

# Rebuild and restart
docker compose up -d --build

# Or rebuild specific service
docker compose build app
docker compose up -d app
```

### Database Operations

```bash
# Backup database
docker compose exec db pg_dump -U lhims_user lhims > backup_$(date +%Y%m%d).sql

# Restore database
cat backup.sql | docker compose exec -T db psql -U lhims_user lhims

# Access database shell
docker compose exec db psql -U lhims_user -d lhims
```

### Health Checks

```bash
# Check service health
docker compose ps

# Check application health
curl http://localhost/health

# Check database connection
docker compose exec app python -c "from app.db.database import SessionLocal; db = SessionLocal(); db.close(); print('OK')"
```

---

## 🔧 Troubleshooting

### Services Won't Start

**Check logs:**
```bash
docker compose logs
```

**Common issues:**

1. **Port already in use:**
```bash
# Check what's using port 80
sudo netstat -tlnp | grep :80

# Change port in .env
NGINX_HTTP_PORT=8080
```

2. **Database connection error:**
```bash
# Check database is running
docker compose ps db

# Check database logs
docker compose logs db

# Verify environment variables
docker compose exec app env | grep POSTGRES
```

3. **Permission errors:**
```bash
# Fix file permissions
sudo chown -R $USER:$USER .
chmod +x docker-entrypoint.sh
```

### Application Errors

**Check application logs:**
```bash
docker compose logs app
```

**Common fixes:**

1. **Migration errors:**
```bash
# Reset migrations (WARNING: data loss!)
docker compose down -v
docker compose up -d
```

2. **Import errors:**
```bash
# Rebuild image
docker compose build --no-cache app
docker compose up -d app
```

### Database Issues

**Database won't start:**
```bash
# Check database logs
docker compose logs db

# Check disk space
df -h

# Remove and recreate (WARNING: data loss!)
docker compose down -v
docker compose up -d
```

**Connection refused:**
```bash
# Wait for database to be ready
docker compose exec app bash -c "until pg_isready -h db -U lhims_user; do sleep 1; done"
```

### Network Issues

**Can't access from network:**
```bash
# Check firewall
sudo ufw status

# Allow Docker ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check Docker network
docker network ls
docker network inspect lhims_lhims_network
```

### Performance Issues

**High memory usage:**
```bash
# Check resource usage
docker stats

# Reduce workers in Dockerfile
# Change: --workers 4 to --workers 2
```

**Slow database:**
```bash
# Check database configuration in docker-compose.yml
# Adjust PostgreSQL settings if needed
```

---

## 🚀 Production Deployment

### Security Hardening

1. **Change default passwords:**
```bash
# Update .env with strong passwords
POSTGRES_PASSWORD=<strong_password>
SECRET_KEY=<strong_secret_key>
```

2. **Use HTTPS:**
```bash
# Generate SSL certificates
mkdir -p nginx/ssl
# Place cert.pem and key.pem in nginx/ssl/
# Uncomment HTTPS server block in nginx.conf
```

3. **Restrict database access:**
```bash
# Remove POSTGRES_PORT from docker-compose.yml
# Database will only be accessible internally
```

4. **Set proper file permissions:**
```bash
chmod 600 .env
chmod 755 docker-entrypoint.sh
```

### Performance Optimization

1. **Adjust worker count:**
Edit `Dockerfile`:
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "8"]
```

2. **Database tuning:**
Edit `docker-compose.yml` PostgreSQL command section.

3. **Resource limits:**
Add to `docker-compose.yml`:
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### Backup Strategy

**Automated backups:**

```bash
# Create backup script
nano backup.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
mkdir -p $BACKUP_DIR

# Backup database
docker compose exec -T db pg_dump -U lhims_user lhims | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

```bash
chmod +x backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /path/to/lhims/backup.sh
```

### Monitoring

**View resource usage:**
```bash
docker stats
```

**Set up monitoring (optional):**
- Use Docker monitoring tools
- Set up log aggregation
- Configure alerts

### Scaling

**Scale application:**
```bash
# Scale app to 3 instances
docker compose up -d --scale app=3
```

**Note:** Update Nginx upstream configuration for load balancing.

---

## 📊 Service Architecture

```
┌─────────────────┐
│   Client        │
│   Browser       │
└────────┬────────┘
         │
         │ HTTP/HTTPS
         │
┌────────▼────────┐
│     Nginx       │ Port 80/443
│  (Reverse Proxy)│
└────────┬────────┘
         │
         │ HTTP
         │
┌────────▼────────┐
│   FastAPI App   │ Port 8000
│   (Uvicorn)     │
└────────┬────────┘
         │
         │ PostgreSQL
         │
┌────────▼────────┐
│   PostgreSQL    │ Port 5432
│   Database      │
└─────────────────┘
```

---

## 🔄 Update Procedure

1. **Backup:**
```bash
./backup.sh
```

2. **Pull updates:**
```bash
git pull  # If using git
# Or copy new files
```

3. **Rebuild:**
```bash
docker compose build
```

4. **Update:**
```bash
docker compose up -d
```

5. **Run migrations:**
```bash
docker compose exec app alembic upgrade head
```

6. **Verify:**
```bash
docker compose ps
curl http://localhost/health
```

---

## ✅ Checklist

- [ ] Docker and Docker Compose installed
- [ ] `.env` file configured
- [ ] Services built and started
- [ ] Database migrations run
- [ ] Initial data seeded
- [ ] Application accessible
- [ ] Admin user created
- [ ] Backups configured
- [ ] Security hardened
- [ ] Monitoring set up

---

## 📞 Quick Reference

```bash
# Start
docker compose up -d

# Stop
docker compose down

# Logs
docker compose logs -f

# Restart
docker compose restart

# Rebuild
docker compose build

# Shell access
docker compose exec app bash

# Database access
docker compose exec db psql -U lhims_user -d lhims
```

---

**End of Docker Setup Guide**

For more information, see:
- `DEPLOYMENT_TUTORIAL_UBUNTU.md` - Traditional deployment
- `DEPLOYMENT_ALTERNATIVES.md` - Other deployment options
- `DETAILED_DEPLOYMENT_GUIDE.md` - Comprehensive guide

