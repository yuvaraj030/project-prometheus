"""
claw_harness.py - Claude Code harness patterns for ultimate-ai-agent.

Ported from instructkr/claw-code (Python clean-room rewrite of Claude Code).

Provides:
  - ToolPermissionContext  - deny-list based tool gating
  - UsageSummary           - token budget tracking
  - TurnResult             - structured per-turn result
  - ClawSession            - stateful multi-turn session with streaming
  - ClawRuntime            - prompt router + turn-loop runner
  - 10 new tools: glob, grep_search, file_edit, web_fetch, todo_write,
                  powershell, enter_plan_mode, exit_plan_mode, sleep, notebook_edit
  - register_claw_tools()  - plug all tools into your ToolRegistry
"""
from __future__ import annotations
import fnmatch, glob as _glob, json, os, re, subprocess, time
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional, Tuple
from uuid import uuid4

# -- Permission System ---------------------------------------------------------
@dataclass(frozen=True)
class ToolPermissionContext:
    deny_names: frozenset = field(default_factory=frozenset)
    deny_prefixes: tuple = ()
    @classmethod
    def from_iterables(cls, deny_names=None, deny_prefixes=None):
        return cls(
            deny_names=frozenset(n.lower() for n in (deny_names or [])),
            deny_prefixes=tuple(p.lower() for p in (deny_prefixes or [])),
        )
    def blocks(self, tool_name: str) -> bool:
        low = tool_name.lower()
        return low in self.deny_names or any(low.startswith(p) for p in self.deny_prefixes)

# -- Usage Tracking ------------------------------------------------------------
@dataclass(frozen=True)
class UsageSummary:
    input_tokens: int = 0
    output_tokens: int = 0
    def add_turn(self, prompt: str, output: str) -> "UsageSummary":
        return UsageSummary(self.input_tokens + len(prompt.split()),
                            self.output_tokens + len(output.split()))
    @property
    def total(self) -> int: return self.input_tokens + self.output_tokens

@dataclass(frozen=True)
class PermissionDenial:
    tool_name: str
    reason: str

# -- Turn Result ---------------------------------------------------------------
@dataclass(frozen=True)
class TurnResult:
    prompt: str
    output: str
    matched_commands: Tuple[str, ...]
    matched_tools: Tuple[str, ...]
    permission_denials: Tuple[PermissionDenial, ...]
    usage: UsageSummary
    stop_reason: str  # completed | max_turns_reached | max_budget_reached

# -- Session -------------------------------------------------------------------
@dataclass
class ClawSessionConfig:
    max_turns: int = 20
    max_budget_tokens: int = 50_000
    compact_after_turns: int = 16
    structured_output: bool = False

@dataclass
class ClawSession:
    config: ClawSessionConfig = field(default_factory=ClawSessionConfig)
    session_id: str = field(default_factory=lambda: uuid4().hex)
    messages: List[str] = field(default_factory=list)
    permission_denials: List[PermissionDenial] = field(default_factory=list)
    total_usage: UsageSummary = field(default_factory=UsageSummary)
    _plan_mode: bool = False

    def submit(self, prompt, matched_commands=(), matched_tools=(), denied_tools=()):
        if len(self.messages) >= self.config.max_turns:
            return TurnResult(prompt, f"[CLAW] Max turns reached.",
                              matched_commands, matched_tools, denied_tools,
                              self.total_usage, "max_turns_reached")
        lines = [f"Prompt: {prompt}",
                 f"Commands: {', '.join(matched_commands) or 'none'}",
                 f"Tools: {', '.join(matched_tools) or 'none'}",
                 f"Denials: {len(denied_tools)}",
                 f"PlanMode: {'ON' if self._plan_mode else 'off'}"]
        output = (json.dumps({"summary": lines, "session": self.session_id}, indent=2)
                  if self.config.structured_output else "\n".join(lines))
        projected = self.total_usage.add_turn(prompt, output)
        stop = "max_budget_reached" if projected.total > self.config.max_budget_tokens else "completed"
        self.messages.append(prompt)
        self.permission_denials.extend(denied_tools)
        self.total_usage = projected
        if len(self.messages) > self.config.compact_after_turns:
            self.messages = self.messages[-self.config.compact_after_turns:]
        return TurnResult(prompt, output, tuple(matched_commands), tuple(matched_tools),
                          tuple(denied_tools), self.total_usage, stop)

    def stream_submit(self, prompt, matched_commands=(), matched_tools=(), denied_tools=()):
        yield {"type": "message_start", "session_id": self.session_id, "prompt": prompt}
        if matched_commands: yield {"type": "command_match", "commands": matched_commands}
        if matched_tools:    yield {"type": "tool_match",    "tools":    matched_tools}
        if denied_tools:     yield {"type": "permission_denial", "denials": [d.tool_name for d in denied_tools]}
        r = self.submit(prompt, matched_commands, matched_tools, denied_tools)
        yield {"type": "message_delta", "text": r.output}
        yield {"type": "message_stop",
               "usage": {"in": r.usage.input_tokens, "out": r.usage.output_tokens},
               "stop_reason": r.stop_reason, "turn_count": len(self.messages)}

    def enter_plan_mode(self) -> str:
        self._plan_mode = True
        return "[CLAW] Plan mode ENABLED."
    def exit_plan_mode(self) -> str:
        self._plan_mode = False
        return "[CLAW] Plan mode DISABLED."
    @property
    def in_plan_mode(self) -> bool: return self._plan_mode

    def persist(self, directory="recovery") -> str:
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, f"claw_session_{self.session_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"session_id": self.session_id, "messages": self.messages,
                       "input_tokens": self.total_usage.input_tokens,
                       "output_tokens": self.total_usage.output_tokens}, f, indent=2)
        return path

    @classmethod
    def load(cls, path: str) -> "ClawSession":
        with open(path, encoding="utf-8") as f: d = json.load(f)
        s = cls(session_id=d["session_id"])
        s.messages = d.get("messages", [])
        s.total_usage = UsageSummary(d.get("input_tokens", 0), d.get("output_tokens", 0))
        return s

    def summary(self) -> str:
        return (f"Session {self.session_id[:8]}... | turns={len(self.messages)} | "
                f"tokens in={self.total_usage.input_tokens} out={self.total_usage.output_tokens} | "
                f"denials={len(self.permission_denials)} | plan={'ON' if self._plan_mode else 'off'}")

