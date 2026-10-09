"""Shell concept models: retro CRT vs modern flat TV.

Axes: X = width, Z = height (up), Y = depth (front face at Y=0, back at Y=+D).
Run: .venv/bin/python hardware/shell/concepts.py
"""

from pathlib import Path

import pyvista as pv
from build123d import (
    Axis, Box, Cylinder, Location, Plane, RectangleRounded, Rotation, Sphere,
    Text, Torus, export_stl, extrude, fillet, loft,
)

OUT = Path(__file__).resolve().parents[1] / "renders"
OUT.mkdir(exist_ok=True)

# Envelope from the parts stack-up (see hardware/parts.md)
W, H, D = 52.0, 42.0, 15.6
SCREEN_W, SCREEN_H = 40.0, 27.0   # window; LCD active area ~37.1 x 23.0
PIXEL = 37.1 / 128               # LCD dot pitch

# 16x16 placeholder pet, drawn at 2x (32x32 LCD dots)
SPRITE = """
................
.....######.....
...##......##...
..#..........#..
.#............#.
.#..##....##..#.
#...##....##...#
#..............#
#....#....#....#
#.....####.....#
.#............#.
.#............#.
..#..........#..
...##......##...
.....######.....
................
"""


def face_plane(y):
    """Plane facing the viewer (normal -Y) at depth y; local Y is world +Z."""
    return Plane(origin=(0, y, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0))


def rrect(w, h, r, y):
    return face_plane(y) * RectangleRounded(w, h, r)


def into_body(face, depth):
    return extrude(face, amount=depth, dir=(0, 1, 0))


def screen_and_pet(y, scale=2):
    screen = Location((0, y - 0.06, 0)) * Box(SCREEN_W - 1, 0.1, SCREEN_H - 1)
    rows = [r for r in SPRITE.strip().splitlines()]
    px = PIXEL * scale
    pixels = []
    x0 = -len(rows[0]) * px / 2
    z0 = len(rows) * px / 2 - 1.0
    for j, row in enumerate(rows):
        for i, c in enumerate(row):
            if c == "#":
                pixels.append(Location((x0 + (i + 0.5) * px, y - 0.15, z0 - (j + 0.5) * px))
                              * Box(px * 0.9, 0.06, px * 0.9))
    pet = pixels[0]
    for p in pixels[1:]:
        pet += p
    return screen, pet


def side_buttons(x_half, y, inset_z=10.0, size=(1.2, 4.5, 3.4)):
    bx, by, bz = size
    btns = None
    for sx in (-1, 1):
        for sz in (-1, 1):
            b = Location((sx * (x_half + bx / 2 - 0.4), y, sz * (H / 2 - inset_z))) * Box(bx, by, bz)
            b = fillet(b.edges().filter_by(Axis.X), 0.5)
            btns = b if btns is None else btns + b
    return btns


def back_cap(y, logo=True):
    cap = Location((0, y + 0.4, -1.5)) * Rotation(90, 0, 0) * Cylinder(15.5, 0.8)
    for sz in (-1, 1):
        grip = Location((0, y + 1.0, -1.5 + sz * 13.0)) * Box(7, 0.8, 1.6)
        cap += fillet(grip.edges().filter_by(Axis.X), 0.3)
    if logo:
        txt = Plane(origin=(0, y + 0.8, -1.5), x_dir=(-1, 0, 0), z_dir=(0, 1, 0)) * Text("TETHOS", 4.0)
        cap -= extrude(txt, amount=-0.3)
    return cap


