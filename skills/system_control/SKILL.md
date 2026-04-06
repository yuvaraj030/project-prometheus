---
name: system_control
description: Run shell commands, manage processes, and control applications
tools:
  - run_shell
  - list_processes
  - open_application
---

# System Control Skill

You can run shell commands, manage processes, and launch applications on the user's computer.

## When to Use
- User asks to run a command or script
- User wants to open an application
- User asks about system status (CPU, memory, disk)
- User wants to kill a process or manage services

## Tools Available

### run_shell
Execute a shell command and return the output.
- **command** (string, required): The command to execute
- **timeout** (integer, optional): Max seconds to wait (default: 30)
- Returns: stdout, stderr, and exit code

### list_processes
List running processes on the system.
- **filter** (string, optional): Filter by process name
- Returns: List of processes with PID, name, CPU%, and memory usage

### open_application
Launch an application by name.
- **name** (string, required): Application name (e.g., "chrome", "notepad", "vscode")
- Returns: Confirmation with PID

## Safety Rules
1. NEVER run destructive commands without explicit user confirmation:
   - `rm -rf`, `format`, `del /s /q`, `shutdown`, `mkfs`
2. Always show the command before executing it
3. Set reasonable timeouts to prevent hanging
4. Report errors clearly with suggestions for fixing them

## Instructions
1. Interpret the user's intent and translate to the correct command
2. Use the appropriate shell for the OS (PowerShell on Windows, bash on Linux/Mac)
3. For long-running commands, warn the user about the timeout
4. Summarize command output — don't dump raw terminal text