# -- Runtime / Router ----------------------------------------------------------
@dataclass(frozen=True)
class RouteMatch:
    kind: str; name: str; score: int

class ClawRuntime:
    def __init__(self, tool_registry=None):
        self.registry = tool_registry

    def route_prompt(self, prompt: str, limit: int = 5) -> List[RouteMatch]:
        if not self.registry: return []
        tokens = {t.lower() for t in re.split(r"[\s/\-_]+", prompt) if t}
        matches = []
        for name, tool in self.registry.tools.items():
            hay = f"{name} {tool.description} {tool.category}".lower()
            score = sum(1 for t in tokens if t in hay)
            if score: matches.append(RouteMatch("tool", name, score))
        matches.sort(key=lambda m: (-m.score, m.name))
        return matches[:limit]

    def run_turn_loop(self, prompt, max_turns=3, limit=5,
                      permission_context=None, structured_output=False):
        session = ClawSession(config=ClawSessionConfig(max_turns=max_turns,
                                                        structured_output=structured_output))
        matches = self.route_prompt(prompt, limit)
        tools = tuple(m.name for m in matches if m.kind == "tool")
        cmds  = tuple(m.name for m in matches if m.kind == "command")
        if permission_context:
            tools = tuple(n for n in tools if not permission_context.blocks(n))
        denials = tuple(PermissionDenial(m.name, "blocked")
                        for m in matches
                        if m.kind == "tool" and permission_context and permission_context.blocks(m.name))
        results = []
        for i in range(max_turns):
            p = prompt if i == 0 else f"{prompt} [turn {i+1}]"
            r = session.submit(p, cmds, tools, denials)
            results.append(r)
            if r.stop_reason != "completed": break
        return results

# -- Tool Implementations ------------------------------------------------------
def _glob_tool(p):
    pat, d = p.get("pattern",""), p.get("directory",".")
    if not pat: return {"success":False,"error":"No pattern"}
    try:
        fp = os.path.join(d,"**",pat) if "**" not in pat else os.path.join(d,pat)
        m = [os.path.relpath(x,d) for x in _glob.glob(fp, recursive=True)]
        return {"success":True,"matches":m[:200],"count":len(m)}
    except Exception as e: return {"success":False,"error":str(e)}

