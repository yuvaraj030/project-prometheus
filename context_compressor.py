import json,logging,os,time
from typing import Dict,List
logger=logging.getLogger('ContextCompressor')
THRESHOLD=int(os.environ.get('COMPACT_THRESHOLD_WORDS','3000'))
KEEP_RECENT=int(os.environ.get('COMPACT_KEEP_RECENT','6'))
BOUNDARY="{compact_boundary}"
class ContextCompressor:
    def __init__(self,llm=None,threshold_words=THRESHOLD,keep_recent=KEEP_RECENT):
        self.llm,self.threshold,self.keep=llm,threshold_words,keep_recent
        self._last_ts=0.0;self.stats={"runs":0,"strategy":"none"}
    def maybe_compact(self,messages):
        if not messages or self._words(messages)<self.threshold:return messages
        if time.time()-self._last_ts<30:return messages
        before=self._words(messages)
        messages=self._snip(messages)
        if self._words(messages)<self.threshold:self.stats["strategy"]="snipCompact"
        elif self.llm:messages=self._auto(messages);self.stats["strategy"]="autoCompact"
        else:messages=self._collapse(messages);self.stats["strategy"]="contextCollapse"
        self._last_ts=time.time();self.stats["runs"]+=1
        logger.info(f"[Compact] {before}w->{self._words(messages)}w")
        return messages
    def _snip(self,msgs):
        out=[]
        for m in msgs:
            c=str(m.get("content",""))
            if not c.strip():continue
            if out and out[-1].get("role")==m.get("role") and str(out[-1].get("content",""))[:80]==c[:80]:continue
            out.append(m)
        return out
    def _auto(self,msgs):
        if len(msgs)<=self.keep:return msgs
        old,recent=msgs[:-self.keep],msgs[-self.keep:]
        txt="\n".join([f"[{m.get('role','?').upper()}]: {str(m.get('content',''))[:300]}" for m in old])
        try:
            s=self.llm.call(f"Summarize:\n{txt}",system="200-word summary.",max_tokens=400,Otemperature=0.2)
            if not s or len(s.strip())<20:raise ValueError("empty")
        except Exception as e:logger.warning(f"autoCompact failed:{e}");return self._collapse(msgs)
        return [{"role":"system","content":f"[Summary]\n{s.strip()}"},{"role":"system","content":BOUNDARY,"_marker":True}]+recent
    def _collapse(self,msgs):
        s=[m for m in msgs if m.get("role")=="system"]
        n=[m for m in msgs if m.get("role")!="system"]
        return s+[{"role":"system","content":BOUNDARY+"(truncated)","_marker":True}]+n[-self.keep:]
    def _words(self,msgs):return sum(len(str(m.get("content","")).split()) for m in msgs)
def compact_history(history,llm=None):
    msgs=[{"role":"assistant","content":h} for h in history]
    out=ContextCompressor(llm=llm).maybe_compact(msgs)
    return [m["content"] for m in out if not m.get("_marker")]
