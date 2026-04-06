"""
Nexa Language — Coroutine Scheduler (v23)
async/await support without Python asyncio dependency.

Design: simple cooperative multitasking via generator-based coroutines.
  - async def → returns a Task
  - await expr → yields control back to scheduler
  - Scheduler runs tasks round-robin until all complete

Usage in Nexa:
  async def fetch(url) {
      let data = await http.get(url)
      return data
  }
  let task = fetch("https://example.com")
  let result = await task
"""
from __future__ import annotations
import time
from typing import Any, Callable, Generator, List, Optional
from collections import deque


class NexaTask:
    """Represents a running async Nexa coroutine."""
    _id_counter = 0

    def __init__(self, coro, name: str = "<task>"):
        NexaTask._id_counter += 1
        self.id = NexaTask._id_counter
        self.name = name
        self._coro = coro       # generator
        self.result: Any = None
        self.error: Optional[Exception] = None
        self.done = False
        self._callbacks: List[Callable] = []

    def add_done_callback(self, fn: Callable):
        self._callbacks.append(fn)

    def _set_result(self, val):
        self.result = val
        self.done = True
        for cb in self._callbacks:
            try: cb(self)
            except Exception: pass

    def _set_error(self, err: Exception):
        self.error = err
        self.done = True

    def __repr__(self):
        status = "done" if self.done else "pending"
        return f"Task<{self.name} #{self.id} {status}>"


class EventLoop:
    """Single-threaded cooperative event loop for Nexa async/await."""

    def __init__(self):
        self._ready: deque = deque()    # tasks ready to run
        self._waiting: List = []        # (resume_time, task) sleeping tasks
        self._current: Optional[NexaTask] = None

    def create_task(self, coro, name: str = "<task>") -> NexaTask:
        """Schedule a coroutine as a task."""
        task = NexaTask(coro, name)
        self._ready.append(task)
        return task

    def run(self, main_coro=None) -> Any:
        """Run the event loop until all tasks complete."""
        if main_coro is not None:
            main_task = self.create_task(main_coro, "main")
        else:
            main_task = None

        while self._ready or self._waiting:
            # Wake sleeping tasks
            now = time.monotonic()
            due = [t for t in self._waiting if t[0] <= now]
            for wake_at, task in due:
                self._waiting.remove((wake_at, task))
                self._ready.append(task)

            if not self._ready:
                if self._waiting:
                    next_wake = min(t[0] for t in self._waiting)
                    time.sleep(max(0, next_wake - time.monotonic()))
                continue

            task = self._ready.popleft()
            self._current = task

            try:
                val = next(task._coro)
                # val may be a "yield" type
                if isinstance(val, _SleepFuture):
                    self._waiting.append((time.monotonic() + val.seconds, task))
                elif isinstance(val, NexaTask):
                    # await another task
                    if val.done:
                        self._ready.append(task)
                    else:
                        val.add_done_callback(lambda t: self._ready.append(task))
                else:
                    self._ready.append(task)  # yield None = requeue
            except StopIteration as e:
                task._set_result(e.value)
            except Exception as e:
                task._set_error(e)
                print(f"  ❌ Task '{task.name}' raised: {e}")

        self._current = None
        if main_task: return main_task.result
        return None

    def sleep(self, seconds: float):
        """Return a sleep future — use as: yield loop.sleep(1.0)"""
        return _SleepFuture(seconds)

    def current_task(self) -> Optional[NexaTask]:
        return self._current


class _SleepFuture:
    def __init__(self, seconds: float):
        self.seconds = seconds


# ── Global default loop ────────────────────────────────────────────────────────
_default_loop: Optional[EventLoop] = None


def get_event_loop() -> EventLoop:
    global _default_loop
    if _default_loop is None:
        _default_loop = EventLoop()
    return _default_loop


def run(coro) -> Any:
    """Run a single async coroutine synchronously — top-level entry."""
    loop = EventLoop()
    return loop.run(coro)


def sleep(seconds: float) -> _SleepFuture:
    """Pause for `seconds` without blocking the event loop."""
    return _SleepFuture(seconds)


# ── nexa_lang integration helpers ─────────────────────────────────────────────
def make_async_wrapper(fn):
    """
    Wrap an interpreter FunctionDef or Python callable as a coroutine.
    In Nexa: async def foo() {} → the interpreter calls this wrapper.
    """
    def wrapper(*args, **kwargs):
        result = fn(*args, **kwargs)
        yield  # one yield to mark it as a generator
        return result
    return wrapper


def await_value(val):
    """
    Handle `await expr` in interpreter:
    - If val is a NexaTask: wait synchronously until done.
    - If val is a generator/coroutine: run it to completion.
    - Otherwise: return val immediately.
    """
    if isinstance(val, NexaTask):
        loop = EventLoop()
        loop._ready.append(val)
        loop.run()
        if val.error: raise val.error
        return val.result
    if hasattr(val, '__next__') or hasattr(val, 'send'):
        # Run generator to completion
        result = None
        try:
            while True:
                next(val)
        except StopIteration as e:
            result = e.value
        return result
    return val  # plain value — await is a no-op
