# api/routes/redirect_routes/service_redirect.py

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from api.services.service_services.redirect_service import get_service_url

router = APIRouter()
logger = logging.getLogger(__name__)


async def proxy_request(
    request: Request, target_url: str, additional_path: Optional[str] = None
) -> Response:
    """
    Proxy an HTTP request to the target service URL.

    Parameters
    ----------
    request : Request
        The original FastAPI request object.
    target_url : str
        The base URL of the target service.
    additional_path : Optional[str]
        Additional path to append to the target URL.

    Returns
    -------
    Response
        The response from the target service.

    Raises
    ------
    HTTPException
        If the request to the target service fails.
    """
    # Construct the full target URL
    service_url = target_url.rstrip("/")
    if additional_path:
        additional_path = additional_path.lstrip("/")
        full_url = f"{service_url}/{additional_path}"
    else:
        full_url = service_url

    # Add query parameters from original request
    if request.url.query:
        full_url = f"{full_url}?{request.url.query}"

    # Prepare headers (exclude host and other problematic headers)
    headers_to_forward = {}
    excluded_headers = {
        "host",
        "content-length",
        "transfer-encoding",
        "connection",
        "upgrade",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
    }

    for name, value in request.headers.items():
        if name.lower() not in excluded_headers:
            headers_to_forward[name] = value

    # Get request body for methods that support it
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
        except Exception as e:
            logger.warning(f"Failed to read request body: {str(e)}")
            body = None

    # Make the proxied request
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=full_url,
                headers=headers_to_forward,
                content=body,
                follow_redirects=False,  # Let the client handle redirects
            )

            # Prepare response headers (exclude problematic ones)
            response_headers = {}
            excluded_response_headers = {
                "content-encoding",
                "content-length",
                "transfer-encoding",
                "connection",
                "upgrade",
                "server",
            }

            for name, value in response.headers.items():
                if name.lower() not in excluded_response_headers:
                    response_headers[name] = value

            # Return the response from the target service
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type"),
            )

    except httpx.TimeoutException:
        logger.error(f"Timeout when proxying request to {full_url}")
        raise HTTPException(status_code=504, detail="Service request timed out")
    except httpx.ConnectError:
        logger.error(f"Connection error when proxying request to {full_url}")
        raise HTTPException(
            status_code=502, detail="Unable to connect to the target service"
        )
    except Exception as e:
        logger.error(f"Error proxying request to {full_url}: {str(e)}")
        raise HTTPException(
            status_code=502, detail=f"Error communicating with target service: {str(e)}"
        )


# Functional endpoints (hidden from Swagger but actually work)
@router.api_route(
    "/services/redirect/{service_identifier}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,  # Hide from Swagger UI
)
async def proxy_to_service_functional(service_identifier: str, request: Request):
    """
    Functional proxy endpoint for service redirection.

    This endpoint actually performs the proxy functionality but is hidden
    from Swagger UI to avoid CORS issues.
    """
    service_url, error = await get_service_url(service_identifier)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return await proxy_request(request, service_url)


@router.api_route(
    "/services/redirect/{service_identifier}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,  # Hide from Swagger UI
)
async def proxy_to_service_with_path_functional(
    service_identifier: str, path: str, request: Request
):
    """
    Functional proxy endpoint for service redirection with additional path.

    This endpoint actually performs the proxy functionality but is hidden
    from Swagger UI to avoid CORS issues.
    """
    service_url, error = await get_service_url(service_identifier)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return await proxy_request(request, service_url, path)


