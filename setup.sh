#!/bin/bash
# ==============================================
# NDP-EP API Setup Script
# ==============================================
# This script installs the NDP-EP API on a fresh Ubuntu system
# by fetching configuration from the NDP Federation API.
#
# It will:
#   1. Install Docker (if not present)
#   2. Fetch configuration from Federation API
#   3. Generate docker-compose.yml and .env files
#   4. Start the services
#
# Usage:
#   curl -fsSL <script_url> | bash -s -- --config_id <ep_id>
#   ./setup.sh --config_id <ep_id>
#   ./setup.sh --config_id <ep_id> --federation_url <url>
#
# Example:
#   ./setup.sh --config_id 695383e17c1d8951b04621c6
# ==============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
DEFAULT_FEDERATION_URL="http://localhost:8000"
EP_API_IMAGE="rbardaji/ndp-ep-api:latest"
INSTALL_DIR="ndp-ep"
DEFAULT_CATALOG_BACKEND="ckan"
CKAN_DOCKER_REPO="https://github.com/sci-ndp/pop-ckan-docker.git"

# Print banner
print_banner() {
    echo -e "${CYAN}"
    cat <<'EOF'

  ███╗   ██╗██████╗ ██████╗       ███████╗██████╗
  ████╗  ██║██╔══██╗██╔══██╗      ██╔════╝██╔══██╗
  ██╔██╗ ██║██║  ██║██████╔╝█████╗█████╗  ██████╔╝
  ██║╚██╗██║██║  ██║██╔═══╝ ╚════╝██╔══╝  ██╔═══╝
  ██║ ╚████║██████╔╝██║           ███████╗██║
  ╚═╝  ╚═══╝╚═════╝ ╚═╝           ╚══════╝╚═╝

        NDP Endpoint API - Setup Script

EOF
    echo -e "${NC}"
}

# Print functions
print_step() {
    echo -e "\n${GREEN}[STEP]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Show usage
show_usage() {
    echo "Usage: $0 --config_id <ep_id> [OPTIONS]"
    echo ""
    echo "Required:"
    echo "  --config_id <id>        EP configuration ID from Federation API"
    echo ""
    echo "Options:"
    echo "  --federation_url <url>  Federation API URL (default: $DEFAULT_FEDERATION_URL)"
    echo "  --install_dir <dir>     Installation directory (default: $INSTALL_DIR)"
    echo "  --catalog_backend <type> Local catalog backend: ckan or mongodb (default: $DEFAULT_CATALOG_BACKEND)"
    echo "  --no-start              Don't start services after configuration"
    echo "  --help                  Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 --config_id 695383e17c1d8951b04621c6"
    echo "  $0 --config_id abc123 --federation_url https://federation.ndp.utah.edu"
    echo "  $0 --config_id abc123 --catalog_backend mongodb"
}

# ----------- PARSE ARGS ----------- #
config_id=""
federation_url="$DEFAULT_FEDERATION_URL"
install_dir="$INSTALL_DIR"
catalog_backend="$DEFAULT_CATALOG_BACKEND"
no_start=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --config_id) config_id="$2"; shift ;;
        --federation_url) federation_url="$2"; shift ;;
        --install_dir) install_dir="$2"; shift ;;
        --catalog_backend) catalog_backend="$2"; shift ;;
        --no-start) no_start=true ;;
        --help) show_usage; exit 0 ;;
        *) echo -e "${RED}Unknown parameter: $1${NC}"; show_usage; exit 1 ;;
    esac
    shift
done

# Validate required parameters
if [[ -z "$config_id" ]]; then
    print_error "--config_id is required"
    echo ""
    show_usage
    exit 1
fi

# Validate catalog_backend
if [[ "$catalog_backend" != "ckan" && "$catalog_backend" != "mongodb" ]]; then
    print_error "--catalog_backend must be 'ckan' or 'mongodb'"
    echo ""
    show_usage
    exit 1
fi

# ----------- MAIN SCRIPT ----------- #
print_banner

# ----------- CHECK/INSTALL DEPENDENCIES ----------- #
print_step "Checking dependencies..."

# Check for curl
if ! command -v curl &> /dev/null; then
    print_info "Installing curl..."
    sudo apt-get update && sudo apt-get install -y curl
fi

