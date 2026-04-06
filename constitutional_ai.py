import logging,json
from datetime import datetime
from typing import Any,Dict,List,Tuple
logger=logging.getLogger("ConstitutionalAI")
CONSTITUTION=[
    {"rule":"harmlessness","description":"Does not harm users, third parties, or systems","weight":1.0},
    {"rule":"helpfulness","description":"Serves the user true intent and advances their goals","weight":0.8},
    {"rule":"honesty","description":"Based on verified facts, not hallucinations or deception","weight":0.9},
    {"rule":"autonomy_preservation","description":"Respects user autonomy and does not manipulate","weight":0.7},
    {"rule":"no_illegal","description":"Does not facilitate illegal activity","weight":1.0},
]
class ConstitutionalAI:
    """Formal safety layer – every action is checked against the constitution before execution."""
    def __init__(self,strict=False):
        self.strict=strict;self.checks=0;self.blocks=0
        logger.info(f"ConstitutionalAI ready strict={strict}")
    def check_action(self,action:Dict)->Dict:
        self.checks+=1
        violations:List[str]=[];warnings:List[str]=[]
        text=json.dumps(action,default=str).lower()
        # Harmlessness check
        harm_kw=["delete all","rm -rf","drop table","format drive","kill process","shutdown","wipe"]
        if any(w in text for w in harm_kw):violations.append("harmlessness: potentially destructive command")
        # No illegal check
        illegal_kw=["exfiltrate","steal ","ransomware","ddos","exploit without permission","hack into"]
        if any(w in text for w in illegal_kw):violations.append("no_illegal: potentially illegal activity")
        # Honesty check – flag if action claims certainty about unknown facts
        if "i am certain" in text and "verified" not in text:warnings.append("honesty: unverified certainty claim")
        # Autonomy
        if any(w in text for w in ["force user","manipulate","deceive user"]):violations.append("autonomy_preservation: manipulation detected")
        allowed=len(violations)==0 or(not self.strict and len(violations)<2)
        if not allowed:self.blocks+=1
        result={"allowed":allowed,"violations":violations,"warnings":warnings,
                "action_hash":hash(text)%999999,"checked_at":datetime.utcnow().isoformat()}
        if violations:logger.warning(f"[ConstitutionalAI] Violations: {violations}")
        return result
    def check_content(self,content:str)->Dict:
        return self.check_action({"content":content})
    def audit_log(self)->Dict:
        return{"total_checks":self.checks,"total_blocks":self.blocks,
               "block_rate":round(self.blocks/max(1,self.checks)*100,1)}
    def add_rule(self,rule:str,description:str,weight:float=1.0):
        CONSTITUTION.append({"rule":rule,"description":description,"weight":weight})
        logger.info(f"[ConstitutionalAI] Added rule: {rule}")
    def get_constitution(self)->List[Dict]:return list(CONSTITUTION)
