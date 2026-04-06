import json,logging,os,re
from pathlib import Path
from typing import Dict,List,Optional
logger=logging.getLogger("PermissionEngine")
RULES_FILE=os.environ.get("PERMISSION_RULES_FILE","permissions.json")
SAFE={"get_time","read_file","list_files","glob","grep_search","web_search","web_fetch","tool_search","file_read"}
ASK={"run_shell","bash","powershell","run_code","repl","write_file","file_write","file_edit"}
class PermissionEngine:
    def __init__(self,rules_file=RULES_FILE):
        self.rules_file=Path(rules_file);self.rules={"allow":[],"deny":[],"ask":[]};self.load_rules()
    def check(self,tool_name,params=None):
        for r in self.rules["deny"]:
            if self._m(r,tool_name):return "deny"
        for r in self.rules["allow"]:
            if self._m(r,tool_name):return "allow"
        for r in self.rules["ask"]:
            if self._m(r,tool_name):return "ask"
        if tool_name in SAFE:return "allow"
        if tool_name in ASK:return "ask"
        return "ask"
    def add_rule(self,action,pattern,name=""):
        self.rules[action].append({"pattern":pattern,"name":name or pattern});self.save_rules()
    def remove_rule(self,action,pattern):
        self.rules[action]=[r for r in self.rules[action] if r.get("pattern")!=pattern];self.save_rules()
    def load_rules(self):
        if not self.rules_file.exists():return
        try:data=json.loads(self.rules_file.read_text(encoding="utf-8"));self.rules=data.get("rules",self.rules)
        except Exception as e:logger.warning(f"load:{e}")
    def save_rules(self):
        try:self.rules_file.write_text(json.dumps({"rules":self.rules},indent=2),encoding="utf-8")
        except Exception as e:logger.error(f"save:{e}")
    def interactive_prompt(self,tool_name,params=None):
        try:
            p=json.dumps(params,default=str)[:80] if params else "(none)"
            ans=input(f"[Perm] Allow {tool_name}({p})? [y/n/always/never] ").strip().lower()
            if ans in("y","yes"):return "allow"
            if ans=="always":self.add_rule("allow",tool_name);return "allow"
            if ans=="never":self.add_rule("deny",tool_name);return "deny"
            return "deny"
        except:return "deny"
    def _m(self,rule,tool_name):
        pat=rule.get("pattern","")
        try:return bool(re.match(pat.replace("*",".*")+"$",tool_name))
        except:return pat==tool_name