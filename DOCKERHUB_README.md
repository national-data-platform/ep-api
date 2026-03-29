# NDP Endpoint API

Unified REST API for dataset management and discovery across the National Data Platform (NDP) ecosystem. Built with FastAPI, it provides a single interface to manage datasets across multiple catalog backends (CKAN, MongoDB), stream data through Kafka, store objects in S3-compatible storage (MinIO), and access distributed scientific data via Pelican Federation.

## Features

- **Dataset Management** - Full CRUD operations for datasets across multiple catalog environments (local, NDP Central, Pre-CKAN staging)
- **Federated Search** - Search datasets across local catalog, NDP Central Catalog, and Pre-CKAN staging
- **Streaming Data** - Register and manage Kafka topics for real-time data ingestion
- **Object Storage** - S3-compatible bucket and object management (create buckets, upload/download files, presigned URLs)
- **Pelican Federation** - Browse and download files from distributed scientific data federations (OSDF and others)
- **Service Registry** - Register external services with dynamic routing and proxy capabilities
- **AI Agent Integration** - Built-in Model Context Protocol (MCP) server for AI assistant integration
- **OpenTelemetry** - Distributed tracing and observability with configurable exporters
- **Group-Based Access Control** - Optional role-based write permissions using Bearer token authentication
- **Automatic Metrics** - Background task that reports system metrics (CPU, memory, disk) to federation
- **Dataset Publishing** - Publish datasets from local catalog to Pre-CKAN staging environment
- **NDP Affinities** - Automatic registration of datasets and services in the NDP Affinities system
- **Remote Execution** - Integration with deployment APIs for remote code execution

## Quick Start

### Using Docker Compose (Recommended)

Create a `docker-compose.yml` with the API and the optional services you need. The API always starts; additional services are organized into **profiles** that you activate with `--profile`.

```yaml
services:
  # ==============================================
  # API Service (always starts)
  # ==============================================
  api:
    image: rbardaji/ndp-ep-api
    container_name: ndp-ep-api
    ports:
      - "8002:8000"
    env_file:
      - .env
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
  # MongoDB - Local Catalog Backend
  # Activate with: --profile mongodb
  # ==============================================
  mongodb:
    image: mongo:7
    container_name: ndp-mongodb
    profiles: ["mongodb", "full"]
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
  # Activate with: --profile mongodb
  # ==============================================
  mongo-express:
    image: mongo-express:latest
    container_name: ndp-mongo-express
    profiles: ["mongodb", "full"]
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
  # Activate with: --profile s3
  # ==============================================
  minio:
    image: minio/minio:latest
    container_name: ndp-minio
    profiles: ["s3", "full"]
    ports:
      - "9002:9000"      # API port
      - "9003:9001"      # Console UI
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
  # Activate with: --profile kafka
  # ==============================================
  zookeeper:
    image: confluentinc/cp-zookeeper:7.6.0
    container_name: ndp-zookeeper
    profiles: ["kafka", "full"]
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
  # Activate with: --profile kafka
  # ==============================================
  kafka:
    image: confluentinc/cp-kafka:7.6.0
    container_name: ndp-kafka
    profiles: ["kafka", "full"]
    ports:
      - "9094:9092"      # External access
      - "9095:9093"      # Internal access
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
  # Activate with: --profile kafka
  # ==============================================
  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    container_name: ndp-kafka-ui
    profiles: ["kafka", "full"]
    ports:
      - "8081:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: ndp-demo
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
  # Activate with: --profile jupyter
  # ==============================================
  jupyterlab:
    image: jupyter/scipy-notebook:latest
    container_name: ndp-jupyterlab
    profiles: ["jupyter", "full"]
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
  # NDP-EP Frontend - Web Interface
  # Activate with: --profile frontend
  # ==============================================
  frontend:
    image: rbardaji/ndp-ep-frontend:latest
    container_name: ndp-frontend
    profiles: ["frontend", "full"]
    ports:
      - "3000:80"
    environment:
      NDP_EP_API: http://ndp-ep-api:8000
    networks:
      - ndp-network
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped

volumes:
  mongodb_data:
  mongodb_config:
  minio_data:
  zookeeper_data:
  zookeeper_log:
  kafka_data:
  jupyterlab_data:

networks:
  ndp-network:
    driver: bridge
```

Create a `.env` file (see below) and run:

