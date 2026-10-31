"""Story JSON -> Apple-style HTML deck -> PDF (Chromium). Uses the apple-design skill: materials, tight tracking at
display sizes, restrained color, hierarchy through weight and size. Usage: python tools/render_deck.py story.json out.pdf"""
import json, re, sys, html, os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
story = json.load(open(sys.argv[1])); OUT = sys.argv[2]
EYEBROW = {"Where we start": "Context", "Scope map": "Scope", "Architecture": "Technical", "Core data model": "Data",
           "Demo data plan": "Demo", "The 10 minute demo story": "Demo", "One week build plan": "Plan",
           "Business case frame and open questions": "Business case", "Design system foundations": "Design system",
           "Palette options, set 1": "Design system", "Palette options, set 2": "Design system",
           "Recommendation and next steps": "Next steps"}
BLOBS = [("92% -5%", "rgba(15,118,110,.20)", "0% 105%", "rgba(245,158,11,.18)"),
         ("5% -8%", "rgba(37,99,235,.14)", "100% 100%", "rgba(15,118,110,.18)"),
         ("100% 40%", "rgba(245,158,11,.16)", "0% 0%", "rgba(15,118,110,.16)"),
         ("50% -20%", "rgba(124,58,237,.12)", "90% 110%", "rgba(245,158,11,.16)")]

def mk(t):
    t = re.sub(r'\s+size="?\d+"?', "", t)
    return t.replace("&nbsp;|&nbsp;", " &nbsp;&middot;&nbsp; ")

def flat(x):
    for i in x:
        if isinstance(i, list): yield from flat(i)
        else: yield i

def plain(t): return html.unescape(re.sub(r"<[^>]+>", "", t))

def pill(txt):
    k = {"Deep": "deep", "Medium": "med", "Light": "light"}.get(txt)
    return f'<span class="pill {k}">{txt}</span>' if k else None

def table_html(n):
    rows = n["data"]
    def cell(c, head):
        if isinstance(c, dict) and "x" in c:
            txt = c["x"]; p = pill(plain(txt).strip())
            return p or mk(txt)
        return ""
    out = ['<table class="dt"><thead><tr>' + "".join(f"<th>{cell(c, True)}</th>" for c in rows[0]) + "</tr></thead><tbody>"]
    for r in rows[1:]:
        out.append("<tr>" + "".join(f'<td class="{"first" if i == 0 else ""}">{cell(c, False)}</td>' for i, c in enumerate(r)) + "</tr>")
    return "".join(out) + "</tbody></table>"

def swatch_html(n):
    bg = {}
    for cmd in n["style"]:
        if cmd[0] == "BACKGROUND" and cmd[1] == cmd[2]: bg[tuple(cmd[1])] = cmd[3]
    rows = n["data"]; cols = max(len(r) for r in rows); out = [f'<div class="sw" style="grid-template-columns:repeat({cols},1fr)">']
    for ri, r in enumerate(rows):
        for ci, c in enumerate(r):
            if isinstance(c, dict) and (ci, ri) in bg:
                out.append(f'<div class="chip" style="background:{bg[(ci, ri)]}">{mk(c["x"])}</div>')
            else:
                out.append("<div></div>")
    return "".join(out) + "</div>"

def drawing_html(n):
    h = n["h"]; s = [f'<svg viewBox="0 0 {n["w"]} {h}" class="mock" xmlns="http://www.w3.org/2000/svg">']
    for r in n["shapes"]:
        if not r["fill"]: continue
        s.append(f'<rect x="{r["x"]}" y="{h - r["y"] - r["h"]}" width="{r["w"]}" height="{r["h"]}" rx="{r["rx"] or 3}" fill="{r["fill"]}" fill-opacity="{r["op"]}"/>')
    return "".join(s) + "</svg>"

def nodes_html(nodes):
    out, ul = [], []
    def fl():
        if ul: out.append("<ul>" + "".join(ul) + "</ul>"); ul.clear()
    for n in flat(nodes):
        t = n["t"]
        if t == "li": ul.append(f"<li>{mk(n['x'])}</li>"); continue
        fl()
        if t == "p":
            s = n["s"]; c = {"H2": "h2", "SMALL": "small", "BODY": "body", "pn": "ptitle", "TAG": "tag"}.get(s, "body")
            out.append(f'<p class="{c}">{mk(n["x"])}</p>')
        elif t == "table": out.append(table_cell(n))
        elif t == "drawing": out.append(drawing_html(n))
    fl()
    return "".join(out)

def table_cell(n):
    d = n["data"]
    first = d[0][0] if d and d[0] else None
    if isinstance(first, dict) and first.get("s") == "HEAD": return table_html(n)
    if any(c[0] == "BACKGROUND" and c[1] == c[2] for c in n["style"]): return swatch_html(n)
    return grid_html(n)