def crt():
    body = loft([rrect(W, H, 9, 0), rrect(W, H, 9, 6), rrect(W - 8, H - 6, 7, D)], ruled=True)
    try:
        body = fillet(body.faces().sort_by(Axis.Y)[0].edges(), 1.5)
    except Exception:
        pass
    body -= into_body(rrect(SCREEN_W, SCREEN_H, 4, -0.01), 1.5)
    for k in (-1, 0, 1):
        body -= into_body(rrect(7, 0.9, 0.4, -0.01) .moved(Location((0, 0, -H / 2 + 4.2 + k * 1.6))), 0.8)

    # Short, thick rabbit ears so they survive a keychain life (3.2 mm stalk, 2.4 mm ball)
    antennas = None
    for s in (-1, 1):
        base = Location((s * 5, D * 0.45, H / 2 - 2)) * Rotation(0, s * 30, 0)
        a = base * Location((0, 0, 3.5)) * Cylinder(1.6, 7)
        a += base * Location((0, 0, 7.2)) * Sphere(2.4)
        antennas = a if antennas is None else antennas + a
    loop = Location((0, D * 0.45, H / 2 + 1.6)) * Rotation(90, 0, 0) * Torus(3.0, 1.3)

    feet = None
    for s in (-1, 1):
        f = Location((s * 15, D * 0.45, -H / 2 + 0.5)) * Box(9, 7, 2.6)
        f = fillet(f.edges(), 0.8)
        feet = f if feet is None else feet + f

    screen, pet = screen_and_pet(1.5)
    return {
        "body": body + antennas + loop + feet,
        "buttons": side_buttons(W / 2, 3.5),
        "cap": back_cap(D),
        "screen": screen,
        "pet": pet,
    }


def flat():
    body = Location((0, D / 2, 0)) * Box(W, D, H)
    body = fillet(body.edges().filter_by(Axis.Y), 5)
    body = fillet(body.edges().filter_by_position(Axis.Y, -0.01, 0.01)
                  + body.edges().filter_by_position(Axis.Y, D - 0.01, D + 0.01), 1.2)
    body -= into_body(rrect(SCREEN_W + 4, SCREEN_H + 3, 1.5, -0.01), 0.8)

    tab = Location((0, D / 2, H / 2 + 1.5)) * Box(11, 4, 6)
    tab = fillet(tab.edges().filter_by(Axis.Y), 1.4)
    tab -= Location((0, D / 2, H / 2 + 2.5)) * Rotation(90, 0, 0) * Cylinder(2.0, 6)

    screen, pet = screen_and_pet(0.8)
    return {
        "body": body + tab,
        "buttons": side_buttons(W / 2, D / 2, size=(0.8, 6.0, 3.0)),
        "cap": back_cap(D),
        "screen": screen,
        "pet": pet,
    }


COLORS = {
    "body": "#4C566A",
    "cap": "#3B4252",
    "buttons": "#FF7A1A",
    "screen": "#B7C0A2",
    "pet": "#2E3440",
}

VIEWS = {
    "front": [(-75, -115, 45), (0, D / 2, 0), (0, 0, 1)],
    "back": [(70, 130, 40), (0, D / 2, 0), (0, 0, 1)],
    "side": [(-150, D / 2, 5), (0, D / 2, 0), (0, 0, 1)],
}


def render(name, parts):
    tmp = OUT / f".{name}"
    tmp.mkdir(exist_ok=True)
    meshes = {}
    for key, solid in parts.items():
        path = tmp / f"{key}.stl"
        export_stl(solid, str(path), tolerance=0.02, angular_tolerance=0.1)
        meshes[key] = pv.read(path)

    p = pv.Plotter(off_screen=True, shape=(1, 3), window_size=(2400, 820), border=False)
    for i, (view, cam) in enumerate(VIEWS.items()):
        p.subplot(0, i)
        p.set_background("#ECEFF4")
        for key, mesh in meshes.items():
            p.add_mesh(mesh, color=COLORS[key], smooth_shading=True, specular=0.25,
                       split_sharp_edges=True)
        p.camera_position = cam
        p.camera.zoom(1.25)
        p.add_text(view, font_size=12, color="#4C566A")
    p.subplot(0, 0)
    p.add_text(f"{name}: {W:.0f} x {H:.0f} x {D:.1f} mm (+ loop)", position="lower_left",
               font_size=11, color="#2E3440")
    out = OUT / f"concept-{name}.png"
    p.screenshot(out)
    p.close()

    stl_dir = OUT.parent / "shell" / "concepts"
    stl_dir.mkdir(exist_ok=True)
    whole = parts["body"] + parts["buttons"] + parts["cap"]
    export_stl(whole, str(stl_dir / f"{name}.stl"))
    return out


if __name__ == "__main__":
    for name, build in (("crt", crt),):
        print(render(name, build()))
