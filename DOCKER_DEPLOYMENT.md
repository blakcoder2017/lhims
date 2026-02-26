# LHIMS Docker Deployment Guide

This document describes how to deploy LHIMS (Laboratory and Hospital Information Management System) using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+ 
- Docker Compose 2.0+
- At least 2GB of RAM
- At least 10GB of disk space

## Quick Start

### 1. Configure Environment Variables

Copy the example environment file and update the values:

```bash
cp env.example .env
nano .env
```

Important values to update:
- `POSTGRES_PASSWORD` - Set a strong password for PostgreSQL
- `SECRET_KEY` - Generate a secure secret key (use: `openssl rand -hex 32`)

### 2. Start the Application

Using the deployment script:

```bash
./deploy_docker.sh start
```

Or using docker compose directly:

```bash
docker compose up -d --build
```

### 3. Access the Application

After starting, access LHIMS at:
- **URL**: http://localhost:8000
- **Health Check**: http://localhost:8000/health

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
./deploy_docker.sh start
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

### Initialize Database
```bash
./deploy_docker.sh init-db
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
