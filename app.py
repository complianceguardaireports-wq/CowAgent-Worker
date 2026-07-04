"""
CowAgent Worker - Main Entry Point
CEO/Orchestrator for Autonomous AI Company
Runs on port 8080, supervisor.sh manages this process
"""

import os
import sys
import json
import signal
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
PLUGIN_DIR = BASE_DIR / "plugins"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("cowagent")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config() -> dict:
    for name in ("config.json", "config.json.template"):
        path = BASE_DIR / name
        if path.exists():
            logger.info("Loading config from %s", path)
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    logger.warning("No config file found, using defaults")
    return {}


CONFIG = load_config()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


# ---------------------------------------------------------------------------
# Plugin loader (lightweight - imports plugin modules without CowAgent bridge)
# ---------------------------------------------------------------------------

_plugins: dict = {}


def _load_plugins():
    """Discover and import plugin packages from the plugins/ directory."""
    if not PLUGIN_DIR.is_dir():
        logger.warning("Plugin directory %s not found", PLUGIN_DIR)
        return

    for entry in PLUGIN_DIR.iterdir():
        if entry.is_dir() and (entry / "__init__.py").exists():
            pkg_name = entry.name
            try:
                mod = __import__(f"plugins.{pkg_name}", fromlist=[pkg_name])
                _plugins[pkg_name] = mod
                logger.info("Loaded plugin: %s", pkg_name)
            except Exception as exc:
                logger.warning("Failed to load plugin %s: %s", pkg_name, exc)

    # Top-level plugin modules (e.g. ai_infrastructure.py)
    for py_file in PLUGIN_DIR.glob("*.py"):
        if py_file.stem == "__init__":
            continue
        try:
            mod = __import__(f"plugins.{py_file.stem}", fromlist=[py_file.stem])
            _plugins[py_file.stem] = mod
            logger.info("Loaded plugin module: %s", py_file.stem)
        except Exception as exc:
            logger.warning("Failed to load plugin module %s: %s", py_file.stem, exc)


# ---------------------------------------------------------------------------
# AI infrastructure singleton
# ---------------------------------------------------------------------------

_ai_infra = None


async def _get_ai_infra():
    global _ai_infra
    if _ai_infra is not None:
        return _ai_infra

    try:
        from plugins.ai_infrastructure import (
            AutonomousAIInfrastructure,
            AIInfrastructureConfig,
        )

        plugin_cfg = CONFIG.get("plugin_config", {})
        omniroute_cfg = plugin_cfg.get("omniroute", {})
        ninerouter_cfg = plugin_cfg.get("ninerouter", {})

        cfg = AIInfrastructureConfig(
            omniroute_url=os.getenv(
                "OMNIROUTE_URL",
                omniroute_cfg.get("base_url", "http://omniroute:3000"),
            ),
            ninerouter_url=os.getenv(
                "NINEROUTER_URL",
                ninerouter_cfg.get("base_url", "http://9router:8080"),
            ),
            api_key=os.getenv("LOCAL_AI_KEY", "local-autonomous-key"),
            primary_provider="omniroute",
            enable_failover=ninerouter_cfg.get("fallback_enabled", True),
        )

        _ai_infra = AutonomousAIInfrastructure(cfg)
        await _ai_infra.initialize()
        logger.info("AI infrastructure initialised (OmniRoute + 9Router)")
    except Exception as exc:
        logger.error("AI infrastructure init failed: %s", exc)
        _ai_infra = None

    return _ai_infra


async def _close_ai_infra():
    global _ai_infra
    if _ai_infra is not None:
        try:
            await _ai_infra.close()
        except Exception:
            pass
        _ai_infra = None


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_plugins()
    logger.info("CowAgent starting on port %s", os.getenv("PORT", "8080"))
    logger.info("Plugins loaded: %s", list(_plugins.keys()))

    # Warm up AI infrastructure in the background (non-blocking)
    try:
        await _get_ai_infra()
    except Exception:
        logger.warning("AI infra not ready yet (will retry on first request)")

    yield

    await _close_ai_infra()
    logger.info("CowAgent shut down")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CowAgent",
    description="CEO/Orchestrator for the Autonomous AI Company",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    infra_status = "not_ready"
    infra_detail = {}

    if _ai_infra is not None:
        try:
            detail = await _ai_infra.health_check()
            infra_status = detail.get("status", "unknown")
            infra_detail = detail
        except Exception as exc:
            infra_status = "error"
            infra_detail = {"error": str(exc)}

    return {
        "status": "healthy",
        "service": "cowagent",
        "version": "1.0.0",
        "plugins": list(_plugins.keys()),
        "ai_infrastructure": infra_status,
        "infra_detail": infra_detail,
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    for msg in request.messages:
        if msg.role not in ("system", "user", "assistant"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role: {msg.role}. Must be system, user, or assistant",
            )

    infra = await _get_ai_infra()
    if infra is None:
        raise HTTPException(
            status_code=503,
            detail="AI infrastructure unavailable (OmniRoute / 9Router)",
        )

    messages = [m.model_dump() for m in request.messages]

    system_msg = CONFIG.get(
        "character_desc",
        "You are CowAgent, CEO of an autonomous AI Company.",
    )
    if not any(m["role"] == "system" for m in messages):
        messages.insert(0, {"role": "system", "content": system_msg})

    model = request.model or CONFIG.get("model", "auto")
    temperature = request.temperature or CONFIG.get("temperature", 0.7)
    max_tokens = request.max_tokens or CONFIG.get("conversation_max_tokens", 4096)

    try:
        result = await infra.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return result
    except Exception as exc:
        logger.error("Chat completion failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/")
async def root():
    return {
        "service": "cowagent",
        "version": "1.0.0",
        "description": "CEO/Orchestrator for the Autonomous AI Company",
        "endpoints": {
            "health": "/health",
            "chat": "/api/chat (POST)",
        },
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _handle_signal(sig, _frame):
    logger.info("Received signal %s, shutting down...", sig)
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOSTNAME", "0.0.0.0")

    logger.info("Starting CowAgent on %s:%s", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")
