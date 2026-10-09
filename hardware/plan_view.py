"""Draw the board floor plan (front + back) and check for collisions.

Run: .venv/bin/python hardware/plan_view.py
"""

import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

import layout as L

OUT = Path(__file__).resolve().parent / "renders" / "floorplan.png"
NO_CHECK = {("BT1", "CELL")}


def rect(name):
    x, z, w, h, side, _ = L.PARTS[name]
    return x - w / 2, z - h / 2, x + w / 2, z + h / 2, side


def inside_board(x0, z0, x1, z1):
    hw, hh, r = L.BOARD_W / 2, L.BOARD_H / 2, L.BOARD_R
    for x, z in ((x0, z0), (x0, z1), (x1, z0), (x1, z1)):
        if abs(x) > hw or abs(z) > hh:
            return False
        cx, cz = hw - r, hh - r
        if abs(x) > cx and abs(z) > cz and math.hypot(abs(x) - cx, abs(z) - cz) > r:
            return False
    return True


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def rect_hits_circle(r, cx, cz, rad):
    nx = min(max(cx, r[0]), r[2])
    nz = min(max(cz, r[1]), r[3])
    return math.hypot(nx - cx, nz - cz) < rad


def check():
    problems = []
    names = list(L.PARTS)
    for n in names:
        r = rect(n)
        if not inside_board(*r[:4]) and n != "LCD1":
            problems.append(f"{n} pokes outside the board")
    back = [n for n in names if L.PARTS[n][4] == "back" and n != "BT1"]
    for i, a in enumerate(back):
        for b in back[i + 1:]:
            if overlaps(rect(a), rect(b)):
                problems.append(f"{a} overlaps {b}")
        if rect_hits_circle(rect(a), *L.CELL):
            problems.append(f"{a} overlaps the battery")
    for hx, hz in L.BOSS_CENTERS:
        r = L.NOTCH_R
        notch = (hx - r, hz - r, hx + r, hz + r)
        for n in back:
            if overlaps(notch, rect(n)):
                problems.append(f"boss notch ({hx},{hz}) hits {n}")
        if rect_hits_circle(notch, *L.CELL):
            problems.append(f"boss notch ({hx},{hz}) hits the battery")
    if False:
            problems.append(f"boss notch ({hx},{hz}) hits the battery")
    return problems


def draw(ax, side, title):
    hw, hh = L.BOARD_W / 2, L.BOARD_H / 2
    mirror = -1 if side == "back" else 1   # back view is seen from behind
    ax.add_patch(FancyBboxPatch((-hw + L.BOARD_R, -hh + L.BOARD_R), L.BOARD_W - 2 * L.BOARD_R,
                                L.BOARD_H - 2 * L.BOARD_R, boxstyle=f"round,pad={L.BOARD_R}",
                                fc="#A3BE8C" if side == "front" else "#8FBCBB", ec="#2E3440", lw=1.5, alpha=0.35))
    shell = FancyBboxPatch((-L.W / 2 + 9, -L.H / 2 + 9), L.W - 18, L.H - 18, boxstyle="round,pad=9",
                           fc="none", ec="#4C566A", lw=1, ls="--")
    ax.add_patch(shell)
    for n, (x, z, w, h, s, _) in L.PARTS.items():
        if s != side:
            continue
        xm = x * mirror
        color = {"LCD1": "#B7C0A2", "BT1": "#D8DEE9"}.get(n, "#FF7A1A" if n.startswith("SW") else "#5E81AC")
        ax.add_patch(Rectangle((xm - w / 2, z - h / 2), w, h, fc=color, ec="#2E3440", alpha=0.8))
        ax.text(xm, z, n, ha="center", va="center", fontsize=7, color="#2E3440")
    if side == "back":
        cx, cz, rad = L.CELL
        ax.add_patch(Circle((cx * mirror, cz), rad, fc="none", ec="#BF616A", lw=1.5))
        ax.add_patch(Circle((cx * mirror, cz), L.CAP_OPENING_R, fc="none", ec="#BF616A", lw=1, ls=":"))
        ax.text(cx * mirror, cz - 4, "CR2477", ha="center", fontsize=8, color="#BF616A")
    if side == "front":
        ax.add_patch(Rectangle((-L.RIBBON_W / 2, -16.8), L.RIBBON_W, 16.8 + 2.5,
                               fc="#EBCB8B", ec="#2E3440", alpha=0.5))
        ax.text(0, -10, "ribbon (behind LCD)", ha="center", fontsize=6)
    for hx, hz in L.BOSS_CENTERS:
        ax.add_patch(Circle((hx * mirror, hz), L.NOTCH_R, fc="white", ec="#2E3440"))
        ax.text(hx * mirror, hz + 2.6, "boss", ha="center", fontsize=6, color="#4C566A")
    ax.set_xlim(-L.W / 2 - 2, L.W / 2 + 2)
    ax.set_ylim(-L.H / 2 - 2, L.H / 2 + 2)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=11)
    ax.grid(True, lw=0.3, alpha=0.5)


if __name__ == "__main__":
    probs = check()
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    draw(axes[0], "front", "Front (screen side)")
    draw(axes[1], "back", "Back (battery side, seen from behind)")
    fig.suptitle(f"Board {L.BOARD_W:.1f} x {L.BOARD_H:.1f} mm inside a {L.W:.0f} x {L.H:.0f} mm shell"
                 + ("" if not probs else f"   |   {len(probs)} problem(s)"), fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT, dpi=130)
    print(OUT)
    print("\n".join(probs) if probs else "no collisions")
