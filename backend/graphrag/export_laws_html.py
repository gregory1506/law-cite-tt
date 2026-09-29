"""Export a self-contained, chapter-level atlas of the Laws of Trinidad and Tobago.

The source graph is too large for a useful browser overview (23k+ nodes). This
export keeps every chapter and rolls section-level semantic links up to chapter
pairs. The result is a single HTML file with no runtime dependencies.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRAPH = ROOT / "graphify-out" / "graph.json"
DEFAULT_OUTPUT = ROOT / "citation-tool" / "public" / "laws-graph.html"


def _normalise_chapter(value: str | None) -> str | None:
    if not value:
        return None
    malformed = re.fullmatch(r".+?\s+Chap\s+(\d+)\s+(\d+)", value)
    return f"{malformed.group(1)}:{malformed.group(2)}" if malformed else value


def _chapter_number(node: dict) -> str | None:
    return _normalise_chapter(node.get("chapter_number"))


def _chapter_group(chapter: str) -> str:
    match = re.match(r"^(\d+):", chapter)
    return match.group(1) if match else "Other"


def build_chapter_graph(graph: dict, neighbours: int = 3) -> dict:
    """Collapse section-level semantic edges into a sparse chapter graph."""
    by_id = {node["id"]: node for node in graph["nodes"]}
    chapter_nodes = [node for node in graph["nodes"] if node.get("type") == "chapter"]
    section_counts = Counter(
        _chapter_number(node)
        for node in graph["nodes"]
        if node.get("type") == "idea" and _chapter_number(node)
    )

    pair_stats: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"count": 0, "total": 0.0, "max": 0.0}
    )
    for edge in graph["edges"]:
        if edge.get("type") != "SEMANTIC":
            continue
        source = _chapter_number(by_id.get(edge["source"], {}))
        target = _chapter_number(by_id.get(edge["target"], {}))
        if not source or not target or source == target:
            continue
        pair = tuple(sorted((source, target)))
        weight = float(edge.get("weight", 0))
        stats = pair_stats[pair]
        stats["count"] += 1
        stats["total"] += weight
        stats["max"] = max(stats["max"], weight)

    adjacency: dict[str, list[tuple[float, tuple[str, str]]]] = defaultdict(list)
    for pair, stats in pair_stats.items():
        # Multiple matching provisions are stronger evidence than a single hit,
        # while the logarithm prevents large Acts from dominating the atlas.
        score = stats["max"] + math.log1p(stats["count"]) * 0.025
        adjacency[pair[0]].append((score, pair))
        adjacency[pair[1]].append((score, pair))

    chosen_pairs: set[tuple[str, str]] = set()
    for candidates in adjacency.values():
        candidates.sort(reverse=True)
        chosen_pairs.update(pair for _, pair in candidates[:neighbours])

    group_counts = Counter(
        _chapter_group(_chapter_number(node) or "Other")
        for node in chapter_nodes
    )
    ordered_groups = sorted(
        group_counts,
        key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else 999, value),
    )
    group_index = {group: index for index, group in enumerate(ordered_groups)}

    nodes = []
    for node in sorted(chapter_nodes, key=lambda item: item.get("chapter_number", "")):
        raw_chapter = node.get("chapter_number", "Unknown")
        chapter = _normalise_chapter(raw_chapter) or "Unknown"
        group = _chapter_group(chapter)
        title = node.get("label") or chapter
        malformed_title = re.fullmatch(r"(.+?)\s+Chap\s+\d+\s+\d+", title)
        if malformed_title:
            title = malformed_title.group(1)
        nodes.append(
            {
                "id": chapter,
                "title": title,
                "group": group,
                "groupIndex": group_index[group],
                "sections": section_counts[chapter],
                "year": node.get("year") or "",
                "classification": node.get("classification") or "",
            }
        )

    links = []
    for source, target in sorted(chosen_pairs):
        stats = pair_stats[(source, target)]
        links.append(
            {
                "source": source,
                "target": target,
                "matches": stats["count"],
                "similarity": round(stats["max"], 4),
                "average": round(stats["total"] / stats["count"], 4),
                "evidence": "INFERRED",
            }
        )

    return {
        "nodes": nodes,
        "links": links,
        "groups": [
            {"id": group, "count": group_counts[group], "index": group_index[group]}
            for group in ordered_groups
        ],
        "meta": {
            "chapters": len(nodes),
            "links": len(links),
            "sections": sum(section_counts.values()),
            "sourceNodes": len(graph["nodes"]),
            "sourceEdges": len(graph["edges"]),
        },
    }


HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="theme-color" content="#080d14">
  <link rel="icon" href="data:,">
  <title>Atlas of the Laws of Trinidad and Tobago</title>
  <style>
    :root {
      color-scheme: dark;
      --ink: #f3efe3;
      --muted: #91a0ad;
      --faint: #52616e;
      --gold: #e7b84b;
      --coral: #f1785c;
      --panel: rgba(13, 21, 31, .92);
      --line: rgba(177, 194, 207, .17);
      --border: rgba(198, 211, 219, .18);
      --serif: Iowan Old Style, Palatino Linotype, Book Antiqua, Palatino, Georgia, serif;
      --sans: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif;
    }
    * { box-sizing: border-box; }
    html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; }
    body {
      background: #080d14;
      color: var(--ink);
      font-family: var(--sans);
    }
    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background:
        radial-gradient(circle at 68% 38%, rgba(39, 77, 98, .21), transparent 38%),
        linear-gradient(rgba(255,255,255,.018) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.018) 1px, transparent 1px);
      background-size: auto, 40px 40px, 40px 40px;
    }
    button, input { font: inherit; }
    button { color: inherit; }
    .skip-link {
      position: fixed; left: 16px; top: -60px; z-index: 20;
      padding: 9px 13px; background: var(--gold); color: #171006;
      border-radius: 4px; font-weight: 800;
    }
    .skip-link:focus { top: 14px; }
    .shell { position: relative; width: 100%; height: 100%; }
    canvas { display: block; width: 100%; height: 100%; cursor: grab; touch-action: none; }
    canvas.dragging { cursor: grabbing; }
    .masthead {
      position: fixed; top: 24px; left: 26px; z-index: 3;
      max-width: min(520px, calc(100vw - 52px)); pointer-events: none;
    }
    .kicker {
      display: flex; align-items: center; gap: 9px; margin: 0 0 8px;
      color: var(--gold); font-size: 11px; font-weight: 800;
      letter-spacing: .16em; text-transform: uppercase;
    }
    .kicker::before { content: ""; width: 22px; height: 2px; background: var(--gold); }
    h1 {
      margin: 0; max-width: 510px; font: 600 clamp(30px, 4vw, 58px)/.96 var(--serif);
      letter-spacing: -.035em; text-wrap: balance;
    }
    .lede {
      margin: 12px 0 0; max-width: 460px; color: var(--muted);
      font-size: 13px; line-height: 1.55;
    }
    .lede strong { color: var(--ink); font-weight: 700; }
    .toolbar {
      position: fixed; top: 24px; right: 26px; z-index: 5;
      display: flex; align-items: center; gap: 8px;
    }
    .search-wrap { position: relative; }
    .search-wrap svg {
      position: absolute; left: 11px; top: 50%; width: 15px; transform: translateY(-50%);
      color: var(--muted); pointer-events: none;
    }
    #search {
      width: min(300px, 38vw); height: 40px; padding: 0 34px 0 35px;
      border: 1px solid var(--border); border-radius: 5px;
      outline: 0; background: var(--panel); color: var(--ink);
      box-shadow: 0 14px 40px rgba(0,0,0,.24); backdrop-filter: blur(12px);
    }
    #search::placeholder { color: var(--muted); }
    #search:focus { border-color: var(--gold); box-shadow: 0 0 0 3px rgba(231,184,75,.13); }
    #clearSearch {
      position: absolute; right: 5px; top: 5px; width: 30px; height: 30px;
      border: 0; background: transparent; color: var(--muted); cursor: pointer;
    }
    #clearSearch[hidden] { display: none; }
    .icon-button {
      display: grid; width: 40px; height: 40px; place-items: center;
      border: 1px solid var(--border); border-radius: 5px;
      background: var(--panel); cursor: pointer; backdrop-filter: blur(12px);
    }
    .icon-button:hover, .icon-button:focus-visible { border-color: var(--gold); outline: none; }
    .icon-button svg { width: 17px; }
    .status {
      position: fixed; left: 26px; bottom: 24px; z-index: 4;
      display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    }
    .metric, .legend-item {
      min-height: 30px; display: inline-flex; align-items: center; gap: 7px;
      padding: 0 10px; border: 1px solid var(--border); border-radius: 4px;
      background: rgba(10, 16, 24, .82); color: var(--muted); font-size: 11px;
      backdrop-filter: blur(10px);
    }
    .metric strong { color: var(--ink); }
    .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--gold); box-shadow: 0 0 9px var(--gold); }
    .line-swatch { width: 20px; height: 1px; background: rgba(127,189,218,.7); }
    .detail {
      position: fixed; right: 26px; bottom: 24px; z-index: 6;
      width: min(350px, calc(100vw - 52px)); max-height: min(480px, calc(100vh - 100px));
      overflow: auto; padding: 20px; border: 1px solid var(--border); border-radius: 6px;
      background: var(--panel); box-shadow: 0 24px 70px rgba(0,0,0,.48);
      backdrop-filter: blur(18px); transform-origin: bottom right;
      transition: opacity .18s ease, transform .18s ease;
    }
    .detail[hidden] { display: none; }
    .detail-top { display: flex; justify-content: space-between; gap: 12px; }
    .detail .chapter { margin: 0 0 4px; color: var(--gold); font: 800 12px/1 var(--sans); letter-spacing: .12em; text-transform: uppercase; }
    .detail h2 { margin: 0; font: 600 27px/1.05 var(--serif); letter-spacing: -.02em; }
    .close {
      flex: 0 0 auto; width: 30px; height: 30px; border: 1px solid var(--border);
      border-radius: 4px; background: transparent; cursor: pointer;
    }
    .detail-stats { display: flex; gap: 18px; margin: 18px 0; padding: 13px 0; border-block: 1px solid var(--border); }
    .detail-stats span { display: grid; gap: 2px; color: var(--muted); font-size: 10px; text-transform: uppercase; letter-spacing: .08em; }
    .detail-stats strong { color: var(--ink); font-size: 15px; letter-spacing: 0; }
    .detail h3 { margin: 0 0 9px; color: var(--muted); font-size: 10px; text-transform: uppercase; letter-spacing: .12em; }
    .connections { display: grid; gap: 5px; margin: 0; padding: 0; list-style: none; }
    .connections button {
      width: 100%; padding: 8px 9px; border: 0; border-left: 2px solid rgba(127,189,218,.45);
      background: rgba(255,255,255,.025); text-align: left; cursor: pointer;
    }
    .connections button:hover, .connections button:focus-visible { background: rgba(231,184,75,.09); border-left-color: var(--gold); outline: none; }
    .connections b { display: block; color: var(--ink); font-size: 12px; }
    .connections small { color: var(--muted); font-size: 10px; }
    .notice {
      position: fixed; left: 50%; top: 50%; z-index: 8; transform: translate(-50%,-50%);
      padding: 12px 16px; border: 1px solid var(--border); border-radius: 5px;
      background: var(--panel); color: var(--muted); font-size: 12px; pointer-events: none;
      opacity: 0; transition: opacity .18s ease;
    }
    .notice.show { opacity: 1; }
    @media (max-width: 760px) {
      .masthead { top: 18px; left: 18px; }
      .masthead h1 { max-width: 310px; font-size: 34px; }
      .lede { max-width: 300px; font-size: 11px; }
      .toolbar { top: auto; right: 18px; left: 18px; bottom: 18px; }
      #search { width: 100%; }
      .search-wrap { flex: 1; }
      .status { left: 18px; bottom: 68px; right: 18px; }
      .status .legend-item { display: none; }
      .detail { right: 18px; bottom: 68px; width: calc(100vw - 36px); max-height: 42vh; }
    }
    @media (prefers-reduced-motion: reduce) { .detail, .notice { transition: none; } }
  </style>
</head>
<body>
  <a class="skip-link" href="#search">Skip to graph search</a>
  <main class="shell" aria-label="Interactive graph of the Laws of Trinidad and Tobago">
    <canvas id="graph" aria-label="Chapter graph. Search for or select a law to inspect its connections."></canvas>
    <header class="masthead">
      <p class="kicker">LawCite TT · Statute Atlas</p>
      <h1>The laws,<br>seen as a system.</h1>
      <p class="lede"><strong>Every point is one statutory chapter.</strong> Proximity groups chapter families; lines show strong section-level semantic relationships. Select a point to trace its neighbourhood.</p>
    </header>
    <div class="toolbar" role="search">
      <div class="search-wrap">
        <label for="search" style="position:absolute;clip:rect(0 0 0 0)">Find a law</label>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="m20 20-3.7-3.7"></path></svg>
        <input id="search" type="search" autocomplete="off" aria-label="Find a law" placeholder="Find a law or chapter…">
        <button id="clearSearch" type="button" aria-label="Clear search" hidden>×</button>
      </div>
      <button class="icon-button" id="reset" type="button" title="Reset view" aria-label="Reset graph view">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"></path><path d="M3 3v5h5"></path></svg>
      </button>
    </div>
    <div class="status" aria-label="Graph legend">
      <span class="metric"><span class="dot"></span><strong id="chapterCount"></strong> chapters</span>
      <span class="metric"><strong id="sectionCount"></strong> provisions</span>
      <span class="legend-item"><span class="line-swatch"></span> inferred semantic relationship</span>
    </div>
    <aside class="detail" id="detail" aria-live="polite" hidden>
      <div class="detail-top">
        <div><p class="chapter" id="detailChapter"></p><h2 id="detailTitle"></h2></div>
        <button class="close" id="closeDetail" type="button" aria-label="Close law details">×</button>
      </div>
      <div class="detail-stats"><span>Provisions<strong id="detailSections"></strong></span><span>Family<strong id="detailGroup"></strong></span><span>Links<strong id="detailLinks"></strong></span></div>
      <h3>Strongest relationships</h3>
      <ul class="connections" id="connections"></ul>
    </aside>
    <div class="notice" id="notice" role="status"></div>
  </main>
  <script>
    const DATA = __GRAPH_DATA__;
    const canvas = document.querySelector('#graph');
    const ctx = canvas.getContext('2d');
    const detail = document.querySelector('#detail');
    const search = document.querySelector('#search');
    const clearSearch = document.querySelector('#clearSearch');
    const notice = document.querySelector('#notice');
    const nodeById = new Map(DATA.nodes.map(node => [node.id, node]));
    const linksByNode = new Map(DATA.nodes.map(node => [node.id, []]));
    DATA.links.forEach(link => {
      linksByNode.get(link.source)?.push({...link, other: link.target});
      linksByNode.get(link.target)?.push({...link, other: link.source});
    });

    let width = 0, height = 0, dpr = 1;
    let camera = { x: 0, y: 0, scale: 1 };
    let selected = null, hovered = null, matches = new Set();
    let pointer = null, moved = false;
    const palette = ['#e7b84b','#f1785c','#72b7ce','#7bc4a4','#be8ddb','#d6965c','#86aee8','#d0d877'];

    function layoutNodes() {
      const rings = Math.ceil(Math.sqrt(DATA.groups.length));
      DATA.groups.forEach((group, gi) => {
        const angle = gi * 2.399963;
        const radius = 150 + 115 * Math.sqrt(gi);
        group.x = Math.cos(angle) * radius;
        group.y = Math.sin(angle) * radius;
      });
      const grouped = new Map(DATA.groups.map(group => [group.id, []]));
      DATA.nodes.forEach(node => grouped.get(node.group)?.push(node));
      grouped.forEach((nodes, groupId) => {
        const group = DATA.groups.find(item => item.id === groupId);
        nodes.sort((a, b) => a.id.localeCompare(b.id, undefined, {numeric: true}));
        nodes.forEach((node, index) => {
          const a = index * 2.399963 + group.index * .29;
          const r = 16 + 10.5 * Math.sqrt(index);
          node.x = group.x + Math.cos(a) * r;
          node.y = group.y + Math.sin(a) * r;
          node.radius = 2.6 + Math.min(4.4, Math.sqrt(node.sections) * .22);
        });
      });
    }

    function fitCamera() {
      const xs = DATA.nodes.map(n => n.x), ys = DATA.nodes.map(n => n.y);
      const bounds = {minX: Math.min(...xs)-90, maxX: Math.max(...xs)+90, minY: Math.min(...ys)-90, maxY: Math.max(...ys)+90};
      camera.scale = Math.min(width/(bounds.maxX-bounds.minX), height/(bounds.maxY-bounds.minY)) * .92;
      camera.x = width/2 - ((bounds.minX+bounds.maxX)/2)*camera.scale;
      camera.y = height/2 - ((bounds.minY+bounds.maxY)/2)*camera.scale;
    }

    function resize() {
      width = innerWidth; height = innerHeight; dpr = Math.min(devicePixelRatio || 1, 2);
      canvas.width = width*dpr; canvas.height = height*dpr;
      canvas.style.width = width+'px'; canvas.style.height = height+'px';
      ctx.setTransform(dpr,0,0,dpr,0,0);
      fitCamera();
      draw();
    }
    const screen = node => ({x: node.x*camera.scale+camera.x, y: node.y*camera.scale+camera.y});

    function draw() {
      ctx.setTransform(dpr,0,0,dpr,0,0);
      ctx.clearRect(0,0,width,height);
      const focus = selected || hovered;
      const neighbours = focus ? new Set((linksByNode.get(focus)||[]).map(l=>l.other)) : null;
      ctx.lineCap = 'round';
      DATA.links.forEach(link => {
        if (focus && link.source !== focus && link.target !== focus) return;
        const a = screen(nodeById.get(link.source)), b = screen(nodeById.get(link.target));
        ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y);
        ctx.strokeStyle = focus ? 'rgba(132,202,230,.62)' : `rgba(109,160,181,${Math.min(.18,.035+link.matches*.009)})`;
        ctx.lineWidth = focus ? Math.min(2.2,.7+link.matches*.08) : .55;
        ctx.stroke();
      });
      DATA.nodes.forEach(node => {
        const p = screen(node);
        if (p.x < -15 || p.y < -15 || p.x > width+15 || p.y > height+15) return;
        const isFocus = node.id === focus;
        const isNeighbour = neighbours?.has(node.id);
        const isMatch = matches.has(node.id);
        let alpha = focus && !isFocus && !isNeighbour ? .12 : matches.size && !isMatch ? .16 : .82;
        const color = palette[node.groupIndex % palette.length];
        const radius = Math.max(1.5, node.radius * Math.sqrt(camera.scale));
        ctx.globalAlpha = alpha;
        if (isFocus || isMatch) {
          ctx.beginPath(); ctx.arc(p.x,p.y,radius+7,0,Math.PI*2);
          ctx.fillStyle = isFocus ? 'rgba(231,184,75,.17)' : 'rgba(241,120,92,.16)'; ctx.fill();
        }
        ctx.beginPath(); ctx.arc(p.x,p.y,radius+(isFocus?2:0),0,Math.PI*2);
        ctx.fillStyle = isFocus ? '#fff1bd' : isMatch ? '#ff8b70' : color;
        ctx.shadowBlur = isFocus || isMatch ? 14 : 4; ctx.shadowColor = ctx.fillStyle; ctx.fill();
        ctx.shadowBlur = 0; ctx.globalAlpha = 1;
        if (isFocus || isMatch || (camera.scale > .72 && (isNeighbour || node.sections > 140))) {
          ctx.font = `${isFocus ? 700 : 600} ${isFocus ? 12 : 10}px var(--sans)`;
          ctx.fillStyle = isFocus ? '#fff4d2' : '#c9d2d9';
          ctx.fillText(`${node.id} · ${node.title}`, p.x+radius+6, p.y+3, 230);
        }
      });
      if (!focus && matches.size === 0) drawGroupLabels();
    }

    function drawGroupLabels() {
      if (width < 760) return;
      DATA.groups.forEach(group => {
        const p = {x:group.x*camera.scale+camera.x, y:group.y*camera.scale+camera.y};
        if (p.x<0||p.y<0||p.x>width||p.y>height) return;
        ctx.font = '700 9px var(--sans)'; ctx.fillStyle = 'rgba(224,231,234,.35)';
        ctx.fillText(`CHAPTER ${group.id} · ${group.count}`, p.x+7, p.y-9);
      });
    }

    function hitTest(x,y) {
      let hit=null, distance=14;
      DATA.nodes.forEach(node => {
        const p=screen(node), d=Math.hypot(p.x-x,p.y-y);
        if(d<distance){hit=node;distance=d;}
      });
      return hit;
    }

    function selectNode(node, recenter=false) {
      selected = node?.id || null;
      if (!node) { detail.hidden=true; draw(); return; }
      detail.hidden=false;
      document.querySelector('#detailChapter').textContent=`Chapter ${node.id}`;
      document.querySelector('#detailTitle').textContent=node.title;
      document.querySelector('#detailSections').textContent=node.sections.toLocaleString();
      document.querySelector('#detailGroup').textContent=`${node.group}:xx`;
      const links=[...(linksByNode.get(node.id)||[])].sort((a,b)=>b.matches-a.matches||b.similarity-a.similarity);
      document.querySelector('#detailLinks').textContent=links.length;
      const list=document.querySelector('#connections'); list.replaceChildren();
      links.slice(0,8).forEach(link=>{
        const other=nodeById.get(link.other), li=document.createElement('li'), button=document.createElement('button');
        button.innerHTML=`<b>Chap. ${escapeHTML(other.id)} · ${escapeHTML(other.title)}</b><small>${link.matches} matching section pair${link.matches===1?'':'s'} · up to ${Math.round(link.similarity*100)}% similar</small>`;
        button.onclick=()=>selectNode(other,true); li.append(button); list.append(li);
      });
      if (recenter) {
        const targetScale=Math.max(camera.scale,1.05);
        camera.scale=targetScale; camera.x=width*.52-node.x*targetScale; camera.y=height*.48-node.y*targetScale;
      }
      draw();
    }

    function escapeHTML(value) { const div=document.createElement('div'); div.textContent=value; return div.innerHTML; }
    function announce(message) { notice.textContent=message; notice.classList.add('show'); clearTimeout(announce.timer); announce.timer=setTimeout(()=>notice.classList.remove('show'),1500); }

    canvas.addEventListener('pointerdown', event=>{ pointer={x:event.clientX,y:event.clientY,cx:camera.x,cy:camera.y}; moved=false; canvas.setPointerCapture(event.pointerId); canvas.classList.add('dragging'); });
    canvas.addEventListener('pointermove', event=>{
      if(pointer){ const dx=event.clientX-pointer.x,dy=event.clientY-pointer.y; if(Math.hypot(dx,dy)>3)moved=true; camera.x=pointer.cx+dx;camera.y=pointer.cy+dy;draw();return; }
      const hit=hitTest(event.clientX,event.clientY); const next=hit?.id||null;
      if(next!==hovered){hovered=next;canvas.style.cursor=hit?'pointer':'grab';draw();}
    });
    canvas.addEventListener('pointerup', event=>{ if(!moved)selectNode(hitTest(event.clientX,event.clientY)); pointer=null;canvas.classList.remove('dragging'); });
    canvas.addEventListener('pointercancel',()=>{pointer=null;canvas.classList.remove('dragging');});
    canvas.addEventListener('wheel', event=>{
      event.preventDefault(); const old=camera.scale, factor=Math.exp(-event.deltaY*.0012);
      camera.scale=Math.max(.16,Math.min(4,old*factor));
      camera.x=event.clientX-(event.clientX-camera.x)*(camera.scale/old);
      camera.y=event.clientY-(event.clientY-camera.y)*(camera.scale/old); draw();
    },{passive:false});

    search.addEventListener('input',()=>{
      const q=search.value.trim().toLowerCase(); clearSearch.hidden=!q;
      matches=new Set(q ? DATA.nodes.filter(n=>n.id.toLowerCase().includes(q)||n.title.toLowerCase().includes(q)).map(n=>n.id) : []);
      draw();
      if(q && matches.size===1) selectNode(nodeById.get([...matches][0]),true);
    });
    search.addEventListener('keydown',event=>{
      if(event.key==='Enter'&&matches.size){event.preventDefault();selectNode(nodeById.get([...matches][0]),true);}
      if(event.key==='Escape'){clearSearch.click();search.blur();}
    });
    clearSearch.onclick=()=>{search.value='';matches.clear();clearSearch.hidden=true;draw();search.focus();};
    document.querySelector('#reset').onclick=()=>{selected=null;hovered=null;detail.hidden=true;search.value='';matches.clear();clearSearch.hidden=true;fitCamera();draw();announce('Full atlas restored');};
    document.querySelector('#closeDetail').onclick=()=>selectNode(null);
    addEventListener('resize',resize);

    document.querySelector('#chapterCount').textContent=DATA.meta.chapters.toLocaleString();
    document.querySelector('#sectionCount').textContent=DATA.meta.sections.toLocaleString();
    layoutNodes(); resize();
  </script>
</body>
</html>
'''


def export_html(graph_path: Path, output_path: Path, neighbours: int = 3) -> dict:
    graph = json.loads(graph_path.read_text())
    chapter_graph = build_chapter_graph(graph, neighbours=neighbours)
    payload = json.dumps(chapter_graph, separators=(",", ":"), ensure_ascii=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(HTML_TEMPLATE.replace("__GRAPH_DATA__", payload))
    return chapter_graph["meta"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--neighbours", type=int, default=3)
    args = parser.parse_args()
    meta = export_html(args.graph, args.output, neighbours=args.neighbours)
    print(
        f"wrote {args.output} "
        f"({meta['chapters']} chapters, {meta['sections']} provisions, {meta['links']} links)"
    )


if __name__ == "__main__":
    main()
