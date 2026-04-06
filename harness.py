import logging,os,sys
logger=logging.getLogger("Harness")
class Harness:
    def __init__(self,llm,registry,compressor,coordinator,sessions,permissions,file_history,executor):
        self.llm=llm;self.registry=registry;self.compressor=compressor
        self.coordinator=coordinator;self.sessions=sessions
        self.permissions=permissions;self.file_history=file_history;self.executor=executor
    def step(self,messages):return self.compressor.maybe_compact(messages)
    def check_permission(self,tool_name,params=None,interactive=False):
        action=self.permissions.check(tool_name,params)
        if action=="ask" and interactive:action=self.permissions.interactive_prompt(tool_name,params)
        return action
    def start_coordinator(self):self.coordinator.start_background();logger.info("[Harness] Coordinator started")
    def new_session(self,cwd=None):return self.sessions.new_session(cwd=cwd)
    def status(self):return{"tools":self.registry.count,"compactor":self.compressor.stats,"coordinator":self.coordinator.status()}

def bootstrap(llm,auto_start_coordinator=False):
    sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
    from tool_registry import ToolRegistry
    registry=ToolRegistry();registry.register_builtins()
    for mod,fn in [("claw_harness","register_claw_tools"),("claude_code_tools","register_claude_tools")]:
        try:
            m=__import__(mod);getattr(m,fn)(registry);logger.info(f"[Harness] Loaded {mod}")
        except ImportError:logger.warning(f"[Harness] {mod} not found")
    logger.info(f"[Harness] {registry.count} tools total")
    from context_compressor import ContextCompressor
    from session_store import SessionStore
    from permission_engine import PermissionEngine
    from file_history import FileHistory
    from parallel_executor import ParallelExecutor
    from coordinator_mode import CoordinatorMode
    h=Harness(llm=llm,registry=registry,
              compressor=ContextCompressor(llm=llm),
              coordinator=CoordinatorMode(llm,registry,auto_start=auto_start_coordinator),
              sessions=SessionStore(),
              permissions=PermissionEngine(),
              file_history=FileHistory(),
              executor=ParallelExecutor(registry))
    logger.info("[Harness] Bootstrap complete")
    return h
