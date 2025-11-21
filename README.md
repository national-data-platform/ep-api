# National Data Platform - Endpoint API (NDP-EP API)

A REST API that provides **unified access** to dataset management across the [National Data Platform (NDP)](https://nationaldataplatform.org). Users can search the NDP catalog, ingest new datasets, and manage their own data collections through a single, streamlined M2M interface.

## 🌐 About the National Data Platform

The NDP-EP API integrates seamlessly with the National Data Platform ecosystem:

- **🔐 Unified Authentication**: Uses NDP's authentication system - your NDP account works directly with this API
- **📊 Multi-Catalog Management**: Control and access datasets across three different CKAN environments
- **🔍 Centralized Discovery**: Search the main NDP catalog and other connected data sources
- **📥 Streamlined Ingestion**: Simplified workflow for adding new datasets to the platform

## 🏗️ NDP Catalog Architecture

The National Data Platform uses CKAN as its data catalog management software. This API provides access to three different catalog environments, each with specific access levels and purposes:

### 1. **Local Catalog** 🏠 (CKAN or MongoDB)
You can use your own catalog backend for local dataset management, with your choice of storage:

**CKAN Backend** (Traditional):
- Full CKAN compatibility with all extensions
- Ideal if you already have CKAN infrastructure
- Complete administrative access to your catalog

**MongoDB Backend** (Modern NoSQL):
- Lightweight, no CKAN installation required
- Fast document-based storage
- Easy to deploy and scale
- Perfect for new deployments or cloud-native environments

Both options give you:
- **Full Control**: Create, read, update, and delete datasets
- **Use Case**: Personal or organizational data catalogs
- **Flexibility**: Switch between backends via configuration

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
- **🔄 Pluggable Catalog Backends**: Choose between CKAN or MongoDB for your local catalog
- **🔍 Federated Search**: Discover datasets across local, NDP, and staging catalogs
- **🚀 Specialized Ingestion**: Purpose-built endpoints for Kafka topics, S3 resources, web services, and URLs
- **📦 MINIO S3 Storage**: Direct bucket and object management with secure presigned URLs
- **📋 General Dataset Management**: Flexible API for managing datasets with custom metadata
- **🔧 Service Registry**: Register and discover other services (such as microservices, APIs, or apps)
- **🤖 AI Agent Integration**: Model Context Protocol (MCP) support for AI assistants to interact with the API
- **📈 System Monitoring**: Built-in metrics and health monitoring
- **📚 RESTful API**: Comprehensive OpenAPI/Swagger documentation
- **🔌 Extensible Architecture**: Easy to add new catalog backends (Elasticsearch, PostgreSQL, etc.)

## ⚡ Quick Start

Get the NDP-EP API running with Docker in under 5 minutes:

### Prerequisites

Before you begin, ensure you have:

- **Docker**: Container platform for running the API
  - Install from [docker.com](https://www.docker.com/get-started)
  - Verify installation: `docker --version`

- **Docker Compose**: Container orchestration tool
  - Usually included with Docker Desktop
  - Verify installation: `docker-compose --version`

- **CKAN Instance** (Optional):
  - **Required only if**: You want to use local CKAN or PreCKAN features
  - **Not needed if**: You only plan to use NDP Central Catalog (read-only access)
  - Install CKAN following the [official documentation](https://docs.ckan.org/en/latest/maintaining/installing/index.html)

- **S3-Compatible Storage** (Optional):
  - **Required only if**: You want to use S3 object storage features
  - **Not needed if**: You don't plan to use bucket/object management endpoints
  - **Example**: MINIO is a popular S3-compatible service - see [MINIO setup guide](docs/minio-setup.md) for Docker installation instructions

### 1. Configure Environment Variables

Create a `.env` file or prepare environment variables with your configuration:

```bash
# ==============================================
# API CONFIGURATION
# ==============================================
# API root path prefix (e.g., "/test" or "" for root)
# If empty or not set, the API will be available at the root path
# This is useful when deploying the API behind a reverse proxy at a subpath
ROOT_PATH=

# ==============================================
# ORGANIZATION SETTINGS
# ==============================================
# Your organization name for identification and metrics
ORGANIZATION="My organization"

# Endpoint name for identification in metrics and monitoring
EP_NAME="EP Name"

# ==============================================
# METRICS CONFIGURATION
# ==============================================
# Interval in seconds for sending metrics (default: 3300 seconds = 55 minutes)
METRICS_INTERVAL_SECONDS=3300

# ==============================================
# AUTHENTICATION CONFIGURATION
# ==============================================
# URL for the authentication API to retrieve user information
# This endpoint is used to validate tokens and fetch user details
AUTH_API_URL=https://idp.nationaldataplatform.org/temp/information

# ==============================================
# ACCESS CONTROL (Optional)
# ==============================================
# Enable organization-based access control (True/False)
# When enabled, only users belonging to the configured ORGANIZATION
# can perform POST, PUT, DELETE operations. Other authenticated users
# will receive 403 Forbidden on write operations.
# GET endpoints remain public regardless of this setting.
ENABLE_ORGANIZATION_BASED_ACCESS=False

# ==============================================
# LOCAL CATALOG CONFIGURATION
# ==============================================
# Choose your local catalog backend: "ckan" or "mongodb"
# Global and Pre-CKAN always use CKAN regardless of this setting
LOCAL_CATALOG_BACKEND=ckan

# ==============================================
# LOCAL CKAN CONFIGURATION (if LOCAL_CATALOG_BACKEND=ckan)
# ==============================================
# Enable or disable the local CKAN instance (True/False)
# Set to True if you have your own CKAN installation
CKAN_LOCAL_ENABLED=True

# Base URL of your local CKAN instance (Required if CKAN_LOCAL_ENABLED=True)
# Example: http://192.168.1.134:5000/ or https://your-ckan-domain.com/
CKAN_URL=http://XXX.XXX.XXX.XXX:XXXX/

# API Key for CKAN authentication (Required if CKAN_LOCAL_ENABLED=True)
# Get this from your CKAN user profile -> API Tokens
CKAN_API_KEY=

# ==============================================
# MONGODB CONFIGURATION (if LOCAL_CATALOG_BACKEND=mongodb)
# ==============================================
# MongoDB connection string
MONGODB_CONNECTION_STRING=mongodb://localhost:27017

# MongoDB database name for local catalog
MONGODB_DATABASE=ndp_local_catalog

# ==============================================
# PRE-CKAN CONFIGURATION
# ==============================================
# Enable or disable the Pre-CKAN instance (True/False)
# Set to True if you want to submit datasets to NDP Central Catalog
PRE_CKAN_ENABLED=True

# URL of the Pre-CKAN staging instance (Required if PRE_CKAN_ENABLED=True)
# This is typically provided by the NDP team
PRE_CKAN_URL=http://XX.XX.XX.XXX:5000/

# API key for Pre-CKAN authentication (Required if PRE_CKAN_ENABLED=True)
# Obtain this from the NDP team or your Pre-CKAN user profile
PRE_CKAN_API_KEY=

# ==============================================
# STREAMING CONFIGURATION
# ==============================================
# Enable or disable Kafka connectivity (True/False)
# Set to True if you want to ingest data from Kafka streams
KAFKA_CONNECTION=False

# Kafka broker hostname or IP address (Required if KAFKA_CONNECTION=True)
KAFKA_HOST=

# Kafka broker port number (Required if KAFKA_CONNECTION=True)
# Default Kafka port is 9092
KAFKA_PORT=9092

# ==============================================
# DEVELOPMENT & TESTING
# ==============================================
# Test token for development purposes (Optional)
# Leave blank in production environments for security
TEST_TOKEN=testing_token

# ==============================================
# EXTERNAL SERVICE INTEGRATIONS
# ==============================================
# Enable or disable JupyterLab integration (True/False)
# Set to True if you want to integrate with a JupyterLab instance
USE_JUPYTERLAB=False

# URL to your JupyterLab instance (Required if USE_JUPYTERLAB=True)
# Example: https://jupyter.your-domain.com or http://localhost:8888
JUPYTER_URL=

# ==============================================
# S3 STORAGE CONFIGURATION
# ==============================================
# Enable or disable S3 storage (True/False)
S3_ENABLED=True

# S3 endpoint (host:port) - use your S3-compatible service endpoint
S3_ENDPOINT=XXX.XXX.XXX.XXX:9000

# S3 access credentials
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin123

# Use secure connection (True for HTTPS, False for HTTP)
S3_SECURE=False

# Default region
S3_REGION=us-east-1
```

### 2. Run with Docker

1. **Create the .env file** with your configuration (see step 1)

2. **Run the container**:
```bash
docker run -p 8001:8000 --env-file .env rbardaji/ndp-ep-api
```

### 3. Verify Installation

Once the container is running, verify everything is working:

- **API Documentation**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/status/
- **Interactive API Explorer**: Available at the docs URL

### 4. Common Configuration Scenarios

#### Scenario 1: NDP Central Catalog Only (Read-Only)
```bash
# Minimal configuration for read-only access to NDP Central Catalog
ORGANIZATION="Your Organization"
CKAN_LOCAL_ENABLED=False
PRE_CKAN_ENABLED=False
KAFKA_CONNECTION=False
USE_JUPYTERLAB=False
```

#### Scenario 2: Local CKAN Development
```bash
# Configuration for local CKAN development
ORGANIZATION="Your Organization"
LOCAL_CATALOG_BACKEND=ckan
CKAN_LOCAL_ENABLED=True
CKAN_URL=http://localhost:5000/
CKAN_API_KEY=your-local-ckan-api-key
PRE_CKAN_ENABLED=False
TEST_TOKEN=dev_token
```

#### Scenario 3: MongoDB Local Catalog (No CKAN Required)
```bash
# Lightweight setup with MongoDB backend
ORGANIZATION="Your Organization"
LOCAL_CATALOG_BACKEND=mongodb
MONGODB_CONNECTION_STRING=mongodb://localhost:27017
MONGODB_DATABASE=ndp_local_catalog
PRE_CKAN_ENABLED=False
TEST_TOKEN=dev_token
```

#### Scenario 4: Full NDP Integration with CKAN
```bash
# Complete setup with local CKAN and NDP submission capability
ORGANIZATION="Your Organization"
CKAN_LOCAL_ENABLED=True
CKAN_URL=http://your-ckan-instance:5000/
CKAN_API_KEY=your-local-ckan-api-key
PRE_CKAN_ENABLED=True
PRE_CKAN_URL=https://preckan.nationaldataplatform.org
PRE_CKAN_API_KEY=your-ndp-preckan-api-key
```

## 📖 Usage Examples

For detailed usage examples and tutorials, please check the documentation in the `/docs` folder.

## 🤖 AI Agent Integration (MCP)

The NDP-EP API includes built-in support for the **Model Context Protocol (MCP)**, enabling AI assistants and agents to interact programmatically with all API endpoints.

### What is MCP?

The Model Context Protocol is an emerging standard that defines how AI agents communicate with applications. It allows AI assistants like Claude, ChatGPT, and custom agents to discover and invoke API operations automatically.

### MCP Endpoint

Once the API is running, the MCP server is automatically available at:

```
http://your-api-host:port/mcp
```

For example, with the default Docker setup:
```
http://localhost:8001/mcp
```

### Key Benefits

- **Zero Configuration**: Automatically exposes all existing API endpoints as MCP tools
- **AI-Friendly**: AI agents can discover available operations and their parameters
- **Schema Preservation**: Maintains all request/response models and validation
- **Secure**: Respects existing authentication mechanisms
- **Standard Protocol**: Compatible with any MCP-compliant AI client

### Use Cases

**Dataset Management with AI Assistants:**
- "Search for oceanography datasets in the NDP catalog"
- "Create a new dataset with these metadata fields"
- "List all my S3 buckets and their contents"

**Automated Workflows:**
- AI agents can orchestrate complex data ingestion pipelines
- Automated catalog synchronization between environments
- Intelligent data discovery and recommendation

**Development & Testing:**
- AI-assisted API testing and validation
- Automatic documentation generation
- Code generation for API clients

### Connecting AI Clients

The MCP endpoint works with any MCP-compatible client. Example clients include:

- **Claude Code**: Anthropic's AI coding assistant
- **Custom MCP Clients**: Using the official MCP SDK
- **AI Automation Tools**: Any tool supporting the MCP protocol

For configuration examples and integration guides, visit the [FastAPI-MCP documentation](https://fastapi-mcp.tadata.com).

## 📊 System Metrics

> **⚠️ CAUTION**: This API automatically collects and logs system metrics (default: every 55 minutes, configurable via `METRICS_INTERVAL_SECONDS`).

The NDP-EP API automatically collects and logs comprehensive system metrics at configurable intervals (default: 55 minutes). These metrics provide visibility into system health, resource usage, catalog statistics, and service connectivity.

### Collected Metrics

**System Information:**
- **Public IP Address**: External IP of the API instance
- **Resource Usage**: Real-time CPU percentage, memory (used/total GB), and disk (used/total GB)
- **API Version**: Current version of the NDP-EP API
- **Organization**: Configured organization name
- **EP Name**: Endpoint identifier name

**Catalog Statistics:**
- **Number of Datasets**: Total datasets in local catalog
- **Number of Services**: Total registered services
- **Services List**: Array of all registered service titles

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
  "cpu": "5.7%",
  "memory": "4.8GB/30.8GB",
  "disk": "265.4GB/936.8GB",
  "version": "0.3.2",
  "organization": "Your Organization",
  "ep_name": "Your EP",
  "num_datasets": 23,
  "num_services": 5,
  "services": [
    "Service Title 1",
    "Service Title 2",
    "Service Title 3"
  ],
  "timestamp": "2025-10-09T16:48:09.874843Z"
}
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

For more information about the National Data Platform, visit [nationaldataplatform.org](https://nationaldataplatform.org)