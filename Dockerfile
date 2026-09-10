FROM python:3.12-slim AS base

# System deps for PyMuPDF (needs libmupdf / libfreetype)
RUN apt-get update && apt-get install -y --no-install-recommends `
        libfreetype6 `
        libharfbuzz0b `
        libjpeg62-turbo `
        libopenjp2-7 `
        && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache friendly)
COPY pyproject.toml ./
COPY src/ ./src/

# Install the ohmni package + its dependencies
RUN pip install --no-cache-dir "pydantic>=2.9" "PyMuPDF>=1.24" `
    && pip install --no-cache-dir -e .

# Copy the rest of the application
COPY apps/ ./apps/
COPY scripts/ ./scripts/
COPY fixtures/ ./fixtures/

# Job output goes on a persistent volume at /data
# demo_server.py reads OHMNI_OUTPUT_DIR to find this path
ENV OHMNI_OUTPUT_DIR=/data/demo-jobs

# Expose the HTTP port
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 `
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["python", "scripts/demo_server.py", "--port", "8080", "--host", "0.0.0.0"]
