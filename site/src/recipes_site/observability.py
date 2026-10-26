"""Request logging and HTTP metrics, ported from cups (`cups.api.observability`).

`RequestLogMiddleware` is pure ASGI and sits outermost. For each request it binds
a `request_id` to the log context, times the request and its database queries,
records the Prometheus HTTP metrics, and writes one `request.completed` line.

It is pure ASGI, not `BaseHTTPMiddleware`, so it can read the matched route
template (`scope["route"]`) after the inner app returns. That template, not the
raw path, is the metrics label: every recipe page is `/{slug:path}`, so the
series count stays small however many recipes there are.

Database time reaches the middleware through a mutable accumulator held in a
contextvar. The middleware sets it once; the SQLAlchemy listeners mutate the
object rather than rebinding the variable, so it survives the context copy that
the inner `BaseHTTPMiddleware` layers (Cloudflare Access, CSRF) make.
"""

from __future__ import annotations

import time
import uuid
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

import structlog
from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy import event

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = structlog.get_logger()

# The metric names and the status label are what the fleet's error-rate alerts
# key on, so keep them in step with cups and cocktails.
HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests by method, matched route, and status code.",
    ("method", "route", "status"),
)
HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds by method and matched route.",
    ("method", "route"),
)
HTTP_IN_PROGRESS = Gauge("http_requests_in_progress", "In-flight HTTP requests.")

UNMATCHED_ROUTE = "<unmatched>"

# The scrape and the probes would swamp the request-rate signal.
_UNRECORDED_PATHS = frozenset({"/metrics", "/health"})


class _DbTiming:
    """One request's database time, mutated in place by the cursor listeners."""

    __slots__ = ("ms", "queries")

    def __init__(self) -> None:
        self.ms = 0.0
        self.queries = 0


_db_timing: ContextVar[_DbTiming | None] = ContextVar("_db_timing", default=None)


def register_db_timing(engine: Engine) -> None:
    """Fold each query's wall time into the current request's total. Safe to
    call twice on one engine; outside a request it records nothing."""
    if getattr(engine, "_recipes_db_timing", False):
        return

    @event.listens_for(engine, "before_cursor_execute")
    def _before(conn: Any, *_rest: Any) -> None:
        conn.info.setdefault("_recipes_q_start", []).append(time.perf_counter())

    @event.listens_for(engine, "after_cursor_execute")
    def _after(conn: Any, *_rest: Any) -> None:
        stack = conn.info.get("_recipes_q_start")
        if not stack:
            return
        elapsed_ms = (time.perf_counter() - stack.pop()) * 1000
        acc = _db_timing.get()
        if acc is not None:
            acc.ms += elapsed_ms
            acc.queries += 1

    engine._recipes_db_timing = True  # type: ignore[attr-defined]


def matched_route(scope: Scope) -> str | None:
    """The matched route template (`/{slug:path}`), or None for an unmatched request."""
    route = scope.get("route")
    return getattr(route, "path", None) if route is not None else None


def _inbound_request_id(scope: Scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"x-request-id":
            return bytes(value).decode("latin-1")[:128]
    return None


class RequestLogMiddleware:
    """Outermost: request id, database timing, metrics, and one completion line."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _inbound_request_id(scope) or uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        db = _DbTiming()
        _db_timing.set(db)
        start = time.perf_counter()
        status_code = 500
        path = scope.get("path", "")
        record = path not in _UNRECORDED_PATHS
        if record:
            HTTP_IN_PROGRESS.inc()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message.setdefault("headers", []).append((b"x-request-id", request_id.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - start
            route = matched_route(scope)
            method = scope.get("method", "")
            if record:
                HTTP_IN_PROGRESS.dec()
                label = route or UNMATCHED_ROUTE
                HTTP_REQUESTS.labels(method=method, route=label, status=str(status_code)).inc()
                HTTP_DURATION.labels(method=method, route=label).observe(elapsed)
                # Probes and scrapes stay out of the log too; they'd be most of it.
                logger.info(
                    "request.completed",
                    method=method,
                    path=path,
                    route=route,
                    status=status_code,
                    latency_ms=round(elapsed * 1000, 1),
                    db_ms=round(db.ms, 1),
                    db_queries=db.queries,
                )
            structlog.contextvars.clear_contextvars()
