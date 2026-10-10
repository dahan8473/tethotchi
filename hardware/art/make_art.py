"""Silkscreen art for the board: polygons in world mm (X right, Z up, as seen from the front).

Front (F.Silkscreen, under the LCD): PROTOTYPE banner, Tethos mark, title block, unit-number box, pixel TV.
Back (B.Silkscreen, inside the battery well): a note you see when you change the cell.
Writes art.json for hardware/pcb/add_art.py.
Run: .venv/bin/python hardware/art/make_art.py
"""

import json
import math
import sys
from pathlib import Path

from build123d import Location, Plane, Rectangle, Rotation, Sketch, Text, import_svg
from OCP.BRepTools import BRepTools_WireExplorer

ART = Path(__file__).resolve().parent
sys.path.insert(0, str(ART.parent))
import layout as L  # noqa: E402

FONT = str(ART / "fonts" / "IBMPlexMono-Bold.ttf")
STEP = 0.04   # mm between outline points

PIXEL_TV = [
    "..X.......X..",
    "...X.....X...",
    "....X...X....",
    "XXXXXXXXXXXXX",
    "X...........X",
    "X..XX...XX..X",
    "X...........X",
    "X...X...X...X",
    "X....XXX....X",
    "X...........X",
    "XXXXXXXXXXXXX",
    ".XX.......XX.",
]
PIXEL = 0.42


def place(shape, left=None, top=None, cx=None, cz=None):
    """Move a sketch so its bounding box lines up with the given edge or centre."""
    bb = shape.bounding_box()
    dx = (left - bb.min.X) if left is not None else (cx - (bb.min.X + bb.max.X) / 2)
    dz = (top - bb.max.Y) if top is not None else (cz - (bb.min.Y + bb.max.Y) / 2)
    return Location((dx, dz)) * shape


def text(s, size):
    return Text(s, size, font_path=FONT)


def mark(height):
    faces = import_svg(str(ART / "tethos-mark.svg"))
    sk = Sketch() + faces
    bb = sk.bounding_box()
    return sk.scale(height / bb.size.Y)


def pixel_tv():
    sk = None
    for r, row in enumerate(PIXEL_TV):
        for c, ch in enumerate(row):
            if ch == "X":
                px = Location((c * PIXEL, -r * PIXEL)) * Rectangle(PIXEL + 0.01, PIXEL + 0.01)
                sk = px if sk is None else sk + px
    return sk


def frame(x0, z0, x1, z1, w):
    """Rectangle outline, line width w."""
    outer = Location(((x0 + x1) / 2, (z0 + z1) / 2)) * Rectangle(x1 - x0, z1 - z0)
    inner = Location(((x0 + x1) / 2, (z0 + z1) / 2)) * Rectangle(x1 - x0 - 2 * w, z1 - z0 - 2 * w)
    return outer - inner


def hazard(x0, z0, x1, z1, pitch=1.3):
    """Diagonal warning stripes clipped to a rectangle."""
    zone = Location(((x0 + x1) / 2, (z0 + z1) / 2)) * Rectangle(x1 - x0, z1 - z0)
    stripes = None
    h = z1 - z0
    x = x0 - h
    while x < x1 + h:
        st = Location((x, (z0 + z1) / 2)) * Rotation(0, 0, 45) * Rectangle(pitch / 2, h * 2)
        stripes = st if stripes is None else stripes + st
        x += pitch
    return zone & stripes


def front():
    # Banner: PROTOTYPE between hazard stripes
    bx0, bz1, bx1, bz0 = -18.6, 2.0, 18.6, -3.4
    parts = [frame(bx0, bz0, bx1, bz1, 0.3),
             hazard(bx0 + 0.3, bz0 + 0.3, bx0 + 4.6, bz1 - 0.3),
             hazard(bx1 - 4.6, bz0 + 0.3, bx1 - 0.3, bz1 - 0.3),
             place(text("PROTOTYPE", 3.4), cx=0, cz=(bz0 + bz1) / 2)]

    # Middle row: mark, title block, unit-number box, pixel TV
    top = -4.4
    parts.append(place(mark(5.4), left=-18.4, top=top))
    z = top
    for s, size, gap in (("TETHOTCHI", 2.2, 0.7), ("REV 0.1 OCT 2026", 1.6, 0.6), ("NOT FOR SALE", 1.6, 0)):
        t = place(text(s, size), left=-11.6, top=z)
        parts.append(t)
        z = t.bounding_box().min.Y - gap
    parts.append(place(text("NO.", 1.4), left=6.0, top=top))
    parts.append(frame(6.0, -9.8, 12.6, -6.2, 0.2))           # write the unit number in here
    parts.append(place(text("/5", 2.0), left=10.0, cz=-8.0))
    parts.append(place(pixel_tv(), left=13.6, top=top))

    parts.append(place(text("TECH FOR SOCIAL IMPACT", 1.8), cx=0, cz=-11.6))
    return parts


def back():
    """Battery well, read from behind: build upright, then mirror X."""
    cx, cz, _ = L.CELL
    parts = [place(text("TSI WAS HERE", 1.6), cx=0, cz=6.8 - cz),
             place(text("+ SIDE UP", 1.6), cx=0, cz=4.6 - cz)]
    return [Location((cx, cz)) * p.mirror(Plane.YZ) for p in parts]


def wire_points(wire):
    pts = []
    ex = BRepTools_WireExplorer(wire.wrapped)
    from build123d import Edge
    while ex.More():
        e = Edge(ex.Current())
        n = max(2, math.ceil(e.length / STEP))
        seg = [e.position_at(i / n) for i in range(n + 1)]
        if pts and (seg[0] - pts[-1]).length > (seg[-1] - pts[-1]).length:
            seg.reverse()
        pts.extend(seg if not pts else seg[1:])
        ex.Next()
    return [[round(p.X, 4), round(p.Y, 4)] for p in pts[:-1]]


def polys(parts):
    out = []
    for p in parts:
        for f in p.faces():
            out.append({"outline": wire_points(f.outer_wire()),
                        "holes": [wire_points(w) for w in f.inner_wires()]})
    return out


if __name__ == "__main__":
    data = {"F": polys(front()), "B": polys(back())}
    (ART / "art.json").write_text(json.dumps(data))
    for side, ps in data.items():
        xs = [x for p in ps for x, _ in p["outline"]]
        zs = [z for p in ps for _, z in p["outline"]]
        print(side, len(ps), "polygons", f"X {min(xs):.2f}..{max(xs):.2f}  Z {min(zs):.2f}..{max(zs):.2f}")