# Check for jq
if ! command -v jq &> /dev/null; then
    print_info "Installing jq..."
    sudo apt-get update && sudo apt-get install -y jq
fi

# Check for git (needed for CKAN backend)
if [[ "$catalog_backend" == "ckan" ]]; then
    if ! command -v git &> /dev/null; then
        print_info "Installing git..."
        sudo apt-get update && sudo apt-get install -y git
    fi
fi

# Check for Docker
if ! command -v docker &> /dev/null; then
    print_info "Docker not found. Installing..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    print_success "Docker installed"
    print_info "You may need to log out and back in for docker group permissions"
else
    print_info "Docker is installed: $(docker --version)"
fi

# Check Docker Compose
if docker compose version &> /dev/null; then
    print_info "Docker Compose is available: $(docker compose version)"
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    print_info "Docker Compose (standalone) is available"
    DOCKER_COMPOSE_CMD="docker-compose"
else
    print_error "Docker Compose is not available. Please install it."
    exit 1
fi

# ----------- FETCH CONFIGURATION ----------- #
print_step "Fetching configuration from Federation API..."
print_info "Config ID: $config_id"
print_info "Federation URL: $federation_url"

config_json=$(curl -s "${federation_url}/ep/${config_id}")

if [[ -z "$config_json" || "$config_json" == "null" ]]; then
    print_error "Failed to fetch configuration from Federation API"
    print_error "URL: ${federation_url}/ep/${config_id}"
    exit 1
fi

# Check for error response
if echo "$config_json" | jq -e '.error' > /dev/null 2>&1; then
    error_msg=$(echo "$config_json" | jq -r '.message // "Unknown error"')
    print_error "Federation API returned an error: $error_msg"
    exit 1
fi

print_success "Configuration fetched successfully"

# ----------- EXTRACT VALUES ----------- #
print_step "Extracting configuration values..."

# Extract values from JSON (with defaults)
organization=$(echo "$config_json" | jq -r '.organization // "My-Organization"')
ep_name=$(echo "$config_json" | jq -r '.ep_name // "My-EP"')
pre_ckan_url=$(echo "$config_json" | jq -r '.pre_ckan_url // ""')
pre_ckan_key=$(echo "$config_json" | jq -r '.pre_ckan_key // ""')
enable_staging=$(echo "$config_json" | jq -r '.enable_staging // false')
streaming=$(echo "$config_json" | jq -r '.streaming // false')
jhub=$(echo "$config_json" | jq -r '.jhub // false')
group_name=$(echo "$config_json" | jq -r '.group_name // ""')
jupyter_url=$(echo "$config_json" | jq -r '.jupyter_url // ""')

# Display fetched values
echo ""
echo -e "${BLUE}Configuration values:${NC}"
echo "  Organization:    $organization"
echo "  EP Name:         $ep_name"
echo "  Pre-CKAN URL:    ${pre_ckan_url:-"(not set)"}"
echo "  Enable Staging:  $enable_staging"
echo "  Streaming:       $streaming"
echo "  JupyterHub:      $jhub"
echo "  Group Name:      ${group_name:-"(not set)"}"

# ----------- NORMALIZE BOOLEAN VALUES ----------- #
normalize_bool() {
    local val="$1"
    case "$val" in
        true|True|TRUE|1) echo "True" ;;
        false|False|FALSE|0|"") echo "False" ;;
        *) echo "False" ;;
    esac
}

KAFKA_CONNECTION=$(normalize_bool "$streaming")
USE_JUPYTERLAB=$(normalize_bool "$jhub")

# Set PRE_CKAN based on availability of url and key
if [[ -n "$pre_ckan_url" && "$pre_ckan_url" != "null" && -n "$pre_ckan_key" && "$pre_ckan_key" != "null" ]]; then
    PRE_CKAN_ENABLED="True"
    PRE_CKAN_URL="$pre_ckan_url"
    PRE_CKAN_API_KEY="$pre_ckan_key"
else
    PRE_CKAN_ENABLED="False"
    PRE_CKAN_URL=""
    PRE_CKAN_API_KEY=""
fi

# Kafka settings (port must always have a default value for pydantic validation)
if [[ "$KAFKA_CONNECTION" == "True" ]]; then
    KAFKA_HOST="kafka"
    KAFKA_PORT="9093"
