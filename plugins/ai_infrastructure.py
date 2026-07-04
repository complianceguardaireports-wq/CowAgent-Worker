"""
Autonomous AI Infrastructure Plugin for CowAgent
Unifies OmniRoute (Primary) + 9Router (Backup) for 24/7 LLM operations
No API keys required - all runs locally on PandaStack
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass

from plugins.omniroute_plugin.omniroute_client import OmniRouteClient, OmniRouteConfig
from plugins.ninerouter_plugin.ninerouter_client import NineRouterFailoverManager

@dataclass
class AIInfrastructureConfig:
    omniroute_url: str = "http://omniroute:3000"
    ninerouter_url: str = "http://9router:8080"
    api_key: str = "local-autonomous-key"
    primary_provider: str = "omniroute"
    enable_failover: bool = True
    health_check_interval: int = 30

class AutonomousAIInfrastructure:
    """
    Unified AI infrastructure for autonomous operation.
    Handles all LLM operations without external API keys.
    """
    
    def __init__(self, config: AIInfrastructureConfig = None):
        self.config = config or AIInfrastructureConfig()
        self.failover_manager: Optional[NineRouterFailoverManager] = None
        self.omniroute: Optional[OmniRouteClient] = None
        self._initialized = False
        self.stats = {
            "total_requests": 0,
            "omniroute_requests": 0,
            "ninerouter_requests": 0,
            "failovers": 0,
            "errors": 0
        }
    
    async def initialize(self):
        """Initialize all AI infrastructure components"""
        if self._initialized:
            return
        
        # Initialize OmniRoute client
        omniroute_config = OmniRouteConfig(
            base_url=self.config.omniroute_url,
            timeout=120
        )
        self.omniroute = OmniRouteClient(omniroute_config)
        
        # Initialize failover manager (manages both OmniRoute and 9Router)
        self.failover_manager = NineRouterFailoverManager(
            omniroute_url=self.config.omniroute_url,
            ninerouter_url=self.config.ninerouter_url,
            api_key=self.config.api_key
        )
        await self.failover_manager.__aenter__()
        
        self._initialized = True
        print("[AI Infrastructure] Initialized: OmniRoute + 9Router ready for 24/7 operation")
    
    async def chat_completion(
        self,
        messages: List[Dict],
        model: str = "auto",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        provider: str = "auto"
    ) -> Dict[str, Any]:
        """
        Unified chat completion with automatic failover.
        
        Args:
            messages: Chat messages
            model: Model name (auto, gpt-4o, claude-3.5-sonnet, etc.)
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            stream: Whether to stream response
            provider: "auto" (use failover), "omniroute", or "9router"
        """
        if not self._initialized:
            await self.initialize()
        
        self.stats["total_requests"] += 1
        
        if provider == "omniroute":
            self.stats["omniroute_requests"] += 1
            return await self.omniroute.chat_completion(
                messages, model, temperature, max_tokens, stream
            )
        elif provider == "9router":
            self.stats["ninerouter_requests"] += 1
            return await self.failover_manager.ninerouter.chat_completion(
                messages, model, temperature, max_tokens, stream
            )
        else:
            # Auto mode - use failover manager
            try:
                result = await self.failover_manager.chat_completion(
                    messages, model, temperature, max_tokens, stream
                )
                
                # Track which provider was used
                if self.failover_manager.primary == "omniroute":
                    self.stats["omniroute_requests"] += 1
                else:
                    self.stats["ninerouter_requests"] += 1
                
                return result
            except Exception as e:
                self.stats["errors"] += 1
                self.stats["failovers"] += 1
                raise
    
    async def stream_chat_completion(
        self,
        messages: List[Dict],
        model: str = "auto",
        **kwargs
    ) -> AsyncGenerator[Dict, None]:
        """Stream chat completion responses"""
        if not self._initialized:
            await self.initialize()
        
        # For streaming, use OmniRoute directly
        self.stats["total_requests"] += 1
        self.stats["omniroute_requests"] += 1
        
        async for chunk in self.omniroute.stream_chat_completion(messages, model, **kwargs):
            yield chunk
    
    async def embeddings(self, texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
        """Get embeddings from OmniRoute"""
        if not self._initialized:
            await self.initialize()
        
        return await self.omniroute.embeddings(texts, model)
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of all AI infrastructure"""
        if not self._initialized:
            await self.initialize()
        
        omniroute_healthy = await self.omniroute.health_check()
        
        ninerouter_status = await self.failover_manager.get_status()
        
        return {
            "status": "healthy" if omniroute_healthy else "degraded",
            "omniroute": {
                "healthy": omniroute_healthy,
                "url": self.config.omniroute_url
            },
            "ninerouter": ninerouter_status,
            "stats": self.stats,
            "config": {
                "primary_provider": self.config.primary_provider,
                "failover_enabled": self.config.enable_failover
            }
        }
    
    async def get_available_models(self) -> List[Dict]:
        """Get all available models from both providers"""
        if not self._initialized:
            await self.initialize()
        
        omniroute_models = await self.omniroute.get_models()
        ninerouter_models = await self.failover_manager.ninerouter.list_models()
        
        # Combine and deduplicate
        all_models = {}
        for m in omniroute_models:
            all_models[m.get("id", "")] = {**m, "provider": "omniroute"}
        for m in ninerouter_models:
            mid = m.get("id", "")
            if mid in all_models:
                all_models[mid]["providers"] = ["omniroute", "9router"]
            else:
                all_models[mid] = {**m, "provider": "9router"}
        
        return list(all_models.values())
    
    async def close(self):
        """Clean shutdown"""
        if self.failover_manager:
            await self.failover_manager.__aexit__(None, None, None)
        if self.omniroute:
            await self.omniroute.close()
        self._initialized = False

# Global infrastructure instance
_ai_infrastructure: Optional[AutonomousAIInfrastructure] = None

async def get_ai_infrastructure() -> AutonomousAIInfrastructure:
    """Get or create the global AI infrastructure instance"""
    global _ai_infrastructure
    if _ai_infrastructure is None:
        _ai_infrastructure = AutonomousAIInfrastructure()
        await _ai_infrastructure.initialize()
    return _ai_infrastructure

async def close_ai_infrastructure():
    """Close the global AI infrastructure"""
    global _ai_infrastructure
    if _ai_infrastructure:
        await _ai_infrastructure.close()
        _ai_infrastructure = None

# Convenience functions for direct use
async def ai_chat(messages, model="auto", **kwargs):
    """Quick chat completion"""
    infra = await get_ai_infrastructure()
    return await infra.chat_completion(messages, model, **kwargs)

async def ai_health():
    """Quick health check"""
    infra = await get_ai_infrastructure()
    return await infra.health_check()

async def ai_models():
    """Get available models"""
    infra = await get_ai_infrastructure()
    return await infra.get_available_models()
