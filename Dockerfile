# =============================================================================
# CowAgent-Worker Dockerfile
# Targets: omniroute (port 3000), ninerouter (port 8081), cowagent (port 8080)
# =============================================================================

# =============================================================================
# Stage 1: Clone OmniRoute source from GitHub
# =============================================================================
FROM alpine:3.20 AS omniroute-src

RUN apk add --no-cache git
RUN git clone --depth 1 https://github.com/diegosouzapw/OmniRoute.git /omniroute

# =============================================================================
# Stage 2: Clone 9Router source from GitHub
# =============================================================================
FROM alpine:3.20 AS ninerouter-src

RUN apk add --no-cache git
RUN git clone --depth 1 https://github.com/decolua/9router.git /9router

# =============================================================================
# Stage 3: Build OmniRoute
# =============================================================================
FROM node:20-slim AS omniroute-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 make g++ git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=omniroute-src /omniroute ./

RUN npm install --legacy-peer-deps

ENV NODE_ENV=production
ENV PORT=3000
ENV NEXT_TELEMETRY_DISABLED=1
ARG OMNIROUTE_BUILD_MEMORY_MB=4096
ENV NODE_OPTIONS="--max-old-space-size=${OMNIROUTE_BUILD_MEMORY_MB}"

RUN npm run build

# =============================================================================
# Stage 4: Build 9Router
# =============================================================================
FROM node:20-slim AS ninerouter-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 make g++ git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=ninerouter-src /9router ./

RUN npm install

ENV NODE_ENV=production
ENV PORT=8081
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# =============================================================================
# Stage 5: OmniRoute Runner
# =============================================================================
FROM node:20-slim AS omniroute

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=omniroute-builder /app/.next/standalone ./
COPY --from=omniroute-builder /app/.next/static ./.next/static
COPY --from=omniroute-builder /app/public ./public
COPY --from=omniroute-builder /app/package.json ./

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
ENV NEXT_TELEMETRY_DISABLED=1

RUN mkdir -p /app/data

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:3000/health || curl -f http://localhost:3000/ || exit 1

CMD ["node", "server.js"]

# =============================================================================
# Stage 6: 9Router Runner
# =============================================================================
FROM node:20-slim AS ninerouter

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=ninerouter-builder /app/.next/standalone ./
COPY --from=ninerouter-builder /app/.next/static ./.next/static
COPY --from=ninerouter-builder /app/public ./public
COPY --from=ninerouter-builder /app/custom-server.js ./custom-server.js
COPY --from=ninerouter-builder /app/package.json ./

ENV NODE_ENV=production
ENV PORT=8081
ENV HOSTNAME=0.0.0.0
ENV NEXT_TELEMETRY_DISABLED=1

RUN mkdir -p /app/data

EXPOSE 8081

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8081/health || curl -f http://localhost:8081/ || exit 1

CMD ["node", "custom-server.js"]

# =============================================================================
# Stage 7: CowAgent (Python FastAPI runner)
# =============================================================================
FROM python:3.11-slim AS cowagent

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./

COPY config.json.template ./
COPY plugins/__init__.py ./plugins/__init__.py
COPY plugins/ai_infrastructure.py ./plugins/ai_infrastructure.py
COPY plugins/omniroute_plugin/ ./plugins/omniroute_plugin/
COPY plugins/ninerouter_plugin/ ./plugins/ninerouter_plugin/
COPY plugins/openhands_team/ ./plugins/openhands_team/

ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV HOSTNAME=0.0.0.0

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "app.py"]
