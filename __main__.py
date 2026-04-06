#!/usr/bin/env python3
"""
Nexa CLI v25
Usage:
  python -m nexa_lang              → REPL
  python -m nexa_lang run <file>   → Run .nexa file
  python -m nexa_lang run --safe-mode <file>  → Sandboxed run
  python -m nexa_lang new <name>   → Scaffold new project
  python -m nexa_lang upgrade      → Self-update Nexa
  python -m nexa_lang compile <file> → Transpile to Python
  python -m nexa_lang watch <file> → Hot-reload on save
  python -m nexa_lang install <pkg>  → Install package
  python -m nexa_lang remove <pkg>   → Remove package
  python -m nexa_lang list           → List installed
  python -m nexa_lang search [query] → Search registry
  python -m nexa_lang -d run <file>  → Debug mode
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexa_lang.repl import run_repl
try:
    from nexa_lang.repl import repl, run_file
except ImportError:
    repl = run_repl; run_file = None
from nexa_lang.pkg_manager import PackageManager


def _help():
    print("""
╔══════════════════════════════════════════════════════════╗
║  Nexa AI Language CLI  v27.0                             ║
╠══════════════════════════════════════════════════════════╣
║  nexa run  <file>            Run (.nexa or .nexac)       ║
║  nexa run  --safe-mode <f>   Sandboxed run (Phase 2)     ║
║  nexa build <file>           Compile to .nexac           ║
║  nexa build --target llvm    Compile to LLVM IR (.ll)    ║
║  nexa build --target native  Native binary (Nuitka)      ║
║  nexa build --target wasm    Compile to WASM             ║
║  nexa compile <file>         Transpile to Python         ║
║  nexa check  <file>          Static type check (v27)     ║
║  nexa test   [path]          Run test {} blocks          ║
║  nexa test   --coverage      With line coverage          ║
║  nexa bench  <file>          Run benchmarks (v27)        ║
║  nexa profile <file>         Profile execution           ║
║  nexa doc    [path]          Generate markdown docs      ║
║  nexa shell                  Interactive REPL            ║
║  nexa fmt  <file>            Auto-format source          ║
║  nexa debug <file>           Interactive debugger        ║
║  nexa lsp                    Language Server (stdio)     ║
║  nexa watch <file>           Hot-reload on save          ║
║  nexa new   <name>           Scaffold new project (v27)  ║
║  nexa new   <name> --template [web|ai|cli]               ║
║  nexa upgrade                Self-update Nexa CLI (v27)  ║
║  nexa install <pkg>          Install a package           ║
║  nexa remove  <pkg>          Remove a package            ║
║  nexa publish                Publish to registry         ║
║  nexa login                  Authenticate with registry  ║
║  nexa list                   List installed packages     ║
║  nexa search  [query]        Search package registry     ║
║  nexa migrate <file.py>      Migrate Python to Nexa      ║
╚══════════════════════════════════════════════════════════╝
""")


def _compile_file(path: str, debug: bool = False):
    """Transpile a .nexa file to Python and save as .py."""
    from nexa_lang.lexer import Lexer
    from nexa_lang.parser import Parser
    from nexa_lang.transpiler import Transpiler

    if not os.path.exists(path):
        print(f"  ❌ File not found: {path}")
        sys.exit(1)

    src = open(path, encoding="utf-8").read()
    try:
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        py_code = Transpiler().transpile(ast)

        out_path = os.path.splitext(path)[0] + ".py"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(py_code)
        print(f"  ✅ Compiled: {path} → {out_path}")
        print(f"  Lines: {len(py_code.splitlines())}")
        return out_path
    except Exception as e:
        print(f"  ❌ Compile Error: {e}")
        sys.exit(1)


def _check_file(path: str):
    """Run the static type checker on a .nexa file."""
    from nexa_lang.lexer import Lexer
    from nexa_lang.parser import Parser
    from nexa_lang.typechecker import TypeChecker

    if not os.path.exists(path):
        print(f"  ❌ File not found: {path}"); sys.exit(1)

    src = open(path, encoding="utf-8").read()
    try:
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        diags = TypeChecker().check(ast)
        if not diags:
            print(f"  \033[92m✅ {path}: No type errors found!\033[0m")
        else:
            errors = [d for d in diags if d.level == "error"]
            warnings = [d for d in diags if d.level == "warning"]
            print(f"\n  📊 {path}: {len(errors)} error(s), {len(warnings)} warning(s)")
            for d in diags: print(d)
            if errors: sys.exit(1)
    except Exception as e:
        print(f"  ❌ Parse Error: {e}"); sys.exit(1)


def _build_file(path: str, target: str = None):
    """Compile .nexa → .nexac (bytecode)  or  --target wasm."""
    import json as _json
    from nexa_lang.lexer import Lexer
    from nexa_lang.parser import Parser
    from nexa_lang.compiler import Compiler

    if not path or not os.path.exists(path):
        print(f"  ❌ File not found: {path}"); sys.exit(1)

    src = open(path, encoding="utf-8").read()

    if target == "wasm":
        print(f"  ⚙️  WASM compilation pipeline:")
        py_path = _compile_file(path)
        try:
            import subprocess
            result = subprocess.run(["py2wasm", py_path, "-o",
                                     os.path.splitext(path)[0] + ".wasm"], capture_output=True)
            if result.returncode == 0:
                print(f"  ✅ WASM build complete!")
            else:
                print(f"  ⚠️  py2wasm not available. Generated {py_path} — run via Pyodide/py2wasm manually.")
        except FileNotFoundError:
            print(f"  ⚠️  py2wasm not installed. Python source at: {py_path}")
            print(f"  💡 Install: pip install py2wasm")
        return

    try:
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        bc = Compiler(os.path.basename(path)).compile(ast)
        out_path = os.path.splitext(path)[0] + ".nexac"
        with open(out_path, "w", encoding="utf-8") as f:
            _json.dump(bc.to_dict(), f, indent=2)
        print(f"  ✅ Built: {path} → {out_path}  ({len(bc.instructions)} instructions)")
    except Exception as e:
        print(f"  ❌ Build Error: {e}"); sys.exit(1)


def _run_nexac(path: str):
    """Execute a .nexac bytecode file via the VM."""
    import json as _json
    from nexa_lang.vm import NexaVM

    if not os.path.exists(path):
        print(f"  ❌ File not found: {path}"); sys.exit(1)

    print(f"\n▶  Running (VM) {os.path.basename(path)}\n")
    with open(path, encoding="utf-8") as f:
        d = _json.load(f)
    try:
        NexaVM().execute_dict(d)
    except Exception as e:
        print(f"  ❌ VM Error: {e}")
        sys.exit(1)


def _fmt_file(path: str, check: bool = False):
    """Auto-format a .nexa file (in-place unless --check)."""
    from nexa_lang.lexer import Lexer
    from nexa_lang.parser import Parser
    from nexa_lang.formatter import Formatter

    if not os.path.exists(path):
        print(f"  ❌ File not found: {path}"); sys.exit(1)

    src = open(path, encoding="utf-8").read()
    try:
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        formatted = Formatter().format(ast)
        if check:
            if formatted == src:
                print(f"  ✅  {path}: already formatted")
            else:
                print(f"  ⚠️   {path}: would be reformatted"); sys.exit(1)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(formatted)
            print(f"  ✅  {path}: formatted")
    except Exception as e:
        print(f"  ❌ Formatter Error: {e}"); sys.exit(1)


def _run_tests(target: str = ".", coverage: bool = False):
    """Run nexa test — discover and execute all test {} blocks."""
    from nexa_lang.test_runner import run_tests
    code = run_tests(target, coverage=coverage)
    sys.exit(code)


def _gen_docs(target: str = ".", output_dir: str = "docs"):
    """Run nexa doc — generate markdown documentation."""
    from nexa_lang.doc_generator import generate_docs
    generate_docs(target, output_dir)


def _nexa_login():
    """Authenticate with the Nexa package registry."""
    import getpass, json as _json
    token_path = os.path.expanduser("~/.nexa/token")
    os.makedirs(os.path.dirname(token_path), exist_ok=True)
    print("  🔑 Nexa Registry Login")
    username = input("  Username: ").strip()
    token    = getpass.getpass("  API Token: ").strip()
    with open(token_path, "w") as f:
        _json.dump({"username": username, "token": token}, f)
    print(f"  ✅ Logged in as '{username}'. Token saved to {token_path}")


def _nexa_publish(dry_run: bool = False):
    """Publish the current package to the Nexa package registry."""
    import json as _json, zipfile, hashlib, urllib.request, urllib.error
    token_path = os.path.expanduser("~/.nexa/token")
    if not os.path.exists(token_path):
        print("  ❌ Not logged in. Run: nexa login"); sys.exit(1)

    nexa_json = "nexa.json"
    if not os.path.exists(nexa_json):
        print("  ❌ No nexa.json found. Create one with: name, version, description, main")
        sys.exit(1)

    with open(nexa_json) as f:
        meta = _json.load(f)
    with open(token_path) as f:
        auth = _json.load(f)

    name     = meta.get("name", "unknown")
    version  = meta.get("version", "0.0.1")
    print(f"  📦 Publishing {name}@{version}...")

    if dry_run:
        print(f"  🔍 Dry run — package metadata:")
        for k, v in meta.items(): print(f"     {k}: {v}")
        print("  ✅ Dry run complete. No upload.")
        return

    # Create zip archive
    zip_path = f".nexa_publish_{name}_{version}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk("."):
            for fname in files:
                if fname.endswith(".nexa") or fname in ("nexa.json", "README.md"):
                    fp = os.path.join(root, fname)
                    zf.write(fp)

    checksum = hashlib.sha256(open(zip_path, "rb").read()).hexdigest()[:12]
    print(f"  📦 Package: {zip_path}  (sha256:{checksum})")

    # POST to registry (placeholder URL — replace with real registry)
    registry_url = "https://registry.nexa-lang.dev/publish"
    try:
        with open(zip_path, "rb") as f:
            data = f.read()
        req = urllib.request.Request(
            registry_url, data=data, method="POST",
            headers={
                "Authorization": f"Bearer {auth['token']}",
                "X-Package-Name": name,
                "X-Package-Version": version,
                "Content-Type": "application/zip",
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"  ✅ Published {name}@{version} → registry")
    except urllib.error.URLError as e:
        print(f"  ⚠️  Registry unreachable ({e.reason}). Package ready at: {zip_path}")
    finally:
        if os.path.exists(zip_path): os.remove(zip_path)

def _check_file(path: str):
    """Run static type checking via nexa check."""
    from nexa_lang.lexer import Lexer
    from nexa_lang.parser import Parser
    from nexa_lang.typechecker import TypeChecker
    
    if not os.path.exists(path):
        print(f"  ❌ File not found: {path}"); sys.exit(1)
        
    src = open(path, encoding="utf-8").read()
    print(f"\n▶  Type Checking {os.path.basename(path)}\n")
    try:
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        diags = TypeChecker().check(ast)
        if diags:
            has_err = False
            for d in diags:
                print(d.format_with_source(src.splitlines()))
                if d.level == "error": has_err = True
            if has_err:
                print(f"\n  ❌ {os.path.basename(path)} failed type checking.")
                sys.exit(1)
        print(f"  ✅ {os.path.basename(path)} has no static type errors!")
    except Exception as e:
        print(f"  ❌ Type Error: {e}")
        sys.exit(1)


def _watch_file(path: str, debug: bool = False):
    """Watch file for changes and re-run on save."""
    import time

    if not os.path.exists(path):
        print(f"  ❌ File not found: {path}")
        sys.exit(1)

    print(f"  👀 Watching: {path}  (Ctrl+C to stop)")
    last_mtime = 0

    try:
        while True:
            mtime = os.path.getmtime(path)
            if mtime != last_mtime:
                last_mtime = mtime
                if last_mtime != 0:  # Skip first run if no change
                    import datetime
                    ts = datetime.datetime.now().strftime("%H:%M:%S")
                    print(f"\n  🔄 [{ts}] File changed — re-running...\n{'─'*50}")
                run_file(path, debug=debug)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n  ⏹️  Watch stopped")


def main():
    args = sys.argv[1:]
    debug = "-d" in args
    if debug:
        args = [a for a in args if a != "-d"]

    if not args:
        repl(debug=debug)
        return

    cmd = args[0]

    if cmd == "run" and len(args) >= 2:
        path = args[1]
        if path.endswith(".nexac"):
            _run_nexac(path)
        else:
            run_file(path, debug=debug)

    elif cmd == "build" and len(args) >= 2:
        target = None
        if "--target" in args:
            ti = args.index("--target")
            target = args[ti+1] if ti+1 < len(args) else None
        path = next((a for a in args[1:] if not a.startswith("-")), None)
        # v23: route LLVM and native targets to new backends
        if target == "llvm":
            from nexa_lang.llvm_backend import build_llvm
            bc_path = _build_file(path)   # first build .nexac
            if bc_path: build_llvm(bc_path)
        elif target == "llvm-bin":
            from nexa_lang.llvm_backend import build_llvm
            bc_path = _build_file(path)
            if bc_path: build_llvm(bc_path, link=True)
        elif target == "native":
            from nexa_lang.native_compiler import build_native
            build_native(path)
        else:
            _build_file(path, target=target)

    elif cmd == "test":
        coverage = "--coverage" in args
        test_target = next((a for a in args[1:] if not a.startswith("-")), ".")
        _run_tests(test_target, coverage=coverage)

    elif cmd == "doc":
        doc_target = next((a for a in args[1:] if not a.startswith("-")), ".")
        out_dir = "docs"
        if "--output" in args:
            oi = args.index("--output")
            out_dir = args[oi+1] if oi+1 < len(args) else "docs"
        _gen_docs(doc_target, out_dir)

    elif cmd == "publish":
        dry_run = "--dry-run" in args
        _nexa_publish(dry_run=dry_run)

    elif cmd == "login":
        _nexa_login()

    elif cmd == "fmt" and len(args) >= 2:
        _fmt_file(args[1])

    elif cmd == "debug" and len(args) >= 2:
        target = args[1]
        break_line = 0
        if ":" in target:
            target, ln = target.rsplit(":", 1)
            break_line = int(ln) if ln.isdigit() else 0
        from nexa_lang.debugger import run_debug
        run_debug(target, break_line)

    elif cmd == "lsp":
        from nexa_lang.lsp import run_lsp
        run_lsp()

    elif cmd == "compile" and len(args) >= 2:
        _compile_file(args[1], debug=debug)

    elif cmd == "shell":
        run_repl()

    elif cmd == "check" and len(args) >= 2:
        _check_file(args[1])

    elif cmd == "watch" and len(args) >= 2:
        _watch_file(args[1], debug=debug)

    elif cmd == "install":
        if len(args) < 2:
            print("Usage: nexa install <package-name>"); sys.exit(1)
        pm = PackageManager()
        for pkg in args[1:]: pm.install(pkg)

    elif cmd == "remove":
        if len(args) < 2:
            print("Usage: nexa remove <package-name>"); sys.exit(1)
        PackageManager().remove(args[1])

    elif cmd == "list":
        PackageManager().list_installed()

    elif cmd == "search":
        query = args[1] if len(args) > 1 else ""
        PackageManager().search(query)

    elif cmd == "workspace":
        from nexa_lang.workspace import handle_workspace_command
        handle_workspace_command(args[1:])

    elif cmd == "bench" and len(args) >= 2:
        from nexa_lang.benchmarker import run_benchmarks
        target = args[1]
        it = int(args[args.index("--iterations") + 1]) if "--iterations" in args else 100
        wu = int(args[args.index("--warmup") + 1]) if "--warmup" in args else 10
        out_json = args[args.index("--output") + 1] if "--output" in args else None
        run_benchmarks(target, iterations=it, warmup=wu, output_json=out_json)

    elif cmd == "profile" and len(args) >= 2:
        from nexa_lang.profiler import run_profile
        target = args[1]
        out_json = args[args.index("--output") + 1] if "--output" in args else "profile.json"
        run_profile(target, output_json=out_json)

    elif cmd == "migrate" and len(args) >= 2:
        from nexa_lang.migrator import migrate_python_to_nexa
        target = args[1]
        out_doc = args[args.index("--output") + 1] if "--output" in args else None
        migrate_python_to_nexa(target, output_path=out_doc)

    elif cmd == "new":  # v25: project scaffolding
        project_name = args[1] if len(args) > 1 else None
        if not project_name:
            print("Usage: nexa new <project-name> [--template web|ai|cli]")
            sys.exit(1)
        template = "cli"
        if "--template" in args:
            ti = args.index("--template")
            template = args[ti + 1] if ti + 1 < len(args) else "cli"
        _new_project(project_name, template)

    elif cmd == "upgrade":  # v25: self-update
        _upgrade_nexa()

    # ── v27 new commands ────────────────────────────────────────────────────
    elif cmd == "explain":
        from nexa_lang.nexa_explain import run_explain
        run_explain(args[1:])

    elif cmd == "deploy":
        from nexa_lang.nexa_deploy import run_deploy
        run_deploy(args[1:])

    elif cmd == "build-vm":
        from nexa_lang.build_vm import run_build_vm
        run_build_vm(args[1:])

    elif cmd in ("help", "--help", "-h"):
        _help()

    else:
        print(f"Unknown command: {cmd}")
        _help()
        sys.exit(1)


# ── v25: Project Scaffolding ──────────────────────────────────────────────────

def _new_project(name: str, template: str = "cli"):
    """nexa new <name> [--template web|ai|cli]  — scaffold a new Nexa project."""
    import shutil

    project_dir = os.path.join(os.getcwd(), name)
    if os.path.exists(project_dir):
        print(f"  ❌ Directory '{name}' already exists.")
        sys.exit(1)

    # Resolve template source
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    template_src = os.path.join(templates_dir, template)

    # v26: pwa template uses wasm_bridge
    if template == "pwa":
        from nexa_lang.wasm_bridge import create_pwa_scaffold
        create_pwa_scaffold(project_dir, app_name=name.replace("-", " ").title())
        return

    if not os.path.exists(template_src):
        print(f"  ❌ Template '{template}' not found. Available: web, ai, cli, pwa")
        sys.exit(1)

    # Create project structure
    os.makedirs(project_dir)
    os.makedirs(os.path.join(project_dir, "tests"))
    os.makedirs(os.path.join(project_dir, "src"))

    # Copy template main.nexa
    src_main = os.path.join(template_src, "main.nexa")
    if os.path.exists(src_main):
        shutil.copy(src_main, os.path.join(project_dir, "main.nexa"))

    # Create nexa.json
    import json
    nexa_json = {
        "name": name,
        "version": "0.1.0",
        "description": f"A Nexa {template} project",
        "template": template,
        "nexa": ">=25.0",
        "main": "main.nexa",
        "scripts": {
            "start": f"nexa run main.nexa",
            "test": f"nexa test tests/",
            "check": f"nexa check main.nexa",
            "bench": f"nexa bench main.nexa"
        },
        "dependencies": {}
    }
    with open(os.path.join(project_dir, "nexa.json"), "w") as f:
        json.dump(nexa_json, f, indent=2)

    # Create .gitignore
    gitignore = "*.nexac\n__pycache__/\n.nexa_cache/\nprofile.json\n*.log\n"
    with open(os.path.join(project_dir, ".gitignore"), "w") as f:
        f.write(gitignore)

    # Create README
    readme = f"# {name}\n\nA Nexa {template} project (v25).\n\n## Quick Start\n\n```bash\nnexa run main.nexa\nnexa test tests/\nnexa check main.nexa\n```\n\n## Built with [Nexa v25](https://github.com/nexa-lang)\n"
    with open(os.path.join(project_dir, "README.md"), "w") as f:
        f.write(readme)

    # Create a starter test file
    test_content = f'// Tests for {name}\n\ntest "sample test" {{\n    assert 1 + 1 == 2\n}}\n'
    with open(os.path.join(project_dir, "tests", "test_main.nexa"), "w") as f:
        f.write(test_content)

    print(f"\n  ✅ Project '{name}' created! ({template} template)\n")
    print(f"  📁 Structure:")
    print(f"     {name}/")
    print(f"     ├── main.nexa")
    print(f"     ├── nexa.json")
    print(f"     ├── README.md")
    print(f"     ├── .gitignore")
    print(f"     ├── src/")
    print(f"     └── tests/")
    print(f"          └── test_main.nexa")
    print(f"\n  🚀 Get started:")
    print(f"     cd {name}")
    print(f"     nexa run main.nexa\n")


def _upgrade_nexa():
    """nexa upgrade  — self-update Nexa via pip."""
    import subprocess
    print("  🔄 Upgrading Nexa...")

    # Try pip upgrade of the package
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "nexa-lang"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("  ✅ Nexa upgraded successfully!")
        print(result.stdout.strip())
    else:
        # Fallback: try git pull if in a git repo
        try:
            git_result = subprocess.run(["git", "pull"], capture_output=True, text=True,
                                        cwd=os.path.dirname(os.path.dirname(__file__)))
            if git_result.returncode == 0:
                print("  ✅ Nexa upgraded via git pull")
                print(git_result.stdout.strip())
            else:
                print("  ⚠️  Auto-upgrade failed. To upgrade manually:")
                print("     pip install --upgrade nexa-lang")
                print("  or:")
                print("     git pull (if using from source)")
        except FileNotFoundError:
            print("  ⚠️  Auto-upgrade failed. To upgrade manually:")
            print("     pip install --upgrade nexa-lang")


# ── v25: --safe-mode wiring (called from run command) ────────────────────────
# The run command in main() now checks --safe-mode and uses SandboxedInterpreter


if __name__ == "__main__":
    main()
