FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libffi8 \
        shared-mime-info \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY .python-version pyproject.toml uv.lock ./
COPY src ./src
COPY templates ./templates

RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uv", "run", "fastapi", "run", "--app", "postnatal_pulse.main:app", "--host", "0.0.0.0", "--port", "8000"]
