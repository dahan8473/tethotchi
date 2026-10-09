"""Tethos Pet shell v0.1: retro CRT TV, two halves + twist-lock cap + 4 button plungers.

Axes: X = width, Z = up, Y = depth (front face Y=0, back face Y=D). Dimensions from hardware/layout.py.
Run: .venv/bin/python hardware/shell/shell.py  -> STEP/STL in hardware/shell/out, renders in hardware/renders
"""

import math
import sys
from pathlib import Path

from build123d import (
    Axis, Box, Cylinder, Location, Plane, RectangleRounded, Rotation, Sphere, Text, Torus,
    export_step, export_stl, extrude, fillet, loft,
)

HW = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HW))
import layout as L  # noqa: E402

OUT = HW / "shell" / "out"
OUT.mkdir(parents=True, exist_ok=True)

W, H, D = L.W, L.H, L.D
T = L.WALL
TF = L.FRONT_WALL
Y_STRAIGHT = L.Y_SPLIT      # straight-walled front half; the back half carries the CRT taper
BACK_INSET_W, BACK_INSET_H = 8.0, 6.0
R_FRONT, R_BACK = 9.0, 7.0

LCD_W, LCD_H = 43.5, 33.6
WINDOW_W, WINDOW_H, WINDOW_R = L.LCD_VA[0] - 0.4, L.LCD_VA[1] - 0.4, 2.5   # just inside the LCD visual area
WINDOW_Z = L.LCD_VA_Z
FIT = 0.2                                        # general clearance for printed fits

BTN_Y = L.Y_PCB_BACK + 1.7                       # SKRT actuator centre is 1.7 mm off the board
BTN_HOLE = 2.6                                   # round hole in the side wall
BTN_CAP_D, BTN_CAP_OUT = 2.3, 0.9                # plunger shaft and how far it sticks out
BTN_FLANGE = (3.8, 3.2, 0.45)                    # Y, Z, X: keeps the plunger in; 0.16 mm short of the actuator

CAP_R = 15.5                                     # outer face of the twist cap
CAP_PLUG_R = L.CAP_OPENING_R - FIT
LUG_ANGLES = (90, 210, 330)                      # 3 lugs, 120 deg apart
LUG_SPAN = 28                                    # degrees per lug
NOTCH_SPAN = 34
LUG_R = 16.3
LOCK_TURN = 60                                   # degrees to lock
CAP_TOL = (0.15, 0.25, 0.35)                     # print all three, keep the one that feels right


def face_plane(y):
    return Plane(origin=(0, y, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0))


def rrect(w, h, r, y, x=0.0, z=0.0):
    return face_plane(y) * Location((x, z, 0)) * RectangleRounded(w, h, r)


def slab(w, h, r, y0, y1, x=0.0, z=0.0):
    return extrude(rrect(w, h, r, y0, x, z), amount=y1 - y0, dir=(0, 1, 0))


def ybox(x, z, w, h, y0, y1):
    """Axis-aligned box spanning y0..y1."""
    return Location((x, (y0 + y1) / 2, z)) * Box(w, y1 - y0, h)


def ycyl(x, z, r, y0, y1):
    return Location((x, (y0 + y1) / 2, z)) * Rotation(90, 0, 0) * Cylinder(r, y1 - y0)


def outer_sections(inset=0.0, y0=0.0, y_back=D):
    k = inset
    return [
        rrect(W - 2 * k, H - 2 * k, R_FRONT - k, y0),
        rrect(W - 2 * k, H - 2 * k, R_FRONT - k, Y_STRAIGHT),
        rrect(W - BACK_INSET_W - 2 * k, H - BACK_INSET_H - 2 * k, R_BACK - k, y_back),
    ]


def body():
    outer = loft(outer_sections(), ruled=True)
    try:
        outer = fillet(outer.faces().sort_by(Axis.Y)[0].edges(), 1.5)
    except Exception:
        pass
    inner = loft(outer_sections(T, TF, D - T), ruled=True)
    return outer - inner


