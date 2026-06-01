FROM python:3.12-slim

WORKDIR /app

# Copy only what the build needs first (better layer caching), then install the
# package plus API extras (fastapi + uvicorn).
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir ".[api]"

# 预置快照（可选）：snapshot/leads.json 存在时，API 直接返回它而不现抓 —— 云端冷容器秒出、稳定。
COPY snapshot ./snapshot
ENV LEADFINDER_SNAPSHOT=/app/snapshot/leads.json

# 微信云托管 / 任意容器：监听 $PORT（默认 8080），绑定 0.0.0.0。
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn leadfinder.api:app --host 0.0.0.0 --port ${PORT:-8080}"]
