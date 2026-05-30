FROM python:3.12-slim

WORKDIR /app

# Copy only what the build needs first (better layer caching), then install the
# package plus API extras (fastapi + uvicorn).
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir ".[api]"

# 微信云托管 / 任意容器：监听 $PORT（默认 8080），绑定 0.0.0.0。
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn leadfinder.api:app --host 0.0.0.0 --port ${PORT:-8080}"]
