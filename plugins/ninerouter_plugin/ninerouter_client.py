#!/usr/bin/env python3
"""
9Router Client Plugin for CowAgent
Provides backup AI gateway and network intelligence layer
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class RouterStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class NineRouterConfig:
    base_url: str = "http://localhost:8080"
    api_key: str = "local-autonomous-key"
    timeout: int = 30
    failover_threshold_ms: int = 5000
    health_check_interval: int = 30

class NineRouterClient:
    """Client for 9Router - backup AI gateway and network layer"""
    
    def __init__(self, config: NineRouterConfig = None):
        self.config = config or NineRouterConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self.status = RouterStatus.HEALTHY
        self.last_health_check = 0
        self.latency_ms = 0
        self.error_count = 0
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            headers={"Authorization": f"Bearer {self.config.api_key}"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make HTTP request with error handling"""
        if not self.session:
            await self.__aenter__()
        
        url = f"{self.config.base_url}{endpoint}"
        start = time.time()
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                self.latency_ms = int((time.time() - start) * 1000)
                
                if response.status == 200:
                    self.error_count = 0
                    return await response.json()
                else:
                    self.error_count += 1
                    text = await response.text()
                    raise Exception(f"9Router error {response.status}: {text}")
                    
        except asyncio.TimeoutError:
            self.error_count += 1
            raise Exception("9Router request timeout")
        except Exception as e:
            self.error_count += 1
            raise
    
    async def health_check(self) -> Dict:
        """Check 9Router health status"""
        try:
            result = await self._request("GET", "/health")
            self.status = RouterStatus.HEALTHY
            self.last_health_check = time.time()
            return result
        except Exception as e:
            self.status = RouterStatus.UNHEALTHY
            raise
    
    async def chat_completion(
        self,
        messages: List[Dict],
        model: str = "auto",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False
    ) -> Dict:
        """Chat completion via 9Router"""
        payload = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        return await self._request("POST", "/v1/chat/completions", json=payload)
    
    async def list_models(self) -> List[Dict]:
        """List available models"""
        result = await self._request("GET", "/v1/models")
        return result.get("data", [])
    
    async def get_status(self) -> Dict:
        """Get 9Router status and metrics"""
        return {
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "error_count": self.error_count,
            "last_health_check": self.last_health_check,
            "base_url": self.config.base_url
        }

class NineRouterFailoverManager:
    """Manages failover between OmniRoute (primary) and 9Router (backup)"""
    
    def __init__(
        self,
        omniroute_url: str = "http://localhost:3000",
        ninerouter_url: str = "http://localhost:8080",
        api_key: str = "local-autonomous-key"
    ):
        self.omniroute = NineRouterClient(NineRouterConfig(
            base_url=omniroute_url,
            api_key=api_key
        ))
        self.ninerouter = NineRouterClient(NineRouterConfig(
            base_url=ninerouter_url,
            api_key=api_key
        ))
        self.primary = "omniroute"
        self.failover_count = 0
        self.last_failover = 0
        
    async def __aenter__(self):
        await self.omniroute.__aenter__()
        await self.ninerouter.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.omniroute.__aexit__(exc_type, exc_val, exc_tb)
        await self.ninerouter.__aexit__(exc_type, exc_val, exc_tb)
    
    async def chat_completion(
        self,
        messages: List[Dict],
        model: str = "auto",
        **kwargs
    ) -> Dict:
        """Chat completion with automatic failover"""
        # Try primary first
        if self.primary == "omniroute":
            try:
                return await self.omniroute.chat_completion(messages, model, **kwargs)
            except Exception as e:
                return await self._failover_to_backup(messages, model, e, **kwargs)
        else:
            try:
                return await self.ninerouter.chat_completion(messages, model, **kwargs)
            except Exception as e:
                return await self._failover_to_backup(messages, model, e, **kwargs)
    
    async def _failover_to_backup(
        self,
        messages: List[Dict],
        model: str,
        error: Exception,
        **kwargs
    ) -> Dict:
        """Failover to backup router"""
        self.failover_count += 1
        self.last_failover = time.time()
        
        if self.primary == "omniroute":
            self.primary = "ninerouter"
            print(f"[9Router Failover] OmniRoute failed: {error}. Switching to 9Router...")
            return await self.ninerouter.chat_completion(messages, model, **kwargs)
        else:
            self.primary = "omniroute"
            print(f"[9Router Failover] 9Router failed: {error}. Switching to OmniRoute...")
            return await self.omniroute.chat_completion(messages, model, **kwargs)
    
    async def check_and_recover(self) -> bool:
        """Check if primary recovered and switch back"""
        if self.primary == "ninerouter":
            try:
                await self.omniroute.health_check()
                self.primary = "omniroute"
                print("[9Router Failover] OmniRoute recovered. Switching back to primary.")
                return True
            except:
                pass
        elif self.primary == "omniroute":
            try:
                await self.ninerouter.health_check()
            except:
                pass
        return False
    
    def get_status(self) -> Dict:
        return {
            "primary": self.primary,
            "failover_count": self.failover_count,
            "last_failover": self.last_failover,
            "omniroute": self.omniroute.get_status() if hasattr(self.omniroute, 'get_status') else {},
            "ninerouter": self.ninerouter.get_status() if hasattr(self.ninerouter, 'get_status') else {}
        }

# Singleton instance for global access
_failover_manager: Optional[NineRouterFailoverManager] = None

async def get_failover_manager() -> NineRouterFailoverManager:
    global _failover_manager
    if _failover_manager is None:
        _failover_manager = NineRouterFailoverManager()
        await _failover_manager.__aenter__()
    return _failover_manager

async def close_failover_manager():
    global _failover_manager
    if _failover_manager:
        await _failover_manager.__aexit__(None, None, None)
        _failover_manager = None
