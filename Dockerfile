# ==============================================================================
# Airi Sensei v3.0 Production Dockerfile
# Based on pinned OpenClaw Agent Runtime (Slim variant, no heavy Chromium)
# ==============================================================================
FROM ghcr.io/openclaw/openclaw:2026.10.10-beta.5-slim

USER root

# Install minimal Python runtime for migration utilities and curl for health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy OpenClaw configuration and Airi workspace assets
COPY openclaw.json ./openclaw.json
COPY workspace/ ./workspace/
COPY skills/ ./skills/
COPY scripts/ ./scripts/
COPY entrypoint.sh ./entrypoint.sh

RUN chmod +x ./entrypoint.sh ./scripts/*.py

# Runtime environment configuration
ENV OPENCLAW_HOME=/data/.openclaw \
    OPENCLAW_CONFIG_PATH=/data/.openclaw/openclaw.json \
    OPENCLAW_WORKSPACE=/data/workspace \
    PORT=8080 \
    HOST=0.0.0.0

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
