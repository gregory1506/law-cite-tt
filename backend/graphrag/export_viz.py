"""Generate interactive HTML viz (subset for browser) + Neo4j cypher export."""
import json
import random
from collections import Counter
from pathlib import Path

OUT = Path("graphify-out")


def make_html(max_nodes: int = 400, max_edges: int = 2500) -> None:
    g = json.loads((OUT / "graph.json").read_text())
    nodes, edges = g["nodes"], g["edges"]

    random.seed(42)
    # anchor on the biggest semantic clusters: keep high-degree nodes + their
    # highest-weight edges to stay under the browser budget
    degrees = Counter()
    for e in edges:
        degrees[e["source"]] += 1
        degrees[e["target"]] += 1

    chosen = sorted(
        [n for n in nodes if n["type"] == "concept"],
        key=lambda n: -n.get("n_ideas", 0),
    )[:30]
    chosen_ids = {n["id"] for n in chosen}
    # pull ideas adjacent to concepts + top-degree ideas
    by_degree = sorted(nodes, key=lambda n: -degrees.get(n["id"], 0))
    for n in by_degree:
        if len(chosen_ids) >= max_nodes:
            break
        chosen_ids.add(n["id"])
    for e in edges:
        if len(chosen_ids) >= max_nodes:
            break
        if e["source"] in chosen_ids or e["target"] in chosen_ids:
            chosen_ids.add(e["source"])
            chosen_ids.add(e["target"])

    kept_nodes = [n for n in nodes if n["id"] in chosen_ids]
    id2idx = {n["id"]: i for i, n in enumerate(kept_nodes)}
    kept_edges = []
    for e in edges:
        if e["source"] in id2idx and e["target"] in id2idx and e["type"] != "PART_OF":
            kept_edges.append((id2idx[e["source"]], id2idx[e["target"]], e["type"]))
        if len(kept_edges) >= max_edges:
            break

    node_data = [
        {
            "id": n["id"],
            "label": n["label"][:40],
            "type": n["type"],
            "size": 8 if n["type"] == "concept" else (4 if n["type"] == "idea" else 12),
        }
        for n in kept_nodes
    ]
    colors = {"chapter": "#ef5350", "idea": "#42a5f5", "concept": "#66bb6a"}
    links = [{"source": s, "target": t, "type": ty} for s, t, ty in kept_edges]
    colors_json = json.dumps(colors)
    nodes_json = json.dumps(node_data)
    links_json = json.dumps(links)
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Laws of TT — GraphRAG</title>
<script src="https://cdn.jsdelivr.net/npm/force-graph@1.44.4/dist/force-graph.min.js"></script>
<style>body{{margin:0;font-family:ui-monospace,Menlo,monospace;background:#0d1117;color:#c9d1d9}}
#top{{position:fixed;top:10px;left:12px;z-index:9;font-size:13px;background:#161b22;padding:6px 12px;border-radius:6px;border:1px solid #30363d}}
</style></head><body>
<div id="top">Laws of Trinidad and Tobago — GraphRAG (n={len(node_data)}, e={len(kept_edges)})
<span style="color:#66bb6a">green=concept</span> <span style="color:#42a5f5">blue=idea</span> <span style="color:#ef5350">red=chapter</span></div>
<script>
const data={{nodes:{nodes_json},links:{links_json}}};
const g=ForceGraph()(document.body).graphData(data)
 .nodeColor(d=>({colors_json})[d.type])
 .nodeVal(d=>d.size).nodeLabel(d=>d.label)
 .linkColor(l=>l.type==='SEMANTIC'?'rgba(100,140,255,0.15)':'rgba(230,230,230,0.35)')
 .linkWidth(0.6).nodeRelSize(4).cooldownTicks(150);
</script></body></html>"""
    (OUT / "graph.html").write_text(html)
    print(f"wrote graph.html ({len(node_data)} nodes, {len(kept_edges)} edges)")


def make_cypher(max_nodes: int = 2000) -> None:
    g = json.loads((OUT / "graph.json").read_text())
    nodes, edges = g["nodes"], g["edges"]
    id2idx = {}
    lines = ["// GraphRAG import for the Laws of Trinidad and Tobago", ""]
    n_emitted = 0
    for n in nodes:
        if n["type"] == "chapter" or n["type"] == "concept" or n_emitted < max_nodes:
            id2idx[n["id"]] = True
            label = (n["label"] or n["id"]).replace("\\", " ").replace('"', "'")
            lines.append(
                f'CREATE (n:`{n["type"].upper()}` {{id:"{n["id"]}", label:"{label[:80]}"}});'
            )
            n_emitted += 1
    for e in edges:
        if e["source"] in id2idx and e["target"] in id2idx:
            rel = e["type"]
            lines.append(
                f'MATCH (a {{id:"{e["source"]}"}}),(b {{id:"{e["target"]}"}}) '
                f'CREATE (a)-[:{rel} {{evidence:"{e["evidence"]}"}}]->(b);'
            )
    (OUT / "graph.cypher").write_text("\n".join(lines))
    print(f"wrote graph.cypher ({len(lines)} statements)")


if __name__ == "__main__":
    make_html()
    make_cypher()
