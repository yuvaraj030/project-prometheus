
import os
import yaml
import subprocess

def test_deployment_readiness():
    print("[TEST] Verifying Deployment Readiness...")
    errors = []

    # 1. Check Dockerfile
    if os.path.exists("Dockerfile"):
        print("  [1/4] Dockerfile found.")
        with open("Dockerfile", "r") as f:
            content = f.read()
            if "FROM python" not in content:
                errors.append("Dockerfile missing base image.")
            if "CMD" not in content:
                errors.append("Dockerfile missing CMD.")
    else:
        errors.append("Dockerfile not found.")

    # 2. Check docker-compose.yml
    if os.path.exists("docker-compose.yml"):
        print("  [2/4] docker-compose.yml found.")
        try:
            with open("docker-compose.yml", "r") as f:
                config = yaml.safe_load(f)
                if "services" not in config or "ultimate-agent" not in config["services"]:
                    errors.append("docker-compose.yml is missing 'ultimate-agent' service.")
                
                service = config["services"]["ultimate-agent"]
                if "build" not in service:
                    errors.append("docker-compose service missing 'build' context.")
        except Exception as e:
            errors.append(f"docker-compose.yml parsing error: {e}")
    else:
        errors.append("docker-compose.yml not found.")

    # 3. Check cloud_deploy.sh
    if os.path.exists("cloud_deploy.sh"):
        print("  [3/4] cloud_deploy.sh found.")
        # We don't execute it, just check for key commands
        with open("cloud_deploy.sh", "r") as f:
            content = f.read()
            if "docker compose up" not in content and "docker-compose up" not in content:
                errors.append("cloud_deploy.sh missing docker-compose launch command.")
    else:
        errors.append("cloud_deploy.sh not found.")

    # 4. Check requirements.txt
    if os.path.exists("requirements.txt"):
        print("  [4/4] requirements.txt found.")
    else:
        errors.append("requirements.txt not found.")

    if not errors:
        print("\n[PASS] Deployment infrastructure verified.")
    else:
        print("\n[FAIL] Deployment issues found:")
        for err in errors:
            print(f"  - {err}")
        exit(1)

if __name__ == "__main__":
    test_deployment_readiness()
