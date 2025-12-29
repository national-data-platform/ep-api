#!/bin/bash
# ==============================================
# NDP-EP API Installation Script
# ==============================================
# This script installs the NDP-EP API on a fresh Ubuntu system.
# It will:
#   1. Install Docker and Docker Compose (if not present)
#   2. Configure environment variables interactively
#   3. Generate .env file
#   4. Start the services
# ==============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
print_banner() {
    echo -e "${BLUE}"
    echo "========================================"
    echo "     NDP-EP API Installation Script    "
    echo "========================================"
    echo -e "${NC}"
}

# Print step
print_step() {
    echo -e "\n${GREEN}[STEP]${NC} $1"
}

# Print info
print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Print error
print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check and install Docker
install_docker() {
    print_step "Checking Docker installation..."

    if command -v docker &> /dev/null; then
        print_info "Docker is already installed: $(docker --version)"
    else
        print_info "Docker is not installed. Installing..."
        apt-get update
        apt-get install -y curl
        curl -fsSL https://get.docker.com | sh
        print_info "Docker installed successfully."
    fi
}

# Check Docker Compose
check_docker_compose() {
    print_step "Checking Docker Compose..."

    if docker compose version &> /dev/null; then
        print_info "Docker Compose is available: $(docker compose version)"
    else
        print_error "Docker Compose is not available. Please install Docker Compose plugin."
        exit 1
    fi
}

# Prompt for variable with default
prompt_var() {
    local var_name=$1
    local prompt_text=$2
    local default_value=$3
    local is_secret=${4:-false}

    if [[ "$is_secret" == "true" ]]; then
        echo -ne "${YELLOW}$prompt_text${NC}"
        if [[ -n "$default_value" ]]; then
            echo -ne " [****]: "
        else
            echo -ne ": "
        fi
        read -rs value
        echo
    else
        if [[ -n "$default_value" ]]; then
            echo -ne "${YELLOW}$prompt_text${NC} [$default_value]: "
        else
            echo -ne "${YELLOW}$prompt_text${NC}: "
        fi
        read -r value
    fi

    if [[ -z "$value" ]]; then
        value="$default_value"
    fi

    eval "$var_name=\"$value\""
}

