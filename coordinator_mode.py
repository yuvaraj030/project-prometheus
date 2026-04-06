import logging,threading,time
from typing import Dict,List,Optional
from uuid import uuid4
logger=logging.getLogger("CoordinatorMode")
POLL_S=float(__import__("os").environ.get("COORDINATOR_POLL_S","30"))
MAX_TASKS=int(__import__("os").environ.get("COORDINATOR_MAX_TASKS","3"))
class CoordinatorMode:
    def __init__(self,llm,tool_registry,task_store=None,poll_interval=POLL_S,max_tasks=MAX_TASKS,react_steps=10,auto_start=False):
        self.llm,self.registry=llm,tool_registry
        self.poll_interval,self.max_tasks,self.react_steps=poll_interval,max_tasks,react_steps
        if task_store is not None:self._store=task_store
        else:
            try:from claude_code_tools import get_task_store;self._store=get_task_store()
            except ImportError:self._store={}
        self._running=False;self._thread=None;self._active={};self.stats={"scans":0,"claimed":0,"completed":0,"failed":0}
        if auto_start:self.start_background()
    def start_background(self):
        if self._running:return
        self._running=True
        self._thread=threading.Thread(target=self._loop,name="Coordinator",daemon=True)
        self._thread.start()
        logger.info(f"[Coordinator] Started poll={self.poll_interval}s max={self.max_tasks}")
    def stop(self):self._running=False
    def run_once(self):return self._scan()
    def status(self):return{"running":self._running,"active":len(self._active),"pending":len(self._pending()),"stats":self.stats}
    def inject_task(self,title,description="",priority="normal"):
        tid=uuid4().hex[:8]
        self._store[tid]={"id":tid,"title":title,"description":description,"priority":priority,"tags":["coordinator"],"status":"pending","output":[],"created_at":time.time()}
        return tid
    def _loop(self):
        while self._running:
            try:self._reap();self._scan()
            except Exception as e:logger.error(f"[Coordinator] {e}")
            time.sleep(self.poll_interval)
    def _scan(self):
        self.stats["scans"]+=1
        slots=self.max_tasks-len(self._active)
        if slots<=0:return{"claimed":[],"reason":"no_slots"}
        pending=self._pending()
        if not pending:return{"claimed":[],"reason":"no_tasks"}
        pri={"high":0,"normal":1,"low":2}
        pending.sort(key=lambda t:(pri.get(t.get("priority","normal"),1),t.get("created_at",0)))
        claimed=[]
        for task in pending[:slots]:
            tid=task["id"]
            if tid in self._active:continue
            self._claim(task);claimed.append(tid);self.stats["claimed"]+=1
        return{"claimed":claimed}
    def _pending(self):return[t for t in self._store.values() if t.get("status")=="pending"]
    def _claim(self,task):
        tid=task["id"]
        self._store[tid]["status"]="running";self._store[tid]["claimed_at"]=time.time()
        t=threading.Thread(target=self._execute,args=(task,),daemon=True)
        self._active[tid]=t;t.start()
        logger.info(f"[Coordinator] Claimed {tid}: {task.get('title','?')[:60]}")
    def _execute(self,task):
        tid=task["id"]
        obj=(task.get("title","")+" "+task.get("description","")).strip(". ")
        try:
            from react_agent import ReactAgent
            result=ReactAgent(self.llm,self.registry,max_steps=self.react_steps,verbose=False).run(obj)
            ok=result.get("success",False)
            self._store[tid]["status"]="completed" if ok else "failed"
            self._store[tid]["output"].append({"ts":time.time(),"text":str(result.get("result",""))[:400],"success":ok})
            self.stats["completed" if ok else "failed"]+=1
        except Exception as e:
            self._store[tid]["status"]="failed"
            self._store[tid]["output"].append({"ts":time.time(),"text":str(e),"success":False})
            self.stats["failed"]+=1
        finally:self._active.pop(tid,None)
    def _reap(self):
        done=[t for t,th in list(self._active.items()) if not th.is_alive()]
        for t in done:self._active.pop(t,None)