"""Stamp hardware/art/art.json onto the routed board as silkscreen polygons (group "tsi_art").

Run after route.py, with KiCad's Python. Re-running replaces the previous art.
"""

import json
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_pcb as B  # noqa: E402

ART = os.path.join(HERE, "..", "art", "art.json")
LAYERS = {"F": pcbnew.F_SilkS, "B": pcbnew.B_SilkS}


def main():
    board = pcbnew.LoadBoard(B.OUT)
    for g in list(board.Groups()):
        if g.GetName() == "tsi_art":
            g.RemoveAll()
            board.Delete(g)
    for d in list(board.GetDrawings()):   # the art is the only board-level silkscreen polygon
        if d.GetLayer() in LAYERS.values() and d.Type() == pcbnew.PCB_SHAPE_T and d.GetShape() == pcbnew.SHAPE_T_POLY:
            board.Delete(d)
    group = pcbnew.PCB_GROUP(board)
    group.SetName("tsi_art")
    board.Add(group)

    data = json.load(open(ART))
    n = 0
    for side, polys in data.items():
        for p in polys:
            ps = pcbnew.SHAPE_POLY_SET()
            o = ps.NewOutline()
            for x, z in p["outline"]:
                ps.Append(B.mm(x), B.mm(-z), o)
            for hole in p["holes"]:
                h = ps.NewHole(o)
                for x, z in hole:
                    ps.Append(B.mm(x), B.mm(-z), o, h)
            s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_POLY)
            s.SetPolyShape(ps)
            s.SetFilled(True)
            s.SetWidth(0)
            s.SetLayer(LAYERS[side])
            board.Add(s)
            group.AddItem(s)
            n += 1
    board.Save(B.OUT)
    print(f"art: {n} polygons")


if __name__ == "__main__":
    main()
