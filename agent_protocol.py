import json,logging,time,uuid
from datetime import datetime
from typing import Any,Dict,List,Optional
logger=logging.getLogger("AgentProtocol")
MSG_TYPES=("knowledge_share","goal_request","tool_result","critique","heartbeat","task_assign")
class AgentProtocol:
    """Standardised ACP message bus for multi-agent coordination."""
    def __init__(self,agent_id:str="main"):
        self.agent_id=agent_id;self._inbox:List[Dict]=[];self._handlers:Dict[str,Any]={}
        logger.info(f"AgentProtocol ready agent_id={agent_id}")
    def send(self,to:str,msg_type:str,content:Any,confidence:float=1.0)->Dict:
        if msg_type not in MSG_TYPES:logger.warning(f"Unknown msg type: {msg_type}")
        msg={"id":str(uuid.uuid4())[:8],"from":self.agent_id,"to":to,"type":msg_type,
             "content":content,"confidence":confidence,"timestamp":datetime.utcnow().isoformat()}
        logger.debug(f"[ACP] {self.agent_id} -> {to}: {msg_type}");return msg
    def receive(self,msg:Dict)->Optional[Dict]:
        if msg.get("to") not in(self.agent_id,"*"):return None
        self._inbox.append(msg)
        handler=self._handlers.get(msg["type"])
        if handler:
            try:return handler(msg)
            except Exception as e:logger.error(f"Handler error: {e}")
        return msg
    def on(self,msg_type:str,handler):self._handlers[msg_type]=handler
    def flush(self)->List[Dict]:msgs=list(self._inbox);self._inbox.clear();return msgs
    def share_knowledge(self,to:str,facts:List[Dict],confidence:float=0.8)->Dict:
        return self.send(to,"knowledge_share",{"facts":facts},confidence)
    def request_goal_help(self,to:str,goal:str,context:Dict=None)->Dict:
        return self.send(to,"goal_request",{"goal":goal,"context":context or {}})
    def send_tool_result(self,to:str,tool:str,result:Any)->Dict:
        return self.send(to,"tool_result",{"tool":tool,"result":result})
    def critique(self,to:str,plan:str,issues:List[str])->Dict:
        return self.send(to,"critique",{"plan":plan,"issues":issues})
def make_broadcast(protocol:AgentProtocol,agents:List[str],msg_type:str,content:Any)->List[Dict]:
    return[protocol.send(a,msg_type,content) for a in agents]
