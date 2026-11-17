FROM python:3.12-slim AS builder
WORKDIR /app

ARG TAILWIND_VERSION=v3.4.17
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/download/${TAILWIND_VERSION}/tailwindcss-linux-x64 \
    && chmod +x tailwindcss-linux-x64 \
    && mv tailwindcss-linux-x64 /usr/local/bin/tailwindcss \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml .
COPY src ./src
COPY static ./static
COPY tailwind.input.css .
RUN pip install --no-cache-dir . \
    && tailwindcss -i tailwind.input.css -o static/main.css --content "./src/templates/**/*.html" --minify \
    && curl -sL https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js -o static/htmx.min.js \
    && curl -sL https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js -o static/alpine.min.js \
    && mkdir -p static/css static/webfonts \
    && curl -sL "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css" -o static/css/font-awesome.min.css \
    && curl -sL "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/webfonts/fa-solid-900.woff2" -o static/webfonts/fa-solid-900.woff2 \
    && curl -sL "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/webfonts/fa-regular-400.woff2" -o static/webfonts/fa-regular-400.woff2 \
    && curl -sL "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/webfonts/fa-brands-400.woff2" -o static/webfonts/fa-brands-400.woff2 \
    && curl -sL "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/PretendardVariable.woff2" -o static/PretendardVariable.woff2

FROM python:3.12-slim AS runner
ARG VERSION=latest
LABEL org.opencontainers.image.version="${VERSION}"
ENV APP_VERSION=${VERSION}
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
# yt-dlp needs a JS runtime (deno) to solve YouTube challenges; without it downloads hit 403
COPY --from=denoland/deno:bin-2.9.8 /deno /usr/local/bin/deno

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/static ./static
COPY src ./src

RUN mkdir -p /downloads /app/data

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:////app/data/jukebox.db
ENV DOWNLOAD_DIR=/downloads
# Trust X-Forwarded-For from a reverse proxy connecting via the published host
# port (peer IP is the Docker bridge gateway, not 127.0.0.1), plus Cloudflare's
# edge IPs (https://www.cloudflare.com/ips/) for setups proxied through it —
# without this, the chain stops at Cloudflare's hop and logs its edge IP
# instead of the real visitor IP. Override via FORWARDED_ALLOW_IPS in .env if
# the proxy chain differs.
ENV FORWARDED_ALLOW_IPS=172.16.0.0/12,173.245.48.0/20,103.21.244.0/22,103.22.200.0/22,103.31.4.0/22,141.101.64.0/18,108.162.192.0/18,190.93.240.0/20,188.114.96.0/20,197.234.240.0/22,198.41.128.0/17,162.158.0.0/15,104.16.0.0/13,104.24.0.0/14,172.64.0.0/13,131.0.72.0/22,2400:cb00::/32,2606:4700::/32,2803:f800::/32,2405:b500::/32,2405:8100::/32,2a06:98c0::/29,2c0f:f248::/32

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
