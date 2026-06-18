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

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/static ./static
COPY src ./src

RUN mkdir -p /downloads /app/data

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:////app/data/jukebox.db
ENV DOWNLOAD_DIR=/downloads

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
