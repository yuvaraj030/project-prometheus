
import sys
import os
import asyncio
import json
from unittest.mock import MagicMock, patch
from datetime import datetime

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mission_control import MissionControl

async def test_mission_control():
    print("[TEST] Verifying Mission Control Autonomy...")
    
    # Mock dependencies
    mock_db = MagicMock()
    mock_llm = MagicMock()
    mock_swarm = MagicMock()
    
    mc = MissionControl(mock_db, mock_llm, mock_swarm)
    
    tenant_id = 1
    title = "Deploy to Mars"
    objective = "Establish a base on Mars using AI robots."
    
    # 1. Test Create Mission
    print("  [1/4] Testing mission creation...", end="", flush=True)
    mock_db.add_mission.return_value = 101
    mid = mc.create_mission(tenant_id, title, objective)
    
    if mid == 101:
        mock_db.add_mission.assert_called_once()
        print(" [PASS]")
    else:
        print(" [FAIL] Wrong ID returned.")
        return

    # 2. Test Sync with Swarms (Spawn)
    print("  [2/4] Testing swarm spawning...", end="", flush=True)
    mock_db.get_active_missions.return_value = [
        {"id": 101, "title": title, "objective": objective, "status": "active", "swarm_id": None}
    ]
    mock_swarm.spawn_swarm.return_value = "swarm_mars_1"
    
    mc.sync_with_swarms(tenant_id)
    
    mock_swarm.spawn_swarm.assert_called_with(objective)
    mock_db.update_mission.assert_called_with(tenant_id, 101, swarm_id="swarm_mars_1")
    print(" [PASS]")

    # 3. Test Sync with Swarms (Completion)
    print("  [3/4] Testing swarm completion...", end="", flush=True)
    mock_db.get_active_missions.return_value = [
        {"id": 101, "title": title, "objective": objective, "status": "active", "swarm_id": "swarm_mars_1", "progress": 10}
    ]
    mock_db.get_mission.return_value = mock_db.get_active_missions.return_value[0]
    mock_db.get_mission.return_value["metadata"] = json.dumps({"logs": []})
    
    mock_swarm.check_status.return_value = "completed"
    mock_swarm.get_final_report.return_value = "Base established successfully."
    
    # Mock LLM analysis of report
    mock_llm.call.return_value = json.dumps({
        "completed": True,
        "progress_increase": 90,
        "summary": "Mars base is operational."
    })
    
    mc.sync_with_swarms(tenant_id)
    
    # Check if update_mission was called with status=completed and progress=100
    # The last call to update_mission in _process_swarm_report should be:
    # self.db.update_mission(tid, mid, progress=100, status="completed", ...)
    
    called_args = mock_db.update_mission.call_args[1]
    if called_args.get("status") == "completed" and called_args.get("progress") == 100:
        print(" [PASS]")
    else:
        print(f" [FAIL] Final status: {called_args.get('status')}, Progress: {called_args.get('progress')}")

    # 4. Test Sync All Tenants
    print("  [4/4] Testing multi-tenant sync...", end="", flush=True)
    mock_db.conn.execute.return_value.fetchall.return_value = [{"id": 1}, {"id": 2}]
    
    with patch.object(mc, 'sync_with_swarms') as mock_sync:
        mc.sync_all_tenants()
        if mock_sync.call_count == 2:
            print(" [PASS]")
        else:
            print(f" [FAIL] Sync called {mock_sync.call_count} times.")

if __name__ == "__main__":
    asyncio.run(test_mission_control())
