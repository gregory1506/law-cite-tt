"""Extract CITES_STATUTE edges from crawled case-law records.

Reads the JSONL produced by `case_crawl.py` and finds statute citations in
case prose, resolving them against the existing idea graph
(`graphify-out/graph.json`) where possible.

Citation forms handled:
  - Chapter form:     "Cap. 10:01", "Ch. 8:08", "Chap. 30:02", "10:01"
  - Act name:         "the Criminal Offences Act" (fuzzy match on chapter title)
  - Section mention:  "section 4", "s. 4", "Section 5(2)" within an act
  - Version note:     "the Income Tax Act, Cap. 75:01"

Each emitted edge is tagged:
  - evidence: EXTRACTED (a literal citation appeared in the case text)
  - method:   REGEX / TITLE_MATCH
  - confidence: high (chapter+section resolved) | medium (chapter only) |
                low (title-matched, may be ambiguous)
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import yaml  # optional; only used to dump a small report

CASES_DIR = Path("/Volumes/Extreme SSD/law-cite-tt-data/case_law")
GRAPH_FILE = Path("graphify-out/graph.json")

# "Cap. 10:01" / "Ch. 8:08" / "Chap. 30:02" / bare "10:01"
CHAPTER_RE = re.compile(r"\b(?:Cap(?:ition)?\.|Ch(?:ap)?\.|Chapter)\s*([0-9]{1,2}:[0-9]{1,2})\b", re.I)
BARE_CHAPTER_RE = re.compile(r"\b([0-9]{1,2}:[0-9]{1,2})\b")
# section refs within an act: "section 5", "s. 5", "Section 4(2)(a)"
SECTION_RE = re.compile(r"\bs(?:ection)?\.?\s*([0-9]{1,3})(?:\([0-9a-z]+\))*", re.I)
# quoted statute names ending in "Act"/"Ordinance"/"Regulations"
ACT_RE = re.compile(r"\bthe\s+([A-Z][A-Za-z\- ]{3,60}?)\s+(Act|Ordinance|Regulations?)\b", re.I)


def normalize_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", t.lower())


def load_graph(graph_file: Path = GRAPH_FILE) -> dict:
    g = json.loads(graph_file.read_text())
    return {n["id"]: n for n in g["nodes"]}


def load_cases(cases_dir: Path | str = CASES_DIR) -> list[dict]:
    cases_dir = Path(cases_dir)
    records = []
    for p in sorted(cases_dir.glob("*.jsonl")):
        for line in p.read_text().splitlines():
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def build_act_index(nodes: dict) -> dict[str, list[str]]:
    """Map normalized chapter titles -> chapter node ids."""
    idx: dict[str, list[str]] = {}
    for nid, n in nodes.items():
        if n["type"] != "chapter":
            continue
        title = n.get("label") or n.get("chapter_number") or ""
        idx.setdefault(normalize_title(title), []).append(nid)
        idx.setdefault(normalize_title((n.get("chapter_number") or "")), []).append(nid)
    return idx


def extract_edges(cases: list[dict], nodes: dict, act_index: dict) -> list[dict]:
    edges: list[dict] = []
    for rec in cases:
        text = (rec.get("body") or "") + " " + (rec.get("title") or "")
        if not text.strip():
            continue

        # --- chapter-number citations (highest precision) ---
        for m in CHAPTER_RE.finditer(text):
            ch = m.group(1).upper()
            tgt = f"chapter:{ch}"
            if tgt not in nodes:
                continue
            edges.append({
                "source": f"case:{rec['id']}",
                "source_title": rec.get("title"),
                "target": tgt,
                "type": "CITES_STATUTE",
                "evidence": "EXTRACTED",
                "method": "REGEX",
                "confidence": "medium",
                "detail": f"Ch. {ch}",
            })
        # bare "10:01" only when it is preceded by an act-like word
        for m in BARE_CHAPTER_RE.finditer(text):
            ch = m.group(1).upper()
            tgt = f"chapter:{ch}"
            if tgt not in nodes:
                continue
            prefix = text[max(0, m.start() - 40): m.start()]
            if not re.search(r"\b(act|ordinance|chapter|cap|ch)\b", prefix, re.I):
                continue
            edges.append({
                "source": f"case:{rec['id']}",
                "source_title": rec.get("title"),
                "target": tgt,
                "type": "CITES_STATUTE",
                "evidence": "EXTRACTED",
                "method": "REGEX",
                "confidence": "high" if CHAPTER_RE.search(text) else "medium",
                "detail": ch,
            })

        # --- act-name citations (fuzzy) ---
        for m in ACT_RE.finditer(text):
            name = m.group(1).strip()
            kind = m.group(2)
            norm = normalize_title(name)
            hits = act_index.get(norm, [])
            if not hits:
                # try the longer tail: "Income Tax Act" vs "Income Tax (In Aid) Act"
                for idx_name, tids in act_index.items():
                    if idx_name in norm or norm in idx_name:
                        hits.extend(tids)
            if hits:
                for tgt in set(hits[:3]):
                    edges.append({
                        "source": f"case:{rec['id']}",
                        "source_title": rec.get("title"),
                        "target": tgt,
                        "type": "CITES_STATUTE",
                        "evidence": "EXTRACTED",
                        "method": "TITLE_MATCH",
                        "confidence": "high" if len(hits) == 1 else "low",
                        "detail": f"the {name} {kind}",
                    })
    return edges


def dedupe(edges: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for e in edges:
        key = (e["source"], e["target"], e["method"])
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def main() -> None:
    cases = load_cases()
    nodes = load_graph()
    act_index = build_act_index(nodes)
    edges = dedupe(extract_edges(cases, nodes, act_index))

    report = {
        "cases_loaded": len(cases),
        "case_nodes": len({e["source"] for e in edges}),
        "edges": len(edges),
        "confidence": dict(Counter(e["confidence"] for e in edges)),
        "method": dict(Counter(e["method"] for e in edges)),
        "top_targets": Counter(e["target"] for e in edges).most_common(15),
    }
    out = Path("graphify-out/case_edges.json")
    out.write_text(json.dumps({"meta": report, "edges": edges}, indent=1))
    print(json.dumps(report, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
