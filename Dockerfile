# One Dockerfile, two images (plan.md §3.4, §11.2):
#   docker build .                         the local image (target `local`): docker-compose.yml runs it for the
#                                          backend and the worker, with the code bind-mounted over /app
#   docker build --target production \     the production image: Cloud Run's web service, worker and jobs, and the
#     --build-arg GIT_SHA=<commit> .       local rehearsal (docker-compose.prod.yml; deploy/README.md)
# The production image adds the SPA, built by Node 22 for /static/, and the collected static files that WhiteNoise
# serves. LibreOffice and poppler stay out of both: they live in the parity tools image (§3.1).

# ---- python: the runtime and the pinned libraries ------------------------------------------------------------------
FROM python:3.12-slim AS python

# No .pyc files (the code is bind-mounted from a synced folder locally) and unbuffered logs.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Non-root user, as in the earlier Vantage image.
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home appuser

# Uploaded and issued files live in a Docker volume mounted here (plan.md §3.4, §3.5); in the cloud, in the bucket.
# Created now and owned by appuser, so a new named volume inherits that owner.
RUN mkdir -p /data/media && chown appuser:appuser /data/media

WORKDIR /app

# psycopg2-binary ships wheels, so no compiler or Postgres client is needed.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- backend: the app's code (the local image) ----------------------------------------------------------------------
FROM python AS backend

# Project code, owned by appuser in a single layer.
COPY --chown=appuser:appuser . .
RUN chmod +x /app/start.sh

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/start.sh"]

# ---- spa: the SPA, built for /static/ (§11.2; slice 69) -----------------------------------------------------------
FROM node:22-alpine AS spa
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# The assets are served under /static/ by WhiteNoise; index.html is answered for every page path (backend/spa.py).
RUN npx vite build --base=/static/ --outDir /spa --emptyOutDir

# ---- code: the app without the SPA's sources ------------------------------------------------------------------------
FROM backend AS code
USER root
RUN rm -rf /app/frontend

# ---- production: Cloud Run's image ----------------------------------------------------------------------------------
FROM python AS production
ENV ENVIRONMENT=production
COPY --from=code --chown=appuser:appuser /app /app
COPY --from=spa --chown=appuser:appuser /spa /app/spa
# Static files are collected once, here: compressed, with Vite's hashed assets cached for good (settings.py).
RUN python manage.py collectstatic --noinput --verbosity 0
# The commit /api/health/ names (§3.5, §11.3). Last, so a new commit rebuilds nothing above.
ARG GIT_SHA=unknown
ENV GIT_SHA=${GIT_SHA}
USER appuser
EXPOSE 8000
# start.sh runs gunicorn (web, the default), `worker`, `migrate`, or any command it is given (deploy/README.md).
ENTRYPOINT ["/app/start.sh"]

# ---- local: the default target, the image docker-compose.yml builds -------------------------------------------------
FROM backend AS local