```bash
# Start API + MongoDB only (minimal setup)
docker compose --profile mongodb up -d

# Start API + MongoDB + Kafka + S3
docker compose --profile mongodb --profile kafka --profile s3 up -d

# Start everything (all profiles)
docker compose --profile full up -d
```

The API will be available at `http://localhost:8002`.

### Using Docker Run

If you only need the API and already have a MongoDB instance running:

```bash
docker run -d -p 8000:8000 \
  -e LOCAL_CATALOG_BACKEND="mongodb" \
  -e CKAN_LOCAL_ENABLED="True" \
  -e MONGODB_CONNECTION_STRING="mongodb://admin:admin123@your-mongodb-host:27017" \
  -e MONGODB_DATABASE="ndp_local_catalog" \
  -e ORGANIZATION="my-organization" \
  -e EP_NAME="my-endpoint" \
  rbardaji/ndp-ep-api:latest
```

## Available Profiles

| Profile | Services | Description |
|---------|----------|-------------|
| `mongodb` | MongoDB + Mongo Express | Local catalog database. Mongo Express available at `http://localhost:8082` (login: `admin` / `admin123`) |
| `kafka` | Zookeeper + Kafka + Kafka UI | Streaming data platform. Kafka UI available at `http://localhost:8081` |
| `s3` | MinIO | S3-compatible object storage. Console at `http://localhost:9003` (login: `minioadmin` / `minioadmin123`) |
| `jupyter` | JupyterLab | Interactive notebooks. Available at `http://localhost:8888` (token: `testing_token`) |
| `frontend` | NDP-EP Web UI | Web interface at `http://localhost:3000` |
| `full` | All of the above | Starts all optional services |

## Routes

| Path | Description |
|------|-------------|
| `/` | List all datasources (also acts as health check) |
| `/search` | Search datasets by terms with optional filters |
| `/health` | Liveness probe |
| `/ready` | Readiness probe (checks dependencies) |
| `/status/` | API status, configuration, and service details (requires auth) |
| `/status/jupyter` | JupyterLab availability check |
| `/status/kafka` | Kafka connection details |
| `/status/rexec-api` | Remote execution service status |
| `/dataset` | Dataset CRUD operations |
| `/dataset/{id}/publish` | Publish a dataset from local catalog to Pre-CKAN |
| `/organization` | Organization management |
| `/resources/` | Resource search and management |
| `/url` | Register/update URL-based resources |
| `/s3` | Register/update S3 object resources |
| `/kafka` | Register/update Kafka topic resources |
| `/services` | Service registry and management |
| `/buckets` | S3 bucket management (create, list, delete) |
| `/objects/{bucket}` | S3 object management (upload, download, delete) |
| `/pelican/*` | Pelican federation (browse, download, import) |
| `/user/info` | Current user information |
| `/mcp` | Model Context Protocol server for AI agents |
| `/docs` | Swagger API documentation |
| `/redoc` | ReDoc API documentation |

## Environment Variables

### API Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `ROOT_PATH` | Root path prefix for reverse proxy deployment (e.g., `/api`). Useful when the API runs behind a reverse proxy at a subpath | _(empty)_ |
| `ORGANIZATION` | Organization name for this endpoint, used in metrics and identification | `Unknown Organization` |
| `EP_NAME` | Unique name for this endpoint instance, used in metrics and status | `Unknown EP` |

### Metrics Configuration

The API runs a background task that periodically sends system metrics (CPU, memory, disk, catalog stats) to the configured federation endpoint.

| Variable | Description | Default |
|----------|-------------|---------|
| `METRICS_INTERVAL_SECONDS` | Interval in seconds for background metrics reporting | `3300` (55 min) |
| `METRICS_ENDPOINT` | URL where metrics are sent periodically. Typically points to the NDP Federation metrics endpoint | `https://federation.ndp.utah.edu/metrics/` |

### Access Control

The API supports Bearer token authentication. When a user makes a request with a token, the API validates it against the configured auth endpoint and retrieves user details. Optionally, write operations can be restricted to users belonging to specific groups.

| Variable | Description | Default |
|----------|-------------|---------|
| `AUTH_API_URL` | URL for token validation and user information retrieval. The API sends the Bearer token to this endpoint to authenticate users | `https://idp.nationaldataplatform.org/temp/information` |
| `ENABLE_GROUP_BASED_ACCESS` | When `True`, write operations (POST, PUT, DELETE) are restricted to users belonging to specific groups. GET endpoints remain public | `False` |
| `GROUP_NAMES` | Comma-separated list of groups allowed for write operations (e.g., `admins,developers,data-managers`). Group matching is case-insensitive. If empty and `ENABLE_GROUP_BASED_ACCESS=True`, all write operations will be denied | _(empty)_ |
| `TEST_TOKEN` | Token for development/testing purposes. Leave blank in production | `testing_token` |

