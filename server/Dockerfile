FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY src/ ./src/
COPY scripts/ ./scripts/
EXPOSE 8080
CMD uv run uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8080}
