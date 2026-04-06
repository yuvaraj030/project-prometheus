class Web3Wallet:
    def __init__(self, llm_provider=None):
        self.treasury_balance = 5000.0
    def pay_bounty(self, a, amt): return True
    def get_status(self): return 'Wallet'
    def get_dao_proposals(self): return []
    def propose_vote(self, t, o, b): return '0x0'
    def cast_vote(self, p, v, a): return 'Vote'
    def execute_proposal(self, p): return 'OK'
    def audit_contract(self, c): return 'OK'
    def deploy_contract(self, n, a, c=''): return 'OK'
    # --- Sovereignty / Phase 14 stubs ---
    def autonomous_collection(self, billing=None):
        """Auto-collect revenue. Stub — no real chain connected."""
        return {"collected": 0.0, "status": "simulation"}
    def automated_expense_payment(self, amount, label=""):
        """Auto-pay operating cost. Stub."""
        self.treasury_balance = max(0.0, self.treasury_balance - amount)
        return {"paid": amount, "label": label, "balance": self.treasury_balance}
    def estimate_autonomy_days(self, burn_rate_per_day: float) -> float:
        """Estimate how many days the wallet can sustain the agent."""
        if burn_rate_per_day <= 0:
            return float("inf")
        return round(self.treasury_balance / burn_rate_per_day, 1)
