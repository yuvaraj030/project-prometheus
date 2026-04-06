"""
Gateway Server — FastAPI-based central control plane for the AI Agent.

Endpoints:
  POST /chat          — Send a message, get AI response
  GET  /status        — Agent health and stats
  GET  /skills        — List loaded skills
  POST /heartbeat/trigger — Manually trigger heartbeat check
  WS   /ws            — Real-time event stream

Authentication: X-API-Key header
"""

import os
import sys
import json
import time
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger("Gateway")
AGENT_ERROR = None # Store initialization error for diagnostics

# Try to import FastAPI — graceful fallback if not installed
try:
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Header, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.responses import StreamingResponse
    from starlette.middleware.base import BaseHTTPMiddleware
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logger.warning("FastAPI not installed. Run: pip install fastapi uvicorn")

from config import CONFIG

# Fix #21: JWT Auth
try:
    from jwt_auth import JWTAuth
except ImportError:
    JWTAuth = None

# Fix #20: Plugin hot-reload
try:
    from plugin_hot_reload import PluginHotReload
except ImportError:
    PluginHotReload = None

# Fix #19: MCP server
try:
    from mcp_server import AgentMCPServer
except ImportError:
    AgentMCPServer = None


if FASTAPI_AVAILABLE:
    class RateLimitMiddleware(BaseHTTPMiddleware):
        """Block IPs that exceed rate limits via SecurityEngine."""

        def __init__(self, app, security_engine=None):
            super().__init__(app)
            self.security = security_engine

        async def dispatch(self, request: Request, call_next):
            if self.security:
                client_ip = request.client.host if request.client else "unknown"
                allowed = await asyncio.to_thread(self.security.firewall_check, client_ip)
                if not allowed:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": f"Rate limit exceeded for {client_ip}. Try again later."},
                    )
            return await call_next(request)


# --- Request/Response Models ---

if FASTAPI_AVAILABLE:

    class ChatRequest(BaseModel):
        message: str
        tenant_id: int = 1
        use_react: bool = True  # Use ReAct tool-use loop

    class ChatResponse(BaseModel):
        response: str
        elapsed_ms: int
        tools_used: List[str] = []

    class PassiveLearnRequest(BaseModel):
        content: str
        source: str = "browser_extension"
        tenant_id: int = 1

    class StatusResponse(BaseModel):
        status: str
        uptime_seconds: float
        provider: str
        model: str
        skills_loaded: int
        tools_registered: int
        total_interactions: int
        memory_entries: int

    class HeartbeatResponse(BaseModel):
        status: str
        checks_performed: int
        alerts: List[str]


