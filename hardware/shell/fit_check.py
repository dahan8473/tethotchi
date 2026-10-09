"""Fit check: place placeholder board parts inside the shell, report collisions, render views.

Run: .venv/bin/python hardware/shell/fit_check.py
"""

import sys
from pathlib import Path

import pyvista as pv
from build123d import Box, Cylinder, Location, Plane, Rotation, export_stl

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import layout as L  # noqa: E402
import shell as S   # noqa: E402
from concepts import screen_and_pet  # noqa: E402

RENDERS = HERE.parent / "renders"


def internals():
    """Board-side volumes from layout.py. Heights are datasheet values."""
    heights = {"J1": 2.5, "U1": 1.2, "Y1": 0.8, "BZ1": 2.5, "TP1": 0.1, "C_BULK": 1.6,
               "SW_A": 3.3, "SW_B": 3.3, "SW_C": 3.3, "SW_D": 3.3}
    out = {}
    board = S.slab(L.BOARD_W, L.BOARD_H, L.BOARD_R, L.Y_PCB, L.Y_PCB_BACK)
    for bx, bz in L.BOSS_CENTERS:
        board -= S.ycyl(bx, bz, L.NOTCH_R, L.Y_PCB - 0.1, L.Y_PCB_BACK + 0.1)
        board -= S.ybox(bx, (bz - L.BOARD_H / 2) / 2, 2 * L.NOTCH_R, abs(bz + L.BOARD_H / 2) + 0.2,
                        L.Y_PCB - 0.1, L.Y_PCB_BACK + 0.1)
    out["pcb"] = board
    out["lcd"] = S.ybox(0, 0, S.LCD_W, S.LCD_H, L.Y_LCD, L.Y_LCD + L.LCD_T)
    for n, (x, z, w, h, side, _) in L.PARTS.items():
        if n in ("LCD1", "BT1"):
            continue
        if n.startswith("SW_"):
            # Alps SKRT: body 2.56 deep behind the footprint origin line, Ø2 actuator 0.84 proud (datasheet p.2)
            sgn = 1 if x > 0 else -1
            body = S.ybox(x + sgn * (1.21 - 1.35) / 2, z, 2.56, 4.5, L.Y_PCB_BACK, L.Y_PCB_BACK + 3.3)
            act = (Location((x + sgn * (1.21 + 0.42), S.BTN_Y, z)) * Rotation(0, 90, 0) * Cylinder(1.0, 0.84))
            out[n] = body + act
            continue
        if side == "front":
            out[n] = S.ybox(x, z, w, h, L.Y_PCB - heights[n], L.Y_PCB)
        else:
            out[n] = S.ybox(x, z, w, h, L.Y_PCB_BACK, L.Y_PCB_BACK + heights[n])
    # Ribbon: out of the LCD bottom edge, folded behind the LCD, up into J1
    y_lcd_back = L.Y_LCD + L.LCD_T
    out["ribbon"] = (S.ybox(0, -S.LCD_H / 2 - 0.6, L.RIBBON_W, 1.0, y_lcd_back - 1.0, y_lcd_back + 1.6)
                     + S.ybox(0, (-S.LCD_H / 2 + L.PARTS["J1"][1] - 2.75) / 2, L.RIBBON_W,
                              L.PARTS["J1"][1] - 2.75 + S.LCD_H / 2, y_lcd_back + 0.2, y_lcd_back + 0.5))
    cx, cz, r = L.CELL
    out["cell"] = S.ycyl(cx, cz, r, L.Y_PCB_BACK + 0.3, L.Y_PCB_BACK + 0.3 + 7.7)
    clip_x, clip_z = L.PARTS["BT1"][0], L.PARTS["BT1"][1]
    out["clip"] = S.ybox(clip_x, clip_z + 4, 25.6, 6.0, L.Y_PCB_BACK + 8.0, L.Y_PCB_BACK + 8.3)
    return out


def collisions(shell_parts, inner, buttons=None):
    hits = []
    if buttons is not None:
        for n in ("SW_A", "SW_B", "SW_C", "SW_D"):
            v = (buttons & inner[n]).volume
            if v > 0.0:
                hits.append(f"button plunger presses {n} at rest ({v:.3f} mm3)")
    for sn in ("front", "back"):
        for iname, solid in inner.items():
            v = (shell_parts[sn] & solid).volume
            if v > 0.05:
                hits.append(f"{iname} hits {sn} shell ({v:.2f} mm3)")
    return hits


