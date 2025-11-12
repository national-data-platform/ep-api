# api/repositories/mongodb_repository.py
"""
MongoDB implementation of the DataCatalogRepository interface.

This module provides a MongoDB-based catalog backend that mimics CKAN's
API responses, allowing MongoDB to be used as a drop-in replacement for
the local CKAN instance.
"""

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import DuplicateKeyError

from api.repositories.base_repository import DataCatalogRepository


class MongoDBRepository(DataCatalogRepository):
    """
    MongoDB implementation of the catalog repository.

    This class provides a MongoDB backend for the data catalog that
    maintains compatibility with CKAN's API structure and behavior.

    The database structure:
    - packages collection: Stores datasets/packages
    - resources collection: Stores resources (linked to packages)
    - organizations collection: Stores organizations

    Parameters
    ----------
    connection_string : str
        MongoDB connection string (e.g., "mongodb://localhost:27017")
    database_name : str
        Name of the database to use (default: "ndp_local_catalog")
    """

    def __init__(self, connection_string: str, database_name: str = "ndp_local_catalog"):
        """
        Initialize MongoDB repository.

        Parameters
        ----------
        connection_string : str
            MongoDB connection URI
        database_name : str
            Database name to use
        """
        self.client = MongoClient(connection_string)
        self.db = self.client[database_name]
        self.packages = self.db.packages
        self.resources = self.db.resources
        self.organizations = self.db.organizations

        # Create indexes for better performance
        self._create_indexes()

    def _create_indexes(self):
        """Create necessary indexes for collections."""
        # Package indexes
        self.packages.create_index("name", unique=True)
        self.packages.create_index("owner_org")
        self.packages.create_index([("title", "text"), ("notes", "text")])

        # Resource indexes
        self.resources.create_index("package_id")

        # Organization indexes
        self.organizations.create_index("name", unique=True)

    def _clean_doc(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove MongoDB's _id field and ensure proper structure.

        Parameters
        ----------
        doc : dict
            MongoDB document

        Returns
        -------
        dict
            Cleaned document compatible with CKAN response format
        """
        if doc and "_id" in doc:
            doc.pop("_id")
        return doc

    def package_create(self, **kwargs) -> Dict[str, Any]:
        """
        Create a new package in MongoDB.

        Parameters
        ----------
        name : str
            Unique package name
        title : str
            Package title
        owner_org : str
            Organization ID or name
        notes : str, optional
            Package description
        extras : list, optional
            List of extra metadata dicts with 'key' and 'value'

        Returns
        -------
        dict
            Created package data

        Raises
        ------
        Exception
            If package creation fails (e.g., duplicate name, org not found)
        """
        # Validate that organization exists (matching CKAN behavior)
        owner_org = kwargs.get("owner_org")
        if owner_org:
            org = self.organizations.find_one({"$or": [{"id": owner_org}, {"name": owner_org}]})
            if not org:
                # Match CKAN's error format exactly
                raise Exception("{'owner_org': ['Organization does not exist'], '__type': 'Validation Error'}")
            # Use the organization ID (not name) for consistency
            owner_org = org["id"]

        package_id = str(uuid.uuid4())
        now = datetime.utcnow()

        package_doc = {
            "id": package_id,
            "name": kwargs.get("name"),
            "title": kwargs.get("title", ""),
            "owner_org": owner_org,
            "notes": kwargs.get("notes", ""),
            "extras": kwargs.get("extras", []),
            "resources": [],
            "metadata_created": now.isoformat(),
            "metadata_modified": now.isoformat(),
            "state": "active",
            "type": "dataset",
        }

        try:
            self.packages.insert_one(package_doc.copy())
        except DuplicateKeyError:
            raise Exception(f"Package with name '{kwargs.get('name')}' already exists")
        except Exception as e:
            raise Exception(f"Error creating package: {str(e)}")

        return self._clean_doc(package_doc)

    def package_show(self, id: str) -> Dict[str, Any]:
        """
        Retrieve a package by ID or name.

        Parameters
        ----------
        id : str
            Package ID or name

        Returns
        -------
        dict
            Package data

        Raises
        ------
        Exception
            If package not found
        """
        package = self.packages.find_one({"$or": [{"id": id}, {"name": id}]})

        if not package:
            raise Exception(f"Package '{id}' not found")

        return self._clean_doc(package)

    def package_update(self, **kwargs) -> Dict[str, Any]:
        """
        Update an existing package.

        Parameters
        ----------
        id : str
            Package ID or name to update
        **kwargs
            Fields to update

        Returns
        -------
        dict
            Updated package data

        Raises
        ------
        Exception
            If package not found or update fails
        """
        package_id = kwargs.get("id")
        if not package_id:
            raise Exception("Package ID is required for update")

        # Get existing package
        existing = self.package_show(package_id)

        # Update metadata_modified
        kwargs["metadata_modified"] = datetime.utcnow().isoformat()

        # Merge with existing data
        updated_package = {**existing, **kwargs}

        # Update in database
        result = self.packages.update_one(
            {"id": existing["id"]}, {"$set": updated_package}
        )

        if result.matched_count == 0:
            raise Exception(f"Package '{package_id}' not found")

        return self.package_show(existing["id"])

    def package_patch(self, **kwargs) -> Dict[str, Any]:
        """
        Partially update a package (only specified fields).

        Parameters
        ----------
        id : str
            Package ID or name
        **kwargs
            Fields to patch

        Returns
        -------
        dict
            Updated package data

        Raises
        ------
        Exception
            If package not found or patch fails
        """
        package_id = kwargs.pop("id")
        if not package_id:
            raise Exception("Package ID is required for patch")

        # Get existing package to get the real ID
        existing = self.package_show(package_id)

        # Update metadata_modified
        kwargs["metadata_modified"] = datetime.utcnow().isoformat()

        # Apply partial update
        result = self.packages.update_one({"id": existing["id"]}, {"$set": kwargs})

        if result.matched_count == 0:
            raise Exception(f"Package '{package_id}' not found")

        return self.package_show(existing["id"])

    def package_delete(self, id: str) -> None:
        """
        Delete a package and its resources.

        Parameters
        ----------
        id : str
            Package ID or name to delete

        Raises
        ------
        Exception
            If package not found
        """
        # Get package to ensure it exists and get real ID
        package = self.package_show(id)

        # Delete associated resources
        self.resources.delete_many({"package_id": package["id"]})

        # Delete package
        result = self.packages.delete_one({"id": package["id"]})

        if result.deleted_count == 0:
            raise Exception(f"Package '{id}' not found")

    def package_search(
        self,
        q: str = "*:*",
        fq: str = "",
        fq_list: Optional[List[str]] = None,
        rows: int = 10,
        start: int = 0,
        sort: str = "score desc, metadata_modified desc",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Search packages in MongoDB.

        Parameters
        ----------
        q : str
            Search query (supports text search on title and notes)
        fq : str
            Filter query (format: "field:value")
        fq_list : Optional[List[str]]
            List of filter queries (alternative to fq)
        rows : int
            Number of results to return
        start : int
            Offset for pagination
        sort : str
            Sort specification

        Returns
        -------
        dict
            Search results with 'count' and 'results' keys
        """
        query = {}

        # Handle text search
        if q and q != "*:*":
            # Simple text search on title and notes
            query["$or"] = [
                {"title": {"$regex": re.escape(q), "$options": "i"}},
                {"notes": {"$regex": re.escape(q), "$options": "i"}},
                {"name": {"$regex": re.escape(q), "$options": "i"}},
            ]

        # Handle filter query list (preferred method)
        if fq_list:
            for filter_item in fq_list:
                if ":" in filter_item:
                    field, value = filter_item.split(":", 1)
                    field = field.strip()
                    value = value.strip().strip('"')
                    query[field] = value
        # Handle filter query string (fallback)
        elif fq:
            filters = fq.split(" AND ")
            for filter_item in filters:
                if ":" in filter_item:
                    field, value = filter_item.split(":", 1)
                    field = field.strip()
                    value = value.strip().strip('"')
                    query[field] = value

        # Parse sort (simplified - supports "field asc/desc")
        sort_list = []
        if sort:
            for sort_item in sort.split(","):
                parts = sort_item.strip().split()
                if len(parts) >= 2:
                    field = parts[0]
                    direction = ASCENDING if "asc" in parts[1].lower() else DESCENDING
                    sort_list.append((field, direction))

        # Execute query
        cursor = self.packages.find(query)

        if sort_list:
            cursor = cursor.sort(sort_list)

        # Get total count
        count = self.packages.count_documents(query)

        # Apply pagination
        results = list(cursor.skip(start).limit(rows))

        # Clean documents
        results = [self._clean_doc(doc) for doc in results]

        # Expand owner_org to organization object (CKAN compatibility)
        for result in results:
            if result.get("owner_org"):
                org = self.organizations.find_one(
                    {"$or": [{"id": result["owner_org"]}, {"name": result["owner_org"]}]}
                )
                if org:
                    result["organization"] = {
                        "id": org["id"],
                        "name": org["name"],
                        "title": org.get("title", ""),
                        "description": org.get("description", ""),
                        "image_url": org.get("image_url", ""),
                        "type": org.get("type", "organization"),
                        "state": org.get("state", "active"),
                    }

        return {"count": count, "results": results}

    def resource_create(self, **kwargs) -> Dict[str, Any]:
        """
        Create a resource within a package.

        Parameters
        ----------
        package_id : str
            Package ID to add resource to
        name : str
            Resource name
        url : str
            Resource URL
        description : str, optional
            Resource description
        format : str, optional
            Resource format

        Returns
        -------
        dict
            Created resource data

        Raises
        ------
        Exception
            If resource creation fails or package not found
        """
        package_id = kwargs.get("package_id")
        if not package_id:
            raise Exception("package_id is required for resource creation")

        # Verify package exists
        package = self.package_show(package_id)

        resource_id = str(uuid.uuid4())
        now = datetime.utcnow()

        resource_doc = {
            "id": resource_id,
            "package_id": package["id"],
            "name": kwargs.get("name", ""),
            "url": kwargs.get("url", ""),
            "description": kwargs.get("description", ""),
            "format": kwargs.get("format", ""),
            "created": now.isoformat(),
            "last_modified": now.isoformat(),
        }

        try:
            # Insert resource document
            self.resources.insert_one(resource_doc.copy())

            # Add resource to package's resources array
            self.packages.update_one(
                {"id": package["id"]}, {"$push": {"resources": resource_doc.copy()}}
            )

            # Update package metadata_modified
            self.packages.update_one(
                {"id": package["id"]},
                {"$set": {"metadata_modified": now.isoformat()}},
            )

        except Exception as e:
            raise Exception(f"Error creating resource: {str(e)}")

        return self._clean_doc(resource_doc)

    def resource_show(self, id: str) -> Dict[str, Any]:
        """
        Retrieve a resource by ID.

        Parameters
        ----------
        id : str
            Resource ID

        Returns
        -------
        dict
            Resource data

        Raises
        ------
        Exception
            If resource not found
        """
        resource = self.resources.find_one({"id": id})

        if not resource:
            raise Exception(f"Resource '{id}' not found")

        return self._clean_doc(resource)

    def resource_delete(self, id: str) -> None:
        """
        Delete a resource.

        Parameters
        ----------
        id : str
            Resource ID to delete

        Raises
        ------
        Exception
            If resource not found
        """
        # Get resource to find package_id
        resource = self.resource_show(id)

        # Remove from resources collection
        self.resources.delete_one({"id": id})

        # Remove from package's resources array
        self.packages.update_one(
            {"id": resource["package_id"]}, {"$pull": {"resources": {"id": id}}}
        )

        # Update package metadata_modified
        self.packages.update_one(
            {"id": resource["package_id"]},
            {"$set": {"metadata_modified": datetime.utcnow().isoformat()}},
        )

    def organization_create(self, **kwargs) -> Dict[str, Any]:
        """
        Create a new organization.

        Parameters
        ----------
        name : str
            Unique organization name
        title : str, optional
            Organization title
        description : str, optional
            Organization description

        Returns
        -------
        dict
            Created organization data

        Raises
        ------
        Exception
            If organization creation fails
        """
        org_id = str(uuid.uuid4())
        now = datetime.utcnow()

        org_doc = {
            "id": org_id,
            "name": kwargs.get("name"),
            "title": kwargs.get("title", ""),
            "description": kwargs.get("description", ""),
            "created": now.isoformat(),
            "state": "active",
            "type": "organization",
        }

        try:
            self.organizations.insert_one(org_doc.copy())
        except DuplicateKeyError:
            raise Exception(
                f"Organization with name '{kwargs.get('name')}' already exists"
            )
        except Exception as e:
            raise Exception(f"Error creating organization: {str(e)}")

        return self._clean_doc(org_doc)

    def organization_show(self, id: str) -> Dict[str, Any]:
        """
        Retrieve an organization by ID or name.

        Parameters
        ----------
        id : str
            Organization ID or name

        Returns
        -------
        dict
            Organization data

        Raises
        ------
        Exception
            If organization not found
        """
        org = self.organizations.find_one({"$or": [{"id": id}, {"name": id}]})

        if not org:
            raise Exception(f"Organization '{id}' not found")

        return self._clean_doc(org)

    def organization_list(
        self, all_fields: bool = False, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        List all organizations.

        Parameters
        ----------
        all_fields : bool
            If True, return full organization data; if False, return only names

        Returns
        -------
        list
            List of organizations or organization names
        """
        if all_fields:
            orgs = list(self.organizations.find({}))
            return [self._clean_doc(org) for org in orgs]
        else:
            orgs = list(self.organizations.find({}, {"name": 1, "_id": 0}))
            return [org["name"] for org in orgs]

    def organization_delete(self, id: str) -> None:
        """
        Delete an organization.

        Note: This does not delete packages belonging to the organization,
        matching CKAN's default behavior.

        Parameters
        ----------
        id : str
            Organization ID or name to delete

        Raises
        ------
        Exception
            If organization not found
        """
        # Get organization to ensure it exists and get real ID
        org = self.organization_show(id)

        # Delete organization
        result = self.organizations.delete_one({"id": org["id"]})

        if result.deleted_count == 0:
            raise Exception(f"Organization '{id}' not found")

    def check_health(self) -> bool:
        """
        Check if MongoDB backend is reachable and operational.

        Returns
        -------
        bool
            True if MongoDB is healthy and reachable, False otherwise
        """
        try:
            # Try to ping MongoDB server
            self.client.admin.command("ping")
            return True
        except Exception:
            return False
