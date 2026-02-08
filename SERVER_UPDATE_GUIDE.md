# LHIMS Server Update Guide

**Date**: February 6, 2026  
**Purpose**: Complete guide for updating LHIMS server with changes  
**Target**: Developers who have made changes and need to deploy them

## 🚀 Quick Start Guide

### 🔄 **Step 1: Stop Current Server**
```bash
# Stop any running uvicorn processes
pkill -f uvicorn

# Verify no processes are running
ps aux | grep uvicorn
```

### 🔄 **Step 2: Activate Virtual Environment**
```bash
# Navigate to project directory
cd /Users/macbookpro/Documents/seproject/python_projects/lhims

# Activate virtual environment
source venv/bin/activate

# Verify activation
which python  # Should show venv/bin/python
```

### 🔄 **Step 3: Install Dependencies (if needed)**
```bash
# Install any new dependencies
pip install -r requirements.txt

# Or install specific packages
pip install package_name
```

### 🔄 **Step 4: Run Database Migrations**
```bash
# Apply any pending database migrations
alembic upgrade head

# Check migration status
alembic current

# Create specific migration if needed
alembic revision --autogenerate -m "Description of changes"
```

### 🔄 **Step 5: Start Server in Development Mode**
```bash
# Start with auto-reload for development
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Start without auto-reload for production
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Start with specific workers
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 🔄 **Step 6: Verify Server is Running**
```bash
# Check if server is responding
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs

# Check logs
tail -f logs/uvicorn.log

# Test specific endpoints
curl -X GET http://localhost:8000/api/v1/patients
```

## 🏗 **Development Workflow**

### 📋 **Making Changes**
1. **Code Changes**
   ```bash
   # Edit your files
   vim app/routers/example.py
   nano app/models/example.py
   ```

2. **Database Changes**
   ```bash
   # Create new migration
   alembic revision --autogenerate -m "Add new feature"
   
   # Apply migration
   alembic upgrade head
   ```

3. **Template Changes**
   ```bash
   # Edit HTML templates
   vim app/templates/example.html
   ```

4. **Configuration Changes**
   ```bash
   # Update environment variables
   vim .env
   
   # Update settings in database
   python scripts/update_settings.py
   ```

### 🔄 **Testing Changes**
1. **Unit Testing**
   ```bash
   # Run all tests
   pytest tests/
   
   # Run specific test
   pytest tests/test_example.py
   ```

2. **Integration Testing**
   ```bash
   # Test API endpoints
   python test_api_endpoints.py
   
   # Test UI functionality
   python test_ui_workflows.py
   ```

3. **Manual Testing**
   ```bash
   # Test in browser
   # Navigate to http://localhost:8000
   # Login with test credentials
   # Test all major workflows
   ```

## 🐳 **Production Deployment**

### 🚀 **Option 1: Direct Deployment**
```bash
# Stop development server
pkill -f uvicorn

# Start production server
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 🐳 **Option 2: Using Gunicorn (Production Server)**
```bash
# Install gunicorn
pip install gunicorn

# Create gunicorn config
cat > gunicorn.conf.py << EOF
bind = "0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
timeout = 30
keepalive = 2
preload_app = True
EOF

# Start with gunicorn
gunicorn -c gunicorn.conf.py app.main:app
```

### 🐳 **Option 3: Using Docker**
```bash
# Build Docker image
docker build -t lhims .

# Run with docker-compose
docker-compose up -d

# Or run single container
docker run -d -p 8000:8000 --name lhims lhims
```

### 🐳 **Option 4: Using Systemd (Linux Service)**
```bash
# Create systemd service
sudo cat > /etc/systemd/system/lhims.service << EOF
[Unit]
Description=LHIMS Hospital Management System
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/path/to/lhims
Environment=PATH=/path/to/venv/bin
ExecStart=/path/to/venv/bin/gunicorn -c gunicorn.conf.py app.main:app
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable lhims
sudo systemctl start lhims
sudo systemctl status lhims
```

## 🔧 **Configuration Management**

### 📝 **Environment Variables**
```bash
# .env file example
cat > .env << EOF
DATABASE_URL=postgresql://username:password@localhost:5432/lhims
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=development
DEBUG=true
EOF

# Production .env
cat > .env.production << EOF
DATABASE_URL=postgresql://username:password@localhost:5432/lhims
SECRET_KEY=your-production-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
ENVIRONMENT=production
DEBUG=false
EOF
```

### 🗄️ **Database Configuration**
```bash
# PostgreSQL setup
sudo -u postgres psql -c "CREATE DATABASE lhims;"
sudo -u postgres createuser -P lhims
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE lhims TO lhims;"

# Update connection string in .env
# For production, use connection pooling
DATABASE_URL=postgresql://lhims:password@localhost:5432/lhims?pool_size=20&max_overflow=20
```

## 📊 **Monitoring and Logging**

### 📋 **Application Logs**
```bash
# Enable detailed logging
export LOG_LEVEL=INFO

# Start with logging
python -m uvicorn app.main:app --log-level info --log-file logs/uvicorn.log

# View logs in real-time
tail -f logs/uvicorn.log

# Rotate logs
logrotate -f /etc/logrotate.d/lhims /var/log/lhims/*.log
```

### 📈 **Performance Monitoring**
```bash
# Monitor resource usage
htop
iostat
df -h

# Monitor application metrics
curl -s http://localhost:8000/metrics

# Check database connections
psql -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"
```

## 🔒 **Security Considerations**

### 🛡️ **Production Security**
```bash
# Use HTTPS in production
# Configure reverse proxy (nginx/apache)
# Set up SSL certificates
# Enable security headers

# Environment variables security
export ENVIRONMENT=production
export DEBUG=false

# Database security
# Use connection strings with SSL
# Enable database SSL
# Regular security updates
pip install --upgrade pip
```

