# Build context is the REPO ROOT (the site reads the recipes), so every COPY path
# below is relative to it. See .dockerignore at the root.

# --- Stage 1: compile Tailwind CSS, and pick up htmx ---------------------------
FROM node:26-alpine AS css
WORKDIR /build
COPY site/package.json site/package-lock.json ./
RUN npm ci
COPY site/src/ ./src/
RUN npx --no-install tailwindcss \
    -i src/recipes_site/static/input.css \
    -o /tmp/output.css \
    --minify
# htmx is self-hosted from npm, so Renovate tracks it through package.json.
RUN cp node_modules/htmx.org/dist/htmx.min.js /tmp/htmx.min.js

# --- Stage 2: Python app -----------------------------------------------------
FROM python:3.15-slim

RUN pip install --no-cache-dir uv
WORKDIR /app

# Pinned deps from uv.lock first, so a code or recipe change reuses this layer.
COPY site/pyproject.toml site/uv.lock site/README.md ./
RUN uv export --frozen --no-emit-project --no-hashes -o /tmp/requirements.txt \
    && uv pip install --system -r /tmp/requirements.txt

COPY site/src/ src/
COPY site/migrations/ migrations/
COPY site/alembic.ini ./
RUN uv pip install --system --no-deps -e .
COPY --from=css /tmp/output.css /app/src/recipes_site/static/output.css
COPY --from=css /tmp/htmx.min.js /app/src/recipes_site/static/htmx.min.js

ARG APP_VERSION=0.0.0+dev
RUN printf '__version__ = "%s"\n' "${APP_VERSION}" > /app/src/recipes_site/_version.py

# The recipes themselves change most often, so they go last. .dockerignore keeps
# the app, .git and tooling out; site/ is removed so only recipes remain.
COPY . /app/content/
RUN rm -rf /app/content/site
ENV RECIPES_CONTENT_DIR=/app/content

# Per-commit, below every cacheable step.
ARG ASSET_VERSION=dev
ENV RECIPES_ASSET_VERSION=${ASSET_VERSION}

EXPOSE 8000
CMD ["uvicorn", "recipes_site.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
