# api/routes/search_routes/list_organizations_route.py
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.config.ckan_settings import ckan_settings
from api.services import organization_services
from api.services.auth_services.get_current_user import get_current_user
from api.services.metadata_services import hash_user_id

router = APIRouter()

# This route used to be fully unauthenticated. We only need a user
# identity when the caller asks for ``?mine=true``, so we don't want to
# start rejecting anonymous callers — that would be a breaking change
# for anyone consuming ``GET /organization`` without a token.
_optional_bearer = HTTPBearer(auto_error=False)


def _get_optional_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_optional_bearer),
) -> Optional[Dict[str, Any]]:
    """
    Resolve user info if a Bearer token is provided; return ``None``
    otherwise. Reuses the same validation logic as the required-auth
    dependencies, so behavior with a token matches the rest of the API.
    """
    if creds is None:
        return None
    try:
        return get_current_user(creds)
    except HTTPException:
        return None


@router.get(
    "/organization",
    response_model=List[str],
    summary="List all organizations",
    description=(
        "Retrieve a list of all organizations, with optional name filtering "
        "and optional CKAN server selection."
    ),
    responses={
        200: {
            "description": "A list of all organizations",
            "content": {"application/json": {"example": ["org1", "org2", "org3"]}},
        },
        400: {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "example": {"detail": "Error message explaining the bad request"}
                }
            },
        },
    },
)
async def list_organizations(
    name: Optional[str] = Query(
        None, description="An optional string to filter organizations by name"
    ),
    server: Literal["local", "global", "pre_ckan"] = Query(
        "global",
        description=(
            "Specify the server to list organizations from. Defaults to " "'local'."
        ),
    ),
    mine: bool = Query(
        False,
        description=(
            "When true, only return organizations created by the "
            "authenticated user. Requires a Bearer token; orgs created "
            "before the creator-hash feature carry no attribution and "
            "are never included."
        ),
    ),
    user_info: Optional[Dict[str, Any]] = Depends(_get_optional_user),
):
    """
    Endpoint to list all organizations. Optionally, filter organizations
    by a partial name and specify the CKAN server.

    Parameters
    ----------
    name : Optional[str]
        A string to filter organizations by name (case-insensitive).
    server : Literal['local', 'global', 'pre_ckan']
        The CKAN server to list organizations from. Defaults to 'local'.
    mine : bool
        If true, restrict the result to organizations that carry the
        authenticated user's creator hash. Requires a Bearer token.
    user_info : Optional[Dict[str, Any]]
        Authenticated user info, when a Bearer token is present.

    Returns
    -------
    List[str]
        A list of organization names, optionally filtered by the provided
        name.

    Raises
    ------
    HTTPException
        If there is an error retrieving the list of organizations, an
        HTTPException is raised with a detailed message.
    """
    if server == "pre_ckan" and not ckan_settings.pre_ckan_enabled:
        raise HTTPException(
            status_code=400, detail="Pre-CKAN is disabled and cannot be used."
        )

    user_hash: Optional[str] = None
    if mine:
        if not user_info:
            raise HTTPException(
                status_code=401,
                detail=(
                    "Authentication required to filter organizations by "
                    "'mine'. Provide a valid Bearer token."
                ),
            )
        user_hash = hash_user_id(user_info)

    try:
        organizations = organization_services.list_organization(
            name=name, server=server, user_hash=user_hash
        )
        return organizations
    except Exception as e:
        # Convert the internal CKAN error to a more user-friendly message
        error_message = str(e)

        if "No scheme supplied" in error_message:
            # Provide a cleaner explanation for the user
            raise HTTPException(
                status_code=400,
                detail=("Server is not configured or " "is unreachable."),
            )

        # Otherwise, return the original error
        raise HTTPException(status_code=400, detail=error_message)
