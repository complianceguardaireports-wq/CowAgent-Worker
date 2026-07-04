"""
OpenHands Sub-Agent Plugin for CowAgent
Uses local AI Infrastructure (OmniRoute + 9Router) - No API keys required
"""

import os
import json
import asyncio
from typing import Dict, Any

# Import our autonomous AI infrastructure
from plugins.ai_infrastructure import (
    get_ai_infrastructure, 
    AutonomousAIInfrastructure,
    AIInfrastructureConfig
)

class OpenHandsSubAgent:
    """Delegates autonomous coding tasks to OpenHands using local AI infrastructure"""
    
    def __init__(self):
        # Local AI infrastructure config - NO EXTERNAL API KEYS NEEDED
        self.ai_config = AIInfrastructureConfig(
            omniroute_url=os.getenv("OMNIROUTE_URL", "http://localhost:3000"),
            ninerouter_url=os.getenv("NINEROUTER_URL", "http://localhost:8080"),
            api_key=os.getenv("LOCAL_AI_KEY", "local-autonomous-key"),
            primary_provider="omniroute",
            enable_failover=True
        )
        
        # OpenHands runs on PandaStack
        self.openhands_url = os.getenv("OPENHANDS_API_URL", "http://openhands:3000")
        
        # Initialize AI infrastructure
        self.ai_infra: AutonomousAIInfrastructure = None
        
        print("[OpenHandsSubAgent] Initialized with LOCAL AI infrastructure (OmniRoute + 9Router)")
        print("[OpenHandsSubAgent] No external API keys required - fully autonomous")
    
    async def initialize(self):
        """Initialize AI infrastructure asynchronously"""
        self.ai_infra = AutonomousAIInfrastructure(self.ai_config)
        await self.ai_infra.initialize()
    
    def on_handle_context(self, content: str) -> str:
        """Handle messages starting with dev: or openhands: or code:"""
        
        # Intercept messages starting with "dev:" or "openhands:" or "code:"
        triggers = ["dev:", "openhands:", "code:", "build:", "create:"]
        triggered = False
        task = ""
        
        for trigger in triggers:
            if content.lower().startswith(trigger):
                task = content.split(":", 1)[1].strip()
                triggered = True
                break
        
        if not triggered:
            return None
        
        # Send immediate feedback
        feedback = (
            f"[Autonomous Team Mode] Delegating to OpenHands sub-agent...\n\n"
            f"Task: {task}\n"
            f"AI Infrastructure: OmniRoute (primary) + 9Router (failover)\n"
            f"Execution: PandaStack microVM\n\n"
            f"Provisioning isolated workspace..."
        )
        
        # Execute task asynchronously
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(self._execute_task(task))
        
        return result
    
    async def _execute_task(self, task: str) -> str:
        """Execute coding task using OpenHands with local AI infrastructure"""
        
        # First, use AI infrastructure to plan the task
        planning_messages = [
            {
                "role": "system",
                "content": """You are the AI Infrastructure planner for an autonomous coding agent.
                Break down the task into clear steps that OpenHands can execute.
                Return a JSON object with: steps (array), files_to_create (array), 
                estimated_iterations (int), and model_preference (string)."""
            },
            {
                "role": "user", 
                "content": f"Plan this coding task for OpenHands: {task}"
            }
        ]
        
        try:
            # Use our local AI to plan
            plan_result = await self.ai_infra.chat_completion(
                planning_messages,
                model="gpt-4o",
                temperature=0.3,
                max_tokens=2048
            )
            
            plan = json.loads(plan_result.get("choices", [{}])[0].get("message", {}).get("content", "{}"))
            
        except Exception as e:
            print(f"[OpenHandsSubAgent] Planning failed, using default: {e}")
            plan = {
                "steps": ["Analyze requirements", "Implement solution", "Test and verify"],
                "files_to_create": [],
                "estimated_iterations": 10,
                "model_preference": "auto"
            }
        
        # Trigger OpenHands with the task and AI infrastructure
        try:
            import aiohttp
            
            payload = {
                "task": task,
                "max_iterations": plan.get("estimated_iterations", 15),
                "ai_config": {
                    "provider": "local",
                    "api_base": self.ai_config.omniroute_url + "/v1",
                    "api_key": self.ai_config.api_key,
                    "model": plan.get("model_preference", "auto")
                }
            }
            
            # Call OpenHands API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.openhands_url}/api/tasks",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return self._format_result(result, task)
                    else:
                        text = await response.text()
                        return f"OpenHands API Error ({response.status}): {text}"
                        
        except Exception as e:
            print(f"[OpenHandsSubAgent] Execution error: {e}")
            return f"Failed to execute task: {str(e)}"
    
    def _format_result(self, result: Dict, task: str) -> str:
        """Format OpenHands result for user"""
        status = result.get("status", "unknown")
        message = result.get("message", "No message")
        files = result.get("files_created", [])
        logs = result.get("logs", [])
        
        output = f"[OpenHands] Task Completed: {status}\n\n"
        output += f"Original Task: {task}\n\n"
        output += f"Result: {message}\n\n"
        
        if files:
            output += "Files Created:\n"
            for f in files:
                output += f"  - {f}\n"
            output += "\n"
        
        if logs:
            output += "Execution Log (last 5):\n"
            for log in logs[-5:]:
                output += f"  {log}\n"
        
        output += f"\nPowered by: OmniRoute + 9Router (Local AI, No API Keys)"
        
        return output


# Also register a general AI chat handler for non-coding tasks
class LocalAIChat:
    """Direct chat with local AI infrastructure (OmniRoute + 9Router)"""
    
    def __init__(self):
        self.ai_infra = None
    
    async def initialize(self):
        self.ai_infra = await get_ai_infrastructure()
    
    def on_handle_context(self, content: str) -> str:
        """Handle direct AI queries with @ai or /ai prefix"""
        if content.startswith("@ai ") or content.startswith("/ai "):
            query = content.split(" ", 1)[1]
            
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            response = loop.run_until_complete(self._chat(query))
            return response
        
        return None
    
    async def _chat(self, query: str) -> str:
        """Chat with local AI infrastructure"""
        messages = [
            {"role": "system", "content": "You are an autonomous AI assistant running on local infrastructure (OmniRoute + 9Router). No external API calls."},
            {"role": "user", "content": query}
        ]
        
        try:
            result = await self.ai_infra.chat_completion(
                messages,
                model="auto",
                temperature=0.7,
                max_tokens=4096
            )
            
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Add infrastructure info
            provider = "OmniRoute" if self.ai_infra.failover_manager.primary == "omniroute" else "9Router"
            return f"{content}\n\n---\nProvider: {provider} | Local AI Infrastructure | No API Keys"
            
        except Exception as e:
            return f"Error: {str(e)}"
