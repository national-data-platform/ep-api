# api/exceptions/handlers.py
"""Global exception handlers for standardized error responses."""

import logging
from datetime import datetime, timezone
from typing import Union

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from api.middleware.correlation_id import get_correlation_id

logger = logging.getLogger(__name__)


def _build_error_response(
    error_type: str,
    detail: Union[str, dict, list],
    status_code: int,
    request: Request,
) -> JSONResponse:
    """
    Build a standardized error response.

    Parameters
    ----------
    error_type : str
        The type/category of error.
    detail : Union[str, dict, list]
        The error detail message or structured data.
    status_code : int
        HTTP status code.
    request : Request
        The original request.

    Returns
    -------
    JSONResponse
        Standardized error response.
    """
    correlation_id = get_correlation_id()

    response_body = {
        "error": error_type,
        "detail": detail,
        "correlation_id": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "path": str(request.url.path),
    }

    return JSONResponse(status_code=status_code, content=response_body)


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """
    Handle HTTPException with standardized response format.

    Parameters
    ----------
    request : Request
        The incoming request.
    exc : HTTPException
        The HTTP exception raised.

    Returns
    -------
    JSONResponse
        Standardized error response.
    """
    correlation_id = get_correlation_id()

    # Determine error type from status code
    error_type_map = {
        400: "BadRequest",
        401: "Unauthorized",
        403: "Forbidden",
        404: "NotFound",
        405: "MethodNotAllowed",
        409: "Conflict",
        422: "ValidationError",
        500: "InternalServerError",
        502: "BadGateway",
        503: "ServiceUnavailable",
        504: "GatewayTimeout",
    }
    error_type = error_type_map.get(exc.status_code, "HTTPError")

    # Log the error
    log_message = f"[{correlation_id}] {error_type}: {exc.detail}"
    if exc.status_code >= 500:
        logger.error(log_message)
    elif exc.status_code >= 400:
        logger.warning(log_message)

    return _build_error_response(
        error_type=error_type,
        detail=exc.detail,
        status_code=exc.status_code,
        request=request,
    )


async def validation_exception_handler(
    request: Request, exc: Union[RequestValidationError, ValidationError]
) -> JSONResponse:
    """
    Handle validation errors with standardized response format.

    Parameters
    ----------
    request : Request
        The incoming request.
    exc : Union[RequestValidationError, ValidationError]
        The validation exception raised.

    Returns
    -------
    JSONResponse
        Standardized validation error response.
    """
    correlation_id = get_correlation_id()

    # Extract errors
    if isinstance(exc, RequestValidationError):
        errors = exc.errors()
    else:
        errors = exc.errors()

    # Format errors for response
    formatted_errors = []
    for error in errors:
        formatted_errors.append(
            {
                "loc": list(error.get("loc", [])),
                "msg": error.get("msg", "Unknown error"),
                "type": error.get("type", "unknown"),
            }
        )

    logger.warning(
        f"[{correlation_id}] ValidationError: {len(formatted_errors)} errors on {request.url.path}"
    )

    return _build_error_response(
        error_type="ValidationError",
        detail=formatted_errors,
        status_code=422,
        request=request,
    )


async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Handle unexpected exceptions with standardized response format.

    Parameters
    ----------
    request : Request
        The incoming request.
    exc : Exception
        The exception raised.

    Returns
    -------
    JSONResponse
        Standardized error response with 500 status.
    """
    correlation_id = get_correlation_id()

    # Log the full exception for debugging
    logger.exception(
        f"[{correlation_id}] Unhandled exception on {request.url.path}: {str(exc)}"
    )

    return _build_error_response(
        error_type="InternalServerError",
        detail="An unexpected error occurred. Please try again later.",
        status_code=500,
        request=request,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with the FastAPI application.

    Parameters
    ----------
    app : FastAPI
        The FastAPI application instance.
    """
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Exception handlers registered successfully")
