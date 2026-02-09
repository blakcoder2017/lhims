# 🐳 Docker Deployment for Ubuntu 24.04.3 LTS

## Quick Docker Setup (Recommended for Easy Deployment)

This Docker setup handles the pycairo dependency automatically and provides consistent deployment across environments.

## 🚀 One-Command Deployment

```bash
# On your Ubuntu server (192.168.0.130)
git clone <your-repo-url> lhims
cd lhims
cp .env.example .env
# Edit .env with your database password and secret key
docker compose up -d
```

## 📋 Prerequisites

```bash
# Install Docker and Docker Compose
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release

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

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker
```

## ⚙️ Environment Configuration

```bash
# Copy and edit environment file
cp .env.example .env
nano .env
```

**Essential configuration:**
```env
# Database
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_USER=lhims_user
POSTGRES_DB=lhims

# Application
SECRET_KEY=your_generated_secret_key_here
HOST=0.0.0.0
PORT=8000

# Network (for LAN access)
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443
```

## 🐳 Docker Compose Configuration

The existing `docker-compose.yml` should work, but here's an optimized version for LAN deployment:

```yaml
version: '3.8'

services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-lhims}
      POSTGRES_USER: ${POSTGRES_USER:-lhims_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-lhims_user} -d ${POSTGRES_DB:-lhims}"]
      interval: 30s
      timeout: 10s
      retries: 3

  app:
    build: .
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER:-lhims_user}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB:-lhims}
      - SECRET_KEY=${SECRET_KEY}
      - HOST=0.0.0.0
      - PORT=8000
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./app/static:/app/app/static
      - ./backups:/app/backups
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "${NGINX_HTTP_PORT:-80}:80"
      - "${NGINX_HTTPS_PORT:-443}:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./app/static:/app/static:ro
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
```

## 🎨 Dockerfile (Handles Cairo Automatically)

```dockerfile
FROM python:3.12-slim

# Install system dependencies including Cairo
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p app/static/uploads app/static/files/lab_results app/static/images/radiology

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

## 🚀 Deployment Steps

```bash
# 1. Clone or copy application
git clone <your-repo-url> lhims
cd lhims

# 2. Configure environment
cp .env.example .env
nano .env

# 3. Build and start services
docker compose up -d --build

# 4. Run database migrations
docker compose exec app alembic upgrade head

# 5. Seed initial data
docker compose exec app python scripts/seed_permissions.py
docker compose exec app python scripts/seed_admin.py

# 6. Check services
docker compose ps
docker compose logs -f
```

## 🌐 Network Access

After deployment:
- **Access URL**: `http://192.168.0.130`
- **Admin Login**: Username: `admin`, Password: `admin123`

## 📊 Management Commands

```bash
# View all services
docker compose ps

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f app
docker compose logs -f db
docker compose logs -f nginx

# Restart services
docker compose restart

# Update application
git pull
docker compose up -d --build

# Access application shell
docker compose exec app bash

# Access database
docker compose exec db psql -U lhims_user -d lhims

# Backup database
docker compose exec db pg_dump -U lhims_user lhims > backup_$(date +%Y%m%d).sql

# Stop all services
docker compose down

# Stop and remove volumes (WARNING: deletes data!)
docker compose down -v
```

## 🔧 Troubleshooting

### Common Docker Issues

1. **Port conflicts:**
```bash
# Check what's using port 80
sudo netstat -tlnp | grep :80
# Change port in .env: NGINX_HTTP_PORT=8080
```

2. **Permission issues:**
```bash
# Fix file permissions
sudo chown -R $USER:$USER .
chmod +x docker-entrypoint.sh
```

3. **Container won't start:**
```bash
# Check logs
docker compose logs app

# Rebuild without cache
docker compose build --no-cache app
```

4. **Database connection issues:**
```bash
# Check database health
docker compose exec db pg_isready -U lhims_user

# Reset database (WARNING: data loss!)
docker compose down -v
docker compose up -d
```

## 🔒 Security Considerations

```bash
# Secure environment file
chmod 600 .env

# Use HTTPS in production
# Generate SSL certificates and update nginx configuration

# Regular backups
docker compose exec db pg_dump -U lhims_user lhims | gzip > backup_$(date +%Y%m%d).sql.gz

# Update regularly
docker compose pull
docker compose up -d
```

## 📈 Performance Optimization

```yaml
# Add to docker-compose.yml for production
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

## ✅ Docker Deployment Checklist

- [ ] Docker and Docker Compose installed
- [ ] Application code cloned/copied
- [ ] Environment file configured
- [ ] Services built and started
- [ ] Database migrations run
- [ ] Initial data seeded
- [ ] Application accessible from LAN
- [ ] Backup strategy configured
- [ ] Security measures implemented

---

**Docker deployment complete!** Your LHIMS is now running in containers and accessible at `http://192.168.0.130` from any computer on your LAN.
