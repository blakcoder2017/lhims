# LHIMS Docker Deployment Guide

This document describes how to deploy LHIMS (Laboratory and Hospital Information Management System) using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+ 
- Docker Compose 2.0+
- At least 2GB of RAM
- At least 10GB of disk space

## Quick Start

### Option 1: One-Command Install (Recommended)
The easiest way to get started:

```bash
./install.sh
```

This interactive installer will:
- Check Docker installation
- Prompt for configuration (or use defaults with `--quick` flag)
- Auto-generate secure passwords
- Build and start all services
- Initialize the database

### Option 2: Quick Demo Mode
For fast testing with default values:

```bash
./deploy_docker.sh start --demo
```

### Option 3: Semi-Automatic
If you already have Docker installed:

```bash
# Auto-generate .env with secure defaults
./deploy_docker.sh install

# Or just start (will create .env if missing)
./deploy_docker.sh start
```

## Services Included

| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache and Celery broker |
| LHIMS App | 8000 | Main application |
| Nginx (optional) | 80 | Reverse proxy |

## Management Commands

### Start Services
```bash
./deploy_docker.sh start          # Start with auto-initialization
./deploy_docker.sh start --demo  # Quick demo mode
```

### One-Command Install
```bash
./deploy_docker.sh install       # Auto-create .env + start
```

### Interactive Installer
```bash
./install.sh                    # Full interactive installation
./install.sh --quick            # Quick mode with defaults
```

### Stop Services
```bash
./deploy_docker.sh stop
```

### Restart Services
```bash
./deploy_docker.sh restart
```

### View Logs
```bash
./deploy_docker.sh logs          # App logs
./deploy_docker.sh logs postgres # Database logs
./deploy_docker.sh logs all      # All logs
```

### Check Status
```bash
./deploy_docker.sh status
```

### Initialize Database (if needed)
```bash
./deploy_docker.sh init-db       # Initialize database tables
./deploy_docker.sh migrate       # Run migrations
./deploy_docker.sh seed          # Seed initial data
./deploy_docker.sh full-init     # Full initialization (init + migrate + seed)
```

## Directory Structure

```
lhims/
├── app/                    # Application source code
├── nginx/                  # Nginx configuration
│   ├── conf.d/
│   └── nginx.conf
├── uploads/                # Uploaded files (auto-created)
├── backups/               # Database backups (auto-created)
├── logs/                  # Application logs (auto-created)
├── Dockerfile            # Docker build instructions
├── docker-compose.yml    # Docker Compose configuration
├── .env                  # Environment variables
├── deploy_docker.sh      # Deployment management script
└── DOCKER_DEPLOYMENT.md  # This file
```

## Production Deployment

For production deployment with Nginx:

1. Update `.env` with production values
2. Generate SSL certificates (or use Let's Encrypt)
3. Update `nginx/conf.d/lhims.conf` with your domain
4. Start with Nginx:

```bash
docker compose --profile production up -d
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | lhims | Database name |
| `POSTGRES_USER` | lhims_user | Database user |
| `POSTGRES_PASSWORD` | - | Database password (required) |
| `POSTGRES_PORT` | 5432 | PostgreSQL port |
| `APP_PORT` | 8000 | Application port |
| `DEBUG` | False | Debug mode (True/False) |
| `SECRET_KEY` | - | JWT secret key (required) |
| `NGINX_HTTP_PORT` | 80 | HTTP port |
| `NGINX_HTTPS_PORT` | 443 | HTTPS port |

## Troubleshooting

### Container fails to start
Check logs for errors:
```bash
./deploy_docker.sh logs app
```

### Database connection issues
Ensure PostgreSQL container is healthy:
```bash
docker compose ps
```

### First run issues
If this is your first time running LHIMS:
```bash
./deploy_docker.sh full-init   # Run full initialization
```

### Reset everything and start fresh
```bash
./deploy_docker.sh stop
docker compose down -v  # Remove volumes
./deploy_docker.sh start
```

## Stopping and Cleanup

To stop all services:
```bash
./deploy_docker.sh stop
```

To remove all data (including database):
```bash
docker compose down -v
```

## Backup and Restore

### Backup Database
```bash
docker compose exec postgres pg_dump -U lhims_user lhims > backup.sql
```

### Restore Database
```bash
docker compose exec -T postgres psql -U lhims_user -d lhims < backup.sql
```
