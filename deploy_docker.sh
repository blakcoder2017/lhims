#!/bin/bash

# LHIMS Docker Deployment Script
# Usage: ./deploy_docker.sh [start|stop|restart|logs|status|install]
# 
# Quick Start Options:
#   ./deploy_docker.sh start          # Start services with auto-initialization
#   ./deploy_docker.sh install        # Auto-generate .env and start (one command)
#   ./deploy_docker.sh start --demo   # Quick demo mode with default values

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Docker compose file path
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

# Function to generate secret key
generate_secret_key() {
    openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))"
}

# Function to generate random password
generate_password() {
    openssl rand -base64 24 2>/dev/null | tr -d '\n' || python3 -c "import secrets; print(secrets.token_urlsafe(16))"
}

# Function to check Docker and Docker Compose
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed!${NC}"
        echo -e "${YELLOW}Please install Docker: https://docs.docker.com/get-docker/${NC}"
        exit 1
    fi

    if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Error: Docker Compose is not installed!${NC}"
        echo -e "${YELLOW}Please install Docker Compose: https://docs.docker.com/compose/install/${NC}"
        exit 1
    fi
}

# Function to create .env file with default values
create_env_file() {
    if [ -f "$PROJECT_DIR/.env" ]; then
        echo -e "${YELLOW}.env file already exists. Using existing configuration.${NC}"
        return 0
    fi
    
    echo -e "${GREEN}Creating .env file with default configuration...${NC}"
    
    # Generate secure defaults
    SECRET_KEY=$(generate_secret_key)
    DB_PASSWORD=$(generate_password)
    
    cat > "$PROJECT_DIR/.env" << EOF
# LHIMS Docker Environment Variables
# Auto-generated on first run

# ============================================
# Database Configuration
# ============================================
POSTGRES_DB=lhims
POSTGRES_USER=lhims_user
POSTGRES_PASSWORD=$DB_PASSWORD
POSTGRES_PORT=5432

# ============================================
# Application Configuration
# ============================================
APP_TITLE=LHIMS
VERSION=2.0
DEBUG=False

# ============================================
# Security Settings
# ============================================
SECRET_KEY=$SECRET_KEY
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ============================================
# Port Configuration
# ============================================
APP_PORT=8000
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443

# ============================================
# Email Configuration (Optional)
# ============================================
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=

# ============================================
# SMS Configuration (Optional - for Ghana)
# ============================================
AFRICASTALKING_API_KEY=
AFRICASTALKING_USERNAME=
AFRICASTALKING_SENDER_ID=LHIMS

# ============================================
# DHIMS2 Integration Configuration
# ============================================
DHIMS2_BASE_URL=
DHIMS2_USERNAME=
DHIMS2_PASSWORD=
DHIMS2_TIMEOUT_SECONDS=30
DHIMS2_VERIFY_TLS=true
DHIMS2_MAX_RETRIES=5
DHIMS2_BACKOFF_SECONDS=2
DHIMS2_INSTANCE_NAME=production
DHIMS2_DATA_LOCK_DAYS=60
DHIMS2_DRY_RUN=false
EOF
    
    echo -e "${GREEN}.env file created with secure default values.${NC}"
    echo -e "${YELLOW}You can edit .env file to customize settings.${NC}"
}

# Function to wait for database to be ready
wait_for_db() {
    echo -e "${GREEN}Waiting for database to be ready...${NC}"
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U lhims_user -d lhims &> /dev/null; then
            echo -e "${GREEN}Database is ready!${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}Database failed to start within expected time.${NC}"
    return 1
}

# Function to initialize database
init_db() {
    echo -e "${GREEN}Initializing database...${NC}"
    docker compose -f "$COMPOSE_FILE" exec app python init_db.py
}

# Function to run database migrations
migrate() {
    echo -e "${GREEN}Running database migrations...${NC}"
    docker compose -f "$COMPOSE_FILE" exec app alembic upgrade head || true
}

# Function to run seed scripts
seed() {
    echo -e "${GREEN}Running seed scripts...${NC}"
    docker compose -f "$COMPOSE_FILE" exec app python scripts/seed_admin.py 2>/dev/null || true
    echo -e "${GREEN}Seeding complete.${NC}"
}

# Function to do full initialization (init + migrate + seed)
full_init() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Initializing LHIMS Database${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    wait_for_db
    
    echo -e "${GREEN}[1/3] Creating database tables...${NC}"
    init_db
    
    echo -e "${GREEN}[2/3] Running migrations...${NC}"
    migrate
    
    echo -e "${GREEN}[3/3] Seeding initial data...${NC}"
    seed
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Initialization Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
}

# Function to start the application
start() {
    local demo_mode="${1:-}"
    
    echo -e "${GREEN}Starting LHIMS Docker services...${NC}"
    check_docker
    
    # Create necessary directories
    mkdir -p uploads backups logs
    
    # Check for demo mode
    if [ "$demo_mode" = "--demo" ]; then
        echo -e "${YELLOW}Running in QUICK DEMO mode${NC}"
        # Use demo-specific quick settings
        export DEBUG=True
    fi
    
    # Build and start containers
    docker compose -f "$COMPOSE_FILE" up -d --build
    
    # Wait for services to be healthy
    echo -e "${GREEN}Waiting for services to be healthy...${NC}"
    sleep 10
    
    # Check if this is first run (no existing data)
    local is_first_run=false
    if ! docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U lhims_user -d lhims -c "\dt" &> /dev/null; then
        is_first_run=true
    fi
    
    # Run full initialization if first run
    if [ "$is_first_run" = true ]; then
        echo -e "${YELLOW}First run detected. Running full initialization...${NC}"
        full_init
    else
        echo -e "${YELLOW}Existing database found. Skipping initialization.${NC}"
        echo -e "${YELLOW}To re-initialize, run: ./deploy_docker.sh init-db${NC}"
    fi
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}LHIMS services started successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "${YELLOW}Application: http://localhost:${APP_PORT:-8000}${NC}"
    echo -e "${YELLOW}Health Check: http://localhost:${APP_PORT:-8000}/health${NC}"
    echo -e "${YELLOW}Default Login: admin / admin123${NC}"
}

# Function for one-command install (auto-env + start)
install() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  LHIMS One-Command Installer${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    check_docker
    create_env_file
    start
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

# Function to initialize database (standalone)
init_db() {
    echo -e "${GREEN}Initializing database...${NC}"
    docker compose -f "$COMPOSE_FILE" exec app python init_db.py
}

# Function to run seed scripts (standalone)
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
    echo "  install     - One-command install (auto-create .env + start)"
    echo "  start       - Build and start all services"
    echo "  start --demo - Start in quick demo mode (debug enabled)"
    echo "  stop        - Stop all services"
    echo "  restart     - Restart all services"
    echo "  logs        - View logs (use 'all' for all services)"
    echo "  status      - Show service status"
    echo "  init-db     - Initialize the database"
    echo "  migrate     - Run Alembic migrations"
    echo "  seed        - Run seed scripts"
    echo "  full-init   - Run init-db + migrate + seed (full initialization)"
    echo "  test        - Run lab template tests"
    echo "  help        - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 install              # One-command install"
    echo "  $0 start                # Start services"
    echo "  $0 start --demo         # Quick demo mode"
    echo "  $0 logs                 # View app logs"
    echo "  $0 logs all             # View all logs"
}

# Main script logic
case "${1:-help}" in
    install)
        install
        ;;
    start)
        start "${2:-}"
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
    full-init)
        full_init
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