def antennas_and_loop():
    y = L.Y_SPLIT - 2.5
    parts = None
    for s in (-1, 1):
        base = Location((s * 5, y, H / 2 - 0.5)) * Rotation(0, s * 30, 0)
        a = base * Location((0, 0, 3.5)) * Cylinder(1.6, 7)
        a += base * Location((0, 0, 7.2)) * Sphere(2.4)
        parts = a if parts is None else parts + a
    loop = Location((0, y, H / 2 + 2.8)) * Rotation(90, 0, 0) * Torus(3.0, 1.3)
    # Thicken the top wall under the loop: it carries the keychain load
    pad = ybox(0, H / 2 - T - 0.4, 12, 0.8, L.Y_PCB_BACK + 0.1, L.Y_SPLIT)
    return parts + loop + pad


def feet():
    out = None
    for s in (-1, 1):
        f = fillet(ybox(s * 15, -H / 2 + 0.5, 9, 2.6, L.Y_SPLIT - 4, L.Y_SPLIT + 3).edges(), 0.8)
        out = f if out is None else out + f
    return out


def lcd_frame():
    """Ribs that locate the LCD glass; the PCB sits on top of them."""
    ow, oh = LCD_W + 2 * FIT + 1.6, LCD_H + 2 * FIT + 1.6
    frame = slab(ow, oh, 1.0, TF, L.Y_PCB) - slab(LCD_W + 2 * FIT, LCD_H + 2 * FIT, 0.3, TF - 0.1, L.Y_PCB + 0.1)
    frame -= ybox(0, -LCD_H / 2 - 1.0, L.RIBBON_W + 2, 3.0, TF - 0.1, L.Y_PCB + 0.1)   # ribbon fold
    return frame


def bosses():
    out = None
    for bx, bz in L.BOSS_CENTERS:
        post = ycyl(bx, bz, L.BOSS_R, L.Y_PCB_BACK + 0.2, L.Y_SPLIT)
        web = ybox(bx, (bz + (-(H / 2 - T))) / 2, 1.2, abs(-(H / 2 - T) - bz) + 0.5,
                   L.Y_PCB_BACK + 0.2, L.Y_SPLIT)
        b = post + web - ycyl(bx, bz, 0.65, L.Y_PCB_BACK, L.Y_SPLIT + 0.1)   # 1.3 mm pilot for M1.7
        out = b if out is None else out + b
    return out


def button_holes():
    out = None
    for n in ("SW_A", "SW_B", "SW_C", "SW_D"):
        x, z = L.PARTS[n][0], L.PARTS[n][1]
        s = 1 if x > 0 else -1
        hole = Location((s * (W / 2), BTN_Y, z)) * Rotation(0, 90, 0) * Cylinder(BTN_HOLE / 2, 8)
        out = hole if out is None else out + hole
    return out


def sound_slots():
    bx, bz = L.PARTS["BZ1"][0], L.PARTS["BZ1"][1]
    out = None
    for k in (-1, 0, 1):
        s = ybox(bx + k * 1.6, H / 2 - T / 2, 0.8, T * 3, L.Y_PCB_BACK + 0.5, L.Y_SPLIT - 0.8)
        out = s if out is None else out + s
    return out


def lug_ring(r_in, r_out, y0, y1, angles, span, cx, cz):
    """Ring segments (lugs or notches) around (cx, cz) between y0..y1."""
    out = None
    for a in angles:
        seg = None
        steps = 6
        for i in range(steps):
            ang = math.radians(a - span / 2 + span * (i + 0.5) / steps)
            rm = (r_in + r_out) / 2
            piece = (Location((cx + rm * math.cos(ang), (y0 + y1) / 2, cz + rm * math.sin(ang)))
                     * Rotation(0, -math.degrees(ang), 0)
                     * Box(r_out - r_in, y1 - y0, 2 * rm * math.sin(math.radians(span / steps / 2)) + 0.3))
            seg = piece if seg is None else seg + piece
        out = seg if out is None else out + seg
    return out


def back_opening():
    cx, cz, _ = L.CELL
    hole = ycyl(cx, cz, L.CAP_OPENING_R, D - T - 0.5, D + 0.5)
    recess = ycyl(cx, cz, CAP_R + FIT, D - 0.8, D + 0.5)           # cap sits flush
    notches = lug_ring(L.CAP_OPENING_R - 0.5, LUG_R + 0.3, D - T - 0.5, D + 0.1, LUG_ANGLES, NOTCH_SPAN, cx, cz)
    return hole + recess + notches


def detents():
    """Small bumps behind the back wall the lugs click past when locked."""
    cx, cz, _ = L.CELL
    angles = [a + LOCK_TURN - LUG_SPAN / 2 - 4 for a in LUG_ANGLES]
    return lug_ring(L.CAP_OPENING_R + 0.2, LUG_R, D - T - 0.35, D - T, angles, 3, cx, cz)


