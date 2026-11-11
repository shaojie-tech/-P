# ---- 前端构建（Vue3 + Vite）----
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci --silent || npm install --silent
COPY frontend/ ./
RUN npm run build

# ---- 后端运行时（统一 FastAPI 服务：Vue3 前端 + REST + 语音）----
FROM python:3.11-slim

WORKDIR /app

# 先复制依赖声明与源码，安装后再拷入其余文件（利用 Docker 层缓存）
COPY pyproject.toml README.md ./
COPY app ./app
# 可通过 --build-arg PIP_INDEX_URL 覆盖；默认阿里云公网 PyPI 镜像，国内构建更快
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
RUN pip install --no-cache-dir -i ${PIP_INDEX_URL} .

COPY . .

# 前端构建产物（已含静态资源）
COPY --from=frontend /frontend/dist ./frontend/dist

EXPOSE 8765

# 运行时通过环境变量注入 DEEPSEEK_API_KEY（参考 .env.example）
ENV DISABLE_SCHEDULER=0

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=4)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8765"]