# Documentation-only endpoints (visible in Swagger but not functional)
@router.get(
    "/services/redirect/{service_identifier}",
    summary="[DOCS ONLY] Proxy request to service by name or ID",
    include_in_schema=True,
    description=(
        "### ⚠️ **Documentation Only - Not Functional**\n"
        "This endpoint documentation shows how to use the redirect proxy "
        "functionality. The actual functional endpoints are available but "
        "hidden from Swagger UI to avoid CORS issues.\n\n"
        "### Functional Endpoints (use these URLs directly):\n"
        "- `GET /services/redirect/{service_identifier}`\n"
        "- `POST /services/redirect/{service_identifier}`\n"
        "- `PUT /services/redirect/{service_identifier}`\n"
        "- `PATCH /services/redirect/{service_identifier}`\n"
        "- `DELETE /services/redirect/{service_identifier}`\n\n"
        "### How It Works\n"
        "The redirect service acts as a reverse proxy that forwards HTTP "
        "requests to registered services while preserving:\n"
        "- **HTTP Method**: GET, POST, PUT, PATCH, DELETE\n"
        "- **Query Parameters**: All query parameters are forwarded\n"
        "- **Request Body**: For POST, PUT, PATCH methods\n"
        "- **Headers**: Most headers (excluding connection-specific ones)\n\n"
        "### Response Handling\n"
        "- Returns the exact response from the target service\n"
        "- Preserves status codes, headers, and response body\n"
        "- Handles timeouts and connection errors gracefully\n\n"
        "### Example Usage\n"
        "```bash\n"
        "# GET with query parameters\n"
        "curl 'https://your-api.com/services/redirect/my_api?param=value'\n\n"
        "# POST with JSON payload\n"
        "curl -X POST 'https://your-api.com/services/redirect/my_api' \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        '  -d \'{"name": "John", "email": "john@example.com"}\'\n\n'
        "# PUT with payload\n"
        "curl -X PUT 'https://your-api.com/services/redirect/my_api/users/123' \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        '  -d \'{"name": "John Updated"}\'\n'
        "```\n\n"
        "### Testing Tools\n"
        "Use external tools for testing:\n"
        "- **Postman**: Import the API collection\n"
        "- **curl**: Command line HTTP client\n"
        "- **Your application**: Direct HTTP calls\n"
        "- **Browser**: For GET requests only\n"
    ),
    responses={
        200: {
            "description": "Request successfully proxied to target service",
            "content": {
                "application/json": {
                    "example": {"message": "Response from target service"}
                }
            },
        },
        404: {
            "description": "Service not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Service 'my_service' not found"}
                }
            },
        },
        502: {
            "description": "Bad Gateway - Error communicating with target service",
            "content": {
                "application/json": {
                    "example": {"detail": "Unable to connect to the target service"}
                }
            },
        },
        504: {
            "description": "Gateway Timeout - Target service did not respond",
            "content": {
                "application/json": {"example": {"detail": "Service request timed out"}}
            },
        },
    },
)
async def redirect_docs_only(service_identifier: str):
    """
    Documentation-only endpoint for redirect functionality.

    This endpoint is only for documentation purposes and will return
    an error if actually called. Use the functional endpoints directly.
    """
    raise HTTPException(
        status_code=501,
        detail=(
            "This is a documentation-only endpoint. Use the functional "
            "redirect endpoints directly with your HTTP client. "
            f"Available methods: GET, POST, PUT, PATCH, DELETE at "
            f"/services/redirect/{service_identifier}"
        ),
    )


@router.get(
    "/services/redirect/{service_identifier}/{path:path}",
    summary="[DOCS ONLY] Proxy request to service with additional path",
    include_in_schema=True,
    description=(
        "### ⚠️ **Documentation Only - Not Functional**\n"
        "This endpoint documentation shows how to use the redirect proxy "
        "functionality with additional paths. The actual functional endpoints "
        "are available but hidden from Swagger UI to avoid CORS issues.\n\n"
        "### Functional Endpoints (use these URLs directly):\n"
        "- `GET /services/redirect/{service_identifier}/{path}`\n"
        "- `POST /services/redirect/{service_identifier}/{path}`\n"
        "- `PUT /services/redirect/{service_identifier}/{path}`\n"
        "- `PATCH /services/redirect/{service_identifier}/{path}`\n"
        "- `DELETE /services/redirect/{service_identifier}/{path}`\n\n"
        "### Path Handling\n"
        "- The additional path is appended to the service base URL\n"
        "- Query parameters are preserved and forwarded\n"
        "- Request body is forwarded for applicable methods\n\n"
        "### Example Usage\n"
        "```bash\n"
        "# GET request to service endpoint\n"
        "curl 'https://your-api.com/services/redirect/my_api/users/123?include=profile'\n\n"
        "# POST to create resource\n"
        "curl -X POST 'https://your-api.com/services/redirect/my_api/users' \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        '  -d \'{"name": "John", "email": "john@example.com"}\'\n\n'
        "# DELETE resource\n"
        "curl -X DELETE 'https://your-api.com/services/redirect/my_api/users/123'\n"
        "```\n\n"
        "If `my_api` service URL is `https://api.example.com`, then:\n"
        "- GET request goes to: `https://api.example.com/users/123?include=profile`\n"
        "- POST request goes to: `https://api.example.com/users`\n"
        "- DELETE request goes to: `https://api.example.com/users/123`\n"
    ),
    responses={
        200: {
            "description": "Request successfully proxied to target service",
            "content": {
                "application/json": {
                    "example": {"data": "Response from target service endpoint"}
                }
            },
        },
        404: {
            "description": "Service not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Service 'my_service' not found"}
                }
            },
        },
        502: {
            "description": "Bad Gateway - Error communicating with target service",
            "content": {
                "application/json": {
                    "example": {"detail": "Error communicating with target service"}
                }
            },
        },
        504: {
            "description": "Gateway Timeout - Target service did not respond",
            "content": {
                "application/json": {"example": {"detail": "Service request timed out"}}
            },
        },
    },
)
async def redirect_with_path_docs_only(service_identifier: str, path: str):
    """
    Documentation-only endpoint for redirect with path functionality.

    This endpoint is only for documentation purposes and will return
    an error if actually called. Use the functional endpoints directly.
    """
    raise HTTPException(
        status_code=501,
        detail=(
            "This is a documentation-only endpoint. Use the functional "
            "redirect endpoints directly with your HTTP client. "
            f"Available methods: GET, POST, PUT, PATCH, DELETE at "
            f"/services/redirect/{service_identifier}/{path}"
        ),
    )
