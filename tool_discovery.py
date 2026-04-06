import ast,inspect,json,logging,re,sqlite3
from datetime import datetime
from typing import Any,Callable,Dict,List,Optional
logger=logging.getLogger("ToolDiscovery")
_S="""
CREATE TABLE IF NOT EXISTS discovered_tools(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE NOT NULL,description TEXT,source TEXT,source_url TEXT,parameters TEXT,return_type TEXT,code TEXT,enabled INTEGER DEFAULT 1,success_count INTEGER DEFAULT 0,fail_count INTEGER DEFAULT 0,last_used TEXT,registered_at TEXT);
CREATE TABLE IF NOT EXISTS discovery_log(id INTEGER PRIMARY KEY AUTOINCREMENT,source TEXT,found INT DEFAULT 0,registered INT DEFAULT 0,errors TEXT,timestamp TEXT);
"""
class ToolDiscovery:
    def __init__(self,db="discovered_tools.db"):
        self.c=sqlite3.connect(db,check_same_thread=False);self.c.row_factory=sqlite3.Row
        self.c.executescript(_S);self.c.commit();self._cache:Dict[str,Callable]={}
        logger.info("ToolDiscovery ready")
    def discover_from_openapi(self,spec_url:str,base_url:str="",auth:str="")->Dict:
        import urllib.request; found,registered,errors=0,0,[]
        try:
            spec=json.loads(urllib.request.urlopen(spec_url,timeout=10).read()) if spec_url.startswith("http") else json.load(open(spec_url))
            api_base=base_url or self._base(spec,spec_url)
            for path,pi in spec.get("paths",{}).items():
                for method,op in pi.items():
                    if method.upper() not in("GET","POST","PUT","PATCH","DELETE"):continue
                    found+=1; name=self._name(op.get("operationId") or f"{method}_{path}")
                    desc=(op.get("summary") or f"{method.upper()} {path}")[:200]
                    code=f'def {name}(**kw):\n import urllib.request,json\n try:\n  r=urllib.request.Request("{api_base}{path}",method="{method.upper()}")\n  with urllib.request.urlopen(r,timeout=15) as rr: return json.loads(rr.read())\n except Exception as e: return {{"error":str(e)}}\n'
                    if self._store(name,desc,"openapi",spec_url,[],code):registered+=1
        except Exception as e:errors.append(str(e))
        return{"found":found,"registered":registered,"errors":errors}
    def discover_from_module(self,mod_name:str,max_tools:int=30)->Dict:
        import importlib; found,registered,errors=0,0,[]
        try:mod=importlib.import_module(mod_name)
        except ImportError as e:return{"found":0,"registered":0,"errors":[str(e)]}
        for name,obj in inspect.getmembers(mod):
            if not callable(obj) or name.startswith("_") or registered>=max_tools:continue
            found+=1
            try:
                doc=(inspect.getdoc(obj) or f"{mod_name}.{name}")[:200]
                code=f'def {mod_name.replace(".","_")}_{name}(**kw):\n import {mod_name.split(".")[0]}\n try: return {{"result":{mod_name}.{name}(**kw)}}\n except Exception as e: return {{"error":str(e)}}\n'
                if self._store(f"{mod_name.replace('.','_')}_{name}",doc,"module",mod_name,[],code):registered+=1
            except Exception as e:errors.append(f"{name}:{e}")
        return{"found":found,"registered":registered,"errors":errors}
    def discover_from_source_file(self,filepath:str,tag:str="")->Dict:
        found,registered,errors=0,0,[]
        try:
            src=open(filepath,"r",encoding="utf-8").read()
            mod=tag or filepath.replace("\\","/").split("/")[-1].replace(".py","")
            for node in ast.walk(ast.parse(src)):
                if not isinstance(node,ast.FunctionDef) or node.name.startswith("_"):continue
                found+=1
                doc=(ast.get_docstring(node) or f"{node.name} in {filepath}")[:200]
                if self._store(f"{mod}_{node.name}",doc,"source",filepath,[],f"# {filepath}: {node.name}"):registered+=1
        except Exception as e:errors.append(str(e))
        return{"found":found,"registered":registered,"errors":errors}
    def scan_project(self,directory:str,ignore=None)->Dict:
        import os; ignore=ignore or ["venv","__pycache__",".git"]
        tf,tr,files=0,0,0
        for root,dirs,fnames in os.walk(directory):
            dirs[:]=[d for d in dirs if not any(p in d for p in ignore)]
            for f in fnames:
                if not f.endswith(".py"):continue
                r=self.discover_from_source_file(os.path.join(root,f))
                tf+=r["found"];tr+=r["registered"];files+=1
        return{"files":files,"found":tf,"registered":tr}
    def compile_tool(self,name:str)->Optional[Callable]:
        if name in self._cache:return self._cache[name]
        row=self.c.execute("SELECT code FROM discovered_tools WHERE name=? AND enabled=1",(name,)).fetchone()
        if not row:return None
        ns:Dict={}
        try:
            exec(compile(row["code"],f"<tool:{name}>","exec"),ns); fn=ns.get(name)
            if callable(fn):self._cache[name]=fn;return fn
        except Exception as e:logger.error(f"Compile {name}: {e}")
        return None
    def call_tool(self,name:str,**kwargs)->Any:
        fn=self.compile_tool(name)
        if not fn:return{"error":f"Tool '{name}' not found"}
        try:
            r=fn(**kwargs);self.c.execute("UPDATE discovered_tools SET success_count=success_count+1,last_used=? WHERE name=?",(datetime.utcnow().isoformat(),name));self.c.commit();return r
        except Exception as e:
            self.c.execute("UPDATE discovered_tools SET fail_count=fail_count+1 WHERE name=?",(name,));self.c.commit();return{"error":str(e)}
    def list_tools(self,source="",limit=100):
        f=f" AND source='{source}'" if source else ""
        return[dict(r) for r in self.c.execute(f"SELECT * FROM discovered_tools WHERE enabled=1{f} ORDER BY success_count DESC LIMIT {limit}").fetchall()]
    def search_tools(self,q,limit=20):
        q=f"%{q}%";return[dict(r) for r in self.c.execute("SELECT * FROM discovered_tools WHERE enabled=1 AND(LOWER(name) LIKE ? OR LOWER(description) LIKE ?) LIMIT ?",(q,q,limit)).fetchall()]
    def auto_register(self,td:Dict)->bool:return self._store(td["name"],td.get("description",""),"manual","",td.get("parameters",[]),td.get("code",""))
    def get_stats(self)->Dict:
        r=self.c.execute("SELECT COUNT(*) t,SUM(enabled) e,SUM(success_count) c,SUM(fail_count) f FROM discovered_tools").fetchone()
        return{"total":r["t"] or 0,"enabled":r["e"] or 0,"calls":r["c"] or 0,"fails":r["f"] or 0}
    def _name(self,raw):return re.sub(r"_+","_",re.sub(r"[^a-zA-Z0-9_]","_",raw)).strip("_").lower()[:60] or "tool"
    def _base(self,spec,fb):
        s=spec.get("servers",[]);
        if s:return s[0].get("url","").rstrip("/")
        from urllib.parse import urlparse;p=urlparse(fb);return f"{p.scheme}://{p.netloc}"
    def _store(self,name,desc,source,url,params,code)->bool:
        try:
            self.c.execute("INSERT OR IGNORE INTO discovered_tools(name,description,source,source_url,parameters,return_type,code,registered_at) VALUES(?,?,?,?,?,?,?,?)",(name,desc,source,url,json.dumps(params),"any",code,datetime.utcnow().isoformat()))
            self.c.commit();return self.c.execute("SELECT changes()").fetchone()[0]>0
        except:return False
    def close(self):self.c.close()
