# api/services/affinities_services/__init__.py
"""
Affinities integration services.

This package provides services for integrating with the NDP Affinities API
to automatically register datasets, services, and their relationships.
"""

from api.services.affinities_services.affinities_client import AffinitiesClient

__all__ = ["AffinitiesClient"]
