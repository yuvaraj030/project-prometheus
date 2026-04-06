"""
Mindmap Visualizer — generates interactive HTML mindmap from vector memory concepts.
Commands: /mindmap generate|open|export
"""

import os
import json
from datetime import datetime


class MindmapVisualizer:
    """Visualizes knowledge base and concepts as an interactive D3.js mindmap."""

    OUTPUT_FILE = "mindmap_output.html"

    def __init__(self, llm_provider=None, vector_memory=None, tenant_id="default"):
        self.llm = llm_provider
        self.vmem = vector_memory
        self.tid = tenant_id

    def generate(self, topic: str = "Knowledge Base", extra_concepts: list = None) -> dict:
        """Generate an interactive HTML mindmap."""
        # Collect concepts from vector memory
        nodes_data = self._extract_concepts(topic, extra_concepts or [])

        html = self._build_html(topic, nodes_data)
        try:
            with open(self.OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write(html)
            return {
                "success": True,
                "filepath": self.OUTPUT_FILE,
                "node_count": len(nodes_data),
                "message": f"🧠 Mindmap generated with {len(nodes_data)} concepts!\n   📄 File: {self.OUTPUT_FILE}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_in_browser(self) -> str:
        """Open the mindmap in the default browser."""
        import sys
        if not os.path.exists(self.OUTPUT_FILE):
            return "❌ No mindmap generated yet. Run /mindmap generate first."
        if sys.platform == "win32":
            os.startfile(os.path.abspath(self.OUTPUT_FILE))
            return f"🌐 Mindmap opened in browser!"
        else:
            import subprocess
            subprocess.Popen(["xdg-open", self.OUTPUT_FILE])
            return f"🌐 Mindmap opened: {self.OUTPUT_FILE}"

    def _extract_concepts(self, topic: str, extra: list) -> list:
        """Extract concepts from vector memory and LLM."""
        concepts = []

        # From vector memory
        if self.vmem:
            try:
                results = self.vmem.search(self.tid, topic, n_results=20)
                for r in results:
                    text = r.get("text", "")[:100]
                    if text:
                        concepts.append({"id": len(concepts), "text": text, "type": "memory"})
            except Exception:
                pass

        # LLM-expanded concepts
        if self.llm and len(concepts) < 10:
            try:
                prompt = (
                    f"List 15 key concepts, themes, and ideas related to: {topic}\n"
                    "Return ONLY a JSON array of strings, no other text.\n"
                    'Example: ["concept1", "concept2", ...]'
                )
                result = self.llm.chat(prompt)
                if result:
                    import re
                    match = re.search(r'\[.*?\]', result, re.DOTALL)
                    if match:
                        items = json.loads(match.group())
                        for item in items[:15]:
                            concepts.append({"id": len(concepts), "text": str(item)[:60], "type": "ai"})
            except Exception:
                pass

        # Add extra
        for e in extra:
            concepts.append({"id": len(concepts), "text": str(e)[:60], "type": "user"})

        # Fallback
        if not concepts:
            for i, c in enumerate(["AI Agents", "Memory", "Learning", "Goals", "Autonomy",
                                    "Vision", "Voice", "Tools", "Skills", "Evolution"]):
                concepts.append({"id": i, "text": c, "type": "default"})

        return concepts[:30]

    def _build_html(self, topic: str, nodes: list) -> str:
        """Build the D3.js interactive mindmap HTML."""
        # Build graph data
        graph_nodes = [{"id": 0, "text": topic, "group": 0}]
        graph_links = []
        colors = {"memory": "#00d4ff", "ai": "#7c3aed", "user": "#f59e0b", "default": "#10b981"}

        for n in nodes:
            nid = n["id"] + 1
            graph_nodes.append({
                "id": nid,
                "text": n["text"],
                "group": 1,
                "color": colors.get(n["type"], "#10b981")
            })
            graph_links.append({"source": 0, "target": nid})

        # Cross-links for related concepts (every 4th)
        for i in range(1, len(nodes), 4):
            if i + 1 < len(nodes):
                graph_links.append({"source": i, "target": i + 1})

        nodes_json = json.dumps(graph_nodes)
        links_json = json.dumps(graph_links)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>🧠 Mindmap — {topic}</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0a0a1a; font-family:'Segoe UI',Arial,sans-serif; overflow:hidden; color:white; }}
  #title {{ position:fixed; top:20px; left:50%; transform:translateX(-50%);
            background:rgba(0,212,255,0.1); border:1px solid #00d4ff;
            padding:10px 30px; border-radius:30px; font-size:1.2rem;
            color:#00d4ff; letter-spacing:2px; z-index:10; }}
  #info {{ position:fixed; bottom:20px; left:20px; color:#888; font-size:0.8rem; }}
  svg {{ width:100vw; height:100vh; }}
  .link {{ stroke:#333; stroke-width:1.5px; opacity:0.6; }}
  .node circle {{ cursor:pointer; stroke-width:2px; transition:all 0.3s; }}
  .node circle:hover {{ stroke-width:4px; filter:brightness(1.5); }}
  .node text {{ pointer-events:none; font-size:11px; }}
  .center-node circle {{ stroke:#00d4ff; stroke-width:3px; }}
</style>
</head>
<body>
<div id="title">🧠 {topic}</div>
<div id="info">Generated by Ultimate AI Agent — {datetime.now().strftime('%Y-%m-%d %H:%M')} | {len(nodes)} concepts</div>
<svg id="graph"></svg>
<script>
const nodes = {nodes_json};
const links = {links_json};
const w = window.innerWidth, h = window.innerHeight;
const svg = d3.select('#graph');
const g = svg.append('g');
svg.call(d3.zoom().scaleExtent([0.3,3]).on('zoom', e => g.attr('transform', e.transform)));
const sim = d3.forceSimulation(nodes)
  .force('link', d3.forceLink(links).id(d=>d.id).distance(120))
  .force('charge', d3.forceManyBody().strength(-400))
  .force('center', d3.forceCenter(w/2, h/2))
  .force('collision', d3.forceCollide(50));
const link = g.append('g').selectAll('line').data(links).join('line').attr('class','link');
const node = g.append('g').selectAll('g').data(nodes).join('g')
  .attr('class', d => d.group===0 ? 'node center-node' : 'node')
  .call(d3.drag()
    .on('start', (e,d) => {{ if(!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }})
    .on('drag', (e,d) => {{ d.fx=e.x; d.fy=e.y; }})
    .on('end', (e,d) => {{ if(!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }}));
node.append('circle')
  .attr('r', d => d.group===0 ? 40 : 18)
  .attr('fill', d => d.group===0 ? '#1a1a2e' : (d.color || '#10b981'))
  .attr('stroke', d => d.group===0 ? '#00d4ff' : 'rgba(255,255,255,0.3)');
node.append('text')
  .attr('text-anchor','middle')
  .attr('dy', '0.35em')
  .attr('fill', d => d.group===0 ? '#00d4ff' : 'white')
  .attr('font-size', d => d.group===0 ? '14px' : '10px')
  .attr('font-weight', d => d.group===0 ? 'bold' : 'normal')
  .each(function(d) {{
    const words = d.text.split(' ').slice(0,4);
    if(words.length <= 2) {{
      d3.select(this).text(words.join(' '));
    }} else {{
      const el = d3.select(this);
      words.slice(0,2).forEach((w,i) => el.append('tspan').attr('x',0).attr('dy', i===0 ? '-0.5em' : '1.2em').text(w));
    }}
  }});
node.append('title').text(d => d.text);
sim.on('tick', () => {{
  link.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y).attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
  node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
}});
</script>
</body></html>"""
