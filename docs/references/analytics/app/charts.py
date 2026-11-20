"""Server-rendered SVG chart helpers (ADR-011, ADR-019). Thin monotone-cubic splines; colours are tokens only."""


def spline(pts):
    """Monotone cubic (Fritsch-Carlson) as an SVG path. pts: [(x, y)] with increasing x."""
    n = len(pts)
    if n < 2:
        return ""
    dx = [pts[i + 1][0] - pts[i][0] for i in range(n - 1)]
    s = [(pts[i + 1][1] - pts[i][1]) / dx[i] for i in range(n - 1)]
    m = [s[0]] + [0 if s[i - 1] * s[i] <= 0 else 2 * s[i - 1] * s[i] / (s[i - 1] + s[i]) for i in range(1, n - 1)] + [s[-1]]
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(n - 1):
        h = dx[i] / 3
        d += f"C{pts[i][0] + h:.1f},{pts[i][1] + m[i] * h:.1f} {pts[i + 1][0] - h:.1f},{pts[i + 1][1] - m[i + 1] * h:.1f} {pts[i + 1][0]:.1f},{pts[i + 1][1]:.1f}"
    return d


def line_chart(series, d0, d1, w=640, h=200, pad=14, left=48, nticks=3, xfmt=None):
    """Multi-series spline chart on one shared y scale.

    series: [{label, color (css token), vals {day_rel: number}, width (px, default 1.4), dash (svg dasharray or None)}].
    xfmt: optional day -> label; when given, every integer day from d0 to d1 gets a label (use for short non-date axes such as weeks).
    Returns a template-ready dict (paths, y ticks, x labels, Now marker), or None when there is nothing to draw.
    """
    vals = [v for s in series for v in s["vals"].values() if v is not None]
    if not vals or d1 <= d0:
        return None
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or max(abs(hi), 1)
    lo, hi = lo - span * 0.08, hi + span * 0.08
    X = lambda day: left + (day - d0) / (d1 - d0) * (w - left - pad)
    Y = lambda v: h - pad - (v - lo) / (hi - lo) * (h - 2 * pad)
    paths = []
    for s in series:
        pts = [(X(day), Y(v)) for day, v in sorted(s["vals"].items()) if v is not None]
        if len(pts) >= 2:
            paths.append(dict(d=spline(pts), label=s["label"], color=s["color"], width=s.get("width", 1.4), dash=s.get("dash")))
    ticks = [(round(Y(lo + (hi - lo) * i / (nticks - 1)), 1), lo + (hi - lo) * i / (nticks - 1)) for i in range(nticks)]
    xl = [(round(X(day), 1), txt) for day, txt in ((d0, f"D{d0}" if d0 < 0 else "Now"), (0, "Now"), (d1, f"D+{d1}" if d1 > 0 else "Now")) if d0 <= day <= d1]
    xl = list(dict.fromkeys(xl)) if xfmt is None else [(round(X(day), 1), xfmt(day)) for day in range(d0, d1 + 1)]
    return dict(w=w, h=h, left=left, pad=pad, paths=paths, ticks=ticks, xl=xl, now=round(X(0), 1) if d0 <= 0 <= d1 else None)
