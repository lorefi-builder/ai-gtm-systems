"""HTTP layer (Block 3).

Routers map warehouse-mutating actions to endpoints. Every endpoint comments the
production trigger/sync it stands in for. Shared error handling lives here so a
bad request returns a clean JSON error instead of a stack-trace dump.
"""

from __future__ import annotations

from fastapi.responses import JSONResponse

from ops.lifecycle import LifecycleError


def to_error_response(exc: Exception) -> JSONResponse:
    """Map exceptions to clean JSON responses.

    LifecycleError (a guard violation) -> 409 Conflict.
    ValueError (bad input)             -> 400 Bad Request.
    Anything else                      -> 500 with the error type, no traceback.
    """
    if isinstance(exc, LifecycleError):
        return JSONResponse(status_code=409, content={"error": str(exc), "type": "LifecycleError"})
    if isinstance(exc, ValueError):
        return JSONResponse(status_code=400, content={"error": str(exc), "type": "ValueError"})
    return JSONResponse(
        status_code=500, content={"error": str(exc), "type": type(exc).__name__}
    )
