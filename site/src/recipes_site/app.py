"""FastAPI app: the public recipe site."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from fractions import Fraction
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

import structlog
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from recipes_site import __version__, catalog, counts
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
    app.state.templates = templates
    app.state.settings = settings

    def get_catalog() -> catalog.Catalog:
        return catalog.cached(str(settings.content_dir))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__, "build": settings.asset_version}

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

    @app.get("/{slug:path}", response_class=HTMLResponse)
    def recipe_page(
        request: Request, slug: str, background: BackgroundTasks, scale: str | None = None
    ) -> Response:
        slug = slug.strip("/")
        if slug.endswith(".md"):
            slug = slug[:-3]
        cat = get_catalog()
        recipe = cat.recipes.get(slug)
        if recipe is None:
            raise HTTPException(status_code=404)
        factor = ing.parse_scale(scale)
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
                "ingredient_groups": ing_groups,
                "step_groups": step_groups,
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

    app.add_middleware(CloudflareAccessMiddleware, settings=settings)
    return app


app = create_app()
