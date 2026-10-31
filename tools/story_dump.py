"""Run docs/build_book.py under a shim so its content (not its reportlab layout) is captured as JSON.
That keeps one source of content for both the v1 reportlab PDF and the v2 HTML deck."""
import sys, types, json
class Color:
    def __init__(s, h):
        s.hex = h.upper(); x = s.hex.lstrip("#"); s.red, s.green, s.blue = [int(x[i:i + 2], 16) / 255 for i in (0, 2, 4)]
class Tbl:
    def __init__(s, data, colWidths=None, repeatRows=0, rowHeights=None): s.data, s.style = data, []
    def setStyle(s, st): s.style = st
class Drawing:
    def __init__(s, w, h): s.w, s.h, s.shapes = w, h, []
    def add(s, sh): s.shapes.append(sh)
class Rect:
    def __init__(s, x, y, w, h, fillColor=None, strokeColor=None, rx=0, ry=0, fillOpacity=1, **k):
        s.x, s.y, s.w, s.h, s.fill, s.rx, s.op = x, y, w, h, fillColor, rx, fillOpacity
class Doc:
    out = None
    def __init__(s, *a, **k): pass
    def addPageTemplates(s, x): pass
    def build(s, story): Doc.out = story
def mod(name, **kw):
    m = types.ModuleType(name); m.__dict__.update(kw); sys.modules[name] = m; return m
sty = lambda name, **k: name
P_ = lambda text, style, bulletText=None: {"t": "li" if bulletText else "p", "s": style, "x": text}
colors = mod("reportlab.lib.colors", HexColor=Color, white=Color("#FFFFFF"))
mod("reportlab", lib=None)
mod("reportlab.lib", colors=colors)
mod("reportlab.lib.pagesizes", A4=(595.27, 841.89), landscape=lambda s: (max(s), min(s)))
mod("reportlab.lib.styles", ParagraphStyle=sty)
mod("reportlab.lib.enums", TA_LEFT=0)
mod("reportlab.platypus", BaseDocTemplate=Doc, PageTemplate=lambda *a, **k: None, Frame=lambda *a, **k: None, Paragraph=P_,
    Spacer=lambda w, h: {"t": "sp"}, Table=Tbl, TableStyle=lambda c: c, PageBreak=lambda: {"t": "pb"},
    NextPageTemplate=lambda n: {"t": "npt"}, KeepTogether=lambda x: x)
mod("reportlab.graphics")
mod("reportlab.graphics.shapes", Drawing=Drawing, Rect=Rect, String=lambda *a, **k: None, Line=lambda *a, **k: None)

def js(x):
    if isinstance(x, Color): return x.hex
    if isinstance(x, Tbl): return {"t": "table", "data": js(x.data), "style": js(x.style)}
    if isinstance(x, Drawing): return {"t": "drawing", "w": x.w, "h": x.h, "shapes": [{"x": r.x, "y": r.y, "w": r.w, "h": r.h, "fill": js(r.fill), "rx": r.rx, "op": r.op} for r in x.shapes]}
    if isinstance(x, (list, tuple)): return [js(i) for i in x]
    return x
def flat(x):
    for i in x:
        if isinstance(i, list): yield from flat(i)
        else: yield i

src = open(sys.argv[1]).read()
exec(compile(src, "build_book", "exec"), {"__name__": "shim"})
def deep_flat(n):
    if isinstance(n, list): return [deep_flat(i) for i in n]
    return n
story = [n for n in flat(Doc.out) if n.get("t") not in ("npt",)] if all(not isinstance(i, (Tbl, Drawing)) for i in Doc.out) else None
story = [js(n) for n in flat(Doc.out) if not (isinstance(n, dict) and n.get("t") == "npt")]
json.dump(story, open(sys.argv[2], "w"))
print("nodes", len(story))
