# api/repositories/access_request_repository.py
"""
MongoDB-backed repository for the access-request workflow.

The repository is intentionally narrow: a handful of CRUD operations tailored
to the request lifecycle (create pending, list, load, mark decided). It does
not reuse :class:`MongoDBRepository` because that class implements the catalog
contract and carries unrelated collection handling.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pymongo import DESCENDING, MongoClient, ReturnDocument
from pymongo.collection import Collection


def _utcnow() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


class AccessRequestRepository:
    """CRUD helper for the ``access_requests`` collection."""

    def __init__(
        self,
        connection_string: str,
        database_name: str,
        collection_name: str,
    ):
        self._client = MongoClient(connection_string)
        self._collection: Collection = self._client[database_name][collection_name]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        # Lookups by requester and by status dominate the list endpoint.
        self._collection.create_index([("status", 1), ("created_at", DESCENDING)])
        self._collection.create_index("user_sub")

    def close(self) -> None:
        self._client.close()

    def create_pending(
        self,
        user_sub: str,
        username: str,
        email: Optional[str],
        justification: Optional[str],
    ) -> Dict[str, Any]:
        """
        Insert a new pending request.

        Returns
        -------
        Dict[str, Any]
            The inserted document (with ``_id`` set).
        """
        doc = {
            "_id": str(uuid.uuid4()),
            "user_sub": user_sub,
            "username": username,
            "email": email,
            "status": "pending",
            "justification": justification,
            "created_at": _utcnow(),
            "decided_at": None,
            "decided_by_sub": None,
            "decided_by_username": None,
            "grant_type": None,
            "decision_notes": None,
        }
        self._collection.insert_one(doc)
        return doc

    def find_pending_by_user_sub(self, user_sub: str) -> Optional[Dict[str, Any]]:
        """Return the current pending request for a user, if any."""
        return self._collection.find_one({"user_sub": user_sub, "status": "pending"})

    def find_by_id(self, request_id: str) -> Optional[Dict[str, Any]]:
        return self._collection.find_one({"_id": request_id})

    def list(
        self,
        status: Optional[Literal["pending", "approved", "rejected"]] = "pending",
    ) -> List[Dict[str, Any]]:
        """List requests, newest first. ``None`` returns every status."""
        query: Dict[str, Any] = {}
        if status is not None:
            query["status"] = status
        cursor = self._collection.find(query).sort("created_at", DESCENDING)
        return list(cursor)

    def mark_decided(
        self,
        request_id: str,
        status: Literal["approved", "rejected"],
        decided_by_sub: str,
        decided_by_username: str,
        grant_type: Optional[Literal["member", "admin"]],
        decision_notes: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Record the admin's decision on a pending request.

        Returns the updated document, or ``None`` if the request is not in
        ``pending`` state (or does not exist).
        """
        result = self._collection.find_one_and_update(
            {"_id": request_id, "status": "pending"},
            {
                "$set": {
                    "status": status,
                    "decided_at": _utcnow(),
                    "decided_by_sub": decided_by_sub,
                    "decided_by_username": decided_by_username,
                    "grant_type": grant_type,
                    "decision_notes": decision_notes,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return result
