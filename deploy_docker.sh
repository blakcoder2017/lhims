#!/bin/bash

# LHIMS Docker Deployment Script
# Usage: ./deploy_docker.sh [start|stop|restart|logs|status]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Docker compose file path
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

# Check if .env exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo -e "${YELLOW}Please create .env from env.example and update the values.${NC}"
    exit 1
fi

# Function to generate secret key
generate_secret_key() {
    openssl rand -hex 32
}

# Function to check Docker and Docker Compose
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed!${NC}"
        exit 1
    fi

    if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Error: Docker Compose is not installed!${NC}"
        exit 1
    fi
}

# Function to start the application
start() {
    echo -e "${GREEN}Starting LHIMS Docker services...${NC}"
    check_docker
    
    # Create necessary directories
    mkdir -p uploads backups logs
    
    # Build and start containers
    docker compose -f "$COMPOSE_FILE" up -d --build
    
    echo -e "${GREEN}LHIMS services started successfully!${NC}"
    echo -e "${YELLOW}Application is available at: http://localhost:${APP_PORT:-8000}${NC}"
    echo -e "${YELLOW}Health check endpoint: http://localhost:${APP_PORT:-8000}/health${NC}"
}

# Function to stop the application
stop() {
    echo -e "${GREEN}Stopping LHIMS Docker services...${NC}"
    docker compose -f "$COMPOSE_FILE" down
    echo -e "${GREEN}LHIMS services stopped.${NC}"
}

# Function to restart the application
restart() {
    stop
    sleep 2
    start
}

# Function to view logs
logs() {
    docker compose -f "$COMPOSE_FILE" logs -f "${1:-app}"
}

# Function to show status
status() {
    docker compose -f "$COMPOSE_FILE" ps
}

# Function to initialize database
init_db() {
    echo -e "${GREEN}Initializing database...${NC}"
    docker compose -f "$COMPOSE_FILE" exec app python init_db.py
}

# Function to run seed scripts
seed() {
    echo -e "${GREEN}Running seed scripts...${NC}"
    docker compose -f "$COMPOSE_FILE" exec app python scripts/seed_admin.py
    docker compose -f "$COMPOSE_FILE" exec app python scripts/seed_lab_templates_ghana.py
    docker compose -f "$COMPOSE_FILE" exec app python scripts/seed_pharmacy_ghana.py
    echo -e "${GREEN}Seeding complete.${NC}"
}

# Function to run database migrations
migrate() {
    echo -e "${GREEN}Running Alembic migrations...${NC}"
    docker compose -f "$COMPOSE_FILE" exec app alembic upgrade head
    echo -e "${GREEN}Migrations complete.${NC}"
}

# Function to run lab template tests
test_templates() {
    echo -e "${GREEN}Running lab template tests...${NC}"
    docker compose -f "$COMPOSE_FILE" run --rm -v "$PROJECT_DIR:/app" app pytest tests/test_lab_templates.py -v
}

# Function to show help
help() {
    echo "LHIMS Docker Deployment Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start     - Build and start all services"
    echo "  stop      - Stop all services"
    echo "  restart   - Restart all services"
    echo "  logs      - View logs (use 'all' for all services)"
    echo "  status    - Show service status"
    echo "  init-db   - Initialize the database"
    echo "  migrate   - Run Alembic migrations (alembic upgrade head)"
    echo "  seed      - Run seed scripts (admin, lab templates, pharmacy Ghana)"
    echo "  test      - Run lab template tests"
    echo "  help      - Show this help message"
}

# Main script logic
case "${1:-help}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs "${2:-app}"
        ;;
    status)
        status
        ;;
    init-db)
        init_db
        ;;
    migrate)
        migrate
        ;;
    seed)
        seed
        ;;
    test)
        test_templates
        ;;
    help|--help|-h)
        help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        help
        exit 1
        ;;
esac
