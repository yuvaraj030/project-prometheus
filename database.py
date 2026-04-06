"""
Database Module — SQLite persistent storage for the Ultimate AI Agent.
Handles conversations, tasks, clients, metrics, modifications, and audit logs.
"""

import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_SUPPORT = True
except ImportError:
    POSTGRES_SUPPORT = False


class AgentDatabase:
    def __init__(self, db_path: str = "agent_database.db"):
        self.db_path = db_path
        self.db_url = os.getenv("DATABASE_URL")
        self.is_postgres = self.db_url and self.db_url.startswith("postgres")
        
        if self.is_postgres and not POSTGRES_SUPPORT:
            raise ImportError("PostgreSQL support requires 'psycopg2-binary'. Build failed.")

        if self.is_postgres:
            self.conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
            self.logger = logging.getLogger("Database_Postgres")
        else:
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.logger = logging.getLogger("Database_SQLite")
            
        self._create_tables()

    def _commit(self):
        """Commit only when there is an active SQLite transaction.
        SQLite's executescript() leaves the connection in autocommit mode;
        calling conn.commit() with no open transaction raises OperationalError."""
        if self.is_postgres:
            self.conn.commit()
        elif self.conn.in_transaction:
            self.conn.commit()

    def _create_tables(self):
        # Use SERIAL for Postgres, AUTOINCREMENT for SQLite
        id_pk = "SERIAL PRIMARY KEY" if self.is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
        ts_default = "CURRENT_TIMESTAMP"
        
        script = f"""
            CREATE TABLE IF NOT EXISTS tenants (
                id {id_pk},
                name TEXT NOT NULL,
                api_key TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'active',
                branding_json TEXT DEFAULT '{{}}',
                created_at TIMESTAMP DEFAULT {ts_default}
            );

            CREATE TABLE IF NOT EXISTS users (
                id {id_pk},
                tenant_id INTEGER NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'VIEWER',
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT {ts_default}
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id {id_pk},
                tenant_id INTEGER,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                model TEXT,
                created_at TIMESTAMP DEFAULT {ts_default}
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id {id_pk},
                tenant_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 5,
                source TEXT DEFAULT 'user',
                result TEXT,
                created_at TIMESTAMP DEFAULT {ts_default},
                completed_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS knowledge_base (
                id {id_pk},
                tenant_id INTEGER,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                source TEXT,
                created_at TIMESTAMP DEFAULT {ts_default},
                updated_at TIMESTAMP DEFAULT {ts_default},
                UNIQUE(tenant_id, category, key)
            );

            CREATE TABLE IF NOT EXISTS modifications (
                id {id_pk},
                tenant_id INTEGER,
                mod_type TEXT NOT NULL,
                method_name TEXT,
                description TEXT,
                code_preview TEXT,
                backup_file TEXT,
                success INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT {ts_default}
            );

            CREATE TABLE IF NOT EXISTS metrics (
                id {id_pk},
                tenant_id INTEGER,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT {ts_default}
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id {id_pk},
                tenant_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                severity TEXT DEFAULT 'info',
                source TEXT DEFAULT 'system',
                created_at TIMESTAMP DEFAULT {ts_default}
            );

            CREATE TABLE IF NOT EXISTS missions (
                id {id_pk},
                tenant_id INTEGER,
                title TEXT NOT NULL,
                objective TEXT,
                status TEXT DEFAULT 'active',
                priority INTEGER DEFAULT 5,
                progress REAL DEFAULT 0,
                swarm_id TEXT,
                metadata TEXT,
                approval_required INTEGER DEFAULT 0,
                approval_status TEXT DEFAULT 'n/a',
                created_at TIMESTAMP DEFAULT {ts_default},
                updated_at TIMESTAMP DEFAULT {ts_default}
            );

            CREATE TABLE IF NOT EXISTS knowledge_triples (
                id {id_pk},
                tenant_id INTEGER,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                privacy_level TEXT DEFAULT 'private', -- 'private', 'shared', 'public'
                created_at TIMESTAMP DEFAULT {ts_default},
                UNIQUE(tenant_id, subject, predicate, object)
            );

            CREATE TABLE IF NOT EXISTS colony (
                id TEXT PRIMARY KEY,
                parent_id TEXT,
                generation INTEGER DEFAULT 1,
                location TEXT,
                birth_time TEXT,
                status TEXT DEFAULT 'ALIVE',
                created_at TIMESTAMP DEFAULT {ts_default}
            );
        """
        
        if self.is_postgres:
            with self.conn.cursor() as cur:
                cur.execute(script)
            self.conn.commit()
        else:
            self.conn.executescript(script)
            # executescript() auto-commits; no explicit commit needed here
            
        # Indexes
        idx_scripts = [
            "CREATE INDEX IF NOT EXISTS idx_conversations_tenant_session ON conversations(tenant_id, session_id)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_tenant_status ON tasks(tenant_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_audit_tenant_severity ON audit_log(tenant_id, severity)",
            "CREATE INDEX IF NOT EXISTS idx_missions_tenant_status ON missions(tenant_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_tenants_api_key ON tenants(api_key)"
        ]
        for idx in idx_scripts:
            if self.is_postgres:
                with self.conn.cursor() as cur:
                    try: cur.execute(idx)
                    except: pass 
                self.conn.commit()
            else:
                self.conn.execute(idx)
                self._commit()

    # --- Tenants ---
    def add_tenant(self, name: str, api_key: str) -> int:
        cursor = self.conn.execute(
            "INSERT INTO tenants (name, api_key) VALUES (?,?)",
            (name, api_key)
        )
        self._commit()
        return cursor.lastrowid

    def get_tenant_by_api_key(self, api_key: str) -> Optional[Dict]:
        row = self.conn.execute(
            "SELECT * FROM tenants WHERE api_key=? AND status='active'", (api_key,)
        ).fetchone()
        return dict(row) if row else None

    # --- Conversations ---
    def save_message(self, tenant_id: int, session_id: str, role: str, content: str,
                     model: str = "", tokens: int = 0):
        if content is None:
            content = "..." # Prevent NOT NULL constraint violation
        self.conn.execute(
            "INSERT INTO conversations (tenant_id, session_id, role, content, model, tokens_used) VALUES (?,?,?,?,?,?)",
            (tenant_id, session_id, role, content, model, tokens)
        )
        self._commit()

    def get_conversation(self, tenant_id: int, session_id: str, limit: int = 50) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT role, content, created_at FROM conversations WHERE tenant_id=? AND session_id=? ORDER BY id DESC LIMIT ?",
            (tenant_id, session_id, limit)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def get_all_sessions(self, tenant_id: int) -> List[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT session_id FROM conversations WHERE tenant_id=? ORDER BY MAX(id) DESC",
            (tenant_id,)
        ).fetchall()
        return [r["session_id"] for r in rows]

    # --- Tasks ---
    def add_task(self, tenant_id: int, title: str, description: str = "", priority: int = 5,
                 source: str = "user") -> int:
        cursor = self.conn.execute(
            "INSERT INTO tasks (tenant_id, title, description, priority, source) VALUES (?,?,?,?,?)",
            (tenant_id, title, description, priority, source)
        )
        self._commit()
        return cursor.lastrowid

    def complete_task(self, tenant_id: int, task_id: int, result: str = ""):
        self.conn.execute(
            "UPDATE tasks SET status='completed', result=?, completed_at=CURRENT_TIMESTAMP WHERE tenant_id=? AND id=?",
            (result, tenant_id, task_id)
        )
        self._commit()

    def get_pending_tasks(self, tenant_id: int) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM tasks WHERE tenant_id=? AND status='pending' ORDER BY priority DESC, created_at ASC",
            (tenant_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Knowledge ---
    def store_knowledge(self, tenant_id: int, category: str, key: str, value: str,
                        confidence: float = 1.0, source: str = ""):
        self.conn.execute(
            """INSERT INTO knowledge_base (tenant_id, category, key, value, confidence, source)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(tenant_id, category, key) DO UPDATE SET
               value=excluded.value, confidence=excluded.confidence,
               updated_at=CURRENT_TIMESTAMP""",
            (tenant_id, category, key, value, confidence, source)
        )
        self._commit()

    def search_knowledge(self, tenant_id: int, query: str, category: str = None) -> List[Dict]:
        if category:
            rows = self.conn.execute(
                "SELECT * FROM knowledge_base WHERE tenant_id=? AND category=? AND (key LIKE ? OR value LIKE ?)",
                (tenant_id, category, f"%{query}%", f"%{query}%")
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM knowledge_base WHERE tenant_id=? AND (key LIKE ? OR value LIKE ?)",
                (tenant_id, f"%{query}%", f"%{query}%")
            ).fetchall()
        return [dict(r) for r in rows]

    # --- Modifications ---
    def log_modification(self, tenant_id: int, mod_type: str, method_name: str = "",
                         description: str = "", code_preview: str = "",
                         backup_file: str = "", success: bool = True):
        self.conn.execute(
            "INSERT INTO modifications (tenant_id, mod_type, method_name, description, code_preview, backup_file, success) VALUES (?,?,?,?,?,?,?)",
            (tenant_id, mod_type, method_name, description, code_preview, backup_file, int(success))
        )
        self._commit()

    def get_modifications(self, tenant_id: int, limit: int = 20) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM modifications WHERE tenant_id=? ORDER BY id DESC LIMIT ?", 
            (tenant_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def update_tenant_branding(self, tenant_id: int, branding: Dict):
        """Update branding configuration for a tenant (logo, colors, company name)."""
        self.conn.execute(
            "UPDATE tenants SET branding_json=? WHERE id=?",
            (json.dumps(branding), tenant_id)
        )
        self._commit()

    def get_tenant_branding(self, tenant_id: int) -> Dict:
        """Fetch branding info for a tenant."""
        row = self.conn.execute(
            "SELECT branding_json FROM tenants WHERE id=?", (tenant_id,)
        ).fetchone()
        return json.loads(row[0]) if row and row[0] else {}

    # --- User Management (RBAC) ---
    def add_user(self, tenant_id: int, username: str, password_hash: str, role: str = "VIEWER") -> int:
        cursor = self.conn.execute(
            "INSERT INTO users (tenant_id, username, password_hash, role) VALUES (?,?,?,?)",
            (tenant_id, username, password_hash, role)
        )
        self._commit()
        return cursor.lastrowid

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        row = self.conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return dict(row) if row else None

    # --- Colony Management ---
    def register_child(self, child_id: str, parent_id: str, generation: int, location: str):
        self.conn.execute(
            "INSERT INTO colony (id, parent_id, generation, location, birth_time, status) VALUES (?, ?, ?, ?, ?, ?)",
            (child_id, parent_id, generation, location, datetime.now().isoformat(), "ALIVE")
        )
        self._commit()
    
    def get_colony_census(self) -> List[Dict]:
        cursor = self.conn.execute("SELECT * FROM colony")
        cols = [description[0] for description in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def list_tenant_users(self, tenant_id: int) -> List[Dict]:
        rows = self.conn.execute("SELECT id, username, role, status FROM users WHERE tenant_id=?", (tenant_id,)).fetchall()
        return [dict(r) for r in rows]

    def update_user_role(self, user_id: int, role: str):
        self.conn.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
        self._commit()

    # --- Metrics ---
    def record_metric(self, tenant_id: int, name: str, value: float, metadata: str = ""):
        self.conn.execute(
            "INSERT INTO metrics (tenant_id, metric_name, metric_value, metadata) VALUES (?,?,?,?)",
            (tenant_id, name, value, metadata)
        )
        self._commit()

    # --- Audit ---
    def audit(self, tenant_id: int, action: str, details: str = "", severity: str = "info",
              source: str = "system"):
        self.conn.execute(
            "INSERT INTO audit_log (tenant_id, action, details, severity, source) VALUES (?,?,?,?,?)",
            (tenant_id, action, details, severity, source)
        )
        self._commit()

    def get_audit_log(self, tenant_id: int, severity: str = None, limit: int = 50) -> List[Dict]:
        if severity:
            rows = self.conn.execute(
                "SELECT * FROM audit_log WHERE tenant_id=? AND severity=? ORDER BY id DESC LIMIT ?",
                (tenant_id, severity, limit)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM audit_log WHERE tenant_id=? ORDER BY id DESC LIMIT ?", (tenant_id, limit)
            ).fetchall()
        return [dict(r) for r in rows]

    # --- Missions ---
    def add_mission(self, tenant_id: int, title: str, objective: str = "", priority: int = 5,
                    metadata: Dict = None, approval_required: bool = False) -> int:
        status = "pending_approval" if approval_required else "active"
        app_status = "pending" if approval_required else "n/a"
        
        cursor = self.conn.execute(
            """INSERT INTO missions (tenant_id, title, objective, priority, metadata, 
                                   status, approval_required, approval_status) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (tenant_id, title, objective, priority, json.dumps(metadata or {}),
             status, 1 if approval_required else 0, app_status)
        )
        self._commit()
        return cursor.lastrowid

    def update_mission_approval(self, tenant_id: int, mission_id: int, approval: str):
        """Approve or Reject a mission."""
        status = "active" if approval == "approved" else "rejected"
        self.conn.execute(
            "UPDATE missions SET approval_status=?, status=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND tenant_id=?",
            (approval, status, mission_id, tenant_id)
        )
        self._commit()

    def update_mission(self, tenant_id: int, mission_id: int, **kwargs):
        if "metadata" in kwargs and isinstance(kwargs["metadata"], dict):
            kwargs["metadata"] = json.dumps(kwargs["metadata"])
        
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [tenant_id, mission_id]
        self.conn.execute(
            f"UPDATE missions SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE tenant_id=? AND id=?", 
            vals
        )
        self._commit()

    def get_active_missions(self, tenant_id: int) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM missions WHERE tenant_id=? AND status='active' ORDER BY priority DESC, created_at ASC",
            (tenant_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_mission(self, tenant_id: int, mission_id: int) -> Optional[Dict]:
        row = self.conn.execute("SELECT * FROM missions WHERE tenant_id=? AND id=?", (tenant_id, mission_id)).fetchone()
        return dict(row) if row else None

    # --- Dashboard ---
    def get_dashboard_stats(self, tenant_id: int) -> Dict[str, Any]:
        total_convos = self.conn.execute("SELECT COUNT(*) as c FROM conversations WHERE tenant_id=?", (tenant_id,)).fetchone()["c"]
        total_tasks = self.conn.execute("SELECT COUNT(*) as c FROM tasks WHERE tenant_id=?", (tenant_id,)).fetchone()["c"]
        pending_tasks = self.conn.execute("SELECT COUNT(*) as c FROM tasks WHERE tenant_id=? AND status='pending'", (tenant_id,)).fetchone()["c"]
        total_mods = self.conn.execute("SELECT COUNT(*) as c FROM modifications WHERE tenant_id=?", (tenant_id,)).fetchone()["c"]
        active_missions = self.conn.execute("SELECT COUNT(*) as c FROM missions WHERE tenant_id=? AND status='active'", (tenant_id,)).fetchone()["c"]
        return {
            "total_conversations": total_convos,
            "total_tasks": total_tasks,
            "pending_tasks": pending_tasks,
            "active_missions": active_missions,
            "total_modifications": total_mods,
        }

    def get_total_revenue(self, tenant_id: int = None) -> float:
        """Calculate total revenue from metrics."""
        if tenant_id:
            row = self.conn.execute(
                "SELECT SUM(metric_value) as total FROM metrics WHERE tenant_id=? AND metric_name='revenue'",
                (tenant_id,)
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT SUM(metric_value) as total FROM metrics WHERE metric_name='revenue'"
            ).fetchone()
        return row["total"] if row and row["total"] else 0.0

    def close(self):
        self.conn.close()
