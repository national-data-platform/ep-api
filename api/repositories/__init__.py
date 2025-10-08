# api/repositories/__init__.py
"""
Repository layer for data catalog abstraction.

This module provides an abstraction layer over different catalog backends
(CKAN, MongoDB, etc.) allowing the application to switch between them
transparently through configuration.
"""

from api.repositories.base_repository import DataCatalogRepository
from api.repositories.ckan_repository import CKANRepository
from api.repositories.mongodb_repository import MongoDBRepository

__all__ = [
    "DataCatalogRepository",
    "CKANRepository",
    "MongoDBRepository",
]