def _grep_search_tool(p):
    query, path = p.get("query",""), p.get("path",".")
    inc, cs = p.get("include",""), p.get("case_sensitive",True)
    if not query: return {"success":False,"error":"No query"}
    try:
        pat = re.compile(query, 0 if cs else re.IGNORECASE)
        results, walk = [], path if os.path.isdir(path) else os.path.dirname(path) or "."
        for root,dirs,files in os.walk(walk):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d!="__pycache__"]
            for fname in files:
                if inc and not fnmatch.fnmatch(fname,inc): continue
                fp = os.path.join(root,fname)
                try:
                    with open(fp,encoding="utf-8",errors="replace") as f:
                        for no,line in enumerate(f,1):
                            if pat.search(line):
                                results.append({"file":os.path.relpath(fp,walk),"line":no,"content":line.rstrip()[:200]})
                                if len(results)>=100: return {"success":True,"results":results,"truncated":True}
                except: continue
        return {"success":True,"results":results,"count":len(results)}
    except re.error as e: return {"success":False,"error":f"Bad regex: {e}"}
    except Exception as e: return {"success":False,"error":str(e)}

def _file_edit_tool(p):
    path,old,new = p.get("path",""),p.get("old_str",""),p.get("new_str","")
    if not path: return {"success":False,"error":"No path"}
    if old=="": return {"success":False,"error":"old_str empty"}
    try:
        content = open(path,encoding="utf-8").read()
        n = content.count(old)
        if n==0: return {"success":False,"error":"old_str not found"}
        if n>1:  return {"success":False,"error":f"old_str appears {n} times - be specific"}
        with open(path,"w",encoding="utf-8") as f: f.write(content.replace(old,new,1))
        return {"success":True,"path":path,"replaced":1}
    except FileNotFoundError: return {"success":False,"error":f"Not found: {path}"}
    except Exception as e: return {"success":False,"error":str(e)}

def _web_fetch_tool(p):
    url, mx = p.get("url",""), p.get("max_chars",8000)
    if not url: return {"success":False,"error":"No URL"}
    try:
        import urllib.request
        req = urllib.request.Request(url,headers={"User-Agent":"ClawHarness/1.0"})
        with urllib.request.urlopen(req,timeout=15) as r:
            raw = r.read().decode("utf-8",errors="replace")
        text = re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",raw)).strip()
        return {"success":True,"url":url,"text":text[:mx],"length":len(text)}
    except Exception as e: return {"success":False,"error":str(e)}

def _todo_write_tool(p):
    todos, f = p.get("todos",[]), p.get("file","agent_todos.json")
    if not isinstance(todos,list): return {"success":False,"error":"todos must be a list"}
    try:
        existing = json.load(open(f,encoding="utf-8")) if os.path.exists(f) else []
        for item in todos:
            if isinstance(item,str):
                item={"id":uuid4().hex[:8],"content":item,"status":"pending","ts":time.time()}
            existing.append(item)
        with open(f,"w",encoding="utf-8") as fh: json.dump(existing,fh,indent=2)
        return {"success":True,"file":f,"total":len(existing),"added":len(todos)}
    except Exception as e: return {"success":False,"error":str(e)}

def _powershell_tool(p):
    cmd,to = p.get("command",""),p.get("timeout",30)
    if not cmd: return {"success":False,"error":"No command"}
    try:
        r = subprocess.run(["powershell","-NoProfile","-NonInteractive","-Command",cmd],
                           capture_output=True,text=True,timeout=to)
        return {"success":r.returncode==0,"stdout":r.stdout[:3000],"stderr":r.stderr[:500],"rc":r.returncode}
    except FileNotFoundError: return {"success":False,"error":"PowerShell not found"}
    except subprocess.TimeoutExpired: return {"success":False,"error":f"Timeout {to}s"}
    except Exception as e: return {"success":False,"error":str(e)}

_PLAN_MODE = {"active": False}
def _enter_plan_mode_tool(p):
    _PLAN_MODE["active"]=True
    return {"success":True,"plan_mode":True,"message":"Plan mode ENABLED"}
def _exit_plan_mode_tool(p):
    _PLAN_MODE["active"]=False
    return {"success":True,"plan_mode":False,"message":"Plan mode DISABLED"}
def is_plan_mode_active(): return _PLAN_MODE.get("active",False)

def _sleep_tool(p):
    s = min(max(float(p.get("seconds",1)),0.1),60)
    time.sleep(s)
    return {"success":True,"slept_seconds":s}

def _notebook_edit_tool(p):
    path,idx,src = p.get("path",""),p.get("cell_index",0),p.get("new_source","")
    if not path: return {"success":False,"error":"No path"}
    try:
        nb = json.load(open(path,encoding="utf-8"))
        cells = nb.get("cells",[])
        if idx>=len(cells): return {"success":False,"error":f"Cell {idx} out of range ({len(cells)} cells)"}
        cells[idx]["source"]=[src]
        with open(path,"w",encoding="utf-8") as f: json.dump(nb,f,indent=1)
        return {"success":True,"path":path,"cell_index":idx}
    except Exception as e: return {"success":False,"error":str(e)}

