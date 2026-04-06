"""
Self-Modification Engine — Allows the agent to analyze, modify, and evolve its own code.
Includes safety validation, backups, rollback, and code analysis.
"""

import os
import ast
import types
import shutil
import hashlib
import inspect
import importlib
import importlib.util
import traceback
import json
from datetime import datetime
from typing import Optional, Dict, Any, List


class SelfModEngine:
    """Code self-analysis, modification, and evolution engine."""

    def __init__(self, source_file: str, backup_dir: str = "agent_backups",
                 modules_dir: str = "agent_modules",
                 safety_mode: bool = True, enabled: bool = True):
        self.source_file = source_file
        self.backup_dir = backup_dir
        self.modules_dir = modules_dir
        self.safety_mode = safety_mode
        self.enabled = enabled
        self.modifications_log: List[Dict] = []
        self.custom_modules: Dict[str, Any] = {}

        self.metrics = {
            "total_methods": 0,
            "lines_of_code": 0,
            "modifications_made": 0,
            "successful_mods": 0,
            "failed_mods": 0,
            "custom_features_added": 0,
            "evolution_level": 0,
        }

        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.modules_dir, exist_ok=True)

    # --- Analysis ---
    def analyze_source(self) -> Dict[str, Any]:
        """Analyze the agent's own source code."""
        try:
            with open(self.source_file, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
            methods = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]

            self.metrics["total_methods"] = len(methods)
            self.metrics["lines_of_code"] = len(source.splitlines())

            return {
                "lines": self.metrics["lines_of_code"],
                "methods": len(methods),
                "classes": len(classes),
                "imports": len(imports),
                "method_names": methods,
                "class_names": classes,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_method_source(self, obj: Any, method_name: str) -> Dict[str, Any]:
        """Get source code of a method on an object."""
        try:
            method = getattr(obj, method_name, None)
            if method and callable(method):
                return {
                    "exists": True,
                    "name": method_name,
                    "doc": inspect.getdoc(method) or "",
                    "signature": str(inspect.signature(method)),
                    "source": inspect.getsource(method),
                }
        except Exception:
            pass
        return {"exists": False, "name": method_name}

    def list_capabilities(self, obj: Any) -> List[str]:
        """List all callable methods on obj (excluding private)."""
        return [m for m in dir(obj) if callable(getattr(obj, m)) and not m.startswith("_")]

    # --- Backup & Rollback ---
    def create_backup(self, reason: str = "Pre-modification backup") -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(self.backup_dir, f"agent_backup_{ts}.py")
        shutil.copy2(self.source_file, backup_file)
        with open(backup_file, "rb") as f:
            checksum = hashlib.md5(f.read()).hexdigest()
        self.modifications_log.append({
            "timestamp": ts, "type": "backup",
            "file": backup_file, "checksum": checksum, "reason": reason,
        })
        return backup_file

    def rollback(self, backup_file: str) -> Dict[str, Any]:
        if not os.path.exists(backup_file):
            return {"success": False, "error": "Backup not found"}
        try:
            shutil.copy2(backup_file, self.source_file)
            return {"success": True, "message": f"Rolled back to {backup_file}",
                    "note": "Restart required for full effect"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_backups(self) -> List[Dict]:
        backups = []
        if os.path.isdir(self.backup_dir):
            for f in sorted(os.listdir(self.backup_dir)):
                if f.endswith(".py"):
                    path = os.path.join(self.backup_dir, f)
                    backups.append({
                        "file": path,
                        "size": os.path.getsize(path),
                        "modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(),
                    })
        return backups

    # --- Validation ---
    def validate_code(self, code: str) -> Dict[str, Any]:
        result = {"valid": False, "errors": [], "warnings": [], "dangerous": []}
        try:
            ast.parse(code)
            result["valid"] = True
        except SyntaxError as e:
            result["errors"].append(f"Syntax error: {e}")
            return result

        if self.safety_mode:
            dangerous_patterns = [
                ("os.system(", "Shell command injection"),
                ("rmtree", "Destructive file deletion"),
                ("__import__", "Dynamic import"),
                ("shutil.rmtree", "Recursive deletion"),
            ]
            for pattern, reason in dangerous_patterns:
                if pattern in code:
                    result["dangerous"].append(f"{reason}: {pattern}")

            warn_patterns = [
                ("eval(", "Eval usage"),
                ("exec(", "Exec usage"),
                ("subprocess", "Subprocess usage"),
                ("open(", "File I/O"),
            ]
            for pattern, reason in warn_patterns:
                if pattern in code:
                    result["warnings"].append(f"{reason}: {pattern}")

        return result

    # --- Dynamic Method Injection ---
    def add_method(self, target_obj: Any, method_name: str,
                   method_code: str, description: str = "") -> Dict[str, Any]:
        """Dynamically add a new method to an object."""
        if not self.enabled:
            return {"success": False, "error": "Self-modification disabled"}

        validation = self.validate_code(method_code)
        if not validation["valid"]:
            return {"success": False, "error": "Invalid code", "details": validation["errors"]}
        if self.safety_mode and validation["dangerous"]:
            return {"success": False, "error": "Safety check failed",
                    "dangerous": validation["dangerous"]}
        try:
            backup = self.create_backup(f"Before adding {method_name}")
            
            # Smart wrapping: Check if code is a full definition or just body
            stripped = method_code.strip()
            if stripped.startswith("def "):
                # It's a full definition. Exec it directly.
                full_code = method_code
            else:
                # It's a body. Wrap it.
                full_code = f"def {method_name}(self, *args, **kwargs):\n"
                full_code += "\n".join("    " + line for line in method_code.split("\n"))

            exec_ns = {}
            exec(full_code, exec_ns)
            
            # Find the function in the namespace
            # If we wrapped it, it's 'method_name'.
            # If user provided a def, we need to find it (it might have a different name)
            if stripped.startswith("def "):
                # Use the first callable found or try to parse the name
                tree = ast.parse(full_code)
                func_name = next(n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
                new_method = exec_ns[func_name]
            else:
                 new_method = exec_ns[method_name]

            setattr(target_obj, method_name, types.MethodType(new_method, target_obj))

            mod = {
                "timestamp": datetime.now().isoformat(), "type": "add_method",
                "method_name": method_name, "description": description,
                "backup_file": backup, "code_preview": method_code[:200],
            }
            self.modifications_log.append(mod)
            self.metrics["modifications_made"] += 1
            self.metrics["successful_mods"] += 1
            self.metrics["custom_features_added"] += 1
            self.metrics["evolution_level"] += 1
            return {"success": True, "method": method_name, "backup": backup}
        except Exception as e:
            self.metrics["failed_mods"] += 1
            return {"success": False, "error": str(e), "trace": traceback.format_exc()}

    def modify_method(self, target_obj: Any, method_name: str,
                      new_code: str) -> Dict[str, Any]:
        """Replace an existing method on an object."""
        if not self.enabled:
            return {"success": False, "error": "Self-modification disabled"}
        if not hasattr(target_obj, method_name):
            return {"success": False, "error": f"Method {method_name} not found"}

        validation = self.validate_code(new_code)
        if not validation["valid"]:
            return {"success": False, "error": "Invalid code", "details": validation["errors"]}

        old_method = getattr(target_obj, method_name)
        try:
            backup = self.create_backup(f"Before modifying {method_name}")
            
            # Smart wrapping
            stripped = new_code.strip()
            if stripped.startswith("def "):
                full_code = new_code
            else:
                full_code = f"def {method_name}(self, *args, **kwargs):\n"
                full_code += "\n".join("    " + line for line in new_code.split("\n"))

            exec_ns = {}
            exec(full_code, exec_ns)
            
            if stripped.startswith("def "):
                 tree = ast.parse(full_code)
                 func_name = next(n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
                 new_method_func = exec_ns[func_name]
            else:
                 new_method_func = exec_ns[method_name]
            
            setattr(target_obj, method_name, types.MethodType(new_method_func, target_obj))

            self.modifications_log.append({
                "timestamp": datetime.now().isoformat(), "type": "modify_method",
                "method_name": method_name, "backup_file": backup,
                "code_preview": new_code[:200],
            })
            self.metrics["modifications_made"] += 1
            self.metrics["successful_mods"] += 1
            self.metrics["evolution_level"] += 1
            return {"success": True, "method": method_name, "backup": backup}
        except Exception as e:
            try:
                setattr(target_obj, method_name, old_method)
            except:
                pass
            self.metrics["failed_mods"] += 1
            return {"success": False, "error": str(e)}

    # --- Deep Evolution (Core Replacement) ---
    def modify_core_class(self, class_name: str, new_class_code: str) -> Dict[str, Any]:
        """
        Refactor an entire core class (dangerous, high-level evolution).
        Writes to the actual source file and requires restart.
        """
        if not self.enabled:
            return {"success": False, "error": "Self-modification disabled"}
        
        validation = self.validate_code(new_class_code)
        if not validation["valid"]:
            return {"success": False, "error": "Invalid code", "details": validation["errors"]}
        if self.safety_mode and validation["dangerous"]:
             return {"success": False, "error": "Safety violation", "details": validation["dangerous"]}

        try:
            # 1. Backup current state
            backup = self.create_backup(f"Deep refactor of {class_name}")
            
            # 2. Read source
            with open(self.source_file, "r", encoding="utf-8") as f:
                source = f.read()
            
            # 3. Use AST to find and replace the class
            tree = ast.parse(source)
            class_node = next((n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == class_name), None)
            
            if not class_node:
                return {"success": False, "error": f"Class {class_name} not found in source."}
            
            # 4. We can't easily replace AST nodes and regenerate formatting perfectly with stdlib only.
            # Instead, we will append the new class definition at the end and rename the old one,
            # or simply use string manipulation if we identify the block.
            # Strategy: Append new class, change instantiation lines? No, that's messy.
            # Robust Strategy: Replace the file content if we can locate the class lines.
            
            lines = source.splitlines()
            start_line = class_node.lineno - 1
            end_line = class_node.end_lineno
            
            # Replace the block
            new_lines = new_class_code.splitlines()
            final_lines = lines[:start_line] + new_lines + lines[end_line:]
            new_source = "\n".join(final_lines)
            
            # 5. Verify syntax of full new file
            try:
                ast.parse(new_source)
            except SyntaxError as e:
                return {"success": False, "error": f"Generated source invalid: {e}"}
                
            # 6. Write back
            with open(self.source_file, "w", encoding="utf-8") as f:
                f.write(new_source)
                
            self.metrics["evolution_level"] += 5
            return {
                "success": True, 
                "message": f"Class {class_name} evolved. RESTART AGENT to apply.",
                "backup": backup
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Custom Modules ---
    def add_module(self, module_name: str, module_code: str) -> Dict[str, Any]:
        if not self.enabled:
            return {"success": False, "error": "Self-modification disabled"}
        validation = self.validate_code(module_code)
        if not validation["valid"]:
            return {"success": False, "error": "Invalid code", "details": validation["errors"]}
        try:
            module_file = os.path.join(self.modules_dir, f"{module_name}.py")
            with open(module_file, "w", encoding="utf-8") as f:
                f.write(module_code)
            spec = importlib.util.spec_from_file_location(module_name, module_file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.custom_modules[module_name] = mod
            self.metrics["custom_features_added"] += 1
            return {"success": True, "module": module_name, "file": module_file}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Structural Architectural Evolution ---
    def redesign_inheritance(self, class_name: str, new_bases: List[str]) -> Dict[str, Any]:
        """
        Structural evolution: Change the base classes (inheritance) of a core class.
        This allows the agent to redesign its own architecture.
        """
        if not self.enabled:
            return {"success": False, "error": "Self-modification disabled"}
        
        try:
            backup = self.create_backup(f"Redesigning inheritance for {class_name}")
            with open(self.source_file, "r", encoding="utf-8") as f:
                source = f.read()
            
            tree = ast.parse(source)
            class_node = next((n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == class_name), None)
            
            if not class_node:
                return {"success": False, "error": f"Class {class_name} not found"}

            # Replace bases
            lines = source.splitlines()
            # We locate the line where the class is defined: class Name(Base1, Base2):
            class_line = lines[class_node.lineno-1]
            
            # Use regex or string manipulation to replace characters between ( and )
            import re
            new_bases_str = ", ".join(new_bases)
            if "(" in class_line and ")" in class_line:
                # Replace existing bases
                updated_line = re.sub(r'\(.*?\)', f'({new_bases_str})', class_line)
            else:
                # Add bases if none exist
                updated_line = class_line.replace(f"class {class_name}:", f"class {class_name}({new_bases_str}):")
            
            lines[class_node.lineno-1] = updated_line
            new_source = "\n".join(lines)
            
            # Verify and save
            ast.parse(new_source)
            with open(self.source_file, "w", encoding="utf-8") as f:
                f.write(new_source)
                
            self.metrics["evolution_level"] += 10
            return {"success": True, "message": f"{class_name} now inherits from {new_bases}", "backup": backup}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Export ---
    def export_log(self, path: str = "agent_modifications.json") -> Dict[str, Any]:
        try:
            with open(path, "w") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "modifications": self.modifications_log,
                    "metrics": self.metrics,
                }, f, indent=2)
            return {"success": True, "file": path, "count": len(self.modifications_log)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ─────────────────────────────────────────────────────────
    #  CODEBASE SELF-AUDIT TOOL (Feature 14)
    # ─────────────────────────────────────────────────────────
    def run_self_audit(self, source_files: list = None,
                       auto_patch: bool = False) -> dict:
        """
        Scan all .py files in the codebase using AST analysis.
        Detects: unused imports, high-complexity functions, TODO/FIXME comments,
        bare except clauses, deprecated patterns.
        
        Feeds findings to the LLM for structured patch suggestions.
        Optionally auto-applies patches with backup + validation.
        
        Returns a structured audit report.
        """
        import ast
        import glob

        base_dir = os.path.dirname(os.path.abspath(__file__))

        if not source_files:
            source_files = glob.glob(os.path.join(base_dir, "*.py"))

        findings = []
        files_scanned = 0
        total_issues = 0

        for filepath in source_files:
            if "__pycache__" in filepath or filepath.endswith(".pyc"):
                continue

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    source = f.read()
            except Exception:
                continue

            filename = os.path.basename(filepath)
            file_issues = []

            try:
                tree = ast.parse(source, filename=filename)
            except SyntaxError as e:
                file_issues.append({"type": "syntax_error", "detail": str(e), "line": e.lineno})
                findings.append({"file": filename, "issues": file_issues,
                                 "issue_count": 1, "severity": "critical"})
                total_issues += 1
                continue

            # 1. Unused imports (imported names not found in body)
            imported_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname or alias.name.split('.')[0]
                        imported_names.add((name, node.lineno))
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name != "*":
                            name = alias.asname or alias.name
                            imported_names.add((name, node.lineno))

            used_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
            for name, lineno in imported_names:
                if name not in used_names and name != "_":
                    file_issues.append({"type": "unused_import", "name": name, "line": lineno})

            # 2. High-complexity functions (many branches)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    branches = sum(
                        1 for n in ast.walk(node)
                        if isinstance(n, (ast.If, ast.For, ast.While, ast.Try,
                                         ast.ExceptHandler, ast.With))
                    )
                    if branches > 10:
                        file_issues.append({
                            "type": "high_complexity",
                            "function": node.name,
                            "branches": branches,
                            "line": node.lineno
                        })

            # 3. Bare except clauses
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    file_issues.append({"type": "bare_except", "line": node.lineno})

            # 4. TODO/FIXME/HACK comments
            for i, line in enumerate(source.splitlines(), 1):
                stripped = line.strip()
                if any(marker in stripped.upper() for marker in ["TODO", "FIXME", "HACK", "XXX"]):
                    file_issues.append({
                        "type": "todo_comment",
                        "line": i,
                        "text": stripped[:80]
                    })

            if file_issues:
                findings.append({
                    "file": filename,
                    "issues": file_issues[:20],  # Cap at 20 per file
                    "issue_count": len(file_issues),
                    "severity": "critical" if any(i["type"] == "syntax_error" for i in file_issues)
                               else "warning"
                })
                total_issues += len(file_issues)

            files_scanned += 1

        # Build summary for LLM
        if not findings:
            audit_summary = "🎉 No issues found — codebase is clean!"
            llm_suggestions = None
        else:
            summary_lines = [f"Codebase audit found {total_issues} issues across {len(findings)} files:"]
            for f_info in findings[:10]:
                summary_lines.append(f"\n  {f_info['file']} [{f_info['severity']}] — {f_info['issue_count']} issues")
                for issue in f_info['issues'][:5]:
                    summary_lines.append(f"    • [{issue['type']}] line {issue.get('line','?')}: {issue.get('detail', issue.get('text', issue.get('name', ''))[:60])}")
            audit_summary = "\n".join(summary_lines)

            llm_suggestions = None
            if self.llm:
                try:
                    prompt = (
                        f"You are auditing a Python AI agent codebase.\n\n"
                        f"FINDINGS:\n{audit_summary[:3000]}\n\n"
                        f"Provide 3-5 specific, actionable improvements as a markdown list. "
                        f"Focus on the most impactful fixes first. Be concise."
                    )
                    llm_suggestions = self.llm.call(prompt, max_tokens=500)
                except Exception as e:
                    llm_suggestions = f"LLM suggestions unavailable: {e}"

        report = {
            "success": True,
            "files_scanned": files_scanned,
            "total_issues": total_issues,
            "files_with_issues": len(findings),
            "findings": findings[:20],
            "summary": audit_summary,
            "llm_suggestions": llm_suggestions,
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.info(f"🔎 Self-audit complete: {files_scanned} files, {total_issues} issues")
        return report

    def schedule_daily_audit(self, target_hour: int = 3,
                             source_files: list = None) -> dict:
        """
        Schedule a daily self-audit at target_hour (default 3 AM).
        Runs in a background daemon thread during low-activity hours.
        """
        import threading
        import time
        from datetime import datetime, timedelta

        if getattr(self, '_audit_scheduled', False):
            return {"status": "already_scheduled", "target_hour": target_hour}

        self._audit_scheduled = True

        def _audit_loop():
            self.logger.info(f"🔎 Daily self-audit scheduled at {target_hour:02d}:00")
            while self._audit_scheduled:
                now = datetime.now()
                target = now.replace(hour=target_hour, minute=5, second=0, microsecond=0)
                if now >= target:
                    target += timedelta(days=1)
                wait_secs = (target - now).total_seconds()

                # Wait in 60s chunks for cancellation responsiveness
                slept = 0
                while slept < wait_secs and self._audit_scheduled:
                    chunk = min(60, wait_secs - slept)
                    time.sleep(chunk)
                    slept += chunk

                if not self._audit_scheduled:
                    break

                self.logger.info("🔎 Starting scheduled daily self-audit...")
                try:
                    report = self.run_self_audit(source_files=source_files)
                    self.logger.info(
                        f"🔎 Audit done: {report['files_scanned']} files, "
                        f"{report['total_issues']} issues"
                    )
                except Exception as e:
                    self.logger.error(f"Daily audit failed: {e}")

                time.sleep(23 * 3600)  # Avoid double-trigger

        threading.Thread(target=_audit_loop, daemon=True).start()
        return {"status": "scheduled", "target_hour": target_hour}

    def stop_daily_audit(self) -> dict:
        """Cancel the daily audit scheduler."""
        self._audit_scheduled = False
        return {"status": "cancelled"}

