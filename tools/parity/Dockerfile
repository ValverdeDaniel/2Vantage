# The parity tools image (plan.md §3.4, §12.7; Q.5): headless LibreOffice to recalculate workbooks, poppler to
# rasterize and read PDFs, and the Python readers. Recalc (slice 27) and Fidelity (slice 28) run in it; it never
# goes in the app's image. The old file writers are pinned at the old app's versions (V.4 #6).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libreoffice-calc libreoffice-writer libreoffice-impress \
        poppler-utils fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
        openpyxl==3.1.5 \
        pypdf==5.7.0 \
        python-pptx==1.0.2 \
        XlsxWriter==3.3.0 \
        reportlab==4.2.5

RUN groupadd --gid 1000 tools && useradd --uid 1000 --gid tools --create-home tools
USER tools
WORKDIR /work

CMD ["sh", "-c", "soffice --version && pdftoppm -v"]
