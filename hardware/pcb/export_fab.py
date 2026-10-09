"""Export JLCPCB fabrication + assembly files from tethos-pet.kicad_pcb.

Run: .venv/bin/python hardware/pcb/export_fab.py
Writes hardware/pcb/fab/: gerbers.zip, bom.csv, cpl.csv
"""

import csv
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
CONSIGNED = {"U1"}                # ANNA-B112: buy from DigiKey, ship to JLC


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
            w.writerow([r["Ref"], f'{float(r["PosX"]):.3f}mm', f'{float(r["PosY"]):.3f}mm',
                        "Top" if r["Side"] == "top" else "Bottom", f'{float(r["Rot"]):.1f}'])
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
            note = "CONSIGNED: supply 110 pcs (DigiKey)" if set(refs) & CONSIGNED else ""
            w.writerow([value, ",".join(sorted(refs)), fp, lcsc, note])
    return out, len(groups)


if __name__ == "__main__":
    z, names = gerbers()
    print(z, "->", ", ".join(names))
    print(*cpl())
    print(*bom())
