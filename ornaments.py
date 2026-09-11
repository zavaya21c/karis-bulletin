"""Vector cover ornaments.

Every motif is drawn as paths so it stays sharp at any print resolution and
prints cleanly on a mono laser printer. Each function receives a square field
(centre point and radius in points) plus the cover palette.
"""
import math

from reportlab.lib.colors import HexColor

TAU = math.pi * 2


def _cross(c, cx, cy, height, weight, color, serif=True):
    """A slender Latin cross with optional flared ends."""
    arm = height * 0.30
    top = cy + height * 0.52
    bottom = cy - height * 0.48
    node = cy + height * 0.16
    c.setFillColor(color)
    c.setStrokeColor(color)
    c.setLineWidth(0)
    c.rect(cx - weight / 2, bottom, weight, top - bottom, fill=1, stroke=0)
    c.rect(cx - arm, node - weight / 2, arm * 2, weight, fill=1, stroke=0)
    if serif:
        flare = weight * 0.85
        for x, y, w, h in ((cx, top, weight * 2.1, weight * 0.42),
                           (cx, bottom, weight * 2.1, weight * 0.42)):
            c.rect(x - w / 2, y - h / 2 if y == top else y, w, h, fill=1, stroke=0)
        for side in (-1, 1):
            c.rect(cx + side * arm - (flare if side > 0 else 0), node - weight * 1.05,
                   flare, weight * 2.1, fill=1, stroke=0)


def _leaf(c, length, width, color):
    """One laurel leaf drawn from the origin along +x."""
    path = c.beginPath()
    path.moveTo(0, 0)
    path.curveTo(length * 0.35, width, length * 0.75, width * 0.85, length, 0)
    path.curveTo(length * 0.75, -width * 0.85, length * 0.35, -width, 0, 0)
    path.close()
    c.setFillColor(color)
    c.drawPath(path, fill=1, stroke=0)


def leaves(c, cx, cy, r, ink, accent, paper):
    """A laurel wreath — two mirrored branches of tapering leaves — around a cross."""
    gold = HexColor(accent)
    radius = r * 0.92
    c.saveState()
    for side in (-1, 1):
        start, end, count = -96, 72, 11
        path = c.beginPath()
        for step in range(41):
            a = math.radians(start + (end - start) * step / 40)
            x = cx + side * math.cos(a) * radius
            y = cy + math.sin(a) * radius
            path.moveTo(x, y) if step == 0 else path.lineTo(x, y)
        c.setStrokeColor(gold)
        c.setLineWidth(r * 0.022)
        c.drawPath(path, fill=0, stroke=1)
        for i in range(count):
            t = i / (count - 1)
            a = math.radians(start + (end - start) * t)
            x = cx + side * math.cos(a) * radius
            y = cy + math.sin(a) * radius
            taper = 1.0 - 0.42 * t
            for lean in (-1, 1):
                c.saveState()
                c.translate(x, y)
                # Tangent of the arc, tipped outward so leaves sweep up the branch.
                tangent = math.degrees(a) + (90 if side > 0 else 90)
                c.rotate((tangent if side > 0 else 180 - tangent) + lean * 30)
                _leaf(c, r * 0.30 * taper, r * 0.085 * taper, gold)
                c.restoreState()
    c.setFillColor(gold)
    for side in (-1, 1):
        a = math.radians(72)
        c.circle(cx + side * math.cos(a) * radius, cy + math.sin(a) * radius, r * 0.030,
                 fill=1, stroke=0)
    _cross(c, cx, cy - r * 0.04, r * 1.02, r * 0.075, gold)
    c.restoreState()


