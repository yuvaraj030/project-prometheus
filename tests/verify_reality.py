
import sys
import asyncio
from reality_bridge import RealityBridge
from ethical_singularity import EthicalSingularity

class MockDB:
    def audit(self, user_id, event_type, details):
        print(f"[AUDIT] {event_type}: {details}")

def test_reality():
    print("[TEST] Testing Reality Bridge...")
    
    # 1. Setup
    db = MockDB()
    reality = RealityBridge(db)
    ethics = EthicalSingularity()
    reality.set_ethical_core(ethics)
    
    # 2. Scan
    devices = reality.scan_network()
    assert len(devices) > 0, "Scan failed to find devices"
    print(f"[PASS] Scan found {len(devices)} devices")
    
    target_id = devices[0]["id"]
    
    # 3. Safe Control
    print(f"[ACTION] Controlling {target_id} -> ON")
    res = reality.control_device(target_id, "on")
    assert res["status"] in ["executed", "mqtt_sent", "plc_executed"], f"Control failed: {res}"
    print("[PASS] Safe control executed")

    # 4. Unsafe Control (Power Limit)
    print(f"[ACTION] Controlling {target_id} -> OVERDRIVE")
    res_unsafe = reality.control_device(target_id, "overdrive")
    assert res_unsafe["status"] == "blocked", "Safety limit failed"
    assert res_unsafe["reason"] == "safety_power_limit", f"Wrong reason: {res_unsafe}"
    print("[PASS] Safety limit blocked unsafe action")

if __name__ == "__main__":
    test_reality()
