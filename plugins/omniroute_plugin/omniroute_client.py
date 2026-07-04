"""
OmniRoute Plugin for CowAgent
Provides direct access to OmniRoute AI gateway for all LLM operations
"""
import json
import time
import asyncio
import httpx
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class OmniRouteConfig:
    base_url: str = "http://omniroute:3000"
    timeout: int = 120
    retry_attempts: int = 3
    default_model: str = "auto"

class OmniRouteClient:
    """Client for communicating with OmniRoute AI gateway"""
    
    def __init__(self, config: OmniRouteConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=config.timeout)
        self.models_cache = {}
        self.last_health_check = 0
        self.healthy = True
    
    async def health_check(self) -> bool:
        """Check if OmniRoute is healthy"""
        now = time.time()
        if now - self.last_health_check < 30:
            return self.healthy
        
        try:
            response = await self.client.get(f"{self.config.base_url}/health")
            self.healthy = response.status_code == 200
        except Exception:
            self.healthy = False
        
        self.last_health_check = now
        return self.healthy
    
    async def get_models(self) -> List[Dict]:
        """Get available models from OmniRoute"""
        if self.models_cache:
            return self.models_cache
        
        try:
            response = await self.client.get(f"{self.config.base_url}/v1/models")
            if response.status_code == 200:
                data = response.json()
                self.models_cache = data.get("data", [])
                return self.models_cache
        except Exception:
            pass
        return []
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "auto",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Send chat completion request to OmniRoute"""
        
        if model == "auto":
            model = self.config.default_model
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        for attempt in range(self.config.retry_attempts):
            try:
                response = await self.client.post(
                    f"{self.config.base_url}/v1/chat/completions",
                    json=payload
                )
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
            except Exception as e:
                if attempt == self.config.retry_attempts - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        
        raise Exception("Max retries exceeded")
    
    async def embeddings(self, texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
        """Get embeddings from OmniRoute"""
        payload = {"model": model, "input": texts}
        response = await self.client.post(
            f"{self.config.base_url}/v1/embeddings",
            json=payload
        )
        if response.status_code == 200:
            data = response.json()
            return [item["embedding"] for item in data["data"]]
        raise Exception(f"Embeddings failed: {response.text}")
    
    async def close(self):
        await self.client.aclose()

# Global client instance
_omniroute_client: Optional[OmniRouteClient] = None

def get_omniroute_client() -> OmniRouteClient:
    global _omniroute_client
    if _omniroute_client is None:
        config = OmniRouteConfig()
        _omniroute_client = OmniRouteClient(config)
    return _omniroute_client

async def omniroute_chat(messages, model="auto", **kwargs):
    """Convenience function for chat completions"""
    client = get_omniroute_client()
    return await client.chat_completion(messages, model, **kwargs)

async def omniroute_health() -> bool:
    """Check OmniRoute health"""
    client = get_omniroute_client()
    return await client.health_check()
