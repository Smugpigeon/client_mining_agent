# 部署：微信云托管 + 小程序

后端是一个 FastAPI 服务（`leadfinder.api:app`）。小程序是薄前端，通过 HTTPS 调它。

## 本地调试
```
pip install -e ".[api]"
uvicorn leadfinder.api:app --port 8000
```
微信开发者工具 → 详情 → 本地设置 → 勾「不校验合法域名」。
`miniprogram/app.js` 保持默认 `apiMode: "request"`（直连 `http://127.0.0.1:8000`）。

## 微信云托管（生产）
1. 控制台新建服务，上传本仓库（含根目录 `Dockerfile`）；或 `docker build -t leadfinder .` 后推送到云托管镜像仓库。
2. 服务**监听端口设为 8080**（与 Dockerfile 一致）。
3. `miniprogram/app.js` 改 `apiMode: "callContainer"`，填 `cloudEnv`（环境 ID）和 `cloudService`（服务名）。前端用 `wx.cloud.callContainer` 调用——**免合法域名、免单独 ICP/SSL**。
4. 长任务已 job 化：`POST /jobs` 立即回 `job_id`，前端轮询 `GET /jobs/{id}`，完成后 `GET /jobs/{id}/export?fmt=xlsx|csv` 下载。

## 环境变量（可选）
- `PORT`：监听端口（默认 8080）。
- **对话找客户（`/chat`）**：`LLM_API_KEY`（必填，OpenRouter/DeepSeek 等的 key）、`LLM_BASE_URL`（默认 `https://openrouter.ai/api/v1`）、`LLM_MODEL`（如 `openai/gpt-5.5`、`deepseek-chat`）。不配则 `/chat` 返回 503。
  - ⚠️ 云托管容器在国内，调 `openrouter.ai` 可能超时；国内不稳就改用 `LLM_BASE_URL=https://api.deepseek.com` + `LLM_MODEL=deepseek-chat`，或走国内中转。
- **群发真实发信（`/campaign` dry_run=false）**：`SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` / `SMTP_FROM_NAME`。不配则仅 dry-run 预览。
- 微信登录（默认关闭）：配 `WX_APPID` / `WX_SECRET` / `WX_SESSION_SECRET` 后 `/auth/login` 才生效；设 `AUTH_REQUIRED=1` 可强制 `/jobs` 鉴权。不配则登录端点返回 503、不影响其余功能。
