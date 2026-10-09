"""Auto-route tethos-pet.kicad_pcb with Freerouting, then pour the outer-layer ground fills.

Run with KiCad's bundled Python (see build_pcb.py). Needs Java 25+ at /opt/homebrew/opt/openjdk.
Inner layers are planes (In1 = GND, In2 = VBAT), so Freerouting drops vias into them for those nets.
The outer GND pours are added after routing so the router doesn't treat them as obstacles.
"""

import os
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_pcb as B  # noqa: E402

PCB = B.OUT
DSN = os.path.join(HERE, "tethos-pet.dsn")
SES = os.path.join(HERE, "tethos-pet.ses")
JAVA = "/opt/homebrew/opt/openjdk/bin/java"
JAR = os.path.expanduser("~/.local/share/freerouting/freerouting.jar")
PASSES = int(os.environ.get("PASSES", "60"))


VIA_D, VIA_DRILL = 0.45, 0.2
CLEAR = 0.15


def pad_rects(board):
    out = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            x0, z1 = B.world(bb.GetOrigin())
            x1, z0 = B.world(bb.GetEnd())
            out.append((x0, z0, x1, z1, pad.GetNetname(), pad))
    return out


def rect_dist(px, pz, r):
    dx = max(r[0] - px, 0, px - r[2])
    dz = max(r[1] - pz, 0, pz - r[3])
    return (dx * dx + dz * dz) ** 0.5


def via_fits(px, pz, net, rects, vias):
    hw, hh, rad = B.L.BOARD_W / 2, B.L.BOARD_H / 2, B.L.BOARD_R
    m = VIA_D / 2 + 0.4
    if abs(px) > hw - m or abs(pz) > hh - m:
        return False
    cx, cz = hw - rad, hh - rad
    if abs(px) > cx and abs(pz) > cz and ((abs(px) - cx) ** 2 + (abs(pz) - cz) ** 2) ** 0.5 > rad - m:
        return False
    for bx, bz in B.L.BOSS_CENTERS:
        if abs(px - bx) < B.L.NOTCH_R + m and pz < bz + B.L.NOTCH_R + m:
            return False
    x0, z0, x1, z1 = B.L.ANT_KEEPOUT
    if x0 - m < px < x1 + m and pz > z0 - m:
        return False
    for r in rects:
        d = rect_dist(px, pz, r)
        if r[4] == net:
            if d < 0.05 and r[5] is not None:
                return False   # never put a via in a pad
        elif d < VIA_D / 2 + CLEAR:
            return False
    for vx, vz, vnet in vias:
        if ((vx - px) ** 2 + (vz - pz) ** 2) ** 0.5 < VIA_D + CLEAR:
            return False
    return True


def fanout(board, nets=("GND", "VBAT")):
    """Short stub + via from every power/ground pad to the inner plane."""
    rects = pad_rects(board)
    vias = []
    added = 0
    skip_u1_gnd = True
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        for pad in fp.Pads():
            net = pad.GetNetname()
            if net not in nets:
                continue
            if ref == "U1" and net == "GND":
                continue   # module ground pads reach the outer pour directly
            if ref == "BT1":
                continue   # the cell contact is a huge pad on the pour
            px, pz = B.world(pad.GetPosition())
            bb = pad.GetBoundingBox()
            x0, z1 = B.world(bb.GetOrigin())
            x1, z0 = B.world(bb.GetEnd())
            half = max(x1 - x0, z1 - z0) / 2
            fx, fz = B.world(fp.GetPosition())
            ax, az = px - fx, pz - fz
            dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), (0.7, 0.7), (-0.7, 0.7), (0.7, -0.7), (-0.7, -0.7)]
            dirs.sort(key=lambda d: -(d[0] * ax + d[1] * az))   # prefer pointing away from the part
            placed = False
            for dist in (half + 0.45, half + 0.65, half + 0.9, half + 1.2):
                for dx, dz in dirs:
                    vx, vz = px + dx * dist, pz + dz * dist
                    if via_fits(vx, vz, net, rects, vias):
                        v = pcbnew.PCB_VIA(board)
                        v.SetPosition(B.V(vx, vz))
                        v.SetWidth(B.mm(VIA_D))
                        v.SetDrill(B.mm(VIA_DRILL))
                        v.SetNet(pad.GetNet())
                        board.Add(v)
                        t = pcbnew.PCB_TRACK(board)
                        t.SetStart(pad.GetPosition())
                        t.SetEnd(v.GetPosition())
                        t.SetWidth(B.mm(0.3 if net == "VBAT" else 0.25))
                        t.SetLayer(pcbnew.B_Cu if fp.IsFlipped() else pcbnew.F_Cu)
                        t.SetNet(pad.GetNet())
                        board.Add(t)
                        vias.append((vx, vz, net))
                        rects.append((vx - VIA_D / 2, vz - VIA_D / 2, vx + VIA_D / 2, vz + VIA_D / 2, net, None))
                        # the stub is an obstacle for later vias too
                        w = 0.3    # stub half-width 0.15 + margin
                        for k in range(0, 13):
                            sx, sz = px + (vx - px) * k / 12, pz + (vz - pz) * k / 12
                            rects.append((sx - w, sz - w, sx + w, sz + w, net, None))
                        added += 1
                        placed = True
                        break
                if placed:
                    break
            if not placed:
                print(f"  fanout: no room next to {ref}.{pad.GetNumber()} ({net})")
    print(f"fanout vias: {added}")


def main():
    board = pcbnew.LoadBoard(PCB)
    outer = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu)]
    for z in outer:
        board.Remove(z)
    for t in list(board.GetTracks()):
        board.Remove(t)
    gnd = board.FindNet("GND")
    pts = B.ant_gnd_strip()
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(B.V(*a))
        t.SetEnd(B.V(*b))
        t.SetWidth(B.mm(0.35))
        t.SetLayer(pcbnew.B_Cu)
        t.SetNet(gnd)
        board.Add(t)
    fanout(board)
    if not pcbnew.ExportSpecctraDSN(board, DSN):
        raise SystemExit("DSN export failed")

    cmd = [JAVA, "-jar", JAR, "-de", DSN, "-do", SES, "-mp", str(PASSES), "--gui.enabled=false"]
    print(" ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    tail = (res.stdout + res.stderr).strip().splitlines()[-15:]
    print("\n".join(tail))
    if not os.path.exists(SES):
        raise SystemExit("Freerouting produced no session file")

    if not pcbnew.ImportSpecctraSES(board, SES):
        raise SystemExit("SES import failed")

    # Freerouting sometimes necks tracks below the fab minimum to squeeze past pads
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_TRACE_T and t.GetWidth() < B.mm(0.09):
            t.SetWidth(B.mm(0.09))

    big = (-B.L.W, -B.L.H, B.L.W, B.L.H)
    B.rect_zone(board, [pcbnew.F_Cu], *big, net=gnd)
    B.rect_zone(board, [pcbnew.B_Cu], *big, net=gnd)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PCB)
    print("routed and saved", PCB, "tracks:", len(board.GetTracks()))


if __name__ == "__main__":
    main()
