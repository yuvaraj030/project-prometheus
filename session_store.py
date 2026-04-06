import json,logging,os,time
from pathlib import Path
from typing import Any,Dict,List,Optional
from uuid import uuid4
logger=logging.getLogger("SessionStore")
SESSION_DIR=os.environ.get("SESSION_DIR",os.path.join("recovery","sessions"))
class SessionStore:
    def __init__(self,session_dir=SESSION_DIR):
        self.dir=Path(session_dir);self.dir.mkdir(parents=True,exist_ok=True)
    def new_session(self,cwd=None):
        sid=uuid4().hex;self._w(sid,{"type":"meta","session_id":sid,"cwd":cwd or os.getcwd(),"ts":time.time()});return sid
    def append_user(self,sid,content):self._w(sid,{"type":"user","content":content,"ts":time.time()})
    def append_assistant(self,sid,content,usage=None):
        e={"type":"assistant","content":content,"ts":time.time()}
        if usage:e["usage"]=usage
        self._w(sid,e)
    def append_tool_use(self,sid,tool,params):self._w(sid,{"type":"tool_use","tool":tool,"params":params,"ts":time.time()})
    def append_tool_result(self,sid,tool,result):self._w(sid,{"type":"tool_result","tool":tool,"result":result,"ts":time.time()})
    def append_progress(self,sid,step,thought,action):self._w(sid,{"type":"progress","step":step,"thought":thought[:200],"action":action,"ts":time.time()})
    def append_compact(self,sid,summary=""):self._w(sid,{"type":"compact_boundary","summary":summary,"ts":time.time()})
    def get_last_session(self,cwd=None):
        s=self.list_sessions(cwd=cwd);return s[0]["session_id"] if s else None
    def list_sessions(self,cwd=None,limit=20):
        out=[]
        for p in sorted(self.dir.glob("*.jsonl"),key=lambda x:x.stat().st_mtime,reverse=True)[:limit]:
            try:
                first=json.loads(open(p,encoding="utf-8").readline())
                if first.get("type")!="meta":continue
                if cwd and not first.get("cwd","").startswith(cwd):continue
                out.append({"session_id":first["session_id"],"cwd":first.get("cwd",""),"mtime":p.stat().st_mtime})
            except:continue
        return out
    def load_session(self,sid):
        p=self.dir/f"{sid}.jsonl"
        if not p.exists():return[]
        msgs=[]
        for line in open(p,encoding="utf-8"):
            try:
                e=json.loads(line.strip());t=e.get("type","")
                if t=="user":msgs.append({"role":"user","content":e.get("content","")})
                elif t=="assistant":msgs.append({"role":"assistant","content":e.get("content","")})
                elif t=="compact_boundary":msgs.append({"role":"system","content":"[compact_boundary] "+e.get("summary",""),"_marker":True})
            except:continue
        return msgs
    def fork_session(self,src_sid):
        evts=self._r(src_sid);new_sid=uuid4().hex
        self._w(new_sid,{"type":"meta","session_id":new_sid,"cwd":os.getcwd(),"forked_from":src_sid,"ts":time.time()})
        for e in evts:
            if e.get("type")!="meta":self._w(new_sid,e)
        return new_sid
    def _w(self,sid,event):
        try:open(self.dir/f"{sid}.jsonl","a",encoding="utf-8").write(json.dumps(event,default=str)+"\n")
        except Exception as e:logger.error(f"write:{e}")
    def _r(self,sid):
        p=self.dir/f"{sid}.jsonl"
        if not p.exists():return[]
        evts=[]
        for line in open(p,encoding="utf-8"):
            try:evts.append(json.loads(line.strip()))
            except:pass
        return evts