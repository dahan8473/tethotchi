"""Export JLCPCB fabrication + assembly files from tethos-pet.kicad_pcb.

Run: .venv/bin/python hardware/pcb/export_fab.py
Writes hardware/pcb/fab/: gerbers.zip, bom.csv, cpl.csv
"""

import csv
import math
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import circuit as C  # noqa: E402

KC = Path.home() / "Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
PCB = HERE / "tethos-pet.kicad_pcb"
FAB = HERE / "fab"
GERB = FAB / "gerbers"

LAYERS = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"
NOT_ASSEMBLED = {"TP1"}           # footprint only: Tag-Connect pads
RUN_QTY = 5                       # first run: numbered 1/5 .. 5/5
# JLC's 3D models disagree with our footprints for these (checked in their placement preview, 2026-10-10):
# ref -> (extra rotation deg, shift along the part's own Y in mm)
JLC_FIX = {
    "D1": (180, 0.0),     # cathode band
    "BZ1": (180, 0.0),    # + pin
}
CONSIGNED = {"U1"} if RUN_QTY > 25 else set()   # JLC stocks ~29 ANNA-B112; past that, buy from DigiKey and ship to JLC


def run(*args):
    subprocess.run([str(KC), *args], check=True, capture_output=True)


def gerbers():
    GERB.mkdir(parents=True, exist_ok=True)
    for f in GERB.iterdir():
        f.unlink()
    run("pcb", "export", "gerbers", "--layers", LAYERS, "-o", str(GERB) + "/", str(PCB))
    run("pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th", "-o", str(GERB) + "/", str(PCB))
    out = FAB / "gerbers.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(GERB.iterdir()):
            z.write(f, f.name)
    return out, sorted(f.name for f in GERB.iterdir())


def cpl():
    raw = FAB / "pos-raw.csv"
    run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "-o", str(raw), str(PCB))
    rows = list(csv.DictReader(raw.open()))
    out = FAB / "cpl.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in rows:
            if r["Ref"] in NOT_ASSEMBLED:
                continue
            x, y, rot = float(r["PosX"]), float(r["PosY"]), float(r["Rot"])
            if r["Ref"] in JLC_FIX:
                drot, shift = JLC_FIX[r["Ref"]]
                x -= shift * math.sin(math.radians(rot))
                y += shift * math.cos(math.radians(rot))
                rot = (rot + drot) % 360
            w.writerow([r["Ref"], f'{x:.3f}mm', f'{y:.3f}mm',
                        "Top" if r["Side"] == "top" else "Bottom", f'{rot:.1f}'])
    raw.unlink()
    return out, len(rows) - len(NOT_ASSEMBLED)


def bom():
    groups = {}
    for ref, (value, lcsc, fpid, _) in C.PARTS.items():
        if ref in NOT_ASSEMBLED:
            continue
        key = (value, lcsc, fpid.split(":")[1])
        groups.setdefault(key, []).append(ref)
    out = FAB / "bom.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "Note"])
        for (value, lcsc, fp), refs in sorted(groups.items(), key=lambda g: g[1][0]):
            note = f"CONSIGNED: supply {RUN_QTY + 10} pcs (DigiKey)" if set(refs) & CONSIGNED else ""
            w.writerow([value, ",".join(sorted(refs)), fp, lcsc, note])
    return out, len(groups)


if __name__ == "__main__":
    z, names = gerbers()
    print(z, "->", ", ".join(names))
    print(*cpl())
    print(*bom())
