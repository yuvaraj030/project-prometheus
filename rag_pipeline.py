"""
RAG Pipeline — Retrieval-Augmented Generation with PDF/Doc support.
Upload documents → agent answers questions with source citations.
"""
import os
import json
import logging
import hashlib
import re
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("RAGPipeline")


def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks for embedding."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return [c for c in chunks if len(c.strip()) > 50]


def _load_file(path: str) -> str:
    """Load text from file — supports .pdf, .txt, .md, .py, .json, .csv."""
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        try:
            import PyPDF2
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join(p.extract_text() or "" for p in reader.pages)
        except ImportError:
            try:
                import pdfplumber
                with pdfplumber.open(path) as pdf:
                    return "\n".join(p.extract_text() or "" for p in pdf.pages)
            except ImportError:
                logger.warning("No PDF library found (install pypdf2 or pdfplumber). Trying raw read.")
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Cannot read {path}: {e}")
        return ""


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline.
    Ingests documents → stores chunk embeddings → answers queries with citations.
    """

    def __init__(self, llm_provider=None, vector_memory=None):
        self.llm = llm_provider
        self.vmem = vector_memory
        self.ingested_docs: Dict[str, Dict] = {}
        self._state_path = "rag_state.json"
        self._load_state()

    def _load_state(self):
        try:
            if os.path.exists(self._state_path):
                with open(self._state_path) as f:
                    self.ingested_docs = json.load(f)
        except Exception:
            self.ingested_docs = {}

    def _save_state(self):
        try:
            with open(self._state_path, "w") as f:
                json.dump(self.ingested_docs, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save RAG state: {e}")

    def ingest(self, path: str, tenant_id: str = "default") -> Dict[str, Any]:
        """
        Ingest a file or directory into the RAG knowledge base.
        Returns ingestion summary.
        """
        path = os.path.expandvars(path.strip())
        results = {"files": [], "chunks_added": 0, "errors": []}

        if os.path.isdir(path):
            exts = {".pdf", ".txt", ".md", ".py", ".json", ".csv", ".rst"}
            for fname in os.listdir(path):
                fpath = os.path.join(path, fname)
                if Path(fpath).suffix.lower() in exts:
                    r = self._ingest_file(fpath, tenant_id)
                    results["files"].append(r.get("file", fname))
                    results["chunks_added"] += r.get("chunks", 0)
                    if r.get("error"):
                        results["errors"].append(r["error"])
        else:
            r = self._ingest_file(path, tenant_id)
            results["files"].append(r.get("file", path))
            results["chunks_added"] += r.get("chunks", 0)
            if r.get("error"):
                results["errors"].append(r["error"])

        return results

    def _ingest_file(self, path: str, tenant_id: str) -> Dict:
        """Ingest a single file into vector memory."""
        doc_id = hashlib.md5(path.encode()).hexdigest()[:12]
        fname = os.path.basename(path)

        text = _load_file(path)
        if not text.strip():
            return {"file": fname, "chunks": 0, "error": f"Empty or unreadable: {fname}"}

        chunks = _chunk_text(text)
        chunks_stored = 0

        if self.vmem:
            for i, chunk in enumerate(chunks):
                try:
                    meta = {"source": fname, "doc_id": doc_id, "chunk": i}
                    self.vmem.store(
                        tenant_id,
                        f"[RAG:{fname}:{i}] {chunk}",
                        metadata=meta,
                        topic="rag"
                    )
                    chunks_stored += 1
                except Exception as e:
                    logger.debug(f"vmem store error: {e}")
                    # Fallback: store in local dict
                    if doc_id not in self.ingested_docs:
                        self.ingested_docs[doc_id] = {"fname": fname, "chunks": []}
                    self.ingested_docs[doc_id]["chunks"].append(chunk)
                    chunks_stored += 1
        else:
            # No vector memory: store in local JSON
            if doc_id not in self.ingested_docs:
                self.ingested_docs[doc_id] = {"fname": fname, "chunks": []}
            self.ingested_docs[doc_id]["chunks"].extend(chunks)
            chunks_stored = len(chunks)

        self.ingested_docs[doc_id] = {
            "fname": fname,
            "path": path,
            "chunks_count": chunks_stored,
            "ingested_at": datetime.now().isoformat(),
            "chunks": chunks if not self.vmem else []  # Store inline if no vmem
        }
        self._save_state()
        logger.info(f"📚 Ingested '{fname}': {chunks_stored} chunks")
        return {"file": fname, "chunks": chunks_stored}

    def query(self, question: str, tenant_id: str = "default", top_k: int = 5) -> Dict[str, Any]:
        """
        Answer a question using RAG — retrieve relevant chunks, then generate answer with citations.
        """
        if not self.ingested_docs:
            return {
                "answer": "❌ No documents ingested yet. Use /rag ingest <path> first.",
                "citations": [],
                "chunks_used": 0
            }

        # Retrieve relevant chunks
        context_parts = []
        citations = []

        if self.vmem:
            try:
                results = self.vmem.search(tenant_id, question, n_results=top_k)
                for r in results:
                    text = r.get("text", str(r))
                    # Extract source from RAG prefix
                    source = "unknown"
                    m = re.match(r"\[RAG:([^\]]+):\d+\]", text)
                    if m:
                        source = m.group(1)
                        text = text[m.end():].strip()
                    context_parts.append(f"[From: {source}]\n{text}")
                    if source not in citations:
                        citations.append(source)
            except Exception as e:
                logger.debug(f"vmem search error: {e}")

        # Fallback: keyword search through stored chunks
        if not context_parts:
            q_words = set(question.lower().split())
            scored = []
            for doc_id, doc in self.ingested_docs.items():
                fname = doc.get("fname", doc_id)
                for chunk in doc.get("chunks", []):
                    c_words = set(chunk.lower().split())
                    score = len(q_words & c_words)
                    if score > 0:
                        scored.append((score, fname, chunk))
            scored.sort(key=lambda x: -x[0])
            for score, fname, chunk in scored[:top_k]:
                context_parts.append(f"[From: {fname}]\n{chunk}")
                if fname not in citations:
                    citations.append(fname)

        if not context_parts:
            return {
                "answer": "❌ No relevant content found for your question. Try re-ingesting documents.",
                "citations": [],
                "chunks_used": 0
            }

        context = "\n\n---\n\n".join(context_parts[:top_k])
        prompt = (
            f"You are an expert AI assistant. Answer the following question using ONLY the provided context.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION: {question}\n\n"
            f"Provide a detailed, accurate answer. If the context doesn't contain the answer, say so. "
            f"End your answer with a line listing which source files you used."
        )

        if self.llm:
            try:
                answer = self.llm.call(prompt, max_tokens=600)
            except Exception as e:
                answer = f"LLM error: {e}\n\nContext found:\n{context[:500]}"
        else:
            answer = f"[No LLM connected. Here is the raw context:]\n{context[:800]}"

        return {
            "answer": answer,
            "citations": citations,
            "chunks_used": len(context_parts)
        }

    def list_documents(self) -> List[Dict]:
        """List all ingested documents."""
        return [
            {
                "doc_id": did,
                "file": doc.get("fname", did),
                "chunks": doc.get("chunks_count", len(doc.get("chunks", []))),
                "ingested_at": doc.get("ingested_at", "unknown")
            }
            for did, doc in self.ingested_docs.items()
        ]

    def remove_document(self, fname_or_id: str) -> str:
        """Remove a document from the RAG knowledge base."""
        for did, doc in list(self.ingested_docs.items()):
            if doc.get("fname") == fname_or_id or did == fname_or_id:
                del self.ingested_docs[did]
                self._save_state()
                return f"✅ Removed '{doc.get('fname', fname_or_id)}' from RAG knowledge base."
        return f"❌ Document '{fname_or_id}' not found."

    def get_stats(self) -> Dict:
        total_chunks = sum(
            doc.get("chunks_count", len(doc.get("chunks", [])))
            for doc in self.ingested_docs.values()
        )
        return {
            "documents": len(self.ingested_docs),
            "total_chunks": total_chunks,
            "files": [doc.get("fname", did) for did, doc in self.ingested_docs.items()]
        }
