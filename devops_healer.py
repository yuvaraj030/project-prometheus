"""
DevOps Healer
A Windows-specific background guardian that monitors critical processes and event logs.
It automatically attempts to restart crashed services or generate PowerShell fix scripts.
"""

import psutil
import subprocess
import time
import logging
import asyncio
from typing import List, Dict

class DevOpsHealer:
    def __init__(self, llm_provider, database=None):
        self.llm = llm_provider
        self.db = database
        self.logger = logging.getLogger("DevOpsHealer")
        # Example of critical services we want to monitor
        self.critical_services = ["nginx.exe", "mysqld.exe", "redis-server.exe", "python.exe"]
        self.is_active = True
        self.last_check = 0

    def get_crashed_services(self) -> List[str]:
        """Check if any critical services are not in the process list."""
        running = set()
        for proc in psutil.process_iter(['name']):
            try:
                running.add(proc.info['name'].lower())
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        crashed = []
        for service in self.critical_services:
            if service not in running:
                crashed.append(service)
                
        # In a real environment, we'd only flag if they were *supposed* to be running
        # For simulation, we'll return empty if not running, except when explicitly triggered
        return crashed
        
    def get_recent_windows_errors(self, minutes: int = 15) -> str:
        """Fetch recent Application or System errors from Windows Event Viewer."""
        # This requires PowerShell
        script = f"""
        Get-EventLog -LogName Application -EntryType Error,Warning -Newest 5 | 
        Where-Object {{$_.TimeGenerated -gt (Get-Date).AddMinutes(-{minutes})}} | 
        Select-Object Source, EntryType, Message | ConvertTo-Json
        """
        try:
            result = subprocess.run(["powershell", "-Command", script], capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return "No recent errors found."
        except Exception as e:
            self.logger.error(f"Failed to fetch event logs: {e}")
            return str(e)

    def analyze_and_patch(self, error_log: str, service_name: str) -> str:
        """Use LLM to analyze the crash dump/error log and generate a PowerShell fix."""
        prompt = (
            f"You are a Senior Windows DevOps Engineer. A critical service '{service_name}' has crashed or reported an error.\n\n"
            f"Recent Event Log / Error Data:\n{error_log}\n\n"
            f"Provide a short root-cause analysis, and write a single, safe PowerShell command to attempt to restart "
            f"the service, clear locks, or fix the immediate issue. Return the PowerShell command in a ```powershell codeblock."
        )
        
        response = self.llm.call(prompt, max_tokens=500)
        self.logger.info(f"LLM Analysis for {service_name}:\n{response}")
        
        # Extract PowerShell script
        ps_script = None
        response_lower = response.lower()
        if "```powershell" in response_lower:
            try:
                # Find original case by getting index from lower
                start_idx = response_lower.find("```powershell") + len("```powershell")
                end_idx = response_lower.find("```", start_idx)
                if end_idx != -1:
                    ps_script = response[start_idx:end_idx].strip()
            except IndexError:
                pass
        
        return ps_script

    async def run_healing_cycle(self):
        """Main loop called by agent_loops.py to run periodic health checks."""
        if not self.is_active:
            return
            
        now = time.time()
        if now - self.last_check < 300: # Every 5 minutes
            return
            
        self.last_check = now
        self.logger.info("🛡️ DevOps Healer running system checks...")
        
        # 1. Check Event Viewer logs
        logs = await asyncio.to_thread(self.get_recent_windows_errors)
        
        if logs != "No recent errors found." and len(logs) > 20:
            self.logger.warning(f"Recent Windows Errors detected. Analyzing...")
            # For Phase 7, we'll simulate analyzing a generic failed service
            script = await asyncio.to_thread(self.analyze_and_patch, logs, "GenericSystemFailure")
            
            if script:
                self.logger.warning(f"Generated Healing Script (Simulated Execution):\n{script}")
                if self.db:
                   self.db.audit(0, "devops_heal", f"Generated patch for Windows errors. Script length: {len(script)}")
        else:
            self.logger.info("System healthy. No critical application errors in last 15 minutes.")
