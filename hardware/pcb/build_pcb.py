"""Generate the Tethos Pet PCB (KiCad 10) from layout.py + circuit.py.

Run with KiCad's bundled Python:
  ~/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 hardware/pcb/build_pcb.py

World coordinates are the front view used everywhere else (X right, Z up, mm, origin = board centre).
KiCad uses y-down, so y = -Z. "back" parts go on B.Cu (the battery side).
"""

import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
sys.path.insert(0, HW)
import circuit as C  # noqa: E402
import layout as L   # noqa: E402

KICAD_FP = os.path.expanduser("~/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")
LOCAL_FP = os.path.join(HERE, "tethos.pretty")
OUT = os.path.join(HERE, "tethos-pet.kicad_pcb")


def mm(v):
    return pcbnew.FromMM(v)


def V(X, Z):
    return pcbnew.VECTOR2I(mm(X), mm(-Z))


def world(p):
    return pcbnew.ToMM(p.x), -pcbnew.ToMM(p.y)


# ---------------------------------------------------------------------------------------------
# Placement: ref -> (X, Z, side, orient). orient is either a fixed rotation (deg) or a rule
# ("dir", pads_from, pads_to, (dx, dz)) meaning: the vector from the mean of pads_from to the
# mean of pads_to must point along (dx, dz) in the front view.
# ---------------------------------------------------------------------------------------------
P = L.PARTS
PLACE = {
    # module: left pad column (1-9) faces the top edge, pin 1 (antenna end) faces -X
    "U1": (P["U1"][0], P["U1"][1], "back", ("module",)),
    "Y1": (-0.6, 15.6, "back", 90),
    "C5": (1.7, 16.6, "back", 0),
    "C6": (1.7, 14.6, "back", 0),
    "C3": (-4.6, 18.4, "back", 0),
    "C4": (-2.7, 18.4, "back", 0),
    "TP1": (P["TP1"][0], P["TP1"][1], "back", 0),
    "BZ1": (P["BZ1"][0], P["BZ1"][1], "back", 0),
    "Q1": (13.6, 11.8, "back", 0),
    "R1": (15.5, 17.0, "back", 0),
    "D1": (18.7, 17.2, "back", 0),
    "R2": (12.6, 14.8, "back", 0),
    "R3": (11.8, 9.4, "back", 0),
    "Q2": (-12.0, -8.5, "back", 0),
    "C1": (-7.6, -16.5, "back", 0),
    "C2": (-2.8, -16.5, "back", 0),
    "BT1": (L.CELL[0], L.CELL[1], "back", ("cell",)),
    # side switches: actuator (from terminal pads toward MP pads) points out of the nearest side
    "SW1": (P["SW_A"][0], P["SW_A"][1], "back", ("dir", ["1", "2"], ["MP"], (-1, 0))),
    "SW2": (P["SW_B"][0], P["SW_B"][1], "back", ("dir", ["1", "2"], ["MP"], (-1, 0))),
    "SW3": (P["SW_C"][0], P["SW_C"][1], "back", ("dir", ["1", "2"], ["MP"], (1, 0))),
    "SW4": (P["SW_D"][0], P["SW_D"][1], "back", ("dir", ["1", "2"], ["MP"], (1, 0))),
    # front side, under the LCD
    "J1": (0.0, 8.5, "front", 0),   # ribbon tip lands ~z 6.0 after the fold: ~3 mm insertion
    "C10": (0.5, 12.2, "front", 90),
    "C11": (1.5, 12.2, "front", 90),
    "C7": (2.5, 12.2, "front", 90),
    "C8": (3.5, 12.2, "front", 90),
    "C9": (6.5, 12.2, "front", 90),
}