def cap(tol):
    cx, cz, _ = L.CELL
    face = ycyl(cx, cz, CAP_R, D - 0.8, D)
    plug = ycyl(cx, cz, CAP_PLUG_R - tol, D - T - 0.9, D - 0.8)
    lugs = lug_ring(CAP_PLUG_R - tol - 0.5, LUG_R - tol, D - T - 0.9, D - T - tol, LUG_ANGLES, LUG_SPAN, cx, cz)
    c = face + plug + lugs
    for sz in (-1, 1):
        grip = ybox(cx, cz + sz * 12.5, 7, 1.6, D, D + 0.8)
        c += fillet(grip.edges().filter_by(Axis.X), 0.3)
    txt = Plane(origin=(cx, D, cz), x_dir=(-1, 0, 0), z_dir=(0, 1, 0)) * Text("TETHOS", 4.0)
    c -= extrude(txt, amount=-0.3)
    # Pull-tab exit: a notch in the plug edge, at the bottom
    c -= ybox(cx, cz - CAP_PLUG_R + 0.6, 6, 1.6, D - T - 1.0, D - 0.79)
    return c


def back_ribs():
    """Ribs from the back shell that press the PCB onto the LCD frame."""
    out = None
    for x, z in ((-23.0, -1.0), (23.0, -1.0), (-10.0, -18.4), (8.0, -18.4)):
        r = ybox(x, z, 1.0, 1.0, L.Y_PCB_BACK + 0.05, L.Y_SPLIT + 0.5)
        out = r if out is None else out + r
    return out


def screw_holes():
    out = None
    for bx, bz in L.BOSS_CENTERS:
        h = ycyl(bx, bz, 0.95, L.Y_SPLIT - 0.1, D + 0.1)            # clearance for M1.7
        h += ycyl(bx, bz, 1.6, D - 1.0, D + 0.1)                    # head counterbore
        out = h if out is None else out + h
    return out


def back_screw_columns():
    out = None
    for bx, bz in L.BOSS_CENTERS:
        col = ycyl(bx, bz, L.BOSS_R, L.Y_SPLIT, D - 0.5)
        out = col if out is None else out + col
    return out


def button_plunger():
    shaft = Location((BTN_CAP_OUT / 2 + T / 2, 0, 0)) * Rotation(0, 90, 0) * Cylinder(BTN_CAP_D / 2, T + BTN_CAP_OUT)
    fy, fz, fx = BTN_FLANGE
    flange = Location((-fx / 2, 0, 0)) * Box(fx, fy, fz)
    return fillet(shaft.edges().sort_by(Axis.X)[-1:], 0.4) + flange


def split(shape):
    front_cut = ybox(0, 0, W + 20, H + 40, -5, L.Y_SPLIT)
    back_cut = ybox(0, 0, W + 20, H + 40, L.Y_SPLIT, D + 5)
    return shape & front_cut, shape & back_cut


def build():
    shell = body()
    shell -= slab(WINDOW_W, WINDOW_H, WINDOW_R, -0.1, TF + 0.1, 0, WINDOW_Z)
    for k in (-1, 0, 1):   # speaker grille detail under the screen (not through)
        shell -= slab(7, 0.9, 0.4, -0.1, 0.5, 0, -H / 2 + 4.2 + k * 1.6)
    shell += antennas_and_loop() + feet() + lcd_frame()
    shell -= button_holes() + sound_slots()

    front, back = split(shell)
    front += bosses()
    back += back_ribs() + back_screw_columns() + detents()
    back -= back_opening() + screw_holes()
    front -= button_holes()

    parts = {"front": front, "back": back}
    for tol in CAP_TOL:
        parts[f"cap_{int(tol * 100):02d}"] = cap(tol)
    parts["button"] = button_plunger()
    return parts


if __name__ == "__main__":
    parts = build()
    for name, solid in parts.items():
        export_step(solid, str(OUT / f"{name}.step"))
        export_stl(solid, str(OUT / f"{name}.stl"), tolerance=0.01, angular_tolerance=0.1)
        bb = solid.bounding_box()
        print(f"{name:8s} {bb.size.X:6.1f} x {bb.size.Y:5.1f} x {bb.size.Z:5.1f} mm  volume {solid.volume / 1000:.2f} cm3")
