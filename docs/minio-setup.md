# S3-Compatible Storage Setup Guide (MINIO Example)

This guide explains how to set up S3-compatible object storage for use with the NDP-EP API, using MINIO as an example.

## What is MINIO?

MINIO is a popular, high-performance S3-compatible object storage system that can be used as an example for S3 storage setup. It supports:
- **File Storage**: Store and manage files, documents, images, and data
- **Backup Storage**: Create backup repositories for datasets
- **Data Archiving**: Long-term storage of infrequently accessed data
- **API Integration**: Direct S3-compatible API access for applications

## Quick Setup with Docker

### Option 1: Standalone Container

Run MINIO as a single Docker container:

```bash
docker run -d \
  --name ndp-minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin123 \
  -v minio_data:/data \
  minio/minio:latest server /data --console-address ":9001"
```

> **📝 Note**: If you get a "port already allocated" error, make sure no other services are using ports 9000 or 9001. You can check with `docker ps` and stop any conflicting containers.

### Option 2: Using Docker Compose

Create a `docker-compose.yml` file:

```yaml
services:
  minio:
    image: minio/minio:latest
    container_name: ndp-minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin123
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    networks:
      - backend

volumes:
  minio_data:
    driver: local

networks:
  backend:
    driver: bridge
```

Run with:
```bash
# Modern Docker Compose (recommended)
docker compose up -d

# Or legacy docker-compose if available
docker-compose up -d
```

> **📝 Note**: The `version` field is obsolete in modern Docker Compose and will show a warning if included.

## Access Points

Once MINIO is running, you can access:

- **MINIO API**: `http://localhost:9000` (or `http://YOUR_SERVER_IP:9000`)
  - Used by the NDP-EP API for programmatic access
  - S3-compatible REST API endpoint

- **MINIO Console**: `http://localhost:9001` (or `http://YOUR_SERVER_IP:9001`)
  - Web-based management interface
  - Create buckets, upload files, manage users

> **🔧 Replace `localhost`**: If running on a remote server, replace `localhost` with your server's IP address (e.g., `192.168.1.100`).

## Default Credentials

- **Username**: `minioadmin`
- **Password**: `minioadmin123`

> **⚠️ Security Warning**: Change the default credentials in production environments!

## Configure NDP-EP API

Update your `.env` file to connect the API to your S3-compatible storage (using MINIO as example):

```bash
# Enable S3 storage integration
S3_ENABLED=True

# S3 endpoint (replace YOUR_SERVER_IP with your actual server IP)
S3_ENDPOINT=YOUR_SERVER_IP:9000

# S3 credentials (match your S3 service setup)
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin123

# Connection security
S3_SECURE=False  # Set to True if using HTTPS

# Default region
S3_REGION=us-east-1
```

## Verify Installation

### 1. Check Container Status
```bash
docker ps | grep minio
```

> **✅ Expected result**: You should see a running container with ports `9000-9001->9000-9001/tcp`

Example output:
```
12b831bae9ca   minio/minio:latest   "/usr/bin/docker-ent…"   8 seconds ago   Up 7 seconds   0.0.0.0:9000-9001->9000-9001/tcp   ndp-minio
```

### 2. Test API Connection
```bash
# Replace localhost with your server IP if running remotely
curl http://localhost:9000/minio/health/ready
```

> **✅ Expected result**: HTTP 200 response means MINIO API is working correctly.

### 3. Access Web Console
Open `http://localhost:9001` in your browser (replace `localhost` with your server IP if running remotely) and log in with:
- **Username**: `minioadmin`
- **Password**: `minioadmin123`

### 4. Test NDP-EP API Integration
Once both MINIO and the NDP-EP API are running, test the integration:

```bash
# List buckets via NDP-EP API (replace YOUR_API_TOKEN with your actual token)
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
     http://localhost:8001/s3/buckets

# Create a test bucket (replace YOUR_API_TOKEN with your actual token)
curl -X POST \
     -H "Authorization: Bearer YOUR_API_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name": "test-bucket"}' \
     http://localhost:8001/s3/buckets
```

> **🔑 Get API Token**: You can use `testing_token` for development, or get a real token from the NDP authentication system.

## Troubleshooting

### MINIO Container Won't Start
- Check if ports 9000 and 9001 are available
- Verify Docker has permissions to create volumes
- Check container logs: `docker logs ndp-minio`

### Connection Refused from NDP-EP API
- Verify MINIO container is running and accessible
- Check firewall settings for ports 9000/9001
- Ensure MINIO_ENDPOINT in `.env` matches your server IP
- Verify credentials match between MINIO and API configuration

### Permission Denied Errors
- Check MINIO credentials are correct
- Verify the API key has sufficient permissions
- Review MINIO access policies in the web console

## Advanced Configuration

### Multi-Node Setup
For high-availability deployments, refer to the [MINIO distributed setup documentation](https://docs.min.io/docs/distributed-minio-quickstart-guide.html).

### Backup and Recovery
Configure regular backups of your MINIO data directory and consider using MINIO's built-in replication features.

### Monitoring
MINIO provides Prometheus metrics at `http://your-server:9000/minio/v2/metrics/cluster` for monitoring integration.

---

For more information about MINIO, visit the [official documentation](https://docs.min.io/).