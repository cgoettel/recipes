"""FastAPI app: the public recipe site."""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from fractions import Fraction
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import structlog
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.exc import SQLAlchemyError

from recipes_site import __version__, bakers, catalog, cooklog, counts, shopping, stripes
from recipes_site import ingredients as ing
from recipes_site.cf_access import CloudflareAccessMiddleware
from recipes_site.config import Settings, get_settings
from recipes_site.logging import configure_logging

if TYPE_CHECKING:
    from starlette.types import Scope

logger = structlog.get_logger()


class _CachedStaticFiles(StaticFiles):
    """Static assets are versioned (`?v=<build>`) or permanent (fonts), so cache
    them for a year and never revalidate."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


def _pkg_dir(name: str) -> Path:
    return Path(str(resources.files("recipes_site") / name))


_ANCHOR_RE = re.compile(r'<a href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL)

Link = tuple[str, Markup]


def split_links(html: str) -> tuple[Markup, list[Link]]:
    """Pull links out of a checkable row. A row is a <button>, and a link inside
    a button can't be followed (and isn't valid HTML), so the link text stays in
    place and the links themselves render beside the row."""
    links: list[Link] = []

    def repl(m: re.Match[str]) -> str:
        links.append((m.group(1), Markup(m.group(2))))
        return f'<span class="xref">{m.group(2)}</span>'

    return Markup(_ANCHOR_RE.sub(repl, html)), links


@dataclass
class IngredientRow:
    id: str
    amount: str
    item_html: Markup
    flagged: bool
    links: list[Link] = field(default_factory=list)


@dataclass
class StepRow:
    id: str
    number: int
    html: Markup
    links: list[Link] = field(default_factory=list)


@dataclass
class RowGroup[T]:
    heading: str | None
    rows: list[T]


def build_rows(
    recipe: catalog.Recipe, scale: Fraction
) -> tuple[list[RowGroup[IngredientRow]], list[RowGroup[StepRow]]]:
    base = recipe.base_dir
    ing_groups: list[RowGroup[IngredientRow]] = []
    for gi, group in enumerate(recipe.ingredient_groups):
        rows = []
        for ii, line in enumerate(group.items):
            parsed = ing.parse(line)
            shown = ing.display(parsed, scale)
            item_html, links = split_links(catalog.render_inline(shown.item, base))
            rows.append(
                IngredientRow(
                    id=f"i{gi}-{ii}",
                    amount=shown.amount,
                    item_html=item_html,
                    flagged=parsed.flagged,
                    links=links,
                )
            )
        ing_groups.append(RowGroup(heading=group.heading, rows=rows))
    step_groups: list[RowGroup[StepRow]] = []
    number = 0
    for gi, group in enumerate(recipe.step_groups):
        step_rows = []
        for si, text in enumerate(group.items):
            number += 1
            html, links = split_links(catalog.render_inline(text, base))
            step_rows.append(StepRow(id=f"s{gi}-{si}", number=number, html=html, links=links))
        step_groups.append(RowGroup(heading=group.heading, rows=step_rows))
    return ing_groups, step_groups


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    if settings.auth_disabled and not settings.missing_auth_settings():
        # A full Access config means prod; dev leaves the audience empty.
        # Turning auth off there would open the cook log to anyone.
        raise RuntimeError(
            "RECIPES_AUTH_DISABLED is set alongside a complete Cloudflare Access "
            "config; refusing to start with the private pages open"
        )
    if settings.missing_auth_settings() and not settings.auth_disabled:
        logger.warning(
            "auth.private_pages_closed",
            missing=settings.missing_auth_settings(),
            detail="private pages answer 403 until Cloudflare Access is configured",
        )

    app = FastAPI(title="recipes", version=__version__, docs_url=None, redoc_url=None)
    templates = Jinja2Templates(directory=_pkg_dir("templates"))
    templates.env.globals["asset_version"] = settings.asset_version
    templates.env.globals["app_version"] = __version__
    templates.env.globals["scales"] = ing.SCALES
    templates.env.globals["stripes"] = stripes.draw
    templates.env.filters["pct"] = lambda v: f"{float(v):.1f}".rstrip("0").rstrip(".")
    templates.env.filters["grams"] = lambda v: ing.format_number(v, metric=True)
    app.state.templates = templates
    app.state.settings = settings

    def get_catalog() -> catalog.Catalog:
        return catalog.cached(str(settings.content_dir))

    templates.env.globals["nav_categories"] = lambda: get_catalog().categories

    @app.get("/health")
    def health() -> Response:
        # The recipes are baked into the image, so a recipe the catalog can't
        # read breaks every page. Failing here keeps that build from going
        # Ready: the rollout stalls with the old pods serving, and verify_live
        # never sees the new build. No `build` in the error body, so nothing
        # can mistake it for the new build being live.
        try:
            get_catalog()
        except Exception:
            logger.exception("health.catalog_failed")
            return JSONResponse(
                {"status": "error", "detail": "the recipe catalog failed to load"},
                status_code=503,
            )
        return JSONResponse(
            {"status": "ok", "version": __version__, "build": settings.asset_version}
        )

    @app.get("/metrics")
    def metrics(request: Request) -> Response:
        # For the in-cluster scrape only. Anything arriving through Cloudflare
        # carries a CF-Ray header, so the public gets a 404.
        if "cf-ray" in request.headers:
            raise HTTPException(status_code=404)
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    app.mount("/static", _CachedStaticFiles(directory=_pkg_dir("static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> Response:
        cat = get_catalog()
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "categories": cat.categories,
                "recipes": cat.recipes,
                "house_notes": Markup(catalog.render_markdown(cat.house_notes, "")),
            },
        )

    @app.get("/list", response_class=HTMLResponse)
    def shopping_list(request: Request, r: Annotated[list[str] | None, Query()] = None) -> Response:
        cat = get_catalog()
        plan = [
            (cat.recipes[slug], scale)
            for slug, scale in shopping.parse_plan(r or [])
            if slug in cat.recipes
        ]
        labels = {value: label for label, value in ing.SCALES}
        return templates.TemplateResponse(
            request,
            "list.html",
            {
                "plan": [(rec, scale, labels.get(scale, "")) for rec, scale in plan],
                "sections": shopping.build(plan),
                "section_colors": {
                    "Produce": "yellow",
                    "Dairy and eggs": "sky",
                    "Meat and fish": "crimson",
                    "Bakery": "peach",
                    "Frozen": "pale",
                    "Pantry": "violet",
                },
            },
        )

    @app.get("/sw.js")
    def service_worker() -> Response:
        # Served from the root so its scope covers every page.
        body = (_pkg_dir("static") / "sw.js").read_text(encoding="utf-8")
        body = body.replace("__VERSION__", settings.asset_version)
        return Response(
            body,
            media_type="text/javascript",
            headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"},
        )

    # --- The owner's private pages (gated by cf_access + the edge Access app) ---

    def _same_origin(request: Request) -> bool:
        """CSRF guard for the private POSTs: the browser's Origin must be this site."""
        origin = request.headers.get("origin") or ""
        own = f"{request.url.scheme}://{request.url.netloc}"
        return origin in {own, settings.public_origin}

    @app.get("/me", response_class=HTMLResponse)
    def me(request: Request) -> Response:
        cat = get_catalog()
        made = cooklog.made_slugs()
        return templates.TemplateResponse(
            request,
            "me.html",
            {
                "recent": cooklog.recent(),
                "recipes": cat.recipes,
                "untested": sorted(
                    (r for s, r in cat.recipes.items() if s not in made and r.structured),
                    key=lambda r: r.title,
                ),
                "top_viewed": counts.top("view"),
                "top_scaled": counts.top("scale"),
            },
        )

    @app.get("/me/whoami")
    def me_whoami() -> dict[str, bool]:
        # Reaching this at all means the Access check passed. The header's
        # person button calls it to show whether you're signed in.
        return {"owner": True}

    @app.get("/me/status")
    def me_status(slug: str) -> dict[str, object]:
        st = cooklog.status(slug)
        return {"count": st.count, "last": st.last.isoformat() if st.last else None}

    @app.post("/me/log")
    async def me_log(request: Request) -> Response:
        if not _same_origin(request):
            raise HTTPException(status_code=403)
        form = await request.form()
        slug = str(form.get("slug", "")).strip("/")
        if slug not in get_catalog().recipes:
            raise HTTPException(status_code=404)
        made_on = None
        raw_date = str(form.get("made_on", ""))
        if raw_date:
            try:
                made_on = dt.date.fromisoformat(raw_date)
            except ValueError:
                made_on = None
        cooklog.add(slug, str(form.get("note", "")), made_on)
        return RedirectResponse(f"/{slug}?logged=1", status_code=303)

    @app.get("/learn/bakers-percentages", response_class=HTMLResponse)
    def learn_bakers(request: Request) -> Response:
        return templates.TemplateResponse(request, "learn_bakers.html", {"guide": bakers.GUIDE})

    @app.get("/{slug:path}", response_class=HTMLResponse)
    def recipe_page(
        request: Request,
        slug: str,
        background: BackgroundTasks,
        scale: str | None = None,
        dough: str | None = None,
    ) -> Response:
        slug = slug.strip("/")
        if slug.endswith(".md"):
            slug = slug[:-3]
        cat = get_catalog()
        recipe = cat.recipes.get(slug)
        if recipe is None:
            raise HTTPException(status_code=404)
        factor = ing.parse_scale(scale)
        bread = bakers.breakdown(recipe)
        dough_factor = bakers.dough_scale(dough, bread.total) if bread else None
        if dough_factor is not None:
            factor = dough_factor
        ing_groups, step_groups = build_rows(recipe, factor)
        # After the response is sent, so a slow database never delays a page.
        background.add_task(counts.bump, slug, "view" if factor == 1 else "scale")
        base = recipe.base_dir
        return templates.TemplateResponse(
            request,
            "recipe.html",
            {
                "recipe": recipe,
                "scale": factor,
                "bread": bread,
                "dough_target": round(float(bread.total * factor)) if bread else None,
                "by_dough": dough_factor is not None,
                "ingredient_groups": ing_groups,
                "step_groups": step_groups,
                "yield_text": (
                    f"Serves {ing.scale_yield(recipe.serves, factor, servings=True)}"
                    if recipe.serves
                    else f"Makes {ing.scale_yield(recipe.makes, factor)}"
                    if recipe.makes
                    else None
                ),
                "intro_html": Markup(catalog.render_markdown(recipe.intro, base)),
                "sections": [
                    (s.heading, Markup(catalog.render_markdown(s.body, base)))
                    for s in recipe.sections
                    if s.body.strip()
                ],
                "body_html": Markup(catalog.render_markdown(recipe.body, base)),
            },
        )

    @app.exception_handler(404)
    async def not_found(request: Request, _exc: Exception) -> Response:
        return templates.TemplateResponse(request, "404.html", {}, status_code=404)

    @app.exception_handler(SQLAlchemyError)
    async def database_down(request: Request, exc: Exception) -> Response:
        # Only the cook log pages read the database; the recipes never do.
        logger.warning("db.unavailable", path=request.url.path, error=str(exc))
        if "text/html" in request.headers.get("accept", ""):
            return templates.TemplateResponse(request, "unavailable.html", {}, status_code=503)
        return JSONResponse({"detail": "the cook log is unavailable"}, status_code=503)

    app.add_middleware(CloudflareAccessMiddleware, settings=settings)
    return app


app = create_app()
