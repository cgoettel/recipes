"""Cloudflare Access JWT check for the owner's private pages.

The site is public; only paths under PRIVATE_PREFIX are gated. Cloudflare
Access at the edge is the primary gate (an Access app on that path); this
middleware is defense in depth, so a missing or misrouted edge rule still
can't expose private pages.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from functools import lru_cache

import jwt
import structlog
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from recipes_site.config import Settings

logger = structlog.get_logger()

PRIVATE_PREFIX = "/me"


def is_private(path: str) -> bool:
    return path == PRIVATE_PREFIX or path.startswith(PRIVATE_PREFIX + "/")


@lru_cache(maxsize=8)
def _jwks_client(team_domain: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"https://{team_domain}.cloudflareaccess.com/cdn-cgi/access/certs")


def verify(token: str, team_domain: str, audience: str, allowed: set[str]) -> str:
    key = _jwks_client(team_domain).get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        key.key,
        audience=audience,
        issuer=f"https://{team_domain}.cloudflareaccess.com",
        algorithms=["RS256"],
    )
    email = claims.get("email")
    if not isinstance(email, str) or email.lower() not in allowed:
        raise ValueError("email not allowlisted")
    return email


def _forbidden(request: Request) -> Response:
    """A plain page for a browser that reaches /me signed in as someone else."""
    templates = getattr(request.app.state, "templates", None)
    if templates is not None and "text/html" in request.headers.get("accept", ""):
        return templates.TemplateResponse(request, "private.html", status_code=403)  # type: ignore[no-any-return]
    return JSONResponse({"detail": "forbidden"}, status_code=403)


class CloudflareAccessMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, *, settings: Settings) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.settings = settings

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not is_private(request.url.path):
            return await call_next(request)
        s = self.settings
        if s.auth_disabled:
            request.state.owner = True
            return await call_next(request)
        token = request.headers.get("Cf-Access-Jwt-Assertion") or request.cookies.get(
            "CF_Authorization"
        )
        if not token or not s.cf_access_team_domain or not s.cf_access_audience:
            return _forbidden(request)
        try:
            # The JWKS fetch is blocking network I/O; keep it off the event loop.
            await asyncio.to_thread(
                verify,
                token,
                s.cf_access_team_domain,
                s.cf_access_audience,
                s.cf_access_allowed_emails_set,
            )
        except (jwt.PyJWTError, ValueError) as exc:
            logger.warning("cf_access.reject", path=request.url.path, reason=str(exc))
            return _forbidden(request)
        request.state.owner = True
        return await call_next(request)
