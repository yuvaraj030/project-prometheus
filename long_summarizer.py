"""
Long-Context Summarizer — Map-Reduce summarization for books, codebases, transcripts.
Splits content into chunks, summarizes each, then merges into a final summary.
"""
import os
import logging
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger("LongSummarizer")

STYLE_PROMPTS = {
    "brief": "Write a very brief 2-3 sentence summary. Be concise and direct.",
    "detailed": "Write a detailed, comprehensive summary covering all major points.",
    "bullets": "Write a bullet-point summary with key ideas as concise bullets (use • prefix).",
    "executive": "Write an executive summary: overview, key insights, and action items.",
    "technical": "Write a technical summary focusing on algorithms, architecture, and implementation details.",
}


def _load_file(path: str) -> str:
    """Load content from various file types."""
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        try:
            import PyPDF2
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join(p.extract_text() or "" for p in reader.pages)
        except ImportError:
            pass
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def _split_chunks(text: str, chunk_words: int = 1000) -> List[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_words):
        chunk = " ".join(words[i:i + chunk_words])
        if len(chunk.strip()) > 100:
            chunks.append(chunk)
    return chunks


class LongSummarizer:
    """
    Summarizes arbitrarily long content using Map-Reduce approach:
    1. Split into chunks  
    2. Summarize each chunk (Map)
    3. Merge chunk summaries into final summary (Reduce)
    """

    def __init__(self, llm_provider=None):
        self.llm = llm_provider

    def _call_llm(self, prompt: str, max_tokens: int = 400) -> str:
        if not self.llm:
            return "[No LLM connected — install Ollama or set API key]"
        try:
            return self.llm.call(prompt, max_tokens=max_tokens)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return f"[LLM error: {e}]"

    def _summarize_chunk(self, chunk: str, style: str, context: str = "") -> str:
        """Summarize a single chunk."""
        style_instr = STYLE_PROMPTS.get(style, STYLE_PROMPTS["brief"])
        ctx = f"This is part of: {context}\n\n" if context else ""
        prompt = (
            f"{ctx}Summarize the following text. {style_instr}\n\n"
            f"TEXT:\n{chunk}\n\nSUMMARY:"
        )
        return self._call_llm(prompt, max_tokens=300)

    def _merge_summaries(self, summaries: List[str], style: str, title: str = "") -> str:
        """Merge chunk summaries into a final coherent summary."""
        style_instr = STYLE_PROMPTS.get(style, STYLE_PROMPTS["brief"])
        combined = "\n\n---\n\n".join(f"Part {i+1}:\n{s}" for i, s in enumerate(summaries))
        title_ctx = f"'{title}'" if title else "the content"
        prompt = (
            f"You have been given partial summaries of {title_ctx}. "
            f"Merge them into one coherent final summary. {style_instr}\n\n"
            f"PARTIAL SUMMARIES:\n{combined}\n\n"
            f"FINAL MERGED SUMMARY:"
        )
        return self._call_llm(prompt, max_tokens=800)

    def summarize_text(self, text: str, style: str = "brief", title: str = "") -> Dict:
        """
        Summarize raw text. Uses map-reduce for long content.
        Returns dict with summary, chunk_count, word_count.
        """
        if not text.strip():
            return {"summary": "❌ Empty text provided.", "chunks": 0, "words": 0}

        word_count = len(text.split())
        logger.info(f"📄 Summarizing {word_count} words with style='{style}'")

        # Short text: single-pass summarization
        if word_count <= 1500:
            style_instr = STYLE_PROMPTS.get(style, STYLE_PROMPTS["brief"])
            prompt = (
                f"Summarize the following text. {style_instr}\n\n"
                f"TEXT:\n{text}\n\nSUMMARY:"
            )
            summary = self._call_llm(prompt, max_tokens=600)
            return {"summary": summary, "chunks": 1, "words": word_count, "style": style}

        # Long text: map-reduce approach
        chunks = _split_chunks(text, chunk_words=1000)
        print(f"  📊 Document has {word_count:,} words → splitting into {len(chunks)} chunks...")

        # Map: summarize each chunk
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            print(f"  🔄 Summarizing chunk {i+1}/{len(chunks)}...", end="\r", flush=True)
            cs = self._summarize_chunk(chunk, "brief", context=title)
            chunk_summaries.append(cs)
        print()

        # For very many summaries, do a second-level reduce
        if len(chunk_summaries) > 8:
            print(f"  🔀 Merging {len(chunk_summaries)} chunk summaries in two steps...")
            # Group into batches of 6
            batch_summaries = []
            for i in range(0, len(chunk_summaries), 6):
                batch = chunk_summaries[i:i+6]
                merged = self._merge_summaries(batch, "brief", title)
                batch_summaries.append(merged)
            final_summary = self._merge_summaries(batch_summaries, style, title)
        else:
            final_summary = self._merge_summaries(chunk_summaries, style, title)

        return {
            "summary": final_summary,
            "chunks": len(chunks),
            "words": word_count,
            "style": style
        }

    def summarize_file(self, path: str, style: str = "brief") -> Dict:
        """Summarize a file (txt, pdf, md, py, etc.)."""
        path = os.path.expandvars(path.strip())
        if not os.path.exists(path):
            return {"summary": f"❌ File not found: {path}", "chunks": 0, "words": 0}

        fname = os.path.basename(path)
        print(f"  📂 Loading '{fname}'...")
        text = _load_file(path)

        if not text.strip():
            return {"summary": f"❌ Could not read content from '{fname}'", "chunks": 0, "words": 0}

        result = self.summarize_text(text, style=style, title=fname)
        result["file"] = fname
        return result

    def summarize_directory(self, path: str, style: str = "brief",
                            extensions: Optional[List[str]] = None) -> Dict:
        """
        Summarize all files in a directory.
        Returns per-file summaries and an overall summary.
        """
        extensions = extensions or [".py", ".md", ".txt", ".js", ".ts", ".java"]
        path = os.path.expandvars(path.strip())
        if not os.path.isdir(path):
            return {"summary": f"❌ Not a directory: {path}", "file_summaries": {}}

        file_summaries = {}
        all_text_parts = []

        for fname in sorted(os.listdir(path)):
            fpath = os.path.join(path, fname)
            if not os.path.isfile(fpath):
                continue
            if Path(fpath).suffix.lower() not in extensions:
                continue

            print(f"  📄 Summarizing '{fname}'...")
            text = _load_file(fpath)
            if not text.strip():
                continue

            words = len(text.split())
            if words < 20:
                continue

            # Quick per-file summary
            short = self._summarize_chunk(text[:3000], "brief", context=fname)
            file_summaries[fname] = short
            all_text_parts.append(f"[{fname}] {short}")

        if not file_summaries:
            return {"summary": "❌ No readable files found.", "file_summaries": {}}

        # Merge all file summaries into codebase overview
        combined = "\n\n".join(all_text_parts[:20])
        prompt = (
            f"You are reviewing a project directory. Based on these file summaries, "
            f"write an overall project summary. {STYLE_PROMPTS.get(style, '')}\n\n"
            f"{combined}\n\nPROJECT SUMMARY:"
        )
        overall = self._call_llm(prompt, max_tokens=600)

        return {
            "summary": overall,
            "file_summaries": file_summaries,
            "files_processed": len(file_summaries),
            "style": style
        }

    def get_styles(self) -> List[str]:
        return list(STYLE_PROMPTS.keys())