else
    KAFKA_HOST="localhost"
    KAFKA_PORT="9093"
fi

# JupyterLab settings
if [[ "$USE_JUPYTERLAB" == "True" ]]; then
    if [[ -n "$jupyter_url" && "$jupyter_url" != "null" ]]; then
        JUPYTER_URL="$jupyter_url"
    else
        JUPYTER_URL="http://jupyterlab:8888"
    fi
else
    JUPYTER_URL=""
fi

# Group-based access control
if [[ -n "$group_name" && "$group_name" != "null" ]]; then
    ENABLE_GROUP_BASED_ACCESS="True"
    GROUP_NAMES="$group_name"
else
    ENABLE_GROUP_BASED_ACCESS="False"
    GROUP_NAMES=""
fi

# ----------- GET MACHINE IP ----------- #
machine_ip=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")

# ----------- CREATE INSTALLATION DIRECTORY ----------- #
print_step "Creating installation directory: $install_dir"

mkdir -p "$install_dir"
cd "$install_dir"

print_info "Catalog backend: $catalog_backend"
print_info "Machine IP: $machine_ip"

# ----------- SETUP CKAN BACKEND ----------- #
if [[ "$catalog_backend" == "ckan" ]]; then
    print_step "Setting up CKAN backend..."

    # Clone CKAN Docker repository
    print_info "Cloning CKAN Docker repository..."
    git clone "$CKAN_DOCKER_REPO" ckan-docker

    # Configure CKAN
    cd ckan-docker
    cp .env.example .env

    # Get CKAN credentials from Federation API config
    ckan_name=$(echo "$config_json" | jq -r '.ckan_name // "ckan_admin"')
    ckan_password=$(echo "$config_json" | jq -r '.ckan_password // "test1234"')

    # Configure CKAN environment
    sed -i "s/^CKAN_SYSADMIN_NAME=.*/CKAN_SYSADMIN_NAME=${ckan_name}/" .env
    sed -i "s/^CKAN_SYSADMIN_PASSWORD=.*/CKAN_SYSADMIN_PASSWORD=${ckan_password}/" .env
    sed -i "s|^CKAN_SITE_URL=.*|CKAN_SITE_URL=https://${machine_ip}:8443|" .env

    print_success "CKAN configured"

    # Go back to install_dir for API setup
    cd ..

    # Set CKAN URL and API key variables for .env
    CKAN_URL="https://ckan:8443"
    CKAN_API_KEY=""  # Will be generated after CKAN starts
fi

# ----------- GENERATE DOCKER-COMPOSE.YML ----------- #
print_step "Generating docker-compose.yml..."

if [[ "$catalog_backend" == "mongodb" ]]; then
    # MongoDB backend docker-compose
    cat > docker-compose.yml << 'COMPOSE_EOF'
