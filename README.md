# Autonomous AI Company - CowAgent + OmniRoute + 9Router + OpenHands

**Fully autonomous AI company running 24/7 on PandaStack - ZERO external API keys required**

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PANDASTACK CLOUD                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  CowAgent    │  │  OmniRoute   │  │  9Router     │              │
│  │  (CEO/      ) │◄─┤  (Primary   ) │  │  (Backup/   ) │              │
│  │  Orchestrator)  │  AI Gateway)   │  │  Network)    │              │
│  │  Port: 8080   │  │  Port: 3000  │  │  Port: 8081  │              │
│  └──────┬────────┘  └──────┬────────┘  └──────┬────────┘              │
│         │                  │                  │                       │
│         ▼                  ▼                  ▼                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    OpenHands (Coding Agent)                   │    │
│  │              Port: 3001  |  4 CPU  |  8GB RAM                 │    │
│  └──────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Features

| Feature | Implementation |
|---------|---------------|
| **Zero API Keys** | All LLM inference runs locally via OmniRoute/9Router |
| **24/7 Operation** | Supervisor-managed services with auto-restart |
| **Auto-Failover** | OmniRoute primary → 9Router backup (5s threshold) |
| **Self-Healing** | Health checks every 30s, auto-restart on failure |
| **Revenue Ready** | Autonomous task execution via `dev:` commands |
| **Scalable** | PandaStack microVMs for isolated workloads |

---

## Services

| Service | Port | Type | Description |
|---------|------|------|-------------|
| **CowAgent** | 8080 | Worker | CEO/Orchestrator - handles chat, delegates tasks |
| **OmniRoute** | 3000 | Worker | Primary AI Gateway - LLM routing, caching, providers |
| **9Router** | 8081 | Worker | Backup AI Gateway + Network Intelligence |
| **OpenHands** | 3001 | Worker | Autonomous Coding Agent - executes `dev:` tasks |

---

## Deployment

### 1. Push to GitHub

```bash
git add .
git commit -m "Autonomous AI Company: OmniRoute + 9Router + OpenHands"
git push origin main
```

### 2. Deploy on PandaStack

1. Go to [PandaStack.ai](https://pandastack.ai)
2. Click **New Project** → Connect this repository
3. PandaStack reads `pandastack.toml` and provisions all 4 services
4. Set environment variables in dashboard:
   - `OPENHANDS_API_KEY` = `your-secure-random-string`
   - `LOCAL_AI_KEY` = `local-autonomous-key` (or any string)

### 3. Configure Channel (WeChat/Telegram/Slack)

Edit `config.json.template` or set via PandaStack env vars:

- `CHANNEL_TYPE` = `wx` / `telegram` / `slack`
- Other channel configs as needed

### 4. Go Live

Message your bot:

```
dev: Create a Python FastAPI app with user auth and PostgreSQL
```

CowAgent → OpenHands → Delivers working code

---

## Usage Commands

| Command | Action |
|---------|--------|
| `dev: <task>` | Delegate coding task to OpenHands |
| `openhands: <task>` | Same as dev: |
| `code: <task>` | Alias for dev: |
| `build: <task>` | Alias for dev: |
| `@ai <question>` | Direct chat with local AI (OmniRoute) |
| `/ai <question>` | Same as @ai |

---

## Project Structure

```
CowAgent-Worker/
├── Dockerfile                 # Multi-stage build (4 services in 1)
├── pandastack.toml            # PandaStack service definitions
├── config.json.template       # CowAgent config (no API keys!)
├── supervisor.sh              # 24/7 process supervisor
├── app.py                     # CowAgent FastAPI entry point
├── requirements.txt           # Python dependencies
├── plugins/
│   ├── openhands_team/        # OpenHands delegation plugin
│   │   └── openhands_team.py  # Uses local AI infra
│   ├── omniroute_plugin/      # OmniRoute client
│   │   └── omniroute_client.py
│   ├── ninerouter_plugin/     # 9Router client + failover
│   │   └── ninerouter_client.py
│   └── ai_infrastructure.py   # Unified AI infrastructure
├── plugins/omniroute/         # OmniRoute source (submodule)
└── plugins/9router/           # 9Router source (submodule)
```

---

## Local Development

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Node.js 22+

### Run Locally

```bash
# Build all services
docker-compose -f docker-compose.local.yml up -d

# Check health
curl http://localhost:8080/health  # CowAgent
curl http://localhost:3000/health  # OmniRoute
curl http://localhost:8081/health  # 9Router

# Test AI chat
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

---

## Monitoring & Health

All services expose `/health` endpoints:

```bash
# CowAgent
curl http://localhost:8080/health

# OmniRoute  
curl http://localhost:3000/health

# 9Router
curl http://localhost:8081/health

# OpenHands
curl http://localhost:3001/health
```

### Key Metrics

- **Uptime**: 99.99% target (supervisor auto-restart)
- **Failover Time**: < 5 seconds (OmniRoute → 9Router)
- **Latency**: < 200ms local inference
- **Throughput**: 1000+ req/min per service

---

## Security

- **No External API Keys**: All inference local
- **Network Isolation**: Services communicate via internal Docker network
- **Secrets Management**: PandaStack environment variables only
- **Non-Root Containers**: All services run as `appuser` (UID 1000)
- **Read-Only Filesystems**: Where possible

---

## Business Model Ready

This infrastructure supports:

- **SaaS**: Charge per `dev:` task execution
- **Enterprise**: Private deployments with SLA
- **Marketplace**: Sell specialized OpenHands skills
- **Consulting**: "AI Development Team as a Service"

---

## Contributing

1. Fork repository
2. Create feature branch
3. Test locally with `docker-compose`
4. Submit PR

---

## License

MIT - Build your own autonomous AI company!

---

## Credits

- **CowAgent** - [zhayujie/cowagent](https://github.com/zhayujie/cowagent)
- **OmniRoute** - [diegosouzapw/OmniRoute](https://github.com/diegosouzapw/OmniRoute)
- **9Router** - [decolua/9router](https://github.com/decolua/9router)
- **OpenHands** - [All-Hands-AI/OpenHands](https://github.com/All-Hands-AI/OpenHands)
- **PandaStack** - [pandastack.ai](https://pandastack.ai)

---

**Built for autonomous operation. No humans required after deploy.**
