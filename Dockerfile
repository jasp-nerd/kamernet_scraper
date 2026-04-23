FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install deps first so the layer caches between code changes
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY radar/ ./radar/
COPY profiles/ ./profiles/
COPY scripts/ ./scripts/
COPY schema.sql ./

# Run as a non-root user
RUN useradd --create-home --uid 1000 radar \
    && chown -R radar:radar /app
USER radar

# Healthcheck: import the package to confirm the interpreter is alive.
# The scraper itself is network-bound and has no HTTP endpoint to probe.
HEALTHCHECK --interval=5m --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import radar; print(radar.__version__)" || exit 1

ENTRYPOINT ["python", "-m", "radar"]
CMD ["run"]
