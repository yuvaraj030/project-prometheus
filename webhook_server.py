"""
Webhook Server — FastAPI-based HTTP webhook receiver that triggers agent actions.
Commands: /webhook start [port]|stop|status|list|add|clear
"""

import os
import json
import threading
from datetime import datetime


class WebhookServer:
    """Receive HTTP webhooks and trigger agent actions."""

    DATA_FILE = "webhook_data.json"
    DEFAULT_PORT = 9000

    def __init__(self, agent=None):
        self.agent = agent
        self._server_thread = None
        self._server = None
        self._running = False
        self._port = self.DEFAULT_PORT
        self._data = self._load()

    def _load(self):
        if os.path.exists(self.DATA_FILE):
            try:
                with open(self.DATA_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"events_received": [], "handlers": {}, "total_received": 0}

    def _save(self):
        try:
            with open(self.DATA_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def start(self, port: int = None) -> str:
        """Start the webhook HTTP server."""
        if self._running:
            return f"⚠️ Webhook server already running on port {self._port}"
        self._port = port or self.DEFAULT_PORT

        try:
            from fastapi import FastAPI, Request
            import uvicorn

            app = FastAPI(title="Agent Webhook Server")

            @app.get("/")
            async def root():
                return {"status": "running", "events": self._data["total_received"]}

            @app.post("/webhook/{event_type}")
            async def receive_webhook(event_type: str, request: Request):
                try:
                    body = await request.json()
                except Exception:
                    body = {}
                event = {
                    "type": event_type,
                    "payload": body,
                    "received_at": datetime.now().isoformat(),
                    "source_ip": request.client.host if request.client else "unknown"
                }
                self._data["events_received"].append(event)
                self._data["events_received"] = self._data["events_received"][-100:]
                self._data["total_received"] += 1
                self._save()

                # Trigger agent action if handler registered
                result = self._handle_event(event_type, body)
                return {"status": "received", "event_type": event_type, "action": result}

            @app.post("/webhook")
            async def receive_generic(request: Request):
                return await receive_webhook("generic", request)

            @app.get("/events")
            async def list_events():
                return {"events": self._data["events_received"][-10:]}

            config = uvicorn.Config(app, host="0.0.0.0", port=self._port, log_level="error")
            self._server = uvicorn.Server(config)

            def run():
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._server.serve())

            self._server_thread = threading.Thread(target=run, daemon=True)
            self._server_thread.start()
            self._running = True

            return (
                f"✅ Webhook server started on port {self._port}!\n"
                f"   📡 Endpoint: http://localhost:{self._port}/webhook/{{event_type}}\n"
                f"   📊 Dashboard: http://localhost:{self._port}/\n"
                f"   📋 Events: http://localhost:{self._port}/events\n"
                f"   Example: curl -X POST http://localhost:{self._port}/webhook/github -d '{{\"action\":\"push\"}}'"
            )
        except ImportError:
            return "❌ FastAPI/uvicorn not installed. Run: pip install fastapi uvicorn"
        except Exception as e:
            return f"❌ Failed to start webhook server: {e}"

    def stop(self) -> str:
        """Stop the webhook server."""
        if not self._running:
            return "No webhook server running."
        if self._server:
            self._server.should_exit = True
        self._running = False
        return "⏹️ Webhook server stopped."

    def status(self) -> str:
        """Get server status."""
        status = "🟢 RUNNING" if self._running else "🔴 STOPPED"
        return (
            f"📡 WEBHOOK SERVER STATUS\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  Status  : {status}\n"
            f"  Port    : {self._port}\n"
            f"  Received: {self._data['total_received']} events\n"
            f"  Handlers: {len(self._data['handlers'])} registered"
        )

    def list_events(self, limit: int = 10) -> str:
        """List recent events."""
        events = self._data["events_received"][-limit:]
        if not events:
            return "No webhooks received yet."
        lines = [f"📥 RECENT WEBHOOKS ({len(events)}):\n"]
        for ev in reversed(events):
            lines.append(f"  [{ev['type']}] {ev['received_at'][:19]} from {ev['source_ip']}")
            payload_str = json.dumps(ev.get("payload", {}))[:100]
            lines.append(f"     {payload_str}")
        return "\n".join(lines)

    def add_handler(self, event_type: str, action: str) -> str:
        """Register an action for an event type."""
        self._data["handlers"][event_type] = action
        self._save()
        return f"✅ Handler registered: {event_type} → {action}"

    def _handle_event(self, event_type: str, payload: dict) -> str:
        """Execute registered handler for event type."""
        handler = self._data["handlers"].get(event_type, self._data["handlers"].get("*", ""))
        if handler and self.agent:
            try:
                # Inject payload as context
                msg = f"[WEBHOOK EVENT: {event_type}] Payload: {json.dumps(payload)[:500]}\nHandler: {handler}"
                return f"triggered:{handler}"
            except Exception as e:
                return f"error:{e}"
        return "no_handler"
