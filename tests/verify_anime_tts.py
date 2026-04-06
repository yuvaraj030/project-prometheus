
import sys
import subprocess
import time
import threading

def test_anime_tts():
    print("[TEST] Launching Digital Avatar in Anime Mode...")
    
    # 1. Launch Avatar (force anime check by ensuring files exist)
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

    # 2. Simulate TTS Lip Sync
    try:
        print("[ACTION] Simulating Speaking (Lip Sync)...")
        process.stdin.write("talking\n")
        process.stdin.flush()
        
        time.sleep(3) # Let it talk
        
        print("[ACTION] Simulating Silence (Idle)...")
        process.stdin.write("idle\n")
        process.stdin.flush()
        
        print("[PASS] Lip Sync Mock commands sent")
    except Exception as e:
        print(f"[FAIL] IPC broken: {e}")
        process.kill()
        return

    # 3. Quit
    try:
        process.stdin.write("quit\n")
        process.stdin.flush()
        process.wait(timeout=5)
        print("[PASS] Avatar exited")
    except:
        process.kill()

if __name__ == "__main__":
    test_anime_tts()
