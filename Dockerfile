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
    && mkdir -p static \
    && tailwindcss -i tailwind.input.css -o static/main.css --content "./src/templates/**/*.html" --minify

FROM python:3.12-slim AS runner
ARG VERSION=latest
LABEL org.opencontainers.image.version="${VERSION}"
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
