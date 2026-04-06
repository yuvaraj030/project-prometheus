
import sys
import subprocess
import time
import os

def test_avatar():
    print("[TEST] Testing Digital Avatar IPC...")
    
    # 1. Launch Avatar
    try:
        process = subprocess.Popen(
            [sys.executable, "digital_avatar.py"],
            stdin=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        print("[PASS] Avatar process launched")
    except Exception as e:
        print(f"[FAIL] launch failed: {e}")
        return

    time.sleep(2) # Allow GUI to init

    # 2. Send State Commands
    try:
        print("[ACTION] Sending 'active' state...")
        process.stdin.write("active\n")
        process.stdin.flush()
        time.sleep(1)
        
        print("[ACTION] Sending 'idle' state...")
        process.stdin.write("idle\n")
        process.stdin.flush()
        time.sleep(1)
        print("[PASS] Commands sent successfully")
    except Exception as e:
        print(f"[FAIL] IPC broken: {e}")
        process.kill()
        return

    # 3. Quit
    try:
        print("[ACTION] Sending 'quit' command...")
        process.stdin.write("quit\n")
        process.stdin.flush()
        exit_code = process.wait(timeout=5)
        print(f"[PASS] Avatar exited with code {exit_code}")
    except subprocess.TimeoutExpired:
        print("[FAIL] Avatar hung on quit")
        process.kill()

if __name__ == "__main__":
    # Ensure display env is set (mock for headless if needed, but on Windows it should just work or fail gracefully)
    test_avatar()
