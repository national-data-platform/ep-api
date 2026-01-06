# NDP EP API Usage Guide

This guide provides comprehensive documentation for using the NDP Entry Point (EP) API with curl examples, response formats, and common use cases.

## Table of Contents

- [Authentication](#authentication)
- [API Base URL](#api-base-url)
- [Server Selection](#server-selection)
- [Status Endpoints](#status-endpoints)
- [Organizations](#organizations)
- [Datasets](#datasets)
- [Services](#services)
- [URL Resources](#url-resources)
- [S3 Resources](#s3-resources)
- [Kafka Resources](#kafka-resources)
- [Search](#search)
- [Resource Management](#resource-management)
- [Error Handling](#error-handling)

---

## Authentication

The API uses Bearer token authentication. Include the `Authorization` header in your requests:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" https://api.example.com/endpoint
```

### Get User Information

```bash
curl -s http://localhost:8002/user/info \
  -H "Authorization: Bearer testing_token"
```

**Response:**
```json
{
  "roles": ["admin", "user"],
  "groups": ["test_group", "developers"],
  "sub": "test_user",
  "username": "test_user"
}
```

---

## API Base URL

Replace `http://localhost:8002` with your actual API endpoint:

- **Local Development:** `http://localhost:8002`
- **Production:** `https://your-api-domain.com`

### Root Endpoint

```bash
curl -s http://localhost:8002/
```

**Response:**
```json
"API is running successfully."
```

---

## Server Selection

Most endpoints support a `server` query parameter:

| Server | Description |
|--------|-------------|
| `local` | Default. Uses the local catalog backend (MongoDB or CKAN) |
| `pre_ckan` | Uses the pre-production CKAN instance (if enabled) |
| `global` | For search operations across all instances |

Example:
```bash
curl "http://localhost:8002/search?terms=test&server=local"
```

---

## Status Endpoints

### Get API Status

Returns comprehensive information about the API configuration and connected services.

```bash
curl -s http://localhost:8002/status/ \
  -H "Authorization: Bearer testing_token"
```

**Response:**
```json
{
  "api_version": "0.5.0",
  "organization": "Test Organization",
  "ep_name": "test_ep",
  "organization_based_access": false,
  "local_catalog_backend": "mongodb",
  "backend_connected": true,
  "pre_ckan_enabled": true,
  "kafka_enabled": false,
  "jupyterlab_enabled": true,
  "s3_enabled": true,
  "auth_api_url": "https://idp.example.com/information",
  "is_public": true,
  "pre_ckan_connected": true,
  "s3_connected": false
}
```

---

## Organizations

### List Organizations

```bash
curl -s "http://localhost:8002/organization?server=local"
```

**Response:**
```json
["services", "research_group", "test_org"]
```

### Filter Organizations by Name

```bash
curl -s "http://localhost:8002/organization?name=test&server=local"
```

### Create Organization

```bash
curl -s -X POST "http://localhost:8002/organization?server=local" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "research_team",
    "title": "Research Team",
    "description": "Organization for research projects"
  }'
```

**Response:**
```json
{
  "id": "911f00d5-8e99-4d92-9187-5cb8d011c19b",
  "message": "Organization created successfully"
}
```

### Delete Organization

```bash
curl -s -X DELETE "http://localhost:8002/organization/research_team?server=local" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Datasets

### Create General Dataset

```bash
curl -s -X POST "http://localhost:8002/dataset?server=local" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "climate_research_2024",
    "title": "Climate Research Dataset 2024",
    "owner_org": "research_team",
    "notes": "Comprehensive climate data from 2024 research project",
    "tags": ["climate", "research", "2024"],
    "extras": {
      "source": "field_observations",
      "project": "climate_study"
    }
  }'
```

**Response:**
```json
{
  "id": "cf248952-0f9d-4abe-8df2-fbae0b699f4d"
}
```

> **Note:** Some keys are reserved and cannot be used in `extras`: `version`, `ndp_group_id`, `ndp_user_id`

### Update Dataset (Full Update)

```bash
curl -s -X PUT "http://localhost:8002/dataset/DATASET_ID?server=local" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "climate_research_2024_updated",
    "title": "Climate Research Dataset 2024 - Updated",
    "owner_org": "research_team",
    "notes": "Updated comprehensive climate data"
  }'
```

### Partial Update Dataset (PATCH)

Update only specific fields without affecting others:

```bash
curl -s -X PATCH "http://localhost:8002/dataset/DATASET_ID?server=local" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "notes": "Updated description for the dataset"
  }'
```

**Response:**
```json
{
  "message": "Dataset updated successfully"
}
```

---

## Services

Services are registered under the `services` organization.

### Register a New Service

```bash
curl -s -X POST "http://localhost:8002/services?server=local" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "service_name": "weather_api",
    "service_title": "Weather API Service",
    "owner_org": "services",
    "service_url": "https://api.weather.example.com",
    "service_type": "REST API",
    "notes": "Weather data API providing real-time and forecast data",
    "health_check_url": "https://api.weather.example.com/health",
    "documentation_url": "https://docs.weather.example.com"
  }'
```

**Response:**
```json
{
  "id": "f5a319f9-c306-4f39-b7a3-add0dd654ab9"
}
```

### Update Service (PUT)

```bash
curl -s -X PUT "http://localhost:8002/services/SERVICE_ID?server=local" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "service_name": "weather_api",
    "service_title": "Weather API Service - Updated",
    "owner_org": "services",
    "service_url": "https://api.weather.example.com/v2",
    "service_type": "REST API"
  }'
```

### Partial Update Service (PATCH)

```bash
curl -s -X PATCH "http://localhost:8002/services/SERVICE_ID?server=local" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "notes": "Updated service description"
  }'
```

---

## URL Resources

### Create URL Resource

```bash
curl -s -X POST "http://localhost:8002/url?server=local" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "resource_name": "temperature_data",
    "resource_title": "Temperature Dataset",
    "owner_org": "research_team",
    "resource_url": "https://data.example.com/temperature.csv",
    "file_type": "CSV",
    "notes": "Daily temperature readings",
    "processing": {
      "delimiter": ",",
      "header_line": 1,
      "start_line": 2
    }
  }'
```

**Response:**
```json
{
  "id": "a5918817-48a0-4974-8acd-2a582aa090f6"
}
```

### Supported File Types

| File Type | Description |
|-----------|-------------|
| `CSV` | Comma-separated values |
| `JSON` | JSON data files |
| `TXT` | Plain text files |
| `NetCDF` | Network Common Data Form |
| `stream` | Real-time data streams |

### Update URL Resource

```bash
curl -s -X PUT "http://localhost:8002/url/RESOURCE_ID?server=local" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "resource_name": "temperature_data",
    "resource_title": "Temperature Dataset - Updated",
    "owner_org": "research_team",
    "resource_url": "https://data.example.com/temperature_v2.csv",
    "file_type": "CSV"
  }'
```

---

## S3 Resources

### Create S3 Resource

```bash
curl -s -X POST "http://localhost:8002/s3?server=local" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "resource_name": "satellite_images",
    "resource_title": "Satellite Image Archive",
    "owner_org": "research_team",
    "s3_bucket": "research-data",
    "s3_key": "satellite/2024/",
    "file_type": "archive",
    "notes": "Satellite imagery for 2024"
  }'
```

### S3 Bucket Operations

#### List Buckets

```bash
curl -s "http://localhost:8002/s3/buckets/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Create Bucket

```bash
curl -s -X POST "http://localhost:8002/s3/buckets/new-bucket-name" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### List Objects in Bucket

```bash
curl -s "http://localhost:8002/s3/objects/bucket-name" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Get Presigned Download URL

```bash
curl -s "http://localhost:8002/s3/objects/bucket-name/object-key/presigned-download" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Get Presigned Upload URL

```bash
curl -s "http://localhost:8002/s3/objects/bucket-name/object-key/presigned-upload" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Kafka Resources

### Create Kafka Dataset

```bash
curl -s -X POST "http://localhost:8002/kafka?server=local" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "dataset_name": "sensor_stream",
    "dataset_title": "Sensor Data Stream",
    "owner_org": "research_team",
    "kafka_topic": "sensors.temperature",
    "kafka_host": "kafka.example.com",
    "kafka_port": "9092",
    "dataset_description": "Real-time sensor data stream",
    "mapping": {
      "timestamp": "event_time",
      "value": "temperature"
    },
    "processing": {
      "data_key": "data",
      "info_key": "metadata"
    }
  }'
```

### Update Kafka Dataset

```bash
curl -s -X PUT "http://localhost:8002/kafka/DATASET_ID?server=local" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "kafka_topic": "sensors.temperature.v2",
    "kafka_port": "9093"
  }'
```

### Partial Update Kafka Dataset

```bash
curl -s -X PATCH "http://localhost:8002/kafka/DATASET_ID?server=local" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "kafka_host": "new-kafka.example.com"
  }'
```

---

## Search

### Simple GET Search

Search by terms across all fields:

```bash
curl -s "http://localhost:8002/search?terms=climate,temperature&server=local" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
[
  {
    "id": "cf248952-0f9d-4abe-8df2-fbae0b699f4d",
    "name": "climate_research_2024",
    "title": "Climate Research Dataset 2024",
    "owner_org": "research_team",
    "notes": "Comprehensive climate data",
    "resources": [...],
    "extras": {...}
  }
]
```

### Search with Specific Keys

```bash
curl -s "http://localhost:8002/search?terms=research&keys=name&server=local" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Advanced POST Search

```bash
curl -s -X POST "http://localhost:8002/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "owner_org": "services",
    "server": "local"
  }'
```

### Search by Multiple Criteria

```bash
curl -s -X POST "http://localhost:8002/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "search_term": "weather,api",
    "resource_format": "service",
    "server": "local"
  }'
```

### Search with Filter List

```bash
curl -s -X POST "http://localhost:8002/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "filter_list": ["service_type:REST API", "owner_org:services"],
    "server": "local"
  }'
```

---

## Resource Management

### Search Resources

Search for specific resources across datasets:

```bash
curl -s "http://localhost:8002/resources/search?name=temperature&server=local" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "count": 1,
  "results": [
    {
      "id": "5b191c17-153e-4513-83aa-3167de17a317",
      "package_id": "a5918817-48a0-4974-8acd-2a582aa090f6",
      "name": "temperature_data",
      "url": "https://data.example.com/temperature.csv",
      "format": "url",
      "dataset_name": "temperature_data",
      "dataset_title": "Temperature Dataset"
    }
  ]
}
```

### Get Resource by ID

```bash
curl -s "http://localhost:8002/resource/RESOURCE_ID?server=local" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Update Resource within Dataset

