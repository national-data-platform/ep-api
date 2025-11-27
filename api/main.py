# api/main.py

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi_mcp import FastApiMCP

import api.routes as routes
from api.config import ckan_settings, swagger_settings
from api.config.minio_settings import s3_settings
from api.routes.update_routes.put_dataset import router as dataset_update_router
from api.tasks.metrics_task import record_system_metrics

# Define the format for all logs (timestamp, level, message)
log_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# Define the path for the log file
current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_file = os.path.join("logs", f"metrics_{current_datetime}.log")

# Create the 'logs' directory if it does not exist
os.makedirs("logs", exist_ok=True)

# Create a rotating file handler: 5MB per file, keep 3 backups
file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# Create a console handler for stdout logging
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# Configure the root logger to use both handlers
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run tasks on startup and handle shutdown."""
    # Ensure 'services' organization exists
    if ckan_settings.ckan_local_enabled:
        try:
            from api.services.organization_services.list_organization import list_organization
            from api.services.organization_services.create_organization import create_organization

            logger.info("Checking if 'services' organization exists...")
            organizations = list_organization(server="local")

            if "services" not in organizations:
                logger.info("'services' organization not found, creating it...")
                create_organization(
                    name="services",
                    title="Services",
                    description="Organization for managing services",
                    server="local"
                )
                logger.info("✅ 'services' organization created successfully")
            else:
                logger.info("✅ 'services' organization already exists")
        except Exception as e:
            logger.error(f"❌ Error ensuring 'services' organization exists: {str(e)}")

    # Check MINIO connection on startup if enabled
    logger.info(f"S3 configuration - enabled: {s3_settings.enabled}, is_configured: {s3_settings.is_configured}")
    if s3_settings.enabled:
        try:
            from api.services.minio_services.minio_client import minio_client
            logger.info("Checking S3 connection...")

            if minio_client.test_connection():
                logger.info("✅ S3 connection successful")
            else:
                logger.warning("❌ S3 connection failed - check configuration and service availability")
        except Exception as e:
            logger.error(f"❌ Error testing S3 connection: {str(e)}")
    else:
        logger.info("S3 is disabled in configuration")

    task = asyncio.create_task(record_system_metrics())
    yield
    task.cancel()


app = FastAPI(
    title=swagger_settings.swagger_title,
    description=swagger_settings.swagger_description,
    version=swagger_settings.swagger_version,
    root_path=swagger_settings.root_path,
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.default_router, include_in_schema=False)
if ckan_settings.ckan_local_enabled:
    app.include_router(routes.register_router, tags=["Registration"])
app.include_router(routes.search_router, tags=["Search"])
if ckan_settings.ckan_local_enabled:
    app.include_router(routes.update_router, tags=["Update"])
    app.include_router(dataset_update_router, tags=["Update"])
if ckan_settings.ckan_local_enabled:
    app.include_router(routes.delete_router, tags=["Delete"])
app.include_router(routes.redirect_router, tags=["Redirect"])
app.include_router(routes.status_router, prefix="/status", tags=["Status"])
app.include_router(routes.user_router, tags=["User"])
if s3_settings.enabled:
    app.include_router(routes.minio_bucket_router, tags=["S3"])
    app.include_router(routes.minio_object_router, tags=["S3"])

# Include Pelican routes if enabled
pelican_enabled = os.getenv("PELICAN_ENABLED", "false").lower() == "true"
if pelican_enabled:
    from api.routes.pelican_routes import router as pelican_router
    app.include_router(pelican_router)

# Initialize and mount FastAPI-MCP for AI agent communication
mcp = FastApiMCP(app)
mcp.mount_http()


def custom_openapi():
    """
    Customize the OpenAPI schema to support both username/password
    and token-based authentication, and propagate ROOT_PATH to Swagger UI.
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Propagate ROOT_PATH to Swagger UI servers
    if swagger_settings.root_path:
        openapi_schema["servers"] = [{"url": swagger_settings.root_path}]

    # Define security schemes for OAuth2 Password and Bearer Token
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
    }

    # Apply both security schemes globally to all endpoints
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = [
                {"BearerAuth": []},  # Token authentication
            ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Set the custom OpenAPI schema
app.openapi = custom_openapi

# Configure logger
logger = logging.getLogger(__name__)
