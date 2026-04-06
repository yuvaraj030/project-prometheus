import logging,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from typing import Any,Dict,List,Tuple
logger=logging.getLogger("ParallelExecutor")
SAFE_TOOLS={"read_file","list_files","glob","grep_search","web_search","web_fetch","get_time","tool_search","brief","file_read"}
SAFE_CATS={"web","utility"}
class ParallelExecutor:
    def __init__(self,registry,max_workers=4):
        self.registry=registry;self.max_workers=max_workers
    def partition(self,tool_calls):
        safe,serial=[],[]
        for tc in tool_calls:
            name=tc.get("tool","")
            tool=self.registry.get(name)
            cat=tool.category if tool else ""
            if name in SAFE_TOOLS or cat in SAFE_CATS:safe.append(tc)
            else:serial.append(tc)
        return safe,serial
    def run_concurrent(self,tool_calls):
        if not tool_calls:return[]
        results=[None]*len(tool_calls)
        with ThreadPoolExecutor(max_workers=min(self.max_workers,len(tool_calls))) as ex:
            fm={ex.submit(self._call,tc):i for i,tc in enumerate(tool_calls)}
            for fut in as_completed(fm):
                i=fm[fut]
                try:results[i]=fut.result()
                except Exception as e:results[i]={"tool":tool_calls[i].get("tool","?"),"result":{"success":False,"error":str(e)}}
        return results
    def run_serial(self,tool_calls):return[self._call(tc) for tc in tool_calls]
    def run_all(self,tool_calls):
        if not tool_calls:return[]
        safe,serial=self.partition(tool_calls)
        sr,se=iter(self.run_concurrent(safe)),iter(self.run_serial(serial))
        out=[]
        for tc in tool_calls:
            n=tc.get("tool","");tool=self.registry.get(n);cat=tool.category if tool else ""
            out.append(next(sr) if(n in SAFE_TOOLS or cat in SAFE_CATS) else next(se))
        return out
    def _call(self,tc):
        n=tc.get("tool","?");p=tc.get("params",{});t0=time.time()
        r=self.registry.execute(n,p)
        return{"tool":n,"params":p,"result":r,"elapsed_ms":int((time.time()-t0)*1000)}