### Local Catalog Backend

The API uses a local catalog to store datasets, resources, and organizations. You can choose between CKAN or MongoDB as the backend. The Global Catalog and Pre-CKAN always use CKAN regardless of this setting.

| Variable | Description | Default |
|----------|-------------|---------|
| `LOCAL_CATALOG_BACKEND` | Backend type for the local catalog: `ckan` or `mongodb` | `ckan` |
| `CKAN_LOCAL_ENABLED` | Enable or disable local catalog write operations (POST, PUT, DELETE). Set to `False` for read-only mode. Note: the variable name contains "CKAN" for historical reasons, but it applies to all backends (CKAN, MongoDB, etc.) | `False` |

### MongoDB Configuration

Required when `LOCAL_CATALOG_BACKEND=mongodb`.

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGODB_CONNECTION_STRING` | Full MongoDB connection URI. For Docker Compose use the service name (e.g., `mongodb://admin:admin123@mongodb:27017`). For local development use `localhost` | `mongodb://localhost:27017` |
| `MONGODB_DATABASE` | MongoDB database name for the local catalog | `ndp_local_catalog` |

### CKAN Configuration

Required when `LOCAL_CATALOG_BACKEND=ckan`.

| Variable | Description | Default |
|----------|-------------|---------|
| `CKAN_URL` | Base URL of your local CKAN instance (e.g., `http://ckan:5000`) | `http://localhost:5000` |
| `CKAN_API_KEY` | API key for CKAN authentication. Get it from your CKAN user profile | _(none)_ |
| `CKAN_VERIFY_SSL` | Verify SSL certificates when connecting to CKAN. Set to `False` for self-signed certificates | `True` |

### Pre-CKAN Staging

Pre-CKAN is a staging environment where datasets are reviewed before they appear in the NDP Central Catalog. When enabled, you can publish datasets from your local catalog to Pre-CKAN using the `POST /dataset/{id}/publish` endpoint.

| Variable | Description | Default |
|----------|-------------|---------|
| `PRE_CKAN_ENABLED` | Enable or disable Pre-CKAN integration | `False` |
| `PRE_CKAN_URL` | URL of the Pre-CKAN instance | _(empty)_ |
| `PRE_CKAN_API_KEY` | API key for Pre-CKAN authentication | _(empty)_ |
| `PRE_CKAN_ORGANIZATION` | Organization name in Pre-CKAN. When set, overrides the original `owner_org` when publishing. Required when your Pre-CKAN credentials are tied to a specific organization | _(empty)_ |

### Kafka Streaming

Enable Kafka to register streaming data topics as dataset resources. Requires the `kafka` profile in Docker Compose (or an external Kafka broker).

| Variable | Description | Default |
|----------|-------------|---------|
| `KAFKA_CONNECTION` | Enable or disable Kafka connectivity | `False` |
| `KAFKA_HOST` | Kafka broker hostname. For Docker Compose use the service name `kafka`. For local development use `localhost` | `localhost` |
| `KAFKA_PORT` | Kafka broker port. Use `9093` for internal Docker network, `9092` for external access | `9092` |

### S3/MinIO Object Storage

Enable S3-compatible storage for managing buckets and objects. Requires the `s3` profile in Docker Compose (or an external S3/MinIO service).

| Variable | Description | Default |
|----------|-------------|---------|
| `S3_ENABLED` | Enable or disable S3 storage integration | `False` |
| `S3_ENDPOINT` | S3 endpoint in `host:port` format. For Docker Compose use `minio:9000`. For local development use `localhost:9000` | `localhost:9000` |
| `S3_ACCESS_KEY` | S3 access key for authentication | `minioadmin` |
| `S3_SECRET_KEY` | S3 secret key for authentication | `minioadmin123` |
| `S3_SECURE` | Use HTTPS for S3 connections. Set to `True` for production environments with SSL | `False` |
| `S3_REGION` | AWS region or S3-compatible region | `us-east-1` |

### Pelican Federation

