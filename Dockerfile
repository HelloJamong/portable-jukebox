FROM python:3.12-slim AS builder
WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml .
COPY src ./src
RUN pip install --no-cache-dir .

FROM python:3.12-slim AS runner
ARG VERSION=latest
LABEL org.opencontainers.image.version="${VERSION}"
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY src ./src
COPY static ./static

RUN mkdir -p /downloads /app/data

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:////app/data/jukebox.db
ENV DOWNLOAD_DIR=/downloads

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