def glass(c, cx, cy, r, ink, accent, paper):
    """A rose window: two rings of leaded glass petals around a clear centre."""
    tint = [HexColor(accent), HexColor(paper), HexColor(accent), HexColor(paper)]
    lead = HexColor(accent)
    c.saveState()
    for ring, (r0, r1, segments) in enumerate(((r * 0.40, r * 0.72, 12), (r * 0.72, r * 1.0, 16))):
        for k in range(segments):
            a0 = k * TAU / segments
            a1 = (k + 1) * TAU / segments
            mid = (a0 + a1) / 2
            path = c.beginPath()
            path.moveTo(cx + math.cos(a0) * r0, cy + math.sin(a0) * r0)
            path.curveTo(cx + math.cos(a0) * r1, cy + math.sin(a0) * r1,
                         cx + math.cos(mid) * r1 * 1.06, cy + math.sin(mid) * r1 * 1.06,
                         cx + math.cos(a1) * r1, cy + math.sin(a1) * r1)
            path.lineTo(cx + math.cos(a1) * r0, cy + math.sin(a1) * r0)
            path.close()
            shade = tint[(k + ring) % len(tint)]
            c.setFillColor(shade)
            c.setStrokeColor(lead)
            c.setLineWidth(r * 0.016)
            c.setFillAlpha(0.55 if shade == tint[0] else 0.16)
            c.drawPath(path, fill=1, stroke=1)
    c.setFillAlpha(1)
    c.setFillColor(HexColor(paper))
    c.setFillAlpha(0.10)
    c.circle(cx, cy, r * 0.40, fill=1, stroke=0)
    c.setFillAlpha(1)
    c.setStrokeColor(lead)
    c.setLineWidth(r * 0.02)
    c.circle(cx, cy, r * 0.40, fill=0, stroke=1)
    _cross(c, cx, cy, r * 0.62, r * 0.055, HexColor(accent), serif=False)
    c.restoreState()


def rays(c, cx, cy, r, ink, accent, paper):
    """Light breaking from behind a cross."""
    gold = HexColor(accent)
    c.saveState()
    c.setStrokeColor(gold)
    for k in range(60):
        a = k * TAU / 60
        long_ray = k % 5 == 0
        r0 = r * 0.34
        r1 = r * (1.0 if long_ray else 0.78 if k % 2 else 0.62)
        c.setLineWidth(r * (0.020 if long_ray else 0.009))
        c.line(cx + math.cos(a) * r0, cy + math.sin(a) * r0,
               cx + math.cos(a) * r1, cy + math.sin(a) * r1)
    c.setLineWidth(r * 0.016)
    c.circle(cx, cy, r * 0.34, fill=0, stroke=1)
    c.setLineWidth(r * 0.008)
    c.circle(cx, cy, r * 0.30, fill=0, stroke=1)
    _cross(c, cx, cy, r * 0.86, r * 0.07, gold)
    c.restoreState()


def flowers(c, cx, cy, r, ink, accent, paper):
    """Two sprays of small blossoms flanking a slim cross."""
    bloom = HexColor(accent)
    stemcolor = HexColor(ink)
    c.saveState()
    for side in (-1, 1):
        path = c.beginPath()
        path.moveTo(cx + side * r * 0.16, cy - r * 0.74)
        path.curveTo(cx + side * r * 0.70, cy - r * 0.42,
                     cx + side * r * 0.82, cy + r * 0.24,
                     cx + side * r * 0.44, cy + r * 0.82)
        c.setStrokeColor(stemcolor)
        c.setFillAlpha(1)
        c.setStrokeAlpha(0.45)
        c.setLineWidth(r * 0.020)
        c.drawPath(path, fill=0, stroke=1)
        c.setStrokeAlpha(1)
        for i, t in enumerate((0.16, 0.38, 0.60, 0.82, 0.97)):
            x = cx + side * (3 * (1 - t) ** 2 * t * r * 0.70 + 3 * (1 - t) * t ** 2 * r * 0.82
                             + t ** 3 * r * 0.44 + (1 - t) ** 3 * r * 0.16)
            y = cy + (-r * 0.74 * (1 - t) ** 3 - 3 * (1 - t) ** 2 * t * r * 0.42
                      + 3 * (1 - t) * t ** 2 * r * 0.24 + t ** 3 * r * 0.82)
            size = r * (0.15 - i * 0.011)
            for petal in range(6):
                a = petal * TAU / 6 + i
                c.setFillColor(bloom)
                c.setFillAlpha(0.55)
                c.circle(x + math.cos(a) * size * 0.62, y + math.sin(a) * size * 0.62,
                         size * 0.55, fill=1, stroke=0)
            c.setFillAlpha(1)
            c.setFillColor(bloom)
            c.circle(x, y, size * 0.24, fill=1, stroke=0)
    _cross(c, cx, cy, r * 0.98, r * 0.055, HexColor(accent), serif=False)
    c.restoreState()