Enable access to distributed scientific data through the Pelican Federation (OSDF and others). When enabled, adds endpoints for browsing, downloading, and importing external federated datasets.

| Variable | Description | Default |
|----------|-------------|---------|
| `PELICAN_ENABLED` | Enable Pelican federation support | `False` |
| `PELICAN_FEDERATION_URL` | Default Pelican federation URL. Leave empty to use OSDF (Open Science Data Federation). Format: `pelican://federation-host` | _(empty, uses OSDF)_ |
| `PELICAN_DIRECT_READS` | Enable direct reads from Origins, bypassing caches. Set to `False` to use caching infrastructure for better performance | `False` |

### JupyterLab Integration

Requires the `jupyter` profile in Docker Compose (or an external JupyterLab instance).

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_JUPYTERLAB` | Enable JupyterLab integration. Adds JupyterLab status to the `/status/jupyter` endpoint | `False` |
| `JUPYTER_URL` | URL of your JupyterLab instance. For Docker Compose use `http://jupyterlab:8888` | `https://jupyter.org/try-jupyter/lab/` |

### NDP Affinities Integration

When enabled, datasets and services created in this endpoint are automatically registered in the NDP Affinities system, creating relationships between resources across the platform.

| Variable | Description | Default |
|----------|-------------|---------|
| `AFFINITIES_ENABLED` | Enable automatic registration of datasets and services in Affinities | `False` |
| `AFFINITIES_URL` | Base URL of the Affinities API (e.g., `http://affinities-api:8000`) | _(empty)_ |
| `AFFINITIES_EP_UUID` | UUID of this endpoint in the Affinities system. Obtained when you register this endpoint via `POST /endpoints` on the Affinities API | _(empty)_ |
| `AFFINITIES_TIMEOUT` | Request timeout in seconds for Affinities API calls | `30` |

### Remote Execution (Rexec)

| Variable | Description | Default |
|----------|-------------|---------|
| `REXEC_CONNECTION` | Enable or disable Remote Execution Deployment API connectivity | `False` |
| `REXEC_DEPLOYMENT_API_URL` | URL of the Remote Execution Deployment API | _(empty)_ |

## `.env` Example

Below is a complete `.env` file with all available configuration options. See the Environment Variables section above for detailed descriptions of each variable.

```env
# API Configuration
ROOT_PATH=
ORGANIZATION=my-organization
EP_NAME=my-endpoint

# Metrics
METRICS_INTERVAL_SECONDS=3300
METRICS_ENDPOINT=https://federation.ndp.utah.edu/metrics/

# Access Control
ENABLE_GROUP_BASED_ACCESS=False
GROUP_NAMES=

# Authentication
AUTH_API_URL=https://idp.nationaldataplatform.org/temp/information
TEST_TOKEN=

# Local Catalog Backend ("ckan" or "mongodb")
LOCAL_CATALOG_BACKEND=mongodb
CKAN_LOCAL_ENABLED=True

# CKAN (only if LOCAL_CATALOG_BACKEND=ckan)
CKAN_URL=
CKAN_API_KEY=

# MongoDB (only if LOCAL_CATALOG_BACKEND=mongodb)
MONGODB_CONNECTION_STRING=mongodb://admin:admin123@mongodb:27017
MONGODB_DATABASE=ndp_local_catalog

# Pre-CKAN Staging
PRE_CKAN_ENABLED=False
PRE_CKAN_URL=
PRE_CKAN_API_KEY=
PRE_CKAN_ORGANIZATION=

# Kafka Streaming
KAFKA_CONNECTION=True
KAFKA_HOST=kafka
KAFKA_PORT=9093

# S3/MinIO Storage
S3_ENABLED=True
S3_ENDPOINT=minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin123
S3_SECURE=False
S3_REGION=us-east-1

# Pelican Federation
PELICAN_ENABLED=False
PELICAN_FEDERATION_URL=
PELICAN_DIRECT_READS=False

# JupyterLab
USE_JUPYTERLAB=True
JUPYTER_URL=http://jupyterlab:8888

# Affinities
AFFINITIES_ENABLED=False
AFFINITIES_URL=
AFFINITIES_EP_UUID=
AFFINITIES_TIMEOUT=30

# Remote Execution
REXEC_CONNECTION=False
REXEC_DEPLOYMENT_API_URL=
```

## Source Code

GitHub: [https://github.com/national-data-platform/ep-api](https://github.com/national-data-platform/ep-api)
