import json
from typing import Dict, Any, List

class MindPalaceAPI:
    """
    Exposes the ChromaDB vector store as nodes and edges for 3D visualization.
    Extracts semantic relationships between stored memories.
    """
    def __init__(self, vector_memory):
        self.vmem = vector_memory

    def get_graph_data(self, tenant_id: int = 1, limit: int = 100) -> Dict[str, Any]:
        """
        Retrieves recent memories and attempts to link them based on simple semantic 
        or timestamp proximity to form a procedural graph.
        """
        nodes = []
        edges = []
        
        # If no ChromaDB, use fallback
        if not self.vmem.active:
            raw_entries = self.vmem.fallback_store[-limit:]
        else:
            try:
                # We fetch a chunk of recent documents
                res = self.vmem.collection.get(
                    where={"tenant_id": str(tenant_id)},
                    limit=limit
                )
                
                raw_entries = []
                if res and res.get("documents"):
                    for i in range(len(res["documents"])):
                        raw_entries.append({
                            "id": res["ids"][i],
                            "text": res["documents"][i],
                            "metadata": res["metadatas"][i] if res.get("metadatas") else {}
                        })
            except Exception as e:
                print(f"Mind Palace retrieval error: {e}")
                raw_entries = []

        # Build nodes
        for idx, entry in enumerate(raw_entries):
            category = entry.get("metadata", {}).get("category", "unknown")
            nodes.append({
                "id": entry["id"],
                "label": entry["text"][:50] + "..." if len(entry["text"]) > 50 else entry["text"],
                "full_text": entry["text"],
                "group": category,
                "val": 10 if category == "knowledge" else 5
            })
            
            # Simple chronological edges: link node to previous node to form a chain
            if idx > 0:
                edges.append({
                    "source": raw_entries[idx-1]["id"],
                    "target": entry["id"],
                    "value": 1
                })
                
        # Simple semantic edges: if they share the same topic
        for i, source in enumerate(raw_entries):
            src_topic = source.get("metadata", {}).get("topic")
            if not src_topic: continue
            
            for j, target in enumerate(raw_entries):
                if i >= j: continue
                tgt_topic = target.get("metadata", {}).get("topic")
                
                if tgt_topic == src_topic:
                    edges.append({
                        "source": source["id"],
                        "target": target["id"],
                        "value": 5 
                    })

        return {
            "nodes": nodes,
            "links": edges
        }