services:
  # ==============================================
  # API Service (always starts)
  # ==============================================
  api:
    image: rbardaji/ndp-ep-api:latest
    container_name: ndp-ep-api
    ports:
      - "8002:8000"
    env_file:
      - .env
    extra_hosts:
      - "host.docker.internal:host-gateway"
    networks:
      - ndp-network
    restart: unless-stopped
    depends_on:
      mongodb:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # ==============================================
  # MongoDB - Local Catalog Backend
  # ==============================================
  mongodb:
    image: mongo:7
    container_name: ndp-mongodb
    ports:
      - "27018:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: admin123
      MONGO_INITDB_DATABASE: ndp_local_catalog
    volumes:
      - mongodb_data:/data/db
      - mongodb_config:/data/configdb
    networks:
      - ndp-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s

  # ==============================================
  # Mongo Express - MongoDB Web UI
  # ==============================================
  mongo-express:
    image: mongo-express:latest
    container_name: ndp-mongo-express
    ports:
      - "8082:8081"
    environment:
      ME_CONFIG_MONGODB_ADMINUSERNAME: admin
      ME_CONFIG_MONGODB_ADMINPASSWORD: admin123
      ME_CONFIG_MONGODB_URL: mongodb://admin:admin123@mongodb:27017/
      ME_CONFIG_BASICAUTH_USERNAME: admin
      ME_CONFIG_BASICAUTH_PASSWORD: admin123
      ME_CONFIG_MONGODB_ENABLE_ADMIN: 'true'
    networks:
      - ndp-network
    depends_on:
      mongodb:
        condition: service_healthy
    restart: unless-stopped

  # ==============================================
  # MinIO - S3-Compatible Object Storage
  # ==============================================
  minio:
    image: minio/minio:latest
    container_name: ndp-minio
    ports:
      - "9002:9000"
      - "9003:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin123
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    networks:
      - ndp-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ==============================================
  # Zookeeper - Required for Kafka
  # ==============================================
  zookeeper:
    image: confluentinc/cp-zookeeper:7.6.0
    container_name: ndp-zookeeper
    profiles: ["kafka"]
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
      ZOOKEEPER_LOG4J_ROOT_LOGLEVEL: WARN
    volumes:
      - zookeeper_data:/var/lib/zookeeper/data
      - zookeeper_log:/var/lib/zookeeper/log
    networks:
      - ndp-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "2181"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ==============================================
  # Kafka - Streaming Platform
  # ==============================================
  kafka:
    image: confluentinc/cp-kafka:7.6.0
    container_name: ndp-kafka
    profiles: ["kafka"]
    ports:
      - "9094:9092"
      - "9095:9093"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9093,PLAINTEXT_HOST://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_LOG4J_ROOT_LOGLEVEL: WARN
      KAFKA_TOOLS_LOG4J_LOGLEVEL: ERROR
    volumes:
      - kafka_data:/var/lib/kafka/data
    networks:
      - ndp-network
    depends_on:
      zookeeper:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "kafka-broker-api-versions", "--bootstrap-server", "localhost:9093"]
      interval: 10s
      timeout: 10s
      retries: 5
      start_period: 30s

  # ==============================================
  # Kafka UI - Web Interface for Kafka Management
  # ==============================================
  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    container_name: ndp-kafka-ui
    profiles: ["kafka"]
    ports:
      - "8081:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: ndp-cluster
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9093
      KAFKA_CLUSTERS_0_ZOOKEEPER: zookeeper:2181
      DYNAMIC_CONFIG_ENABLED: 'true'
    networks:
      - ndp-network
    depends_on:
      kafka:
        condition: service_healthy
    restart: unless-stopped

  # ==============================================
  # JupyterLab - Interactive Development Environment
  # ==============================================
  jupyterlab:
    image: jupyter/scipy-notebook:latest
    container_name: ndp-jupyterlab
    profiles: ["jupyter"]
    ports:
      - "8888:8888"
    environment:
      JUPYTER_ENABLE_LAB: 'yes'
      JUPYTER_TOKEN: testing_token
    volumes:
      - jupyterlab_data:/home/jovyan/work
    networks:
      - ndp-network
    restart: unless-stopped
    command: start-notebook.sh --NotebookApp.token='testing_token' --NotebookApp.password=''

# ==============================================
# Volumes - Persistent Data Storage
# ==============================================
volumes:
  mongodb_data:
    driver: local
  mongodb_config:
    driver: local
  minio_data:
    driver: local
  zookeeper_data:
    driver: local
  zookeeper_log:
    driver: local
  kafka_data:
    driver: local
  jupyterlab_data:
    driver: local

# ==============================================
# Network Configuration
# ==============================================
networks:
  ndp-network:
    driver: bridge
COMPOSE_EOF

else
    # CKAN backend docker-compose (API only, CKAN is in separate directory)
    cat > docker-compose.yml << 'COMPOSE_EOF'
