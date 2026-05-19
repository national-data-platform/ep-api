# api/models/access_request_model.py
"""
Models for the access-request workflow.
"""

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class AccessRequestCreate(BaseModel):
    """Payload submitted by a user that wants Endpoint access."""

    justification: Optional[str] = Field(
        None,
        max_length=2000,
        description="Optional note explaining why the user needs access.",
        json_schema_extra={"example": "I need access to work on project X."},
    )


class AccessRequestDecision(BaseModel):
    """Shared bits of an approve/reject decision."""

    notes: Optional[str] = Field(
        None,
        max_length=2000,
        description="Optional note attached to the decision.",
        json_schema_extra={"example": "Welcome aboard."},
    )


class AccessRequestApproveDecision(AccessRequestDecision):
    """Payload sent by an admin to approve a pending request."""

    grant_type: Literal["viewer", "writer", "admin", "member"] = Field(
        ...,
        description=(
            "Role tier to grant the user. "
            "'viewer' adds the user to the endpoint group (the AAI's "
            "default per-group assignment is viewer, so this is the "
            "minimal grant). "
            "'writer' additionally assigns the per-endpoint writer role. "
            "'admin' additionally assigns the per-endpoint admin role. "
            "'member' is kept as a deprecated alias for 'viewer' so "
            "existing clients keep working."
        ),
        json_schema_extra={"example": "viewer"},
    )


class AccessRequestRejectDecision(AccessRequestDecision):
    """Payload sent by an admin to reject a pending request."""

    pass


class AccessRequest(BaseModel):
    """Representation of a stored access request."""

    id: str = Field(..., description="Opaque request identifier.")
    user_sub: str = Field(..., description="Requester's IDP subject (uuid).")
    username: str = Field(..., description="Requester's username.")
    email: Optional[str] = Field(
        None, description="Requester's email, if provided by the IDP."
    )
    status: Literal["pending", "approved", "rejected"] = Field(...)
    justification: Optional[str] = None
    created_at: datetime = Field(...)

    # Present when status != pending
    decided_at: Optional[datetime] = None
    decided_by_sub: Optional[str] = None
    decided_by_username: Optional[str] = None
    grant_type: Optional[Literal["viewer", "writer", "admin", "member"]] = None
    decision_notes: Optional[str] = None

    @classmethod
    def from_document(cls, doc: Dict[str, Any]) -> "AccessRequest":
        """Build an :class:`AccessRequest` from a MongoDB document."""
        payload = {k: v for k, v in doc.items() if k != "_id"}
        payload["id"] = str(doc.get("_id") or doc.get("id"))
        return cls.model_validate(payload)