# Configure environment
configure_environment() {
    print_step "Configuring environment variables..."
    echo -e "${BLUE}Press Enter to accept default values shown in brackets.${NC}\n"

    # Organization
    echo -e "\n${GREEN}=== Organization Settings ===${NC}"
    prompt_var "ORGANIZATION" "Organization name" "My-Organization"
    prompt_var "EP_NAME" "Endpoint name" "My-EP"

    # Catalog Backend
    echo -e "\n${GREEN}=== Catalog Backend ===${NC}"
    echo "Choose local catalog backend:"
    echo "  1) CKAN (external CKAN instance)"
    echo "  2) MongoDB (included in docker-compose)"
    echo -ne "${YELLOW}Select [1/2]${NC} [2]: "
    read -r backend_choice
    backend_choice=${backend_choice:-2}

    if [[ "$backend_choice" == "1" ]]; then
        LOCAL_CATALOG_BACKEND="ckan"
        CKAN_LOCAL_ENABLED="True"

        echo -e "\n${GREEN}=== CKAN Configuration ===${NC}"
        prompt_var "CKAN_URL" "CKAN URL" "http://localhost:5000"
        prompt_var "CKAN_API_KEY" "CKAN API Key" "" true
        prompt_var "CKAN_VERIFY_SSL" "Verify SSL certificate (True/False)" "True"
    else
        LOCAL_CATALOG_BACKEND="mongodb"
        CKAN_LOCAL_ENABLED="False"
        CKAN_URL=""
        CKAN_API_KEY=""
        CKAN_VERIFY_SSL="True"
    fi

    # MongoDB (always configured for docker-compose)
    MONGODB_CONNECTION_STRING="mongodb://admin:admin123@mongodb:27017"
    MONGODB_DATABASE="ndp_local_catalog"

    # Pre-CKAN
    echo -e "\n${GREEN}=== Pre-CKAN Configuration ===${NC}"
    echo -ne "${YELLOW}Enable Pre-CKAN integration? (y/n)${NC} [n]: "
    read -r pre_ckan_enabled
    if [[ "$pre_ckan_enabled" == "y" || "$pre_ckan_enabled" == "Y" ]]; then
        PRE_CKAN_ENABLED="True"
        prompt_var "PRE_CKAN_URL" "Pre-CKAN URL" ""
        prompt_var "PRE_CKAN_API_KEY" "Pre-CKAN API Key" "" true
        prompt_var "PRE_CKAN_VERIFY_SSL" "Verify SSL certificate (True/False)" "True"
    else
        PRE_CKAN_ENABLED="False"
        PRE_CKAN_URL=""
        PRE_CKAN_API_KEY=""
        PRE_CKAN_VERIFY_SSL="True"
    fi

    # Kafka
    echo -e "\n${GREEN}=== Kafka Configuration ===${NC}"
    echo -ne "${YELLOW}Enable Kafka streaming? (y/n)${NC} [y]: "
    read -r kafka_enabled
    kafka_enabled=${kafka_enabled:-y}
    if [[ "$kafka_enabled" == "y" || "$kafka_enabled" == "Y" ]]; then
        KAFKA_CONNECTION="True"
        KAFKA_HOST="kafka"
        KAFKA_PORT="9093"
    else
        KAFKA_CONNECTION="False"
        KAFKA_HOST=""
        KAFKA_PORT=""
    fi

    # S3/MinIO
    echo -e "\n${GREEN}=== S3 Storage Configuration ===${NC}"
    echo -ne "${YELLOW}Enable S3 storage (MinIO)? (y/n)${NC} [y]: "
    read -r s3_enabled
    s3_enabled=${s3_enabled:-y}
    if [[ "$s3_enabled" == "y" || "$s3_enabled" == "Y" ]]; then
        S3_ENABLED="True"
        S3_ENDPOINT="minio:9000"
        prompt_var "S3_ACCESS_KEY" "S3 Access Key" "minioadmin"
        prompt_var "S3_SECRET_KEY" "S3 Secret Key" "minioadmin123" true
        S3_SECURE="False"
        S3_REGION="us-east-1"
    else
        S3_ENABLED="False"
        S3_ENDPOINT=""
        S3_ACCESS_KEY=""
        S3_SECRET_KEY=""
        S3_SECURE="False"
        S3_REGION=""
    fi

    # JupyterLab
    echo -e "\n${GREEN}=== JupyterLab Configuration ===${NC}"
    echo -ne "${YELLOW}Enable JupyterLab? (y/n)${NC} [y]: "
    read -r jupyter_enabled
    jupyter_enabled=${jupyter_enabled:-y}
    if [[ "$jupyter_enabled" == "y" || "$jupyter_enabled" == "Y" ]]; then
        USE_JUPYTERLAB="True"
        JUPYTER_URL="http://jupyterlab:8888"
    else
        USE_JUPYTERLAB="False"
        JUPYTER_URL=""
    fi

    # Pelican Federation
    echo -e "\n${GREEN}=== Pelican Federation ===${NC}"
    echo -ne "${YELLOW}Enable Pelican federation? (y/n)${NC} [n]: "
    read -r pelican_enabled
    if [[ "$pelican_enabled" == "y" || "$pelican_enabled" == "Y" ]]; then
        PELICAN_ENABLED="True"
        PELICAN_DIRECT_READS="False"
    else
        PELICAN_ENABLED="False"
        PELICAN_DIRECT_READS="False"
    fi

    # Authentication
    echo -e "\n${GREEN}=== Authentication ===${NC}"
    prompt_var "AUTH_API_URL" "Auth API URL" "https://idp.nationaldataplatform.org/temp/information"
    prompt_var "TEST_TOKEN" "Test token (leave empty for production)" "testing_token"

    # Advanced settings
    ROOT_PATH=""
    METRICS_INTERVAL_SECONDS="3300"
    ENABLE_GROUP_BASED_ACCESS="False"
    GROUP_NAMES=""
    PELICAN_FEDERATION_URL=""
}

