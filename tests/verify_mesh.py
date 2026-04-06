
import sys
import os
import time
import threading
import socket
from unittest.mock import MagicMock

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mesh_manager import MeshManager

def run_peer(agent_id, port):
    print(f"[{agent_id}] Starting on port {port}...")
    mesh = MeshManager(agent_id, port)
    mesh.logger = MagicMock() # Suppress logs or mock them
    
    # We need to manually start the sequence because .start() launches a thread
    # but we want to control the lifecycle for tests.
    # actually .start() is fine if we can stop it.
    
    mesh.start()
    return mesh

def test_mesh_discovery():
    print("[TEST] Verifying Mesh Network Discovery...")
    
    # Start Peer A
    peer_a = run_peer("Agent_A", 50005)
    time.sleep(1) # Wait for start
    
    # Start Peer B
    peer_b = run_peer("Agent_B", 50006)
    print("  [INFO] Waiting 15s for bidirectional discovery...", end="", flush=True)
    time.sleep(15) # Wait for discovery (Mesh broadcasts every 10s)
    
    # Check if A sees B
    print("  [1/3] Checking Peer Discovery...", end="", flush=True)
    peers_a = peer_a.get_active_peers()
    peers_b = peer_b.get_active_peers()
    
    if "Agent_B" in peers_a and "Agent_A" in peers_b:
        print(" [PASS] Mutual discovery successful.")
    else:
        print(f" [FAIL] Discovery incomplete. A sees: {peers_a}, B sees: {peers_b}")
        
    # Test Consensus
    print("  [2/3] Testing Consensus Proposal...", end="", flush=True)
    result = peer_a.initiate_proposal("prop_001", "Upgrade Protocol")
    
    if result["status"] == "PASSED" and result["approval_rate"] > 0.5:
        print(f" [PASS] Proposal Passed ({result['approval_rate']:.0%})")
    else:
        print(f" [FAIL] Proposal Failed: {result}")
        
    # Check gravity
    print("  [3/3] Checking Swarm Gravity...", end="", flush=True)
    best_peer = peer_a.find_strongest_attraction()
    if best_peer == "Agent_B":
         print(" [PASS] Gravity correctly identified Peer B.")
    else:
         print(f" [FAIL] Gravity calculation error. Best peer: {best_peer}")

    # Cleanup
    peer_a.running = False
    peer_b.running = False
    # Close sockets to free ports
    try: peer_a.listener_sock.close() 
    except: pass
    try: peer_b.listener_sock.close() 
    except: pass

if __name__ == "__main__":
    test_mesh_discovery()