class GatewayServer:
    """
    Central Gateway server for the AI Agent.
    Hub-and-spoke architecture — all clients connect through here.
    """

    def __init__(self, agent=None):
        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI is required. Install with: pip install fastapi uvicorn")

        self.agent = agent
        self.app = FastAPI(
            title="Ultimate AI Agent — Gateway",
            description="Central control plane for the Sovereign AI Agent",
            version="2.0.0",
        )
        self.start_time = time.time()
        self.ws_clients: List[WebSocket] = []
        self._interaction_count = 0

        # Fix #21: JWT auth
        self._jwt_auth = JWTAuth() if JWTAuth else None
        if self._jwt_auth and hasattr(self._jwt_auth, 'router'):
            self.app.include_router(self._jwt_auth.router)
            logger.info("[Gateway] JWT auth router mounted at /auth")

        # Fix #19: MCP server manifest
        self._mcp = AgentMCPServer(
            tool_registry=getattr(agent, 'tool_registry', None),
            agent=agent,
        ) if AgentMCPServer and agent else None

        self._setup_middleware()
        self._setup_routes()

    def _get_api_key(self):
        """Get the configured API key."""
        return CONFIG.api_server.api_key

    def _setup_middleware(self):
        # Fix #9: Lock down CORS — only open to * in debug mode
        env_origins = os.getenv("CORS_ORIGINS", "").strip()
        if env_origins:
            cors_origins = [o.strip() for o in env_origins.split(",") if o.strip()]
        elif CONFIG.api_server.debug:
            cors_origins = ["*"]
        else:
            cors_origins = ["http://localhost:3000", "http://localhost:8000"]

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )

        # Fix #10: Wire SecurityEngine rate-limiting as middleware
        security = getattr(self.agent, 'security', None) if self.agent else None
        if security:
            self.app.add_middleware(RateLimitMiddleware, security_engine=security)
            logger.info("[Gateway] Rate-limit middleware active via SecurityEngine")

    def _setup_routes(self):
        app = self.app
        api_key = self._get_api_key()

        # --- Auth dependency ---
        async def verify_api_key(x_api_key: str = Header(default=None)):
            if api_key and api_key != "change-me-in-production":
                if x_api_key != api_key:
                    raise HTTPException(status_code=401, detail="Invalid API key")
            return x_api_key

        # --- Serve Chat UI at root ---
        static_dir = os.path.join(os.path.dirname(__file__), "static")

        @app.get("/")
        async def root():
            index_path = os.path.join(static_dir, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path, media_type="text/html")
            return {
                "name": "Ultimate AI Agent Gateway",
                "version": "2.0.0",
                "status": "running",
                "docs": "/docs",
            }

        # --- JSON Health check ---
        @app.get("/api")
        async def api_root():
            return {
                "name": "Ultimate AI Agent Gateway",
                "version": "2.0.0",
                "status": "running",
                "docs": "/docs",
                "agent_initialized": self.agent is not None,
                "provider": self.agent.llm.provider if self.agent else "None",
                "model": self.agent.llm.model if self.agent else "None",
                "error": AGENT_ERROR
            }

        # --- Neural Mind Palace (3D Memory) ---
        @app.get("/mind-palace")
        async def mind_palace_ui():
            mp_path = os.path.join(static_dir, "mind_palace.html")
            if os.path.exists(mp_path):
                return FileResponse(mp_path, media_type="text/html")
            raise HTTPException(status_code=404, detail="Mind Palace UI not found")

        @app.get("/api/mind_palace_data")
        async def mind_palace_data(tenant_id: int = 1, limit: int = 200, _key=Depends(verify_api_key)):
            if not self.agent or not hasattr(self.agent, 'vmem'):
                raise HTTPException(status_code=503, detail="Vector memory not initialized")
                
            try:
                from mind_palace_api import MindPalaceAPI
                palace = MindPalaceAPI(self.agent.vmem)
                
                # Run the heavy graph extraction off the main event loop thread
                graph_data = await asyncio.to_thread(palace.get_graph_data, tenant_id, limit)
                return graph_data
            except Exception as e:
                logger.error(f"Mind Palace error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # --- Chat ---
        @app.post("/chat", response_model=ChatResponse)
        async def chat(req: ChatRequest, _key=Depends(verify_api_key)):
            if not self.agent:
                raise HTTPException(
                    status_code=503, 
                    detail=f"Agent not initialized. Root cause: {AGENT_ERROR}" if AGENT_ERROR else "Agent not initialized"
                )

            start = time.time()
            try:
                # Smart ReAct routing: skip ReAct for simple queries on local models
                use_react = req.use_react
                if use_react and hasattr(self.agent, 'llm'):
                    is_local = self.agent.llm.provider == 'ollama'
                    tool_keywords = ['run', 'execute', 'search', 'file', 'shell',
                                     'read', 'write', 'list', 'delete', 'create',
                                     'send message', 'open']
                    needs_tools = any(kw in req.message.lower() for kw in tool_keywords)
                    is_simple = len(req.message.split()) < 20 and not needs_tools
                    if is_local and is_simple:
                        use_react = False

                if use_react and hasattr(self.agent, 'react_engine'):
                    response = self.agent.react_engine.run(
                        req.message, tenant_id=req.tenant_id
                    )
                    tools_used = [
                        step.get("tool_call", {}).get("name", "")
                        for step in self.agent.react_engine.get_trace()
                        if "tool_call" in step
                    ]
                else:
                    response = await self.agent.think(
                        user_input=req.message, tenant_id=req.tenant_id
                    )
                    tools_used = []

                elapsed = int((time.time() - start) * 1000)
                self._interaction_count += 1

                # Sanitize: Strip raw TOOL_CALL/JSON if LLM leaks it anywhere in the response
                import re
                hallucination_patterns = [
                    r'TOOL_CALL:?\s*\{[^}]*\}',
                    r'ACTION:\s*\S+:.*',
                    r'\{"name":\s*"[^"]*",\s*"params":\s*\{[^}]*\}\}',
                    r'FINAL_ANSWER:?\s*',
                ]
                
                clean_response = response
                for pattern in hallucination_patterns:
                    clean_response = re.sub(pattern, '', clean_response, flags=re.IGNORECASE | re.DOTALL)
                
                # Strip leftover reasoning prefixes (e.g. "This time, I will try to use...")
                reasoning_patterns = [
                    r'(?i)^.*I will (try to |)use the .* tool.*$',
                    r'(?i)^.*Let me (try|use|call).*tool.*$',
                ]
                for pattern in reasoning_patterns:
                    clean_response = re.sub(pattern, '', clean_response, flags=re.MULTILINE)
                
                response = clean_response.strip()
                
                # If response is empty after sanitization, provide a helpful fallback
                if not response or len(response) < 3:
                    if tools_used:
                        response = f"I've processed your request using {', '.join(tools_used)}. Is there anything else you'd like to know?"
                    else:
                        response = "I'm here to help! Could you tell me more about what you need?"

                # Broadcast to WebSocket clients
                await self._broadcast({
                    "type": "chat",
                    "message": req.message,
                    "response": response[:200],
                    "elapsed_ms": elapsed,
                })

                return ChatResponse(
                    response=response,
                    elapsed_ms=elapsed,
                    tools_used=[t for t in tools_used if t],
                )
            except Exception as e:
                logger.error(f"Chat error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # --- Status ---
        @app.get("/status", response_model=StatusResponse)
        async def status(_key=Depends(verify_api_key)):
            skills_count = 0
            tools_count = 0
            memory_count = 0

            if self.agent:
                if hasattr(self.agent, 'skill_loader'):
                    skills_count = self.agent.skill_loader.count
                if hasattr(self.agent, 'tool_registry'):
                    tools_count = self.agent.tool_registry.count
                if hasattr(self.agent, 'vmem'):
                    try:
                        memory_count = self.agent.vmem.count()
                    except Exception:
                        pass

            return StatusResponse(
                status="running",
                uptime_seconds=round(time.time() - self.start_time, 1),
                provider=CONFIG.api_provider,
                model=CONFIG.get_active_model(),
                skills_loaded=skills_count,
                tools_registered=tools_count,
                total_interactions=self._interaction_count,
                memory_entries=memory_count,
            )

        # --- Skills ---
        @app.get("/skills")
        async def list_skills(_key=Depends(verify_api_key)):
            if self.agent and hasattr(self.agent, 'skill_loader'):
                return {"skills": self.agent.skill_loader.list_skills()}
            return {"skills": []}

        # --- Tools ---
        @app.get("/tools")
        async def list_tools(_key=Depends(verify_api_key)):
            if self.agent and hasattr(self.agent, 'tool_registry'):
                return {"tools": self.agent.tool_registry.list_tools()}
            return {"tools": []}

        # --- Heartbeat ---
        @app.post("/heartbeat/trigger", response_model=HeartbeatResponse)
        async def trigger_heartbeat(_key=Depends(verify_api_key)):
            if self.agent and hasattr(self.agent, 'heartbeat'):
                result = self.agent.heartbeat.run_checks()
                await self._broadcast({"type": "heartbeat", "result": result})
                return HeartbeatResponse(
                    status=result.get("status", "unknown"),
                    checks_performed=result.get("checks_performed", 0),
                    alerts=result.get("alerts", []),
                )
            return HeartbeatResponse(status="no_scheduler", checks_performed=0, alerts=[])

        # --- Continuous Background Passive Learning ---
        @app.post("/api/passive_learn")
        async def passive_learn(req: PassiveLearnRequest, _key=Depends(verify_api_key)):
            if not self.agent or not hasattr(self.agent, 'learner'):
                raise HTTPException(status_code=503, detail="Learning engine not available")
            
            # Sub-agents or extensions send raw text/DOM here
            result = self.agent.learner.learn_text(
                tenant_id=req.tenant_id, 
                text=req.content, 
                topic="passive_monitoring", 
                source=req.source
            )
            
            # If hologram HUD is active, show the passive learning
            if hasattr(self.agent, 'log_ui'):
                self.agent.log_ui(f"[PASSIVE LEARN] Absorbed {len(req.content)} chars from {req.source}")
                
            return {"status": "success", "learned": result}

        # --- WebSocket ---
        @app.websocket("/ws")
        async def websocket_endpoint(ws: WebSocket):
            await ws.accept()
            self.ws_clients.append(ws)
            logger.info(f"WebSocket client connected ({len(self.ws_clients)} total)")
            try:
                while True:
                    data = await ws.receive_text()
                    await ws.send_json({"type": "ack", "data": data})
            except WebSocketDisconnect:
                self.ws_clients.remove(ws)
                logger.info(f"WebSocket client disconnected ({len(self.ws_clients)} total)")

        # --- Goal Dashboard UI ---
        @app.get("/goals-live")
        async def goals_live_ui():
            goals_path = os.path.join(static_dir, "goals_dashboard.html")
            if os.path.exists(goals_path):
                return FileResponse(goals_path, media_type="text/html")
            raise HTTPException(status_code=404, detail="Goals dashboard not found")

        # --- Goal Stats API ---
        @app.get("/api/goals")
        async def get_goals(_key=Depends(verify_api_key)):
            if not self.agent or not hasattr(self.agent, 'goal_engine'):
                return {"active_goals": [], "stats": {}, "error": "Goal engine not available"}
            stats = self.agent.goal_engine.get_stats()
            goals = self.agent.goal_engine.active_goals[:10]
            return {"stats": stats, "goals": goals}

        # --- Goal Dashboard WebSocket (streams live goal updates) ---
        @app.websocket("/ws/goals")
        async def goals_websocket(ws: WebSocket):
            await ws.accept()
            logger.info("Goals WebSocket client connected")
            try:
                while True:
                    payload = {"type": "goal_update", "timestamp": time.time()}
                    if self.agent and hasattr(self.agent, 'goal_engine'):
                        stats = self.agent.goal_engine.get_stats()
                        active = self.agent.goal_engine.active_goals[:10]
                        payload["stats"] = stats
                        payload["active_goals"] = active
                        # Include dream/sleep state if available
                        if hasattr(self.agent, 'dream'):
                            payload["sleep"] = self.agent.dream.get_sleep_status()
                    else:
                        payload["stats"] = {}
                        payload["active_goals"] = []
                    await ws.send_json(payload)
                    await asyncio.sleep(2)  # broadcast every 2 seconds
            except WebSocketDisconnect:
                logger.info("Goals WebSocket client disconnected")
            except Exception as e:
                logger.warning(f"Goals WebSocket error: {e}")

        # --- Help / API Directory ---
        @app.get("/help")
        async def help_page():
            return {
                "name": "Ultimate AI Agent Gateway",
                "endpoints": {
                    "GET  /":                    "Chat UI",
                    "GET  /help":                "This endpoint directory",
                    "GET  /docs":                "Interactive Swagger UI",
                    "POST /chat":                "Send a message, get AI response",
                    "POST /chat/stream":         "SSE streaming chat (token-by-token)",  # Fix #22
                    "GET  /status":              "Agent health and stats",
                    "GET  /skills":              "List loaded skills",
                    "GET  /tools":               "List registered tools",
                    "POST /heartbeat/trigger":   "Manually trigger heartbeat check",
                    "GET  /goals-live":          "Live goal dashboard UI",
                    "GET  /api/goals":           "Goal stats JSON API",
                    "WS   /ws":                  "Real-time WebSocket event stream",
                    "WS   /ws/goals":            "Live goal updates (2s interval)",
                    "GET  /mind-palace":         "3D memory visualization",
                    "GET  /mcp":                 "MCP tool manifest (Fix #19)",
                    "POST /auth/login":          "Get JWT token (Fix #21)",
                    "POST /auth/refresh":        "Refresh JWT token",
                    "GET  /auth/me":             "JWT token info",
                },
                "auth": "Pass X-API-Key header OR Bearer JWT from /auth/login",
            }

        # --- Fix #22: SSE Streaming Chat ---
        @app.post("/chat/stream")
        async def chat_stream(req: ChatRequest, _key=Depends(verify_api_key)):
            """Stream AI response token by token via Server-Sent Events."""
            if not self.agent:
                raise HTTPException(status_code=503, detail="Agent not initialized")

            async def event_generator():
                import re
                words = []
                try:
                    # Get full response then stream word-by-word
                    # (real token streaming requires httpx + async LLM - this is a
                    # word-level simulation compatible with sync LLMProvider)
                    response = await self.agent.think(
                        user_input=req.message, tenant_id=req.tenant_id
                    )
                    # SSE format: "data: <chunk>\n\n"
                    words = response.split()
                    for i, word in enumerate(words):
                        chunk = word + (" " if i < len(words) - 1 else "")
                        yield f"data: {json.dumps({'token': chunk})}\n\n"
                        await asyncio.sleep(0.03)  # ~33 tokens/sec
                    yield f"data: {json.dumps({'done': True, 'total_tokens': len(words)})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

            return StreamingResponse(event_generator(), media_type="text/event-stream",
                                     headers={"Cache-Control": "no-cache",
                                              "X-Accel-Buffering": "no"})

        # --- Fix #19: MCP tool manifest ---
        @app.get("/mcp")
        async def mcp_manifest():
            """Model Context Protocol tool discovery endpoint."""
            if self._mcp:
                return self._mcp.get_jsonrpc_manifest()
            return {"name": "ultimate-ai-agent", "tools": [], "error": "MCP not initialized"}

        # --- Keep-Alive (prevents Render free tier from sleeping) ---
        @app.on_event("startup")
        async def startup_keep_alive():
            asyncio.create_task(self._keep_alive_loop())

            # Fix #20: Start plugin hot-reload watcher
            if PluginHotReload and self.agent:
                hot_reload = PluginHotReload(self.agent)
                hot_reload.start()
                logger.info("[Gateway] Plugin hot-reload watcher started")

    async def _keep_alive_loop(self):
        """Self-ping every 14 minutes to prevent Render free-tier sleep."""
        import httpx
        port = CONFIG.api_server.port
        url = f"http://localhost:{port}/api"
        while True:
            await asyncio.sleep(14 * 60)  # 14 minutes
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, timeout=10)
                    logger.info(f"Keep-alive ping: {resp.status_code}")
            except Exception as e:
                logger.warning(f"Keep-alive ping failed: {e}")

    async def _broadcast(self, message: Dict):
        """Broadcast an event to all connected WebSocket clients."""
        dead = []
        for ws in self.ws_clients:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.ws_clients.remove(ws)

    def run(self, host: str = None, port: int = None):
        """Start the gateway server."""
        import uvicorn
        host = host or CONFIG.api_server.host
        port = port or CONFIG.api_server.port
        print(f"\n{'='*50}")
        print(f"  Ultimate AI Agent — Gateway Server")
        print(f"  http://{host}:{port}")
        print(f"  Docs: http://localhost:{port}/docs")
        print(f"  Help: http://localhost:{port}/help")
        print(f"{'='*50}\n")
        uvicorn.run(self.app, host=host, port=port)


# --- Standalone entry point ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if not FASTAPI_AVAILABLE:
        print("ERROR: FastAPI not installed. Run: pip install fastapi uvicorn")
        sys.exit(1)

    # Load agent in production
    agent = None
    try:
        print("[*] Loading UltimateAgent...")
        from ultimate_agent import UltimateAgent
        from config import CONFIG
        
        provider = CONFIG.api_provider
        api_key = CONFIG.get_active_api_key()
        model = CONFIG.get_active_model()
        
        print(f"[*] Initializing Agent with provider: {provider}, model: {model}")
        agent = UltimateAgent(
            provider=provider, 
            api_key=api_key,
            model=model,
            enable_self_mod=True,
            safety_mode=True
        )
        print("[*] Agent successfully initialized.")
    except Exception as e:
        import traceback
        AGENT_ERROR = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(f"[*] CRITICAL: Failed to load agent:\n{AGENT_ERROR}")
        
    gateway = GatewayServer(agent=agent)
    gateway.run()

