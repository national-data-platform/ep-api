# api/middleware/correlation_id.py
"""Correlation ID middleware for request tracing."""

import uuid
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable to store correlation ID for the current request
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)

# Header name for correlation ID
CORRELATION_ID_HEADER = "X-Correlation-ID"


def get_correlation_id() -> Optional[str]:
    """
    Get the correlation ID for the current request.

    Returns
    -------
    Optional[str]
        The correlation ID if set, None otherwise.
    """
    return correlation_id_ctx.get()


def generate_correlation_id() -> str:
    """
    Generate a new correlation ID.

    Returns
    -------
    str
        A new UUID4 string.
    """
    return str(uuid.uuid4())


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns a unique correlation ID to each request.

    The correlation ID is:
    - Extracted from the incoming X-Correlation-ID header if present
    - Generated as a new UUID4 if not present
    - Stored in a context variable for access throughout the request
    - Added to the response headers
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request and add correlation ID.

        Parameters
        ----------
        request : Request
            The incoming request.
        call_next : callable
            The next middleware or route handler.

        Returns
        -------
        Response
            The response with correlation ID header.
        """
        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get(CORRELATION_ID_HEADER)
        if not correlation_id:
            correlation_id = generate_correlation_id()

        # Set correlation ID in context
        token = correlation_id_ctx.set(correlation_id)

        try:
            # Process the request
            response = await call_next(request)

            # Add correlation ID to response headers
            response.headers[CORRELATION_ID_HEADER] = correlation_id

            return response
        finally:
            # Reset context variable
            correlation_id_ctx.reset(token)