### 🔐 **Authentication & Authorization**
```bash
# Test role-based access
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/patients

# Test session management
curl -c "curl -b session_cookie=value" http://localhost:8000/dashboard

# Verify permissions
python scripts/check_permissions.py
```

## 🔄 **Rollback Procedures**

### ⚠️ **If Something Goes Wrong**
```bash
# 1. Stop server immediately
pkill -f uvicorn

# 2. Check last known good state
git log --oneline -10

# 3. Rollback changes
git checkout last-good-commit

# 4. Revert database if needed
alembic downgrade -1

# 5. Restart server
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 📋 **Database Backup Before Changes**
```bash
# Backup current database
pg_dump lhims > backup_before_changes.sql

# Backup specific tables
pg_dump lhims -t patients > backup_patients.sql
```

## 🐛 **Troubleshooting Common Issues**

### ❌ **Server Won't Start**
```bash
# Check port usage
lsof -i :8000

# Check if another process is using port
netstat -tulpn | grep :8000

# Kill stuck processes
pkill -9 uvicorn

# Clear Python cache
find . -name "*.pyc" -delete
```

### ❌ **Database Connection Issues**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U lhims -d lhims

# Check connection string
python -c "from app.db.database import engine; engine.connect()"

# Reset connection pool
sudo systemctl restart postgresql
```

### ❌ **Permission Issues**
```bash
# Check file permissions
ls -la app/
chmod -R 755 app/

# Check database permissions
sudo -u postgres psql -c "\l"

# Fix ownership
sudo chown -R www-data:www-data /path/to/lhims
```

### ❌ **Template Errors**
```bash
# Check Jinja2 syntax
python -c "from jinja2 import Environment; Environment(loader=FileSystemLoader('.')).get_template('test.html')"

# Check template paths
python -c "from fastapi.templating import Jinja2Templates; print(Jinja2Templates(directory='app/templates'))"
```

## 📦 **Backup and Recovery**

### 💾 **Automated Backups**
```bash
# Set up cron jobs for backups
crontab -e

# Example cron entries (edit with crontab -e)
0 2 * * * /path/to/lhims/scripts/backup_to_drive.py

# Manual backup
python scripts/backup_to_drive.py

# Database backup
pg_dump lhims > backup_$(date +%Y%m%d).sql
```

### 🔄 **Zero-Downtime Deployment**
```bash
# Blue-green deployment strategy
# Deploy to staging first
# Test thoroughly
# Switch traffic to new version
# Keep old version ready for rollback

# Health check endpoint
@router.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}
```

## 📋 **Testing Checklist**

### ✅ **Pre-Deployment Checklist**
- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] Database migrations applied
- [ ] Environment variables set
- [ ] SSL certificates configured
- [ ] Backup procedures tested
- [ ] Monitoring tools configured
- [ ] Rollback plan ready

### ✅ **Post-Deployment Checklist**
- [ ] Server responding correctly
- [ ] Database connections working
- [ ] Authentication functioning
- [ ] Key workflows tested
- [ ] Performance metrics normal
- [ ] Error handling working
- [ ] Logs being collected
- [ ] Backups running successfully

## 🎯 **Best Practices**

### 📋 **Code Quality**
```bash
# Run code formatting
black app/ tests/
isort app/ tests/
flake8 app/ tests/

# Type checking
mypy app/

# Security scanning
bandit -r app/
```

### 🔄 **Version Control**
```bash
# Tag releases
git tag -a v1.0.0 -m "Release version 1.0.0"

# Create release branch
git checkout -b release/v1.0.0

# Merge to main
git checkout main
git merge release/v1.0.0

# Push changes
git push origin main
```

### 📊 **Performance Optimization**
```bash
# Profile application
python -m cProfile -o profile.stats app.main:app

# Use connection pooling
DATABASE_URL=postgresql://user:pass@localhost/lhims?pool_size=20&max_overflow=20

# Enable caching
pip install redis
# Configure Redis cache in settings
```

## 🆘 **Emergency Procedures**

### 🚨 **Critical Issues**
```bash
# Immediate server stop
pkill -f uvicorn

# Switch to maintenance mode
export MAINTENANCE_MODE=true

# Display maintenance page
# Configure reverse proxy to serve maintenance.html

# Database maintenance
sudo -u postgres psql -c "UPDATE pg_database SET datallowconn = false;"
```

### 📞 **Communication Plan**
```bash
# Notify stakeholders
echo "Server maintenance in progress" | mail -s "Server Alert" admin@hospital.com

# Update status page
# Post updates to status page
curl -X POST -d "status=maintenance" https://status.hospital.com/update

# Document incident
echo "$(date): Server maintenance started" >> /var/log/lhims/incidents.log
```

---

## 🎯 **Quick Reference Commands**

### 🔄 **Development Commands**
```bash
# Start development server
python -m uvicorn app.main:app --reload

# Run tests
pytest

# Database operations
alembic upgrade head
alembic revision --autogenerate -m "changes"

# Create superuser
python scripts/create_admin.py
```

### 🚀 **Production Commands**
```bash
# Start production server
gunicorn -c gunicorn.conf.py app.main:app

# Check logs
tail -f /var/log/lhims/uvicorn.log

# Database backup
pg_dump lhims > backup_$(date +%Y%m%d).sql

# Health check
curl http://localhost:8000/health
```

---

**This guide provides comprehensive procedures for updating your LHIMS server in any environment. Choose the sections relevant to your specific needs and follow the step-by-step instructions.**

---

*Guide created on February 6, 2026*  
*System: LHIMS (Local Health Information Management System)*  
*Purpose: Server Update and Deployment Guide*
