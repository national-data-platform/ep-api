# National Data Platform - Endpoint API (NDP-EP API)

A REST API that provides **unified access** to dataset management across the [National Data Platform (NDP)](https://nationaldataplatform.org). Users can search the NDP catalog, ingest new datasets, and manage their own data collections through a single, streamlined M2M interface.

## 🌐 About the National Data Platform

The NDP-EP API integrates seamlessly with the National Data Platform ecosystem:

- **🔐 Unified Authentication**: Uses NDP's authentication system - your NDP account works directly with this API
- **📊 Multi-Catalog Management**: Control and access datasets across three different CKAN environments
- **🔍 Centralized Discovery**: Search the main NDP catalog and other connected data sources
- **📥 Streamlined Ingestion**: Simplified workflow for adding new datasets to the platform

## 🏗️ NDP Catalog Architecture

The National Data Platform uses CKAN as its data catalog management software. This API provides access to three different CKAN environments, each with specific access levels and purposes:

### 1. **Local CKAN** 🏠
If you have your own CKAN instance installed locally, this API can connect to it, giving you:
- **Full Control**: Create, read, update, and delete datasets
- **Use Case**: Personal or organizational data catalogs
- **Permissions**: Complete administrative access to your own catalog

### 2. **NDP Central Catalog** 🌍
This is the main public catalog of the National Data Platform. Through this API you can:
- **Read-Only Access**: Search and discover publicly available datasets
- **Use Case**: Exploring the official NDP data collection
- **Permissions**: Search and view only - no modifications allowed

### 3. **PreCKAN (Staging Environment)** 🔄
This is a staging environment provided by the NDP for dataset submission and review. Here's how it works:
- **Ingestion Gateway**: Submit new datasets for validation and review
- **Use Case**: Contributing datasets to the NDP central catalog
- **Workflow**: Your datasets are analyzed, validated, and if approved, promoted to the central catalog

## 🚀 Key Features

- **🔐 NDP Authentication Integration**: Seamless login with your National Data Platform credentials
- **🔍 Federated Search**: Discover datasets across local, NDP, and staging catalogs
- **🚀 Specialized Ingestion**: Purpose-built endpoints for Kafka topics, S3 resources, web services, and URLs
- **📋 General Dataset Management**: Flexible API for managing datasets with custom metadata
- **🔧 Service Registry**: Register and discover other services (such as microservices, APIs, or apps)
- **📈 System Monitoring**: Built-in metrics and health monitoring
- **📚 RESTful API**: Comprehensive OpenAPI/Swagger documentation

## ⚡ Quick Start

Get the NDP-EP API running in under 5 minutes:

### Prerequisites
- Docker and Docker Compose
- Git
- NDP account (for production use)

### 1. Clone the Repository
```bash
git clone https://github.com/national-data-platform/ep-api.git
cd ndp-endpoint-api
```

### 2. Configure Environment
```bash
cp example.env .env
# Edit .env with your NDP and CKAN configuration
```

### 3. Start the Services
```bash
docker-compose up -d
```

### 4. Access the API
- **API Documentation**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/status/

## ⚙️ Configuration

### Organization Settings

```bash
# Your organization name for identification and metrics
ORGANIZATION="Your Organization Name"
```

### CKAN Catalog Configuration

```bash
# Local CKAN Instance (Optional)
CKAN_LOCAL_ENABLED=False
CKAN_URL=                    # Base URL of your local CKAN instance
CKAN_API_KEY=               # API Key for local CKAN authentication

# Pre-CKAN Staging Environment (Optional)
PRE_CKAN_ENABLED=False
PRE_CKAN_URL=               # URL of the Pre-CKAN staging instance
PRE_CKAN_API_KEY=          # API key for Pre-CKAN authentication
```

### Streaming Services

```bash
# Kafka Integration (Optional)
KAFKA_CONNECTION=False
KAFKA_HOST=                 # Kafka broker hostname or IP address
KAFKA_PORT=                 # Kafka broker port number
```

### Development & Testing

```bash
# Test Token for Development (Leave blank in production)
TEST_TOKEN=                 # Development authentication token
```

### External Service Integrations

```bash
# JupyterLab Integration (Optional)
USE_JUPYTERLAB=False
JUPYTER_URL=                # URL to your JupyterLab instance
```

### Advanced Configuration (Optional)

```bash
# Metrics and Monitoring
METRICS_ENDPOINT=           # Custom endpoint for sending system metrics

# NDP Core Services (Pre-configured but customizable)
CKAN_GLOBAL_URL=           # NDP Central Catalog URL (default: public NDP catalog)
AUTH_API_URL=              # NDP Authentication service URL (default: public NDP auth)
```

### Notes on Configuration

- **NDP Central Catalog**: Always available - no configuration needed (uses public endpoints)
- **Local CKAN**: Only configure if you have your own CKAN instance
- **Pre-CKAN**: Required only for dataset ingestion to NDP central catalog
- **TEST_TOKEN**: For development only - use proper NDP authentication in production
- **Advanced Settings**: `METRICS_ENDPOINT`, `CKAN_GLOBAL_URL`, and `AUTH_API_URL` are pre-configured with NDP defaults but can be overridden for custom deployments or testing environments

## 🐳 Docker Deployment

The NDP-EP API is available as a pre-built Docker image for easy deployment across different environments.

### Quick Start with Docker

```bash
# Pull and run the latest image
docker run -p 8001:8000 rbardaji/ndp-ep-api

# Access the API
# Documentation: http://localhost:8001/docs
# Health Check: http://localhost:8001/status/
```

### Production Deployment with Configuration

#### Option 1: Environment Variables
```bash
docker run -p 8001:8000 \
  -e ORGANIZATION="Your Organization" \
  -e CKAN_LOCAL_ENABLED=false \
  -e PRE_CKAN_ENABLED=true \
  -e PRE_CKAN_URL="https://preckan.nationaldataplatform.org" \
  -e PRE_CKAN_API_KEY="your-api-key" \
  -e KAFKA_CONNECTION=false \
  -e USE_JUPYTERLAB=false \
  rbardaji/ndp-ep-api
```

#### Option 2: Environment File
1. Create an `.env` file:
```bash
ORGANIZATION=Your Organization
CKAN_LOCAL_ENABLED=False
PRE_CKAN_ENABLED=True
PRE_CKAN_URL=https://preckan.nationaldataplatform.org
PRE_CKAN_API_KEY=your-api-key
KAFKA_CONNECTION=False
USE_JUPYTERLAB=False
TEST_TOKEN=
```

2. Run with environment file:
```bash
docker run -p 8001:8000 --env-file .env rbardaji/ndp-ep-api
```

#### Option 3: Docker Compose (Recommended)
Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  ndp-api:
    image: rbardaji/ndp-ep-api:latest
    ports:
      - "8001:8000"
    environment:
      - ORGANIZATION=Your Organization
      - CKAN_LOCAL_ENABLED=False
      - PRE_CKAN_ENABLED=True
      - PRE_CKAN_URL=https://preckan.nationaldataplatform.org
      - PRE_CKAN_API_KEY=your-api-key
      - KAFKA_CONNECTION=False
      - USE_JUPYTERLAB=False
    volumes:
      - ./logs:/code/logs  # Persist logs locally
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/status/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

Run with:
```bash
docker-compose up -d
```

### Docker Image Features

- **Multi-architecture**: Supports AMD64 and ARM64 platforms
- **Production-ready**: Includes 4 worker processes for high performance
- **Health monitoring**: Built-in health checks for container orchestration
- **Security**: Runs as non-root user
- **Optimized**: Minimal image size with only necessary dependencies

### Container Management

```bash
# View running containers
docker ps

# View logs
docker logs <container-id>

# Stop container
docker stop <container-id>

# Update to latest version
docker pull rbardaji/ndp-ep-api:latest
docker-compose up -d  # If using docker-compose
```

## 📖 Usage Examples

For detailed usage examples and tutorials, please check the documentation in the `/docs` folder.

## 🔄 Data Ingestion Workflow

### For NDP Central Catalog:
1. **Submit to PreCKAN**: Use `?server=pre_ckan` parameter
2. **Review**: NDP team reviews the submission
3. **Publication**: Approved datasets are moved to the central catalog

### For Local CKAN:
1. **Direct Access**: Use `?server=local` or default behavior
2. **Immediate**: Changes are applied instantly
3. **Full Control**: Complete CRUD operations available

## 📊 System Metrics

> **⚠️ CAUTION**: This API automatically collects and logs system metrics every 10 minutes.

The NDP-EP API automatically collects and logs comprehensive system metrics every 10 minutes. These metrics provide visibility into system health, resource usage, and service connectivity.

### Collected Metrics

**System Information:**
- **Public IP Address**: External IP of the API instance
- **Resource Usage**: Real-time CPU, memory, and disk utilization percentages
- **API Version**: Current version of the NDP-EP API
- **Organization**: Configured organization name

**Service Registry:**
- **Global CKAN**: NDP central catalog connection details
- **Pre-CKAN**: Staging environment configuration (if enabled)
- **Local CKAN**: Local catalog instance details (if configured)
- **Kafka**: Streaming service configuration (if enabled)
- **JupyterLab**: Notebook service integration (if configured)

### Metrics Output Example

```json
{
 "public_ip": "203.0.113.45",
 "cpu": "15%",
 "memory": "65%", 
 "disk": "45%",
 "version": "1.0.1",
 "organization": "Your Organization",
 "services": {
   "global_ckan": {"url": "https://catalog.nationaldataplatform.org"},
   "pre_ckan": {
     "url": "https://preckan.nationaldataplatform.org",
     "api_key": "configured"
   },
   "local_ckan": {
     "url": "http://localhost:5000",
     "api_key": "configured"
   },
   "kafka": {
     "host": "kafka.example.com",
     "port": "9092",
     "prefix": "ndp"
   },
   "jupyter": {"url": "https://jupyter.example.com"}
 }
}
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

For more information about the National Data Platform, visit [nationaldataplatform.org](https://nationaldataplatform.org)