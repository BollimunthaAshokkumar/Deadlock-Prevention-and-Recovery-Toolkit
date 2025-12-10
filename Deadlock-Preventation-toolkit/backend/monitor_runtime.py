import threading
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set

class RuntimeMonitor:
    """
    Lightweight runtime monitor demo.
    Tracks threads and lock acquire/release events.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.thread_registry: Dict[int, str] = {}
        self.lock_registry: Dict[str, Dict] = {}  # lock_name -> info
        self.events: List[str] = []
        self.wait_graph: Dict[int, Set[str]] = defaultdict(set)

    def register_thread(self, thread_name: str) -> int:
        tid = threading.get_ident()
        with self._lock:
            self.thread_registry[tid] = thread_name
            self.events.append(
                f"[{time.ctime()}] Registered thread {thread_name} (tid={tid})"
            )
        return tid

    def register_lock(self, lock_name: str) -> None:
        with self._lock:
            self.lock_registry.setdefault(lock_name, {"owner": None})
            self.events.append(
                f"[{time.ctime()}] Registered lock {lock_name}"
            )

    def pre_acquire(self, thread_id: int, lock_name: str) -> Optional[List[str]]:
        """Simulate pre-acquire: add edge thread -> lock if lock held."""
        with self._lock:
            info = self.lock_registry.get(lock_name)
            owner = info.get("owner") if info else None
            if owner and owner != thread_id:
                self.wait_graph[thread_id].add(lock_name)
                self.events.append(
                    f"[{time.ctime()}] Thread {thread_id} waiting for {lock_name} "
                    f"(held by thread {owner})"
                )
                # extremely simple mutual-wait cycle check
                for t, locks in self.wait_graph.items():
                    if t != thread_id and lock_name in locks:
                        if any(l in self.wait_graph.get(thread_id, set()) for l in locks):
                            return [f"Cycle detected involving lock {lock_name}"]
            return None

    def post_acquire(self, thread_id: int, lock_name: str) -> None:
        with self._lock:
            self.lock_registry.setdefault(lock_name, {})["owner"] = thread_id
            self.wait_graph[thread_id].discard(lock_name)
            self.events.append(
                f"[{time.ctime()}] Thread {thread_id} acquired {lock_name}"
            )

    def release(self, thread_id: int, lock_name: str) -> None:
        with self._lock:
            info = self.lock_registry.get(lock_name)
            if info and info.get("owner") == thread_id:
                info["owner"] = None
                self.events.append(
                    f"[{time.ctime()}] Thread {thread_id} released {lock_name}"
                )

    def dump_events(self) -> List[str]:
        with self._lock:
            return list(self.events)