def cross(c, cx, cy, r, ink, accent, paper):
    """A single well-proportioned cross inside a hairline circle."""
    gold = HexColor(accent)
    c.saveState()
    c.setStrokeColor(gold)
    c.setLineWidth(r * 0.012)
    c.circle(cx, cy, r * 0.86, fill=0, stroke=1)
    c.setLineWidth(r * 0.030)
    c.circle(cx, cy, r * 0.80, fill=0, stroke=1)
    _cross(c, cx, cy, r * 1.02, r * 0.085, gold)
    c.setLineWidth(r * 0.012)
    for side in (-1, 1):
        c.line(cx + side * r * 0.96, cy, cx + side * r * 1.45, cy)
        c.circle(cx + side * r * 1.56, cy, r * 0.045, fill=1, stroke=0)
    c.restoreState()


def monogram(c, cx, cy, r, ink, accent, paper):
    """A lozenge frame around a slim cross, with hairline wings."""
    gold = HexColor(accent)
    c.saveState()
    c.setStrokeColor(gold)
    for scale, weight in ((1.0, 0.026), (0.90, 0.010)):
        path = c.beginPath()
        path.moveTo(cx, cy + r * scale)
        path.lineTo(cx + r * 0.72 * scale, cy)
        path.lineTo(cx, cy - r * scale)
        path.lineTo(cx - r * 0.72 * scale, cy)
        path.close()
        c.setLineWidth(r * weight)
        c.drawPath(path, fill=0, stroke=1)
    _cross(c, cx, cy, r * 0.96, r * 0.062, gold, serif=False)
    c.setLineWidth(r * 0.012)
    for side in (-1, 1):
        c.line(cx + side * r * 0.86, cy, cx + side * r * 1.60, cy)
    c.restoreState()


def deco(c, cx, cy, r, ink, accent, paper):
    """Art-deco fan: stepped arcs and fine rays behind a cross."""
    gold = HexColor(accent)
    c.saveState()
    c.setStrokeColor(gold)
    for i, radius in enumerate((r * 1.02, r * 0.86, r * 0.70)):
        c.setLineWidth(r * (0.026 if i == 0 else 0.010))
        path = c.beginPath()
        path.arc(cx - radius, cy - radius, cx + radius, cy + radius, 0, 180)
        c.drawPath(path, fill=0, stroke=1)
    c.setLineWidth(r * 0.009)
    for k in range(13):
        a = math.pi * k / 12
        c.line(cx + math.cos(a) * r * 0.30, cy + math.sin(a) * r * 0.30,
               cx + math.cos(a) * r * 0.66, cy + math.sin(a) * r * 0.66)
    c.setLineWidth(r * 0.026)
    c.line(cx - r * 1.02, cy, cx + r * 1.02, cy)
    c.setLineWidth(r * 0.010)
    c.line(cx - r * 0.92, cy - r * 0.09, cx + r * 0.92, cy - r * 0.09)
    _cross(c, cx, cy + r * 0.26, r * 0.90, r * 0.070, gold)
    c.restoreState()


def arch(c, cx, cy, r, ink, accent, paper):
    """A chapel window: rounded arch, mullion and a cross."""
    stone = HexColor(accent)
    c.saveState()
    width = r * 1.12
    base = cy - r * 0.92
    top = cy + r * 0.42
    c.setFillColor(stone)
    c.setFillAlpha(0.20)
    path = c.beginPath()
    path.moveTo(cx - width, base)
    path.lineTo(cx - width, top)
    path.arcTo(cx - width, top - width, cx + width, top + width, 180, -180)
    path.lineTo(cx + width, base)
    path.close()
    c.drawPath(path, fill=1, stroke=0)
    c.setFillAlpha(1)
    c.setStrokeColor(stone)
    c.setLineWidth(r * 0.020)
    c.drawPath(path, fill=0, stroke=1)
    c.setLineWidth(r * 0.012)
    c.line(cx, base + r * 0.10, cx, top + width * 0.72)
    c.line(cx - width * 0.62, base + r * 0.10, cx - width * 0.62, top - r * 0.10)
    c.line(cx + width * 0.62, base + r * 0.10, cx + width * 0.62, top - r * 0.10)
    _cross(c, cx, cy + r * 0.05, r * 1.10, r * 0.062, HexColor(ink), serif=False)
    c.restoreState()


MOTIFS = {'leaves': leaves, 'glass': glass, 'rays': rays, 'flowers': flowers,
          'cross': cross, 'monogram': monogram, 'deco': deco, 'arch': arch}


def draw(c, motif, cx, cy, r, ink, accent, paper):
    fn = MOTIFS.get(motif)
    if fn:
        fn(c, cx, cy, r, ink, accent, paper)
