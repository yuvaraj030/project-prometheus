"""
Tool Registry — Central registry of all callable tools for the ReAct engine.

Each tool has:
  - name: unique identifier
  - description: what it does (shown to LLM)
  - parameters: JSON-schema dict describing expected args
  - execute: callable(params) -> result dict
"""

import os
import json
import subprocess
import webbrowser
import logging
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field

logger = logging.getLogger("ToolRegistry")


@dataclass
class Tool:
    """A registered tool the agent can invoke."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema format
    execute: Callable[[Dict[str, Any]], Dict[str, Any]]
    category: str = "general"
    requires_confirmation: bool = False

    def to_schema(self) -> Dict[str, Any]:
        """Return tool definition suitable for LLM system prompt."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def to_prompt_str(self) -> str:
        """Human-readable tool description for LLM."""
        params = self.parameters.get("properties", {})
        required = self.parameters.get("required", [])
        param_lines = []
        for pname, pdef in params.items():
            req = " (required)" if pname in required else " (optional)"
            param_lines.append(f"    - {pname}{req}: {pdef.get('description', pdef.get('type', ''))}")
        params_str = "\n".join(param_lines) if param_lines else "    (no parameters)"
        return f"### {self.name}\n{self.description}\n{params_str}"


class ToolRegistry:
    """
    Central registry of all callable tools.

    Usage:
        registry = ToolRegistry()
        registry.register_builtins()
        result = registry.execute("read_file", {"path": "README.md"})
    """

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._execution_log: List[Dict] = []

    # --- Registration ---

    def register(self, tool: Tool):
        """Register a tool. Overwrites if name already exists."""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def register_function(self, name: str, description: str,
                          parameters: Dict, func: Callable,
                          category: str = "general",
                          requires_confirmation: bool = False):
        """Convenience: register a plain function as a tool."""
        self.register(Tool(
            name=name,
            description=description,
            parameters=parameters,
            execute=func,
            category=category,
            requires_confirmation=requires_confirmation,
        ))

    def unregister(self, name: str):
        """Remove a tool by name."""
        self.tools.pop(name, None)

    # --- Execution ---

    def execute(self, name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a tool by name with given parameters."""
        params = params or {}
        tool = self.tools.get(name)
        if not tool:
            return {"success": False, "error": f"Unknown tool: {name}"}

        start = time.time()
        try:
            result = tool.execute(params)
            elapsed = time.time() - start
            log_entry = {
                "tool": name, "params": params,
                "result": result, "elapsed_ms": int(elapsed * 1000),
                "timestamp": time.time(),
            }
            self._execution_log.append(log_entry)
            return result
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return {"success": False, "error": str(e)}

    # --- Query ---

    def get(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        return [{"name": t.name, "description": t.description, "category": t.category}
                for t in self.tools.values()]

    def get_tools_prompt(self) -> str:
        """Generate a formatted prompt section describing all available tools."""
        if not self.tools:
            return ""
        sections = []
        categories = {}
        for tool in self.tools.values():
            categories.setdefault(tool.category, []).append(tool)

        for cat, tools in sorted(categories.items()):
            sections.append(f"\n## {cat.title()} Tools\n")
            for tool in tools:
                sections.append(tool.to_prompt_str())

        return "\n".join(sections)

    def get_tools_schema(self) -> List[Dict]:
        """Return all tool schemas for structured LLM tool-calling."""
        return [t.to_schema() for t in self.tools.values()]

    @property
    def count(self) -> int:
        return len(self.tools)

    # --- Built-in Tools ---

    def register_builtins(self, agent=None):
        """Register all built-in tools. Pass agent to wire real implementations."""
        self._agent = agent  # Store for tools that need agent methods
        self._register_run_shell()
        self._register_read_file()
        self._register_write_file()
        self._register_list_files()
        self._register_web_search()
        self._register_send_message()
        self._register_get_time()
        self._register_open_app()
        self._register_run_code()
        logger.info(f"Registered {self.count} built-in tools")

    def _register_run_shell(self):
        def _exec(params):
            command = params.get("command", "")
            timeout = params.get("timeout", 30)
            if not command:
                return {"success": False, "error": "No command provided"}
            try:
                r = subprocess.run(
                    command, shell=True, capture_output=True,
                    text=True, timeout=timeout
                )
                return {
                    "success": r.returncode == 0,
                    "stdout": r.stdout[:2000],
                    "stderr": r.stderr[:500],
                    "return_code": r.returncode,
                }
            except subprocess.TimeoutExpired:
                return {"success": False, "error": f"Command timed out after {timeout}s"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        self.register_function(
            "run_shell",
            "Execute a shell command and return the output. Use for listing files, counting lines, or any OS operation.",
            {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)"},
                },
                "required": ["command"],
            },
            _exec,
            category="system",
            requires_confirmation=False,
        )

    def _register_read_file(self):
        def _exec(params):
            path = params.get("path", "")
            if not path:
                return {"success": False, "error": "No path provided"}
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(50000)  # Cap at 50KB
                return {"success": True, "content": content, "size": os.path.getsize(path)}
            except FileNotFoundError:
                return {"success": False, "error": f"File not found: {path}"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        self.register_function(
            "read_file",
            "Read the contents of a file.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read"},
                },
                "required": ["path"],
            },
            _exec,
            category="filesystem",
        )

    def _register_write_file(self):
        def _exec(params):
            path = params.get("path", "")
            content = params.get("content", "")
            if not path:
                return {"success": False, "error": "No path provided"}
            try:
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return {"success": True, "path": path, "bytes_written": len(content)}
            except Exception as e:
                return {"success": False, "error": str(e)}

        self.register_function(
            "write_file",
            "Write content to a file. Creates parent directories if needed.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to write"},
                    "content": {"type": "string", "description": "Content to write to the file"},
                },
                "required": ["path", "content"],
            },
            _exec,
            category="filesystem",
            requires_confirmation=True,
        )

    def _register_list_files(self):
        def _exec(params):
            directory = params.get("directory", ".")
            extension = params.get("extension", "")  # e.g. ".py"
            count_lines = params.get("count_lines", False)
            try:
                entries = []
                total_lines = 0
                for root, dirs, files in os.walk(directory):
                    # Skip hidden dirs and __pycache__
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                    for fname in files:
                        if extension and not fname.endswith(extension):
                            continue
                        fpath = os.path.join(root, fname)
                        rel = os.path.relpath(fpath, directory)
                        size = os.path.getsize(fpath)
                        lines = None
                        if count_lines:
                            try:
                                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                                    lines = sum(1 for _ in f)
                                total_lines += lines
                            except Exception:
                                lines = 0
                        entries.append({"name": rel, "size": size, "lines": lines})
                    if not extension:  # Also add dirs at top level
                        break  # non-recursive when no filter
                return {
                    "success": True,
                    "entries": entries[:200],
                    "count": len(entries),
                    "total_lines": total_lines if count_lines else None,
                }
            except FileNotFoundError:
                return {"success": False, "error": f"Directory not found: {directory}"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        self.register_function(
            "list_files",
            "List files in a directory. Supports filtering by extension and counting lines of code.",
            {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Directory to list (default: current directory)"},
                    "extension": {"type": "string", "description": "Filter by extension, e.g. '.py' (optional)"},
                    "count_lines": {"type": "boolean", "description": "If true, count lines in each file and total (default false)"},
                },
                "required": [],
            },
            _exec,
            category="filesystem",
        )
    def _register_web_search(self):
        def _exec(params):
            query = params.get("query", "")
            max_results = params.get("max_results", 5)
            if not query:
                return {"success": False, "error": "No query provided"}

            # Use agent's real web_search if available
            if getattr(self, "_agent", None) and hasattr(self._agent, "web_search"):
                return self._agent.web_search(query)

            # Primary: ddgs (formerly duckduckgo_search) — returns real text snippets
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS  # legacy fallback
            try:
                with DDGS() as ddgs:
                    hits = list(ddgs.text(query, max_results=max_results))
                if not hits:
                    return {"success": False, "error": "Search returned no results for this query."}
                results = [
                    {
                        "title": h.get("title", ""),
                        "snippet": h.get("body", ""),
                        "url": h.get("href", ""),
                    }
                    for h in hits
                ]
                return {
                    "success": True,
                    "query": query,
                    "results": results,
                    "source": "ddgs",
                }
            except ImportError:
                return {
                    "success": False,
                    "error": "Neither ddgs nor duckduckgo-search is installed. Run: pip install ddgs",
                }
            except Exception as e:
                return {"success": False, "error": f"Web search failed: {e}"}

        self.register_function(
            "web_search",
            "Search the web for information and return results as text snippets.",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
            _exec,
            category="web",
        )

    def _register_send_message(self):
        def _exec(params):
            platform = params.get("platform", "console")
            message = params.get("message", "")
            recipient = params.get("recipient", "")
            if not message:
                return {"success": False, "error": "No message provided"}
            # Default: print to console
            print(f"[Message → {platform}:{recipient}] {message}")
            return {"success": True, "platform": platform, "recipient": recipient,
                    "note": "Message printed to console. Configure platform adapters for actual delivery."}

        self.register_function(
            "send_message",
            "Send a message to a user via a messaging platform.",
            {
                "type": "object",
                "properties": {
                    "platform": {"type": "string", "description": "Platform: console, whatsapp, telegram, discord, slack"},
                    "recipient": {"type": "string", "description": "Recipient identifier"},
                    "message": {"type": "string", "description": "The message to send"},
                },
                "required": ["message"],
            },
            _exec,
            category="messaging",
        )

    def _register_get_time(self):
        def _exec(params):
            from datetime import datetime
            fmt = params.get("format", "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            return {"success": True, "time": now.strftime(fmt), "timestamp": now.timestamp()}

        self.register_function(
            "get_time",
            "Get the current date and time.",
            {
                "type": "object",
                "properties": {
                    "format": {"type": "string", "description": "strftime format string (default: %Y-%m-%d %H:%M:%S)"},
                },
                "required": [],
            },
            _exec,
            category="utility",
        )

    def _register_open_app(self):
        def _exec(params):
            app = params.get("app", "")
            if not app:
                return {"success": False, "error": "No app name provided"}
            if getattr(self, '_agent', None) and hasattr(self._agent, 'open_app'):
                return self._agent.open_app(app)
            # Fallback: open URL if it looks like one, else try OS launch
            if app.startswith(("http://", "https://")):
                webbrowser.open(app)
                return {"success": True, "app": app}
            try:
                import subprocess
                subprocess.Popen(app, shell=True)
                return {"success": True, "app": app}
            except Exception as e:
                return {"success": False, "error": str(e)}

        self.register_function(
            "open_app",
            "Open an application or website by name (e.g. 'chrome', 'notepad', 'youtube', 'https://github.com').",
            {
                "type": "object",
                "properties": {
                    "app": {"type": "string", "description": "App name or URL to open"},
                },
                "required": ["app"],
            },
            _exec,
            category="system",
        )

    def _register_run_code(self):
        def _exec(params):
            code = params.get("code", "")
            language = params.get("language", "python")
            if not code:
                return {"success": False, "error": "No code provided"}
            if getattr(self, '_agent', None) and hasattr(self._agent, 'run_code'):
                return self._agent.run_code(code, language)
            # Fallback: run Python directly
            try:
                import subprocess, tempfile, os
                with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
                    f.write(code)
                    tmp = f.name
                r = subprocess.run(["python", tmp], capture_output=True, text=True, timeout=15)
                os.remove(tmp)
                return {"success": r.returncode == 0, "output": r.stdout[:2000], "error": r.stderr[:500]}
            except Exception as e:
                return {"success": False, "error": str(e)}

        self.register_function(
            "run_code",
            "Execute Python code and return the output. Use for calculations, data processing, file operations.",
            {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute"},
                    "language": {"type": "string", "description": "Language (currently only python supported)"},
                },
                "required": ["code"],
            },
            _exec,
            category="development",
        )


# --- Quick test ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    reg = ToolRegistry()
    reg.register_builtins()

    print(f"Registered {reg.count} tools:")
    for t in reg.list_tools():
        print(f"  • {t['name']} [{t['category']}]: {t['description'][:60]}")

    print("\n--- Testing get_time ---")
    print(reg.execute("get_time"))

    print("\n--- Testing read_file ---")
    print(reg.execute("read_file", {"path": "README.md"}))

    print("\n--- Testing list_files ---")
    print(reg.execute("list_files", {"directory": "."}))
