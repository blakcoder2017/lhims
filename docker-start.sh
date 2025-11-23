#!/bin/bash
# LHIMS Docker Quick Start Script

set -e

echo "=========================================="
echo "LHIMS Docker Setup"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}.env file not found. Creating from env.example...${NC}"
    if [ -f env.example ]; then
        cp env.example .env
        echo -e "${GREEN}.env file created. Please edit it with your configuration.${NC}"
        echo ""
        echo "Important: Update these values in .env:"
        echo "  - POSTGRES_PASSWORD"
        echo "  - SECRET_KEY (generate with: openssl rand -hex 32)"
        echo ""
        read -p "Press Enter to continue after editing .env file..."
    else
        echo -e "${RED}env.example file not found. Please create .env manually.${NC}"
        exit 1
    fi
fi

# Generate SECRET_KEY if not set
if grep -q "CHANGE_THIS_TO_A_RANDOM_SECRET_KEY" .env; then
    echo -e "${YELLOW}Generating SECRET_KEY...${NC}"
    SECRET_KEY=$(openssl rand -hex 32)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
    else
        # Linux
        sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
    fi
    echo -e "${GREEN}SECRET_KEY generated and updated.${NC}"
fi

# Check if POSTGRES_PASSWORD is set
if grep -q "CHANGE_THIS_TO_A_SECURE_PASSWORD" .env; then
    echo -e "${YELLOW}Please set POSTGRES_PASSWORD in .env file.${NC}"
    read -p "Enter PostgreSQL password: " DB_PASSWORD
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$DB_PASSWORD/" .env
    else
        sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$DB_PASSWORD/" .env
    fi
    echo -e "${GREEN}POSTGRES_PASSWORD updated.${NC}"
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p app/static/uploads
mkdir -p backups
mkdir -p nginx/ssl

# Build and start services
echo ""
echo -e "${GREEN}Building Docker images...${NC}"
docker compose build

echo ""
echo -e "${GREEN}Starting services...${NC}"
docker compose up -d

# Wait for services to be ready
echo ""
echo "Waiting for services to start..."
sleep 10

# Check service status
echo ""
echo -e "${GREEN}Service Status:${NC}"
docker compose ps

# Run migrations
echo ""
echo -e "${GREEN}Running database migrations...${NC}"
docker compose exec -T app alembic upgrade head || echo "Migrations may have already been run."

# Display access information
echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Access the application at:"
echo "  - Local: http://localhost"
echo "  - Network: http://$(hostname -I | awk '{print $1}')"
echo ""
echo "Default Admin Credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "Important: Change the admin password immediately!"
echo ""
echo "Useful commands:"
echo "  - View logs: docker compose logs -f"
echo "  - Stop services: docker compose down"
echo "  - Restart services: docker compose restart"
echo "  - Access shell: docker compose exec app bash"
echo ""
echo "For more information, see DOCKER_SETUP.md"
echo ""