def grid_html(n):
    d = n["data"]; cols = len(d[0])
    split = any(isinstance(c, dict) and c.get("t") == "drawing" for r in d for c in r)
    cells = []
    for r in d:
        for c in r:
            inner = nodes_html([c]) if isinstance(c, dict) else nodes_html(c)
            cells.append(f'<div class="cell">{inner}</div>')
    cls = "split" if split else "grid"
    cw = "auto 1fr" if split else f"repeat({cols},1fr)"
    return f'<div class="{cls} card" style="grid-template-columns:{cw}">' + "".join(cells) + "</div>"

def blocks(rest):
    out, run = [], []
    def fl():
        if run:
            h = nodes_html(run)
            solo_small = len(run) == 1 and run[0]["t"] == "p" and run[0]["s"] == "SMALL"
            out.append(h if solo_small else f'<div class="card free">{h}</div>'); run.clear()
    for n in flat(rest):
        if n["t"] == "table": fl(); out.append(table_cell(n))
        else: run.append(n)
    fl()
    return "".join(out)

slides, cur = [], []
for n in flat(story):
    if n["t"] == "pb": slides.append(cur); cur = []
    elif n["t"] != "sp": cur.append(n)
if cur: slides.append(cur)

N = len(slides); body = []
for k, sl in enumerate(slides):
    if sl[0].get("s") == "wb":
        txt = [mk(n["x"]) for n in sl if n["t"] == "p"]
        body.append(f'<section class="slide cover"><div class="glow"></div><div class="in"><div class="eyebrow light">Product plan &middot; Draft v1</div>'
                    f'<h1 class="ctitle">{txt[0]}</h1><p class="csub">{txt[1]}</p><p class="cmeta">{txt[2]}</p><p class="cmeta dim">{txt[3]}</p></div></section>')
        continue
    h1 = sl[0]; title = plain(h1["x"]); eyebrow = EYEBROW.get(title, "")
    m = re.match(r"^(\d+)\. (.+)$", title)
    if m: eyebrow, title = f"Module {m.group(1)}", m.group(2)
    elif title.startswith("Foundation: "): eyebrow, title = "Foundation", title[12:]
    elif title.startswith("POS: "): eyebrow, title = "Foundation", title[5:].capitalize()
    rest = sl[1:]; head = ""
    if rest and rest[0]["t"] == "p" and rest[0]["s"] == "sub": head = f'<p class="sub">{mk(rest[0]["x"])}</p>'; rest = rest[1:]
    elif rest and rest[0]["t"] == "p" and rest[0]["s"] == "TAG":
        parts = [p.strip() for p in plain(rest[0]["x"]).split("|")]; d = parts[0].replace("Demo depth: ", "")
        head = f'<div class="meta">{pill(d) or ""}<span>{html.escape(" ".join(parts[1:]))}</span></div>'; rest = rest[1:]
    if rest and rest[0]["t"] == "p" and rest[0]["s"] == "BODY" and any(x["t"] == "table" for x in rest):
        head += f'<p class="lede">{mk(rest[0]["x"])}</p>'; rest = rest[1:]
    b = BLOBS[k % 4]
    style = f"--b1:{b[0]};--c1:{b[1]};--b2:{b[2]};--c2:{b[3]}"
    body.append(f'<section class="slide" style="{style}"><div class="in"><div class="fit"><header>'
                f'{"<div class=eyebrow>" + eyebrow + "</div>" if eyebrow else ""}<h1>{html.escape(title)}</h1>{head}</header>'
                f'<main>{blocks(rest)}</main></div></div><footer><span>Dry Fruit House Operations Platform</span>'
                f'<span>Synthetic demo data</span><span>{k + 1} / {N}</span></footer></section>')

CSS = open(os.path.join(HERE, "deck.css")).read().replace("__FONTS__", "file://" + os.path.join(HERE, "fonts"))
HTML = f"<!doctype html><meta charset=utf-8><style>{CSS}</style>" + "".join(body) + """
<script>
document.fonts.ready.then(()=>{window.__z=[];document.querySelectorAll('.slide:not(.cover) .fit').forEach(f=>{
 const box=f.parentElement;let z=1;f.style.zoom=1;
 while(f.getBoundingClientRect().height<box.clientHeight*0.93 && z<1.3){z+=0.02;f.style.zoom=z;}
 while(f.getBoundingClientRect().height>box.clientHeight && z>0.55){z-=0.02;f.style.zoom=z;}
 window.__z.push(Math.round(z*100));});window.__done=true;});
</script>"""
p = os.path.join(HERE, "deck.html"); open(p, "w").write(HTML)
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 720})
    pg.goto("file://" + p); pg.wait_for_function("window.__done===true", timeout=60000)
    print("zoom per slide:", pg.evaluate("window.__z"))
    pg.pdf(path=OUT, width="1280px", height="720px", print_background=True, prefer_css_page_size=True)
    b.close()
print("pdf ->", OUT)
