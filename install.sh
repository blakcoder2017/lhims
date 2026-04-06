#!/bin/bash

# LHIMS Interactive Installer
# Usage: ./install.sh [--quick]
#
# This script provides an interactive way to install LHIMS
# Options:
#   --quick    Skip prompts and use default values (for testing)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Quick mode flag
QUICK_MODE=false
if [ "${1:-}" = "--quick" ]; then
    QUICK_MODE=true
fi

# Print banner
print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║     LHIMS - Laboratory & Hospital Information            ║"
    echo "║              Management System                            ║"
    echo "║                                                           ║"
    echo "║              Interactive Installer                       ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Print step
print_step() {
    echo -e "${BLUE}[$1/$2]${NC} ${GREEN}$3${NC}"
}

# Print success
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Print warning
print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Print error
print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Prompt for input
prompt() {
    local prompt_text="$1"
    local default_value="$2"
    local required="$3"
    
    if [ "$QUICK_MODE" = true ]; then
        echo "$default_value"
        return
    fi
    
    while true; do
        if [ -n "$default_value" ]; then
            read -p "$prompt_text [$default_value]: " value
            value="${value:-$default_value}"
        else
            read -p "$prompt_text: " value
        fi
        
        if [ -n "$value" ] || [ "$required" != "true" ]; then
            echo "$value"
            return
        fi
        
        print_error "This field is required. Please enter a value."
    done
}

# Prompt for password (with confirmation)
prompt_password() {
    local prompt_text="$1"
    local confirm_text="$2"
    
    if [ "$QUICK_MODE" = true ]; then
        # Generate a random password for quick mode
        openssl rand -base64 24 2>/dev/null | tr -d '\n' || python3 -c "import secrets; print(secrets.token_urlsafe(16))"
        return
    fi
    
    while true; do
        read -s -p "$prompt_text: " password
        echo
        
        if [ -z "$password" ]; then
            print_error "Password cannot be empty."
            continue
        fi
        
        read -s -p "$confirm_text: " password_confirm
        echo
        
        if [ "$password" = "$password_confirm" ]; then
            echo "$password"
            return
        fi
        
        print_error "Passwords do not match. Please try again."
    done
}

# Prompt for yes/no
prompt_yes_no() {
    local prompt_text="$1"
    local default="$2"
    
    if [ "$QUICK_MODE" = true ]; then
        echo "$default"
        return
    fi
    
    while true; do
        read -p "$prompt_text [$default]: " value
        value="${value:-$default}"
        
        case "$value" in
            y|Y|yes|Yes|YES)
                echo "yes"
                return
                ;;
            n|N|no|No|NO)
                echo "no"
                return
                ;;
        esac
        
        print_error "Please enter 'yes' or 'no'."
    done
}

# Check prerequisites
check_prerequisites() {
    print_step 1 6 "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed."
        echo ""
        echo "Please install Docker first:"
        echo "  - Ubuntu/Debian: sudo apt install docker.io docker-compose"
        echo "  - Or visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed."
        echo ""
        echo "Please install Docker Compose:"
        echo "  - Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running."
        echo ""
        echo "Please start Docker and try again."
        exit 1
    fi
    
    print_success "All prerequisites satisfied"
}

# Gather configuration
gather_configuration() {
    print_step 2 6 "Gathering configuration..."
    
    echo ""
    echo -e "${YELLOW}Please provide the following information:${NC}"
    echo ""
    
    # Application settings
    APP_TITLE=$(prompt "Application Title" "LHIMS")
    DEBUG_MODE=$(prompt_yes_no "Enable Debug Mode (for development)" "no")
    
    # Network settings
    echo ""
    echo -e "${YELLOW}Network Configuration:${NC}"
    APP_PORT=$(prompt "Application Port" "8000")
    DOMAIN=$(prompt "Domain Name (or IP address)" "localhost")
    
    # Database settings
    echo ""
    echo -e "${YELLOW}Database Configuration:${NC}"
    POSTGRES_DB=$(prompt "Database Name" "lhims")
    POSTGRES_USER=$(prompt "Database Username" "lhims_user")
    POSTGRES_PASSWORD=$(prompt_password "Database Password" "Confirm Database Password")
    POSTGRES_PORT=$(prompt "Database Port" "5432")
    
    # Security
    echo ""
    echo -e "${YELLOW}Security Configuration:${NC}"
    echo "Generating secure secret key..."
    SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
    
    # Optional integrations
    echo ""
    echo -e "${YELLOW}Optional Integrations (press Enter to skip):${NC}"
    SMTP_HOST=$(prompt "SMTP Host (for email notifications)" "")
    SMTP_PORT=$(prompt "SMTP Port" "587")
    SMTP_USER=$(prompt "SMTP Username" "")
    # Note: Password prompt skipped for simplicity
    
    DHIMS2_BASE_URL=$(prompt "DHIMS2 URL (Ghana health system)" "")
    
    print_success "Configuration gathered"
}

