# Changelog

All notable changes to the NDP-EP API project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2025-11-27

### Added
- New endpoint to delete individual resources from a dataset
  - `DELETE /dataset/{dataset_id}/resource/{resource_id}` removes a single resource
  - Dataset and other resources remain intact
  - Supports both local and pre_ckan server parameters
  - New service function `delete_resource()` in dataset_services
- New endpoint to partially update individual resources (PATCH)
  - `PATCH /dataset/{dataset_id}/resource/{resource_id}` updates only specified fields
  - Supports updating name, url, description, format
  - New `resource_patch` method in repositories (CKAN and MongoDB)
  - New service function `patch_resource()` in dataset_services

### Fixed
- ROOT_PATH now properly propagates to Swagger UI requests (fixes #23)
  - Added servers configuration to OpenAPI schema when ROOT_PATH is set

### Documentation
- Added link to "Adding New Catalog Backends" documentation in README (fixes #22)

## [0.3.4] - 2025-11-27

### Fixed
- Use purge instead of delete for CKAN datasets and organizations
  - Changed `package_delete` to use `dataset_purge` for permanent deletion
  - Changed `organization_delete` to use `organization_purge` for permanent deletion
  - CKAN's soft-delete left datasets in database, preventing organization deletion
  - Now datasets and organizations are completely removed, enabling proper cleanup

## [0.3.3] - 2025-11-27

### Fixed
- Fixed AttributeError in service routes when using CKAN backend
  - Service routes accessed `repository.ckan_instance` but CKANRepository stores client as `self.ckan`
  - Affected endpoints: POST /services, PUT /services/{id}, PATCH /services/{id}

## [0.3.2] - 2025-11-12

### Fixed
- **Critical: MongoDB organization search compatibility** - Fixed search by organization name in MongoDB backend
  - MongoDB stores `owner_org` as UUID, but CKAN allows searching by organization name
  - Added automatic organization name → UUID resolution in all search paths (q, fq, fq_list)
  - Ensures `{"owner_org": "services"}` searches work identically in MongoDB and CKAN backends
  - Maintains full backward compatibility with existing code

## [0.3.1] - 2025-11-12

### Fixed
- Fixed MongoDB repository `owner_org` expansion issue where services and datasets showed `owner_org: null` in search results
  - Added automatic expansion of `owner_org` UUID to full `organization` object in `package_search` method
  - Maintains CKAN API compatibility by providing organization details (id, name, title, description) in search results
  - All services now correctly display their associated organization

### Added
- Sample data seeding script (`seed_sample_data.py`) for development and demo purposes
  - Creates 4 organizations (services, marine-research, climate-monitoring, biodiversity-lab)
  - Seeds 5 real public API services (Dog Breed, Cat Facts, JSONPlaceholder, Public Holidays, Open-Meteo Weather)
  - Creates S3 buckets and uploads sample data files with real content
  - Includes cleanup functionality to avoid duplicates
- CHANGELOG.md to track all project changes following Keep a Changelog format

## [0.3.0] - 2025-01-10

### Added
- Pelican federation integration for data discovery across federated origins
  - New Pelican repository (`api/repositories/pelican_repository.py`) for federation access
  - Pelican service layer for federation operations
  - Pelican API endpoints for federated dataset discovery
  - Unified download helper with Pelican support
  - Pelican configuration variables and conditional route integration
  - Pelican Origin configuration file
  - Docker Compose services for Pelican federation (origin, cache, director)
- Comprehensive test suite for Pelican routes
- Pelican federation integration documentation

### Changed
- Docker Compose stack now includes Pelican services (optional)
- Enhanced metrics payload with catalog data and configurable interval
- Added `ep_name` and `metrics_interval` to status endpoint
- Updated metrics format for better observability

### Fixed
- Implemented repository pattern for search functions to support MongoDB
- Ensured `LOCAL_CATALOG_BACKEND` is respected in service routes
- Ensured 'services' organization exists on startup

## [0.2.0] - 2024-12-15

### Added
- FastAPI-MCP integration for AI agent communication
  - MCP (Model Context Protocol) server mounted at `/mcp` endpoint
  - AI agents can discover and invoke all API operations automatically
  - Full API surface exposed as MCP tools
- AI agent integration documentation
- Complete Docker Compose stack with web interfaces
  - MongoDB Express for database management
  - Kafka UI for stream monitoring
  - MinIO Console for S3 storage management
  - JupyterLab for interactive data analysis
- Background metrics task with configurable interval
  - System metrics (CPU, memory, disk, public IP)
  - Catalog statistics (dataset count, service count)
  - Service registry information
  - Automatic posting to federation metrics endpoint

### Changed
- Updated Python base image from 3.9 to 3.13
- Improved metrics task with enhanced payload structure
- Updated README with new configuration and metrics information
- Added configurable API root path for flexible deployment

### Fixed
- Full metrics handler updated to support new system metrics format

## [0.1.0] - 2024-11-01

### Added
- Initial release of NDP-EP API
- Repository pattern architecture for catalog abstraction
  - Abstract base repository (`DataCatalogRepository`)
  - CKAN repository implementation
  - MongoDB repository implementation
  - Factory pattern for runtime backend selection
- Three catalog types support:
  - Local catalog (configurable: CKAN or MongoDB)
  - Global catalog (CKAN, read-only)
  - PreCKAN catalog (CKAN staging)
- Core API functionality:
  - Dataset management (CRUD operations)
  - Resource management (URL, S3, Kafka)
  - Organization management
  - Service registry
  - Federated search across catalogs
- S3 integration with MinIO
  - Bucket management
  - Object upload/download
  - Presigned URLs
  - Metadata operations
- Kafka integration
  - Topic-based dataset ingestion
  - Stream metadata management
- Authentication and authorization
  - Bearer token authentication
  - Organization-based access control
  - User information endpoints
- Health checks and status endpoints
- Comprehensive API documentation (OpenAPI/Swagger)
- Docker support with multi-stage builds
- Logging with rotation
- Environment-based configuration

### Infrastructure
- Docker Compose setup for local development
- MongoDB backend for local catalog
- MinIO for S3-compatible storage
- Apache Kafka for streaming data
- Zookeeper for Kafka coordination

---

## Version Schema

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR** version: Incompatible API changes
- **MINOR** version: New functionality in a backwards compatible manner
- **PATCH** version: Backwards compatible bug fixes

## Categories

Changes are grouped into the following categories:
- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security vulnerability fixes
