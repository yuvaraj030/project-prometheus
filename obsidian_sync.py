"""
Obsidian / Notion Sync — RAG over personal knowledge base.
Indexes all markdown notes from an Obsidian vault (or any .md folder)
into vector memory with frontmatter metadata for semantic search.
"""

import os
import re
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger("ObsidianSync")


class ObsidianSync:
    """
    Syncs a markdown note vault (Obsidian, Logseq, Obsidian, plain .md files)
    into the agent's vector memory for Retrieval-Augmented Generation.
    
    Features:
    - YAML frontmatter extraction (tags, dates, links)
    - Delta sync — only re-indexes changed files (hash-based)
    - Chunked indexing — large notes split into ~512-token windows
    - Wikilink graph awareness ([[linked-note]] references)
    """

    CHUNK_SIZE = 1800  # ~450 tokens per chunk
    CHUNK_OVERLAP = 200  # overlap between chunks for context continuity

    def __init__(self, vector_memory, database, llm_provider=None):
        self.vmem = vector_memory
        self.db = database
        self.llm = llm_provider
        self._index_cache: Dict[str, str] = {}  # filepath -> content hash
        self._load_index_cache()
        logger.info("📚 ObsidianSync initialized.")

    # ─── Cache Persistence ───────────────────────────────
    def _cache_path(self): return "obsidian_sync_cache.json"

    def _load_index_cache(self):
        try:
            with open(self._cache_path(), "r", encoding="utf-8") as f:
                self._index_cache = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._index_cache = {}

    def _save_index_cache(self):
        try:
            with open(self._cache_path(), "w", encoding="utf-8") as f:
                json.dump(self._index_cache, f)
        except Exception:
            pass

    def _file_hash(self, filepath: str) -> str:
        try:
            with open(filepath, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    # ─── Frontmatter Parsing ─────────────────────────────
    def _parse_frontmatter(self, content: str) -> tuple[Dict, str]:
        """Extract YAML frontmatter and return (metadata, body)."""
        meta = {}
        body = content
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                fm = content[3:end].strip()
                body = content[end + 3:].strip()
                # Simple YAML-light parsing
                for line in fm.split("\n"):
                    if ":" in line:
                        key, _, val = line.partition(":")
                        meta[key.strip()] = val.strip().strip('"').strip("'")
        return meta, body

    def _extract_wikilinks(self, text: str) -> List[str]:
        """Extract [[wikilink]] references from note body."""
        return re.findall(r'\[\[([^\]]+)\]\]', text)

    # ─── Chunking ────────────────────────────────────────
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks for vector indexing."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.CHUNK_SIZE
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk.strip())
            start = end - self.CHUNK_OVERLAP
            if start < 0:
                start = 0
            if end >= len(text):
                break
        return chunks

    # ─── Core Sync ───────────────────────────────────────
    def sync_vault(self, vault_path: str, tenant_id: int,
                   force: bool = False) -> Dict[str, Any]:
        """
        Recursively scan vault_path for .md files.
        Only re-indexes files that have changed (hash-based delta sync).
        
        Args:
            vault_path: Path to Obsidian vault or any markdown folder
            tenant_id: Agent tenant ID
            force: Force re-index all files even if unchanged
        """
        if not os.path.isdir(vault_path):
            return {"success": False, "error": f"Vault path not found: {vault_path}"}

        indexed = []
        skipped = []
        errors = []
        total_chunks = 0

        md_files = []
        for root, dirs, files in os.walk(vault_path):
            # Skip hidden dirs and .obsidian config
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if f.endswith(".md"):
                    md_files.append(os.path.join(root, f))

        logger.info(f"📚 Found {len(md_files)} markdown files in vault.")

        for filepath in md_files:
            try:
                current_hash = self._file_hash(filepath)
                cached_hash = self._index_cache.get(filepath, "")

                if not force and current_hash == cached_hash:
                    skipped.append(os.path.basename(filepath))
                    continue

                result = self._index_note(filepath, tenant_id)
                if result["success"]:
                    indexed.append(os.path.basename(filepath))
                    total_chunks += result.get("chunks", 0)
                    self._index_cache[filepath] = current_hash
                else:
                    errors.append(f"{os.path.basename(filepath)}: {result.get('error')}")
            except Exception as e:
                errors.append(f"{os.path.basename(filepath)}: {e}")

        self._save_index_cache()

        summary = {
            "success": True,
            "vault": vault_path,
            "total_files": len(md_files),
            "indexed": len(indexed),
            "skipped_unchanged": len(skipped),
            "errors": len(errors),
            "total_chunks": total_chunks,
            "error_list": errors[:5],
        }
        logger.info(f"✅ Vault sync complete: {len(indexed)} indexed, {len(skipped)} unchanged, {len(errors)} errors")
        return summary

    def _index_note(self, filepath: str, tenant_id: int) -> Dict[str, Any]:
        """Index a single markdown note into vector memory."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            return {"success": False, "error": str(e)}

        if not content.strip():
            return {"success": False, "error": "Empty file"}

        filename = os.path.basename(filepath)
        note_name = os.path.splitext(filename)[0]

        # Parse frontmatter
        meta, body = self._parse_frontmatter(content)
        tags = meta.get("tags", "").replace(",", " ").split()
        links = self._extract_wikilinks(body)

        # Build metadata dict for vector store
        vmeta = {
            "category": "vault_note",
            "type": "obsidian",
            "filename": filename,
            "note_name": note_name,
            "source": filepath,
            "tags": " ".join(tags[:10]),
            "links": " ".join(links[:10]),
            "date": meta.get("date", meta.get("created", "")),
        }

        # Chunk and store
        chunks = self._chunk_text(body)
        if not chunks:
            chunks = [body[:self.CHUNK_SIZE]]

        file_hash = self._file_hash(filepath)
        for i, chunk in enumerate(chunks):
            doc_id = f"obsidian_{file_hash}_{i}"
            header = f"[Note: {note_name}"
            if tags:
                header += f" | Tags: {', '.join(tags[:5])}"
            header += "]\n"
            self.vmem.add(
                tenant_id=tenant_id,
                text=header + chunk,
                metadata={**vmeta, "chunk": str(i)},
                doc_id=doc_id
            )

        return {"success": True, "note": note_name, "chunks": len(chunks),
                "tags": tags, "links": links}

    # ─── Querying ────────────────────────────────────────
    def query_vault(self, tenant_id: int, question: str, n: int = 5) -> str:
        """Semantic search over indexed vault notes."""
        results = self.vmem.search(
            tenant_id, question, n_results=n,
            # category="vault_note"  # filter if your vmem supports it
        )
        if not results:
            return "No relevant notes found in your vault."

        lines = [f"🗂️ From your knowledge vault ({len(results)} relevant notes):"]
        seen = set()
        for r in results:
            text = r.get("text", "")[:500]
            if text in seen:
                continue
            seen.add(text)
            note = r.get("metadata", {}).get("note_name", "Unknown note")
            lines.append(f"\n📄 **{note}**\n{text}")

        return "\n".join(lines)

    def get_status(self) -> Dict[str, Any]:
        return {
            "indexed_files": len(self._index_cache),
            "cache_path": self._cache_path(),
        }
