"""Double-submit CSRF, the fleet's pattern (cups `web/middleware.py`).

Every unsafe request (POST, PUT, PATCH, DELETE) to a private page must echo the
`recipes_csrf` cookie back in an `X-CSRF-Token` header; htmx does that through the
`htmx:configRequest` listener in `static/app.js`. The cookie is `httponly=False`
on purpose, because the browser script has to read it.

What's different from the private apps: this site is public, so the cookie is
only handed out on the private pages (`/me` and below), which only the owner
reaches through Cloudflare Access. Visitors never get a cookie, and the shared
cache-friendly responses (recipes, static assets) never carry `Set-Cookie`. The
owner's header button calls `/me/whoami` on every page, so the cookie is in
place before the cook-log form can appear. The check is scoped the same way: a
public POST (a visitor's counter, say) carries no session to forge, and its
sender never holds the cookie.
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request
    from starlette.responses import Response

CSRF_COOKIE = "recipes_csrf"
CSRF_HEADER = "x-csrf-token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def _is_private(path: str) -> bool:
    return path == "/me" or path.startswith("/me/")


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        token = request.cookies.get(CSRF_COOKIE)
        if request.method not in SAFE_METHODS and _is_private(request.url.path):
            header = request.headers.get(CSRF_HEADER)
            if not token or not header or not secrets.compare_digest(token, header):
                return JSONResponse({"detail": "CSRF token mismatch"}, status_code=403)

        response = await call_next(request)
        if not token and _is_private(request.url.path):
            # Secure everywhere but localhost. Keyed off the hostname, not the
            # scheme: TLS ends at Cloudflare, so the app sees plain http.
            host = (request.url.hostname or "").lower()
            response.set_cookie(
                CSRF_COOKIE,
                secrets.token_urlsafe(32),
                secure=host not in {"localhost", "127.0.0.1", "::1"},
                samesite="strict",
                httponly=False,
            )
        return response
