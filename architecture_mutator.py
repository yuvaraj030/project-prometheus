"""
architecture_mutator.py - Dynamically add/remove/rewire agent modules.
Mutations are stored in mutations.db for audit and rollback.
"""
import importlib, json, sqlite3, sys, time
from pathlib import Path
from typing import Any, Dict, List, Optional

_DB_PATH = Path(__file__).parent / "mutations.db"

class ArchitectureMutator:
    """Manages dynamic module mutations for the agent architecture."""

    def __init__(self, db_path=str(_DB_PATH)):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()
        self._registry: Dict[str, Any] = {}

    def _init_db(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS mutations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                type        TEXT NOT NULL,
                name        TEXT NOT NULL,
                spec        TEXT NOT NULL DEFAULT '{}',
                status      TEXT NOT NULL DEFAULT 'pending',
                applied_at  REAL,
                rolled_back INTEGER NOT NULL DEFAULT 0,
                notes       TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_name ON mutations(name);
        """)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Core mutation operations
    # ------------------------------------------------------------------

    def add_module(self, spec: Dict) -> int:
        """Register and dynamically import a new module.
        spec = {"name": "my_module", "path": "my_module.py", "class": "MyClass"}
        """
        name = spec["name"]
        mutation_id = self._log_mutation("add", name, spec)
        try:
            module = importlib.import_module(name)
            self._registry[name] = module
            self._update_mutation(mutation_id, "applied")
            return mutation_id
        except ImportError as e:
            self._update_mutation(mutation_id, "failed", str(e))
            raise

    def remove_module(self, name: str) -> int:
        """Unload a module from the runtime registry."""
        mutation_id = self._log_mutation("remove", name, {})
        if name in self._registry:
            del self._registry[name]
        if name in sys.modules:
            del sys.modules[name]
        self._update_mutation(mutation_id, "applied")
        return mutation_id

    def rewire(self, source: str, target: str, data_type: str = "any") -> int:
        """Record a data-flow rewiring between two modules."""
        spec = {"source": source, "target": target, "data_type": data_type}
        mutation_id = self._log_mutation("rewire", f"{source}->{target}", spec)
        self._update_mutation(mutation_id, "applied")
        return mutation_id

    def fork_and_experiment(self, mutation: Dict) -> Dict:
        """
        Fork current configuration, apply mutation speculatively,
        and return a result dict with status for the caller to evaluate.
        """
        result = {
            "mutation": mutation,
            "timestamp": time.time(),
            "status": "speculative",
            "notes": "Caller must benchmark and call commit_experiment() or rollback_experiment()",
        }
        mutation_id = self._log_mutation("experiment", mutation.get("name", "anon"), mutation)
        result["mutation_id"] = mutation_id
        return result

    def commit_experiment(self, mutation_id: int, notes: str = "") -> None:
        self._update_mutation(mutation_id, "committed", notes)

    def rollback_experiment(self, mutation_id: int, notes: str = "") -> None:
        self._conn.execute(
            "UPDATE mutations SET status='rolled_back', rolled_back=1, notes=? WHERE id=?",
            (notes, mutation_id),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def list_mutations(self, status: Optional[str] = None) -> List[Dict]:
        query = "SELECT id,type,name,spec,status,applied_at,rolled_back,notes FROM mutations"
        params: tuple = ()
        if status:
            query += " WHERE status=?"
            params = (status,)
        rows = self._conn.execute(query, params).fetchall()
        return [
            {"id":r[0],"type":r[1],"name":r[2],"spec":json.loads(r[3]),
             "status":r[4],"applied_at":r[5],"rolled_back":bool(r[6]),"notes":r[7]}
            for r in rows
        ]

    def get_registry(self) -> Dict[str, str]:
        return {k: str(v) for k, v in self._registry.items()}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _log_mutation(self, mtype, name, spec) -> int:
        cur = self._conn.execute(
            "INSERT INTO mutations (type,name,spec,applied_at) VALUES (?,?,?,?)",
            (mtype, name, json.dumps(spec), time.time()),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore

    def _update_mutation(self, mid, status, notes=""):
        self._conn.execute(
            "UPDATE mutations SET status=?, applied_at=?, notes=? WHERE id=?",
            (status, time.time(), notes, mid),
        )
        self._conn.commit()

# ---------------------------------------------------------------------------
# Module-level singleton + convenience API
# ---------------------------------------------------------------------------
_mutator: Optional[ArchitectureMutator] = None

def get_mutator() -> ArchitectureMutator:
    global _mutator
    if _mutator is None:
        _mutator = ArchitectureMutator()
    return _mutator

def add_module(spec: Dict) -> int:      return get_mutator().add_module(spec)
def remove_module(name: str) -> int:   return get_mutator().remove_module(name)
def rewire(src, tgt, dtype="any"):     return get_mutator().rewire(src, tgt, dtype)
def fork_and_experiment(m: Dict):      return get_mutator().fork_and_experiment(m)
def list_mutations(status=None):       return get_mutator().list_mutations(status)

if __name__ == "__main__":
    m = ArchitectureMutator()
    mid = m.fork_and_experiment({"name": "test_module", "param": 42})
    print("Experiment:", mid)
    m.commit_experiment(mid["mutation_id"], "benchmark passed")
    print("Mutations:", m.list_mutations())
