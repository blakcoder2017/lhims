#!/bin/bash
# LHIMS Server Setup Script for Ubuntu
# Run this script as root or with sudo

set -e

echo "=========================================="
echo "LHIMS Server Setup Script"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

# Update system
echo -e "${GREEN}[1/10] Updating system packages...${NC}"
apt update
apt upgrade -y

# Install dependencies
echo -e "${GREEN}[2/10] Installing system dependencies...${NC}"
apt install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    postgresql \
    postgresql-contrib \
    nginx \
    git \
    curl \
    build-essential \
    libpq-dev \
    python3-dev \
    ufw

# Configure firewall
echo -e "${GREEN}[3/10] Configuring firewall...${NC}"
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Start PostgreSQL
echo -e "${GREEN}[4/10] Starting PostgreSQL...${NC}"
systemctl start postgresql
systemctl enable postgresql

# Create database and user
echo -e "${GREEN}[5/10] Creating database and user...${NC}"
read -sp "Enter PostgreSQL password for lhims_user: " DB_PASSWORD
echo

sudo -u postgres psql << EOF
CREATE DATABASE lhims;
CREATE USER lhims_user WITH PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE lhims TO lhims_user;
\c lhims
GRANT ALL ON SCHEMA public TO lhims_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO lhims_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO lhims_user;
\q
EOF

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')
echo -e "${YELLOW}Server IP detected: $SERVER_IP${NC}"
read -p "Enter server IP (or press Enter to use $SERVER_IP): " CUSTOM_IP
SERVER_IP=${CUSTOM_IP:-$SERVER_IP}

# Generate secret key
SECRET_KEY=$(openssl rand -hex 32)

echo -e "${GREEN}[6/10] Setup complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Copy application files to /opt/lhims"
echo "2. Create .env file with the following:"
echo ""
echo "SQLALCHEMY_DATABASE_URL=postgresql://lhims_user:$DB_PASSWORD@localhost:5432/lhims"
echo "SECRET_KEY=$SECRET_KEY"
echo "ALGORITHM=HS256"
echo "ACCESS_TOKEN_EXPIRE_MINUTES=1440"
echo ""
echo "3. Run: cd /opt/lhims && source venv/bin/activate && pip install -r requirements.txt"
echo "4. Run: alembic upgrade head"
echo "5. Follow the deployment tutorial for Nginx and systemd setup"
echo ""
echo -e "${GREEN}Setup script completed!${NC}"

