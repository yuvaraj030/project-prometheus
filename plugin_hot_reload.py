"""
Plugin Hot-Reload — Fix #20
============================
Watches `skills/` and `tools/` directories for file changes and
automatically reloads the SkillLoader and ToolRegistry without
requiring an agent restart.

Usage:
    hot_reload = PluginHotReload(agent)
    hot_reload.start()   # starts watchdog background thread
    hot_reload.stop()
"""

import os
import time
import logging
import threading
from typing import Optional

logger = logging.getLogger("PluginHotReload")

# Try to import watchdog for efficient file-system notifications
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logger.warning("[HotReload] 'watchdog' not installed. Run: pip install watchdog")


class _SkillReloadHandler:
    """Watchdog event handler that reloads skills/tools on filesystem changes."""

    def __init__(self, agent, cooldown: float = 2.0):
        self.agent = agent
        self.cooldown = cooldown  # debounce: wait N seconds before reloading
        self._last_reload: float = 0

    def on_any_event(self, event):
        if event.is_directory:
            return
        # Debounce: don't reload more than once every `cooldown` seconds
        now = time.time()
        if now - self._last_reload < self.cooldown:
            return
        self._last_reload = now
        path = getattr(event, "src_path", "")
        logger.info(f"[HotReload] Change detected: {path} — reloading plugins...")
        self._reload()

    def _reload(self):
        try:
            if hasattr(self.agent, "skill_loader"):
                self.agent.skill_loader.load_all()
                count = self.agent.skill_loader.enabled_count
                logger.info(f"[HotReload] Skills reloaded: {count} active")
        except Exception as e:
            logger.error(f"[HotReload] Skill reload failed: {e}")

        try:
            if hasattr(self.agent, "tool_registry"):
                self.agent.tool_registry.register_builtins()
                count = self.agent.tool_registry.count
                logger.info(f"[HotReload] Tools reloaded: {count} registered")
        except Exception as e:
            logger.error(f"[HotReload] Tool reload failed: {e}")


if WATCHDOG_AVAILABLE:
    from watchdog.events import FileSystemEventHandler

    class _WatchdogHandler(FileSystemEventHandler):
        def __init__(self, delegate):
            super().__init__()
            self.delegate = delegate

        def on_any_event(self, event):
            self.delegate.on_any_event(event)


class PluginHotReload:
    """
    Monitors skills/ and tools/ directories for changes and hot-reloads
    them into the running agent without a restart.
    """

    def __init__(self, agent, watch_dirs: list = None, poll_interval: float = 3.0):
        self.agent = agent
        base = os.getcwd()
        self.watch_dirs = watch_dirs or [
            os.path.join(base, "skills"),
            os.path.join(base, "tools"),
        ]
        self.poll_interval = poll_interval  # fallback poll interval (seconds)
        self._handler = _SkillReloadHandler(agent)
        self._observer: Optional[Observer] = None
        self._poll_thread: Optional[threading.Thread] = None
        self._running = False

    def start(self):
        """Start watching for plugin changes."""
        if self._running:
            return
        self._running = True

        if WATCHDOG_AVAILABLE:
            self._observer = Observer()
            handler = _WatchdogHandler(self._handler)
            for d in self.watch_dirs:
                if os.path.isdir(d):
                    self._observer.schedule(handler, d, recursive=True)
                    logger.info(f"[HotReload] Watching: {d}")
            self._observer.start()
            logger.info("[HotReload] Watchdog-based hot-reload active.")
        else:
            # Fallback: polling-based watcher
            self._poll_thread = threading.Thread(
                target=self._poll_loop, daemon=True
            )
            self._poll_thread.start()
            logger.info(f"[HotReload] Polling-based hot-reload active (every {self.poll_interval}s).")

    def stop(self):
        """Stop watching."""
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join()
        logger.info("[HotReload] Stopped.")

    def _poll_loop(self):
        """Simple polling fallback when watchdog is not available."""
        snapshots: dict = {}

        def snapshot():
            s = {}
            for d in self.watch_dirs:
                for root, _, files in os.walk(d):
                    for f in files:
                        fp = os.path.join(root, f)
                        try:
                            s[fp] = os.path.getmtime(fp)
                        except OSError:
                            pass
            return s

        snapshots = snapshot()
        while self._running:
            time.sleep(self.poll_interval)
            new_snap = snapshot()
            changed = {k for k, v in new_snap.items() if snapshots.get(k) != v}
            changed |= {k for k in snapshots if k not in new_snap}
            if changed:
                logger.info(f"[HotReload] {len(changed)} file(s) changed — reloading")
                self._handler._reload()
            snapshots = new_snap
