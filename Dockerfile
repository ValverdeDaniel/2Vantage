FROM python:3.12-slim

# No .pyc files (the code is bind-mounted from a synced folder locally) and unbuffered logs.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Non-root user, as in the earlier Vantage image.
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home appuser

# Uploaded and issued files live in a Docker volume mounted here (plan.md §3.4, §3.5).
# Created now and owned by appuser, so a new named volume inherits that owner.
RUN mkdir -p /data/media && chown appuser:appuser /data/media

WORKDIR /app

# psycopg2-binary ships wheels, so no compiler or Postgres client is needed.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Project code, owned by appuser in a single layer.
COPY --chown=appuser:appuser . .
RUN chmod +x /app/start.sh

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/start.sh"]