services:
  # ==============================================
  # API Service (always starts)
  # ==============================================
  api:
    image: rbardaji/ndp-ep-api:latest
    container_name: ndp-ep-api
    ports:
      - "8002:8000"
    env_file:
      - .env
    extra_hosts:
      - "host.docker.internal:host-gateway"
    networks:
      - ndp-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # ==============================================
  # MinIO - S3-Compatible Object Storage
  # ==============================================
  minio:
    image: minio/minio:latest
    container_name: ndp-minio
    ports:
      - "9002:9000"
      - "9003:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin123
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    networks:
      - ndp-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ==============================================
  # Zookeeper - Required for Kafka
  # ==============================================
  zookeeper:
    image: confluentinc/cp-zookeeper:7.6.0
    container_name: ndp-zookeeper
    profiles: ["kafka"]
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
      ZOOKEEPER_LOG4J_ROOT_LOGLEVEL: WARN
    volumes:
      - zookeeper_data:/var/lib/zookeeper/data
      - zookeeper_log:/var/lib/zookeeper/log
    networks:
      - ndp-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "2181"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ==============================================
  # Kafka - Streaming Platform
  # ==============================================
  kafka:
    image: confluentinc/cp-kafka:7.6.0
    container_name: ndp-kafka
    profiles: ["kafka"]
    ports:
      - "9094:9092"
      - "9095:9093"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9093,PLAINTEXT_HOST://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_LOG4J_ROOT_LOGLEVEL: WARN
      KAFKA_TOOLS_LOG4J_LOGLEVEL: ERROR
    volumes:
      - kafka_data:/var/lib/kafka/data
    networks:
      - ndp-network
    depends_on:
      zookeeper:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "kafka-broker-api-versions", "--bootstrap-server", "localhost:9093"]
      interval: 10s
      timeout: 10s
      retries: 5
      start_period: 30s

  # ==============================================
  # Kafka UI - Web Interface for Kafka Management
  # ==============================================
  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    container_name: ndp-kafka-ui
    profiles: ["kafka"]
    ports:
      - "8081:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: ndp-cluster
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9093
      KAFKA_CLUSTERS_0_ZOOKEEPER: zookeeper:2181
      DYNAMIC_CONFIG_ENABLED: 'true'
    networks:
      - ndp-network
    depends_on:
      kafka:
        condition: service_healthy
    restart: unless-stopped

  # ==============================================
  # JupyterLab - Interactive Development Environment
  # ==============================================
  jupyterlab:
    image: jupyter/scipy-notebook:latest
    container_name: ndp-jupyterlab
    profiles: ["jupyter"]
    ports:
      - "8888:8888"
    environment:
      JUPYTER_ENABLE_LAB: 'yes'
      JUPYTER_TOKEN: testing_token
    volumes:
      - jupyterlab_data:/home/jovyan/work
    networks:
      - ndp-network
    restart: unless-stopped
    command: start-notebook.sh --NotebookApp.token='testing_token' --NotebookApp.password=''

# ==============================================
# Volumes - Persistent Data Storage
# ==============================================
volumes:
  minio_data:
    driver: local
  zookeeper_data:
    driver: local
  zookeeper_log:
    driver: local
  kafka_data:
    driver: local
  jupyterlab_data:
    driver: local

# ==============================================
# Network Configuration
# ==============================================
networks:
  ndp-network:
    driver: bridge
COMPOSE_EOF
fi

print_success "docker-compose.yml generated"

# ----------- SET BACKEND-SPECIFIC VARIABLES ----------- #
if [[ "$catalog_backend" == "mongodb" ]]; then
    MONGODB_CONNECTION_STRING="mongodb://admin:admin123@mongodb:27017"
    MONGODB_DATABASE="ndp_local_catalog"
    CKAN_URL=""
    CKAN_API_KEY=""
else
    # CKAN backend
    MONGODB_CONNECTION_STRING=""
    MONGODB_DATABASE=""
    CKAN_URL="https://localhost:8443"
    CKAN_API_KEY=""  # Will be set after CKAN starts
fi

# ----------- GENERATE .ENV FILE ----------- #
print_step "Generating .env file..."

cat > .env << EOF
# ==============================================
# NDP-EP API Configuration
# Generated by setup.sh on $(date)
# Config ID: $config_id
# ==============================================

# ==============================================
# API CONFIGURATION
# ==============================================

ROOT_PATH=

# ==============================================
# ORGANIZATION
# ==============================================

ORGANIZATION="$organization"
EP_NAME="$ep_name"

# ==============================================
# METRICS CONFIGURATION
# ==============================================

METRICS_INTERVAL_SECONDS=3300

# ==============================================
# ACCESS CONTROL
# ==============================================

ENABLE_GROUP_BASED_ACCESS=$ENABLE_GROUP_BASED_ACCESS
GROUP_NAMES=$GROUP_NAMES

# ==============================================
# LOCAL CATALOG CONFIGURATION
# ==============================================

LOCAL_CATALOG_BACKEND=$catalog_backend
CKAN_LOCAL_ENABLED=True

# ==============================================
# CKAN Configuration
# ==============================================

