"""
Vector Memory Module — ChromaDB-backed semantic search for the AI Agent.
Falls back to simple keyword search if ChromaDB is not installed.
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    import psycopg2
    from pgvector.psycopg2 import register_vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False


class VectorMemory:
    """Semantic vector memory using ChromaDB (with keyword fallback)."""

    def __init__(self, persist_dir: str = "agent_vector_db",
                 collection_name: str = "agent_memory",
                 llm_provider: Any = None):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.llm = llm_provider
        self.fallback_store: List[Dict] = []
        self.fallback_file = os.path.join(persist_dir, "fallback_memory.json")
        self.db_url = os.getenv("DATABASE_URL")
        self.is_postgres = self.db_url and self.db_url.startswith("postgres") and PGVECTOR_AVAILABLE
        
        if self.is_postgres:
            try:
                self.conn = psycopg2.connect(self.db_url)
                register_vector(self.conn)
                self._create_pg_table()
                self.active = True
                print("[OK] Vector memory (pgvector) initialized")
            except Exception as e:
                print(f"[WARN] pgvector init failed: {e} - using keyword fallback")
                self.is_postgres = False
                self._load_fallback()
        elif CHROMADB_AVAILABLE:
            try:
                self.client = chromadb.PersistentClient(path=persist_dir)
                self.collection = self.client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                self.active = True
                print("[OK] Vector memory (ChromaDB) initialized")
            except Exception as e:
                print(f"[WARN] ChromaDB init failed: {e} - using keyword fallback")
                self.active = False
                self._load_fallback()
        else:
            print("[INFO] ChromaDB not installed - using keyword fallback memory")
            self.active = False
            self._load_fallback()

    def _create_pg_table(self):
        with self.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.collection_name} (
                    id TEXT PRIMARY KEY,
                    tenant_id INTEGER,
                    text TEXT,
                    metadata JSONB,
                    embedding vector(1536)
                )
            """)
            cur.execute(f"CREATE INDEX IF NOT EXISTS idx_mem_tenant ON {self.collection_name}(tenant_id)")
        self.conn.commit()

    def _load_fallback(self):
        os.makedirs(self.persist_dir, exist_ok=True)
        try:
            with open(self.fallback_file, "r") as f:
                self.fallback_store = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.fallback_store = []

    def _save_fallback(self):
        os.makedirs(self.persist_dir, exist_ok=True)
        with open(self.fallback_file, "w") as f:
            json.dump(self.fallback_store, f, indent=2)

    def add(self, tenant_id: int, text: str, metadata: Optional[Dict[str, Any]] = None,
            doc_id: Optional[str] = None) -> str:
        """Store a memory entry."""
        if not doc_id:
            doc_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        meta = metadata or {}
        meta["tenant_id"] = tenant_id
        meta["timestamp"] = datetime.now().isoformat()

        if self.is_postgres:
            embedding = self.llm.get_embedding(text) if self.llm else [0.0]*1536
            with self.conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {self.collection_name} (id, tenant_id, text, metadata, embedding) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET text=EXCLUDED.text, metadata=EXCLUDED.metadata, embedding=EXCLUDED.embedding",
                    (doc_id, tenant_id, text, json.dumps(meta), embedding)
                )
            self.conn.commit()
        elif self.active:
            try:
                self.collection.add(
                    documents=[text],
                    metadatas=[{k: str(v) for k, v in meta.items()}],
                    ids=[doc_id]
                )
            except Exception as e:
                print(f"⚠️  Vector add error: {e}")
        else:
            self.fallback_store.append({
                "id": doc_id, "text": text, "metadata": meta, "tenant_id": tenant_id
            })
            self._save_fallback()

        return doc_id

    def search(self, tenant_id: int, query: str, n_results: int = 5,
               category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search memory semantically (or by keyword if fallback)."""
        if self.is_postgres:
            embedding = self.llm.get_embedding(query) if self.llm else [0.0]*1536
            with self.conn.cursor() as cur:
                sql = f"SELECT id, text, metadata, embedding <=> %s as distance FROM {self.collection_name} WHERE tenant_id = %s"
                params = [embedding, tenant_id]
                if category:
                    sql += " AND metadata->>'category' = %s"
                    params.append(category)
                sql += " ORDER BY distance ASC LIMIT %s"
                params.append(n_results)
                cur.execute(sql, params)
                rows = cur.fetchall()
                return [
                    {
                        "text": r["text"], "metadata": r["metadata"], "id": r["id"], "distance": r["distance"]
                    } for r in rows
                ]
        elif self.active:
            try:
                where = {"tenant_id": str(tenant_id)}
                if category:
                    where = {"$and": [{"tenant_id": str(tenant_id)}, {"category": category}]}
                
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where=where
                )
                output = []
                for i, doc in enumerate(results["documents"][0]):
                    output.append({
                        "text": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "id": results["ids"][0][i] if results["ids"] else "",
                        "distance": results["distances"][0][i] if results.get("distances") else 0
                    })
                return output
            except Exception as e:
                print(f"⚠️  Vector search error: {e}")
                return []
        else:
            # Keyword fallback
            query_lower = query.lower()
            scored = []
            for entry in self.fallback_store:
                if entry.get("tenant_id") != tenant_id:
                    continue
                text_lower = entry["text"].lower()
                score = sum(1 for word in query_lower.split() if word in text_lower)
                if score > 0:
                    scored.append((score, entry))
            scored.sort(key=lambda x: -x[0])
            return [
                {"text": e["text"], "metadata": e["metadata"], "id": e["id"], "distance": 0}
                for _, e in scored[:n_results]
            ]

    def add_conversation(self, tenant_id: int, role: str, content: str, session_id: str = "default"):
        """Store a conversation turn as a memory."""
        self.add(
            tenant_id=tenant_id,
            text=f"[{role}]: {content}",
            metadata={"category": "conversation", "role": role, "session": session_id}
        )

    def add_knowledge(self, tenant_id: int, topic: str, content: str, source: str = ""):
        """Store a knowledge item."""
        self.add(
            tenant_id=tenant_id,
            text=f"[{topic}]: {content}",
            metadata={"category": "knowledge", "topic": topic, "source": source}
        )

    def add_reflection(self, tenant_id: int, reflection: str):
        """Store a self-reflection."""
        self.add(
            tenant_id=tenant_id,
            text=reflection,
            metadata={"category": "reflection"}
        )

    def recall(self, tenant_id: int, context: str, n: int = 3) -> str:
        """Recall relevant memories as a formatted string for the LLM."""
        results = self.search(tenant_id, context, n_results=n)
        if not results:
            return ""
        lines = ["[Relevant memories]:"]
        for r in results:
            lines.append(f"  - {r['text'][:300]}")
        return "\n".join(lines)

    def count(self) -> int:
        if self.active:
            try:
                return self.collection.count()
            except:
                return 0
        return len(self.fallback_store)

    def clear(self):
        if self.active:
            try:
                self.client.delete_collection(self.collection_name)
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name
                )
            except:
                pass
        else:
            self.fallback_store = []
            self._save_fallback()