```bash
curl -s -X PATCH "http://localhost:8002/dataset/DATASET_ID/resource/RESOURCE_ID?server=local" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "updated_resource_name",
    "description": "Updated resource description"
  }'
```

### Delete Resource from Dataset

```bash
curl -s -X DELETE "http://localhost:8002/dataset/DATASET_ID/resource/RESOURCE_ID?server=local" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Error Handling

### Common HTTP Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `201` | Created |
| `400` | Bad Request - Invalid input |
| `401` | Unauthorized - Missing or invalid token |
| `403` | Forbidden - Insufficient permissions |
| `404` | Not Found - Resource doesn't exist |
| `409` | Conflict - Duplicate resource |
| `422` | Validation Error - Invalid data format |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Duplicate Resource Error

```json
{
  "detail": {
    "error": "Duplicate Dataset",
    "detail": "A dataset with the given name already exists."
  }
}
```

### Validation Error

```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Reserved Key Error

```json
{
  "detail": "Reserved key error: \"Extras contain reserved keys: {'version'}\""
}
```

---

## Best Practices

1. **Always include authentication** - All write operations require a valid Bearer token.

2. **Use appropriate HTTP methods**:
   - `GET` for reading data
   - `POST` for creating new resources
   - `PUT` for full updates
   - `PATCH` for partial updates
   - `DELETE` for removing resources

3. **Handle errors gracefully** - Check the response status code and parse error messages.

4. **Use server parameter** - Specify `server=local` or `server=pre_ckan` based on your environment.

5. **Avoid reserved keys** - Don't use `version`, `ndp_group_id`, or `ndp_user_id` in extras.

---

## Swagger UI

Interactive API documentation is available at:

```
http://localhost:8002/docs
```

The OpenAPI specification can be accessed at:

```
http://localhost:8002/openapi.json
```

---

## Support

For issues and feature requests, please visit:
- GitHub Issues: [national-data-platform/ep-api/issues](https://github.com/national-data-platform/ep-api/issues)