def load_fp(fpid):
    lib, name = fpid.split(":")
    path = LOCAL_FP if lib == "tethos" else os.path.join(KICAD_FP, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit(f"footprint not found: {fpid}")
    return fp


def pad_world(fp, names):
    pts = [world(p.GetPosition()) for p in fp.Pads() if p.GetNumber() in names]
    return sum(x for x, _ in pts) / len(pts), sum(z for _, z in pts) / len(pts)


def place(board, ref, fp):
    X, Z, side, orient = PLACE[ref]
    fp.SetPosition(V(0, 0))
    if side == "back":
        fp.Flip(V(0, 0), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)

    def score(rot):
        fp.SetOrientationDegrees(rot)
        if orient[0] == "module":
            # pads 1..9 must sit on the +Z side, pin 1 toward -X
            col = pad_world(fp, [str(i) for i in range(1, 10)])
            p1, p9 = pad_world(fp, ["1"]), pad_world(fp, ["9"])
            return col[1] - pad_world(fp, ["25", "26", "27", "28", "29"])[1] + (p9[0] - p1[0])
        if orient[0] == "cell":
            return -abs(pad_world(fp, ["1"])[1] - pad_world(fp, ["2"])[1])   # tabs side by side in X
        _, a, b, (dx, dz) = orient
        ax, az = pad_world(fp, a)
        bx, bz = pad_world(fp, b)
        return (bx - ax) * dx + (bz - az) * dz

    if isinstance(orient, (int, float)):
        fp.SetOrientationDegrees(orient)
    else:
        best = max((0, 90, 180, 270), key=score)
        fp.SetOrientationDegrees(best)

    if ref == "BT1":
        # put the (-) pad, not the footprint origin, at the cell centre
        cx, cz = pad_world(fp, ["3"])
        fp.SetPosition(V(X - cx, Z - cz))
    else:
        fp.SetPosition(V(X, Z))


def outline(board):
    """Rounded rectangle with two U-notches in the bottom edge for the shell's screw bosses."""
    hw, hh, r = L.BOARD_W / 2, L.BOARD_H / 2, L.BOARD_R
    nr = L.NOTCH_R

    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetStart(V(*a))
        s.SetEnd(V(*b))
        s.SetWidth(mm(0.1))
        board.Add(s)

    def arc(a, m, b):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetArcGeometry(V(*a), V(*m), V(*b))
        s.SetWidth(mm(0.1))
        board.Add(s)

    k = r * (1 - 1 / math.sqrt(2))
    # top edge, corners
    seg((-hw + r, hh), (hw - r, hh))
    arc((hw - r, hh), (hw - k, hh - k), (hw, hh - r))
    seg((hw, hh - r), (hw, -hh + r))
    arc((hw, -hh + r), (hw - k, -hh + k), (hw - r, -hh))
    # bottom edge with notches (right to left)
    xs = sorted((bx for bx, _ in L.BOSS_CENTERS), reverse=True)
    x = hw - r
    for bx in xs:
        bz = [z for (cx, z) in L.BOSS_CENTERS if cx == bx][0]
        seg((x, -hh), (bx + nr, -hh))
        seg((bx + nr, -hh), (bx + nr, bz))
        arc((bx + nr, bz), (bx, bz + nr), (bx - nr, bz))
        seg((bx - nr, bz), (bx - nr, -hh))
        x = bx - nr
    seg((x, -hh), (-hw + r, -hh))
    arc((-hw + r, -hh), (-hw + k, -hh + k), (-hw, -hh + r))
    seg((-hw, -hh + r), (-hw, hh - r))
    arc((-hw, hh - r), (-hw + k, hh - k), (-hw + r, hh))


def ant_gnd_strip():
    """ANT_GND1 (U1 pad 2) runs straight to the board edge, then along it out of the keep-out (SIM fig. 29)."""
    x0, z0, x1, z1 = L.ANT_KEEPOUT
    pad_x = x1 - 1.499 + (6.5 - 5.44) - 0.0     # pad 2 sits 1.06 mm in from the antenna end
    pad_x = L.PARTS["U1"][0] - 3.25 + 1.06
    pad_z = L.BOARD_H / 2 - L.ANT_EDGE_GAP - 0.41
    edge_z = L.BOARD_H / 2 - 0.6     # 0.35 mm track, 0.3 mm copper-to-edge rule
    return [(pad_x, pad_z), (pad_x, edge_z), (x1 + 0.35, edge_z)]


def rect_zone(board, layers, x0, z0, x1, z1, net=None, rule_area=False, priority=0, points=None):
    z = pcbnew.ZONE(board)
    ls = pcbnew.LSET()
    for layer in layers:
        ls.AddLayer(layer)
    z.SetLayerSet(ls)
    poly = z.Outline()
    poly.NewOutline()
    for X, Z in points or ((x0, z0), (x1, z0), (x1, z1), (x0, z1)):
        poly.Append(mm(X), mm(-Z))
    if rule_area:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
    else:
        z.SetNet(net)
        z.SetAssignedPriority(priority)
        z.SetMinThickness(mm(0.15))
        z.SetLocalClearance(mm(0.2))
        z.SetThermalReliefGap(mm(0.2))
        z.SetThermalReliefSpokeWidth(mm(0.25))
    board.Add(z)
    return z


def rules(board):
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(mm(0.8))
    ds.m_MinClearance = mm(0.09)
    ds.m_TrackMinWidth = mm(0.09)
    ds.m_ViasMinSize = mm(0.45)
    ds.m_MinThroughDrill = mm(0.3)          # JLC 4-layer: 0.3 mm drill / 0.45 mm pad is the no-fee via
    ds.m_ViasMinAnnularWidth = mm(0.075)
    ds.m_CopperEdgeClearance = mm(0.3)
    # tent every via: the CR2477's + rim sits on the board around the (-) pad
    ds.m_CoverViasFront = True
    ds.m_CoverViasBack = True
    ds.m_HoleClearance = mm(0.09)  # KiCad's Alps SKRT footprint has its guide holes close to its own pads
    ns = ds.m_NetSettings
    d = ns.GetDefaultNetclass()
    d.SetClearance(mm(0.12))
    d.SetTrackWidth(mm(0.15))
    d.SetViaDiameter(mm(0.45))
    d.SetViaDrill(mm(0.3))

    def netclass(name, width, clearance, nets):
        nc = pcbnew.NETCLASS(name)
        nc.SetClearance(mm(clearance))
        nc.SetTrackWidth(mm(width))
        nc.SetViaDiameter(mm(0.45))
        nc.SetViaDrill(mm(0.3))
        ns.SetNetclass(name, nc)
        for n in nets:
            ns.SetNetclassPatternAssignment(n, name)

    netclass("Power", 0.3, 0.15, ["GND", "VBAT", "VCELL", "BZ_R", "BZ_D"])
    # SWD leaves the module's inner pad row: needs JLC's 0.09 mm minimums between 0.65 mm pads
    netclass("Fine", 0.12, 0.1, ["SWDIO", "SWDCLK"])   # router necks to ~0.09 at the module pads
    ns.RecomputeEffectiveNetclasses()


def build():
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    board.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_POWER)
    rules(board)
    outline(board)

    nets = {}
    for name in sorted(C.nets()):
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        nets[name] = n

    for ref, (value, lcsc, fpid, pins) in C.PARTS.items():
        fp = load_fp(fpid)
        fp.SetReference(ref)
        fp.SetValue(value)
        if lcsc:
            fp.SetField("LCSC", lcsc)
            fp.GetField("LCSC").SetVisible(False)
        for item in fp.GraphicalItems():
            if isinstance(item, pcbnew.PCB_TEXT) and item.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
                item.SetVisible(False) if hasattr(item, "SetVisible") else None
        board.Add(fp)
        fp.Reference().SetVisible(False)   # tiny board, mostly hidden: no reference text on silk
        fp.Value().SetVisible(False)
        place(board, ref, fp)
        for pad in fp.Pads():
            net = pins.get(pad.GetNumber())
            if net:
                pad.SetNet(nets[net])
        if ref == "BT1":
            # the (-) contact must stay flat: no solder paste on it
            for pad in fp.Pads():
                if pad.GetNumber() == "3":
                    ls = pad.GetLayerSet()
                    ls.RemoveLayer(pcbnew.F_Paste)
                    ls.RemoveLayer(pcbnew.B_Paste)
                    pad.SetLayerSet(ls)

    big = (-L.W, -L.H, L.W, L.H)
    rect_zone(board, [pcbnew.In1_Cu], *big, net=nets["GND"])
    rect_zone(board, [pcbnew.In2_Cu], *big, net=nets["VBAT"])
    rect_zone(board, [pcbnew.F_Cu], *big, net=nets["GND"])
    rect_zone(board, [pcbnew.B_Cu], *big, net=nets["GND"])
    x0, z0, x1, z1 = L.ANT_KEEPOUT
    (px, pz), (_, ez), _ = ant_gnd_strip()
    xa, xb, zh0, zh1, zt = px - 0.3, px + 0.3, ez - 0.3, ez + 0.3, z1 + 1.0
    pz -= 0.4   # cover the track's round end cap at the pad
    corridor = [(x0, z0), (x1, z0), (x1, zh0), (xb, zh0), (xb, pz), (xa, pz), (xa, zh1), (x1, zh1),
                (x1, zt), (x0, zt)]
    rect_zone(board, [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu], x0, z0, x1, zt,
              rule_area=True, points=corridor)
    return board


def report(board):
    print("placement check:")
    for ref in ("U1", "BT1", "SW1", "SW3", "J1"):
        fp = board.FindFootprintByReference(ref)
        bb = fp.GetBoundingBox(False)
        x0, z1 = world(bb.GetOrigin())
        x1, z0 = world(bb.GetEnd())
        print(f"  {ref:4s} rot {fp.GetOrientationDegrees():5.0f} {'B' if fp.IsFlipped() else 'F'}  "
              f"x {x0:6.2f}..{x1:6.2f}  z {z0:6.2f}..{z1:6.2f}")
    u1 = board.FindFootprintByReference("U1")
    pads = {p.GetNumber(): world(p.GetPosition()) for p in u1.Pads()}
    print(f"  U1 pin1 {pads['1']}, pin9 {pads['9']}, pin25 {pads['25']}")
    edge_gap = L.BOARD_H / 2 - (pads["1"][1] + 0.41)
    print(f"  U1 package edge to board edge: {edge_gap:.2f} mm (target {L.ANT_EDGE_GAP})")


if __name__ == "__main__":
    b = build()
    report(b)
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    b.Save(OUT)
    print("saved", OUT)
