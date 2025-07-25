# api/main.py

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

import api.routes as routes
from api.config import ckan_settings, swagger_settings
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
    task = asyncio.create_task(record_system_metrics())
    yield
    task.cancel()


app = FastAPI(
    title=swagger_settings.swagger_title,
    description=swagger_settings.swagger_description,
    version=swagger_settings.swagger_version,
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
if ckan_settings.ckan_local_enabled:
    app.include_router(routes.delete_router, tags=["Delete"])
app.include_router(routes.status_router, prefix="/status", tags=["Status"])
if ckan_settings.ckan_local_enabled:
    app.include_router(routes.update_router, tags=["Update"])
    app.include_router(dataset_update_router, tags=["Update"])


def custom_openapi():
    """
    Customize the OpenAPI schema to support both username/password
    and token-based authentication.
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

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