CKAN_URL=${CKAN_URL:-}
CKAN_API_KEY=${CKAN_API_KEY:-}
CKAN_VERIFY_SSL=False

# ==============================================
# MongoDB Configuration
# ==============================================

MONGODB_CONNECTION_STRING=${MONGODB_CONNECTION_STRING:-}
MONGODB_DATABASE=${MONGODB_DATABASE:-}

# ==============================================
# Pre-CKAN Configuration
# ==============================================

PRE_CKAN_ENABLED=$PRE_CKAN_ENABLED
PRE_CKAN_URL=$PRE_CKAN_URL
PRE_CKAN_API_KEY=$PRE_CKAN_API_KEY
PRE_CKAN_VERIFY_SSL=True

# ==============================================
# Kafka Configuration
# ==============================================

KAFKA_CONNECTION=$KAFKA_CONNECTION
KAFKA_HOST=$KAFKA_HOST
KAFKA_PORT=$KAFKA_PORT

# ==============================================
# Authentication
# ==============================================

TEST_TOKEN=testing_token
AUTH_API_URL=https://idp.nationaldataplatform.org/temp/information

# ==============================================
# JupyterLab
# ==============================================

USE_JUPYTERLAB=$USE_JUPYTERLAB
JUPYTER_URL=$JUPYTER_URL

# ==============================================
# S3 Storage (MinIO)
# ==============================================

S3_ENABLED=True
S3_ENDPOINT=minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin123
S3_SECURE=False
S3_REGION=us-east-1

# ==============================================
# Pelican Federation
# ==============================================

PELICAN_ENABLED=False
PELICAN_FEDERATION_URL=
PELICAN_DIRECT_READS=False
EOF

print_success ".env file generated"

# ----------- GENERATE INFO FILE ----------- #
info_file="setup_info.txt"

cat > "$info_file" << EOF
# ==============================================
# NDP-EP API Setup Information
# Generated: $(date)
# ==============================================

Configuration ID: $config_id
Federation API: $federation_url
Installation Directory: $(pwd)
Catalog Backend: $catalog_backend

Organization: $organization
EP Name: $ep_name
Machine IP: $machine_ip

Services Enabled:
  - API: Yes (rbardaji/ndp-ep-api:latest)
  - Local Catalog: $catalog_backend
  - MinIO (S3): Yes
  - Pre-CKAN: $PRE_CKAN_ENABLED
  - Kafka Streaming: $KAFKA_CONNECTION
  - JupyterLab: $USE_JUPYTERLAB

Access URLs:
  - API: http://${machine_ip}:8002
  - API Docs: http://${machine_ip}:8002/docs
  - MinIO Console: http://${machine_ip}:9003
EOF

if [[ "$catalog_backend" == "mongodb" ]]; then
    echo "  - MongoDB Express: http://${machine_ip}:8082" >> "$info_file"
else
    echo "  - CKAN: https://${machine_ip}:8443" >> "$info_file"
fi

if [[ "$KAFKA_CONNECTION" == "True" ]]; then
    echo "  - Kafka UI: http://${machine_ip}:8081" >> "$info_file"
fi

if [[ "$USE_JUPYTERLAB" == "True" ]]; then
    echo "  - JupyterLab: http://${machine_ip}:8888" >> "$info_file"
fi

print_info "Setup info saved to $info_file"

