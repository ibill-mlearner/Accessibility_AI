from __future__ import annotations

from typing import Any

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    """Base API error for consistent JSON error responses.

    Logic intent:
    - Provide a stable JSON envelope for API failures.
    - Keep payload details unchanged so callers can inspect raw context.
    - Allow future extension for trace IDs, localization, and docs links.
    """

    status_code = 400
    code = "api_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None, status_code: int | None = None) -> None:
        self.message = message
        self.details = details or {}
        if status_code is not None:
            self.status_code = status_code
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }

# used in api routes imports but may just removed these
class BadRequestError(APIError):
    """400 error used when the client request is malformed or incomplete."""

    status_code = 400
    code = "bad_request"


class NotFoundError(APIError):
    """404 error used when a requested API resource cannot be located."""

    status_code = 404
    code = "not_found"


def register_api_error_handlers(app: Flask) -> None:
    """Attach JSON-first error handlers for all API routes.

    Current sprint behavior:
    - Keep existing endpoint error payloads working.
    - Convert framework exceptions into a stable response shape.

    Future growth intent:
    - Add correlation IDs and observability metadata.
    - Add structured machine-readable validation errors.
    """

    @app.errorhandler(APIError)
    def handle_api_error(exc: APIError):
        return jsonify(exc.to_dict()), exc.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(exc: HTTPException):
        # Preserve Werkzeug status code and description while returning JSON.
        payload = {
            "error": {
                "code": exc.name.lower().replace(" ", "_"),
                "message": exc.description,
                "details": {},
            }
        }
        return jsonify(payload), exc.code

    @app.errorhandler(Exception)
    def handle_uncaught_error(exc: Exception):
        payload = {
            "error": {
                "code": "internal_server_error",
                "message": "Unexpected server error",
                "details": {"exception": exc.__class__.__name__},
            }
        }
        return jsonify(payload), 500