COLORS = {"front": "#4C566A", "back": "#434C5E", "cap": "#3B4252", "pcb": "#2E7D5B",
          "lcd": "#B7C0A2", "cell": "#C0C5CE", "clip": "#D8DEE9", "button": "#FF7A1A"}


def to_mesh(solid, tag):
    p = RENDERS / f".fit_{tag}.stl"
    export_stl(solid, str(p), tolerance=0.02, angular_tolerance=0.1)
    return pv.read(p)


def render(shell_parts, inner):
    cap = shell_parts["cap_25"]
    buttons = None
    for n in ("SW_A", "SW_B", "SW_C", "SW_D"):
        x, z = L.PARTS[n][0], L.PARTS[n][1]
        s = 1 if x > 0 else -1
        b = shell_parts["button"]
        if s < 0:
            b = b.mirror(Plane.YZ)
        b = Location((s * (S.W / 2 - S.T), S.BTN_Y, z)) * b
        buttons = b if buttons is None else buttons + b

    groups = {
        "front": shell_parts["front"], "back": shell_parts["back"], "cap": cap, "button": buttons,
        "pcb": inner["pcb"], "lcd": inner["lcd"], "cell": inner["cell"], "clip": inner["clip"],
    }
    small = None
    for n in L.PARTS:
        if n in inner and n not in ("LCD1",):
            small = inner[n] if small is None else small + inner[n]
    groups["parts"] = small
    screen, pet = screen_and_pet(L.Y_LCD)
    screen, pet = Location((0, 0, L.LCD_VA_Z)) * screen, Location((0, 0, L.LCD_VA_Z)) * pet
    groups["screen"], groups["pet"] = screen, pet
    COLORS["screen"], COLORS["pet"] = "#B7C0A2", "#2E3440"
    COLORS["parts"] = "#5E81AC"
    meshes = {k: to_mesh(v, k) for k, v in groups.items()}

    explode = {"front": 0, "lcd": -8, "pcb": 6, "parts": 6, "cell": 14, "clip": 14,
               "back": 24, "cap": 34, "button": 0}
    p = pv.Plotter(off_screen=True, shape=(1, 3), window_size=(2400, 820), border=False)

    p.subplot(0, 0)
    p.set_background("#ECEFF4")
    for k in ("front", "back", "cap", "button", "lcd", "screen", "pet"):
        p.add_mesh(meshes[k], color=COLORS[k], smooth_shading=True, specular=0.2, split_sharp_edges=True)
    p.camera_position = [(-75, -115, 45), (0, 8, 0), (0, 0, 1)]
    p.camera.zoom(1.2)
    p.add_text("assembled", font_size=12, color="#4C566A")

    p.subplot(0, 1)
    p.set_background("#ECEFF4")
    for k, m in meshes.items():
        if k in ("screen", "pet"):
            continue
        p.add_mesh(m.translate((0, explode.get(k, 0), 0)), color=COLORS[k], smooth_shading=True,
                   split_sharp_edges=True)
    p.camera_position = [(140, 90, 70), (0, 14, 0), (0, 0, 1)]
    p.camera.zoom(1.15)
    p.add_text("exploded", font_size=12, color="#4C566A")

    p.subplot(0, 2)
    p.set_background("#ECEFF4")
    cut_x = L.CELL[0]
    for k, m in meshes.items():
        if k in ("screen", "pet"):
            continue
        clipped = m.clip(normal=(1, 0, 0), origin=(cut_x, 0, 0), invert=False)
        if clipped.n_points:
            p.add_mesh(clipped, color=COLORS[k], smooth_shading=False, show_edges=False)
    p.camera_position = [(-120, 8, 0), (0, 8, 0), (0, 0, 1)]
    p.camera.zoom(1.5)
    p.add_text("cutaway (through battery centre)", font_size=12, color="#4C566A")

    out = RENDERS / "shell-v0.1.png"
    p.screenshot(out)
    p.close()
    return out


if __name__ == "__main__":
    parts = S.build()
    inner = internals()
    btns = None
    for n in ("SW_A", "SW_B", "SW_C", "SW_D"):
        x, z = L.PARTS[n][0], L.PARTS[n][1]
        b = parts["button"] if x > 0 else parts["button"].mirror(Plane.YZ)
        b = Location((((1 if x > 0 else -1) * (S.W / 2 - S.T)), S.BTN_Y, z)) * b
        btns = b if btns is None else btns + b
    hits = collisions(parts, inner, btns)
    print("\n".join(hits) if hits else "no collisions between shell and board parts")
    print(render(parts, inner))