# Create environment file
create_environment_file() {
    print_step 3 6 "Creating environment configuration..."
    
    # Backup existing .env if it exists
    if [ -f "$PROJECT_DIR/.env" ]; then
        backup_file=".env.backup.$(date +%Y%m%d_%H%M%S)"
        print_warning "Backing up existing .env to $backup_file"
        mv "$PROJECT_DIR/.env" "$PROJECT_DIR/$backup_file"
    fi
    
    # Create new .env file
    cat > "$PROJECT_DIR/.env" << EOF
# LHIMS Environment Configuration
# Generated by interactive installer on $(date)

# ============================================
# Application Configuration
# ============================================
APP_TITLE=$APP_TITLE
VERSION=2.0
DEBUG=$DEBUG_MODE

# ============================================
# Database Configuration
# ============================================
POSTGRES_DB=$POSTGRES_DB
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_PORT=$POSTGRES_PORT

# ============================================
# Security Settings
# ============================================
SECRET_KEY=$SECRET_KEY
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ============================================
# Network Configuration
# ============================================
APP_PORT=$APP_PORT
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443

# ============================================
# Email Configuration (Optional)
# ============================================
SMTP_HOST=$SMTP_HOST
SMTP_PORT=$SMTP_PORT
SMTP_USER=$SMTP_USER
SMTP_PASSWORD=
SMTP_FROM=noreply@$DOMAIN

# ============================================
# SMS Configuration (Optional)
# ============================================
AFRICASTALKING_API_KEY=
AFRICASTALKING_USERNAME=
AFRICASTALKING_SENDER_ID=LHIMS

# ============================================
# DHIMS2 Integration (Optional)
# ============================================
DHIMS2_BASE_URL=$DHIMS2_BASE_URL
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
    
    # Secure the .env file
    chmod 600 "$PROJECT_DIR/.env"
    
    print_success "Environment file created: .env"
}

# Start services
start_services() {
    print_step 4 6 "Building and starting Docker services..."
    
    # Create required directories
    mkdir -p "$PROJECT_DIR/uploads" "$PROJECT_DIR/backups" "$PROJECT_DIR/logs"
    
    # Build and start containers
    docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d --build
    
    print_success "Docker services started"
}

# Initialize database
initialize_database() {
    print_step 5 6 "Initializing database..."
    
    # Wait for database to be ready
    echo "Waiting for database to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker compose -f "$PROJECT_DIR/docker-compose.yml" exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" &> /dev/null; then
            break
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    echo ""
    
    if [ $attempt -gt $max_attempts ]; then
        print_error "Database failed to start. Check logs with: ./deploy_docker.sh logs"
        return 1
    fi
    
    print_success "Database is ready"
    
    # Run initialization
    echo "Creating database tables..."
    docker compose -f "$PROJECT_DIR/docker-compose.yml" exec app python init_db.py
    
    echo "Running migrations..."
    docker compose -f "$PROJECT_DIR/docker-compose.yml" exec app alembic upgrade head 2>/dev/null || true
    
    echo "Seeding initial data..."
    docker compose -f "$PROJECT_DIR/docker-compose.yml" exec app python scripts/seed_admin.py 2>/dev/null || true
    
    print_success "Database initialized"
}

# Print completion message
print_completion() {
    print_step 6 6 "Installation complete!"
    
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║            LHIMS Installation Complete!                 ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Access LHIMS at:${NC}"
    echo -e "  ${GREEN}http://${DOMAIN}:${APP_PORT}${NC}"
    echo ""
    echo -e "${YELLOW}Default Login:${NC}"
    echo -e "  ${GREEN}Username:${NC} admin"
    echo -e "  ${GREEN}Password:${NC} admin123"
    echo ""
    echo -e "${YELLOW}Important:${NC}"
    echo -e "  ${RED}⚠${NC} Please change the default admin password immediately!"
    echo ""
    echo -e "${YELLOW}Management Commands:${NC}"
    echo -e "  Stop:    ${GREEN}./deploy_docker.sh stop${NC}"
    echo -e "  Start:   ${GREEN}./deploy_docker.sh start${NC}"
    echo -e "  Logs:    ${GREEN}./deploy_docker.sh logs${NC}"
    echo -e "  Status:  ${GREEN}./deploy_docker.sh status${NC}"
    echo ""
}

# Main execution
main() {
    print_banner
    
    if [ "$QUICK_MODE" = true ]; then
        echo -e "${YELLOW}Running in QUICK mode with default values${NC}"
        echo ""
    fi
    
    check_prerequisites
    gather_configuration
    create_environment_file
    start_services
    initialize_database
    print_completion
}

# Run main function
main