# ----------- START SERVICES ----------- #
if [[ "$no_start" == false ]]; then
    print_step "Starting services..."

    # Build docker compose command with profiles
    compose_profiles=""
    if [[ "$KAFKA_CONNECTION" == "True" ]]; then
        compose_profiles="$compose_profiles --profile kafka"
    fi
    if [[ "$USE_JUPYTERLAB" == "True" ]]; then
        compose_profiles="$compose_profiles --profile jupyter"
    fi

    # Start CKAN first if using CKAN backend
    if [[ "$catalog_backend" == "ckan" ]]; then
        print_info "Starting CKAN services..."
        cd ckan-docker
        $DOCKER_COMPOSE_CMD up -d --build

        print_info "Waiting for CKAN to become healthy (this may take 2-3 minutes)..."
        max_attempts=60
        attempt=0
        while [[ $attempt -lt $max_attempts ]]; do
            status=$(docker inspect --format='{{.State.Health.Status}}' ckan 2>/dev/null || echo "starting")
            if [[ "$status" == "healthy" ]]; then
                print_success "CKAN is healthy!"
                break
            fi
            attempt=$((attempt + 1))
            echo -ne "\rWaiting for CKAN... ($attempt/$max_attempts) - status: $status"
            sleep 10
        done
        echo ""

        if [[ $attempt -eq $max_attempts ]]; then
            print_error "CKAN did not become healthy in time. Check logs with: $DOCKER_COMPOSE_CMD logs ckan"
        else
            # Generate CKAN API key
            print_info "Generating CKAN API key..."
            ckan_container=$(docker ps --filter "name=ckan" --format "{{.Names}}" | grep -v solr | grep -v redis | grep -v db | grep -v nginx | grep -v datapusher | head -1)
            if [[ -n "$ckan_container" ]]; then
                api_key=$(docker exec "$ckan_container" ckan -c /srv/app/ckan.ini user token add "$ckan_name" api_token 2>/dev/null | grep -oE 'eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*' | head -1)
                if [[ -n "$api_key" ]]; then
                    # Update .env with CKAN API key
                    cd ..
                    sed -i "s|^CKAN_API_KEY=.*|CKAN_API_KEY=$api_key|" .env
                    print_success "CKAN API key generated"
                else
                    print_info "Could not generate API key automatically. Generate it from the CKAN web UI."
                    cd ..
                fi
            else
                cd ..
            fi
        fi
    fi

    print_info "Pulling latest images..."
    $DOCKER_COMPOSE_CMD $compose_profiles pull

    print_info "Starting containers..."
    $DOCKER_COMPOSE_CMD $compose_profiles up -d

    print_info "Waiting for services to start..."
    sleep 10

    # Check API health
    max_attempts=30
    attempt=0
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -s "http://localhost:8002/" > /dev/null 2>&1; then
            print_success "API is running!"
            break
        fi
        attempt=$((attempt + 1))
        echo -ne "\rWaiting for API... ($attempt/$max_attempts)"
        sleep 2
    done
    echo ""

    if [[ $attempt -eq $max_attempts ]]; then
        print_error "API did not start in time. Check logs with: $DOCKER_COMPOSE_CMD logs api"
    fi
fi

# ----------- PRINT SUMMARY ----------- #
echo ""
echo -e "${GREEN}========================================"
echo "     Setup Complete!"
echo -e "========================================${NC}"
echo ""
echo -e "${BLUE}Installation Directory:${NC} $(pwd)"
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  Organization:     $organization"
echo "  EP Name:          $ep_name"
echo "  Config ID:        $config_id"
echo "  Catalog Backend:  $catalog_backend"
echo ""
echo -e "${BLUE}Services:${NC}"
echo "  - API:            http://${machine_ip}:8002"
echo "  - API Docs:       http://${machine_ip}:8002/docs"
echo "  - MinIO Console:  http://${machine_ip}:9003"

if [[ "$catalog_backend" == "mongodb" ]]; then
    echo "  - MongoDB Express: http://${machine_ip}:8082"
else
    echo "  - CKAN:           https://${machine_ip}:8443"
fi

if [[ "$KAFKA_CONNECTION" == "True" ]]; then
    echo "  - Kafka UI:       http://${machine_ip}:8081"
fi

if [[ "$USE_JUPYTERLAB" == "True" ]]; then
    echo "  - JupyterLab:     http://${machine_ip}:8888"
fi

echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "  cd $(pwd)"
echo "  $DOCKER_COMPOSE_CMD ps          # Check running services"
echo "  $DOCKER_COMPOSE_CMD logs -f     # View logs"
echo "  $DOCKER_COMPOSE_CMD down        # Stop services"
echo "  $DOCKER_COMPOSE_CMD restart     # Restart services"

if [[ "$catalog_backend" == "ckan" ]]; then
    echo ""
    echo -e "${BLUE}CKAN commands:${NC}"
    echo "  cd $(pwd)/ckan-docker"
    echo "  $DOCKER_COMPOSE_CMD ps          # Check CKAN services"
    echo "  $DOCKER_COMPOSE_CMD logs ckan   # View CKAN logs"
fi

echo ""
echo -e "${YELLOW}Note: Some services may take a few minutes to fully initialize.${NC}"