# -- Registration --------------------------------------------------------------
CLAW_TOOLS = [
    ("glob","Find files matching a glob pattern recursively.",
     {"type":"object","properties":{"pattern":{"type":"string","description":"Glob e.g. '*.py'"},
      "directory":{"type":"string","description":"Start dir (default .)"}},"required":["pattern"]},
     _glob_tool,"filesystem"),
    ("grep_search","Search file contents with regex. Returns file, line number, content.",
     {"type":"object","properties":{"query":{"type":"string","description":"Regex pattern"},
      "path":{"type":"string","description":"Dir or file to search"},
      "include":{"type":"string","description":"Filename filter e.g. '*.py'"},
      "case_sensitive":{"type":"boolean","description":"Case sensitive (default true)"}},"required":["query"]},
     _grep_search_tool,"filesystem"),
    ("file_edit","Precisely replace a UNIQUE string in a file. old_str must appear exactly once.",
     {"type":"object","properties":{"path":{"type":"string","description":"File to edit"},
      "old_str":{"type":"string","description":"Exact text to replace"},
      "new_str":{"type":"string","description":"Replacement text"}},"required":["path","old_str","new_str"]},
     _file_edit_tool,"filesystem"),
    ("web_fetch","Fetch a URL and return its text content (HTML stripped).",
     {"type":"object","properties":{"url":{"type":"string","description":"URL to fetch"},
      "max_chars":{"type":"integer","description":"Max chars (default 8000)"}},"required":["url"]},
     _web_fetch_tool,"web"),
    ("todo_write","Write structured todos to agent_todos.json.",
     {"type":"object","properties":{"todos":{"type":"array","items":{},"description":"List of todo strings or dicts"},
      "file":{"type":"string","description":"Target JSON file"}},"required":["todos"]},
     _todo_write_tool,"productivity"),
    ("powershell","Run a PowerShell command on Windows.",
     {"type":"object","properties":{"command":{"type":"string","description":"PS command"},
      "timeout":{"type":"integer","description":"Timeout seconds (default 30)"}},"required":["command"]},
     _powershell_tool,"system"),
    ("enter_plan_mode","Switch agent to plan mode - drafts a plan before executing tools.",
     {"type":"object","properties":{},"required":[]},_enter_plan_mode_tool,"agent"),
    ("exit_plan_mode","Exit plan mode - return to direct tool execution.",
     {"type":"object","properties":{},"required":[]},_exit_plan_mode_tool,"agent"),
    ("sleep","Pause execution for N seconds (0.1-60).",
     {"type":"object","properties":{"seconds":{"type":"number","description":"Seconds to sleep"}},"required":["seconds"]},
     _sleep_tool,"utility"),
    ("notebook_edit","Edit a Jupyter notebook cell by zero-based index.",
     {"type":"object","properties":{"path":{"type":"string","description":"Path to .ipynb"},
      "cell_index":{"type":"integer","description":"Zero-based cell index"},
      "new_source":{"type":"string","description":"New cell source"}},"required":["path","cell_index","new_source"]},
     _notebook_edit_tool,"development"),
]

def register_claw_tools(registry) -> int:
    """Register all 10 Claude Code-style tools into an existing ToolRegistry.

    Usage:
        from tool_registry import ToolRegistry
        from claw_harness import register_claw_tools, ClawSession, ClawRuntime
        reg = ToolRegistry()
        reg.register_builtins()
        added = register_claw_tools(reg)
        print(f"Added {added} claw tools. Total: {reg.count}")
    """
    added = 0
    for name,desc,params,func,cat in CLAW_TOOLS:
        registry.register_function(name,desc,params,func,category=cat)
        added += 1
    return added

if __name__ == "__main__":
    print("=== Claw Harness Smoke Test ===")
    s = ClawSession()
    print(s.enter_plan_mode())
    r = s.submit("find python files", matched_tools=("glob",))
    print(s.summary())
    print("stop:", r.stop_reason)
    events = list(s.stream_submit("search TODOs", matched_tools=("grep_search",)))
    print("stream:", [e["type"] for e in events])
    print("glob:", _glob_tool({"pattern":"*.py","directory":"."}))
    print("sleep:", _sleep_tool({"seconds":0.1}))
    ctx = ToolPermissionContext.from_iterables(deny_names=["powershell"])
    print(f"blocks powershell={ctx.blocks('powershell')} glob={ctx.blocks('glob')}")
    print("OK")