# Generate .env file
generate_env_file() {
    print_step "Generating .env file..."

    if [[ -f .env ]]; then
        echo -e "${YELLOW}A .env file already exists. Overwrite? (y/n)${NC} [n]: "
        read -r overwrite
        if [[ "$overwrite" != "y" && "$overwrite" != "Y" ]]; then
            print_info "Keeping existing .env file."
            return
        fi
    fi

    cat > .env << EOF
# ==============================================
# API CONFIGURATION
# ==============================================

ROOT_PATH=$ROOT_PATH

# ==============================================
# ORGANIZATION
# ==============================================

ORGANIZATION="$ORGANIZATION"
EP_NAME="$EP_NAME"

# ==============================================
# METRICS CONFIGURATION
# ==============================================

METRICS_INTERVAL_SECONDS=$METRICS_INTERVAL_SECONDS

# ==============================================
# ACCESS CONTROL
# ==============================================

ENABLE_GROUP_BASED_ACCESS=$ENABLE_GROUP_BASED_ACCESS
GROUP_NAMES=$GROUP_NAMES

# ==============================================
# LOCAL CATALOG CONFIGURATION
# ==============================================

LOCAL_CATALOG_BACKEND=$LOCAL_CATALOG_BACKEND
CKAN_LOCAL_ENABLED=$CKAN_LOCAL_ENABLED

# ==============================================
# CKAN Configuration
# ==============================================

CKAN_URL=$CKAN_URL
CKAN_API_KEY=$CKAN_API_KEY
CKAN_VERIFY_SSL=$CKAN_VERIFY_SSL

# ==============================================
# MongoDB Configuration
# ==============================================

MONGODB_CONNECTION_STRING=$MONGODB_CONNECTION_STRING
MONGODB_DATABASE=$MONGODB_DATABASE

# ==============================================
# Pre-CKAN Configuration
# ==============================================

PRE_CKAN_ENABLED=$PRE_CKAN_ENABLED
PRE_CKAN_URL=$PRE_CKAN_URL
PRE_CKAN_API_KEY=$PRE_CKAN_API_KEY
PRE_CKAN_VERIFY_SSL=$PRE_CKAN_VERIFY_SSL

# ==============================================
# Kafka Configuration
# ==============================================

KAFKA_CONNECTION=$KAFKA_CONNECTION
KAFKA_HOST=$KAFKA_HOST
KAFKA_PORT=$KAFKA_PORT

# ==============================================
# Authentication
# ==============================================

TEST_TOKEN=$TEST_TOKEN
AUTH_API_URL=$AUTH_API_URL

# ==============================================
# JupyterLab
# ==============================================

USE_JUPYTERLAB=$USE_JUPYTERLAB
JUPYTER_URL=$JUPYTER_URL

# ==============================================
# S3 Storage
# ==============================================

S3_ENABLED=$S3_ENABLED
S3_ENDPOINT=$S3_ENDPOINT
S3_ACCESS_KEY=$S3_ACCESS_KEY
S3_SECRET_KEY=$S3_SECRET_KEY
S3_SECURE=$S3_SECURE
S3_REGION=$S3_REGION

# ==============================================
# Pelican Federation
# ==============================================

PELICAN_ENABLED=$PELICAN_ENABLED
PELICAN_FEDERATION_URL=$PELICAN_FEDERATION_URL
PELICAN_DIRECT_READS=$PELICAN_DIRECT_READS
EOF

    print_info ".env file generated successfully."
}

# Start services
start_services() {
    print_step "Starting services with Docker Compose..."

    docker compose up -d

    print_info "Waiting for services to be ready..."
    sleep 10

    # Check if API is running
    if curl -s http://localhost:8002/ > /dev/null 2>&1; then
        print_info "API is running at http://localhost:8002"
    else
        print_info "API is starting... Check with: docker compose logs api"
    fi
}

# Print summary
print_summary() {
    echo -e "\n${GREEN}========================================"
    echo "     Installation Complete!"
    echo -e "========================================${NC}\n"

    echo -e "${BLUE}Services:${NC}"
    echo "  - API:        http://localhost:8002"
    echo "  - API Docs:   http://localhost:8002/docs"

    if [[ "$USE_JUPYTERLAB" == "True" ]]; then
        echo "  - JupyterLab: http://localhost:8888"
    fi

    if [[ "$S3_ENABLED" == "True" ]]; then
        echo "  - MinIO:      http://localhost:9003 (Console)"
    fi

    if [[ "$KAFKA_CONNECTION" == "True" ]]; then
        echo "  - Kafka UI:   http://localhost:8081"
    fi

    echo -e "\n${BLUE}Useful commands:${NC}"
    echo "  docker compose ps        # Check running services"
    echo "  docker compose logs -f   # View logs"
    echo "  docker compose down      # Stop services"
    echo "  docker compose restart   # Restart services"

    echo -e "\n${YELLOW}Note: Some services may take a few minutes to fully start.${NC}"
}

# Main
main() {
    print_banner
    install_docker
    check_docker_compose
    configure_environment
    generate_env_file

    echo -e "\n${YELLOW}Start the services now? (y/n)${NC} [y]: "
    read -r start_now
    start_now=${start_now:-y}

    if [[ "$start_now" == "y" || "$start_now" == "Y" ]]; then
        start_services
    fi

    print_summary
}

main "$@"
