# Tethotchi hardware

Everything is generated from two files:
- `layout.py`: board outline, part positions, shell dimensions, antenna keep-out
- `circuit.py`: parts, LCSC numbers, footprints, every pin's net

## Pipeline

```sh
# 1. floor plan + collision check
.venv/bin/python hardware/plan_view.py

# 2. PCB (KiCad 10, its bundled Python)
KPY=~/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
$KPY hardware/pcb/build_pcb.py          # outline, placement, nets, planes, antenna keep-out
PASSES=150 $KPY hardware/pcb/route.py   # power fanout + Freerouting (needs Java 25+) + ground pours
.venv/bin/python hardware/art/make_art.py   # silkscreen art -> art/art.json
$KPY hardware/pcb/add_art.py                # stamp it on the routed board
~/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb drc --severity-error hardware/pcb/tethos-pet.kicad_pcb

# 3. factory files -> hardware/pcb/fab/{gerbers.zip,bom.csv,cpl.csv}
.venv/bin/python hardware/pcb/export_fab.py

# 4. shell (build123d) -> hardware/shell/out/*.step|stl, fit check against the board parts
.venv/bin/python hardware/shell/shell.py
.venv/bin/python hardware/shell/fit_check.py
```

Freerouting isn't deterministic. `pcb/tethos-pet.routed-ok.kicad_pcb` is a run that passed DRC with 0 errors / 0 unconnected.

## Board
- 48.4 x 38.4 mm, 4 layers, 0.8 mm, ENIG (the CR2477 (-) contact is a bare pad)
- L1 front (LCD side): J1 + LCD caps. L2 GND plane. L3 VBAT plane. L4 back: everything else
- Vias 0.45/0.3 mm, tented (JLC's no-fee via size). Min track/space 0.09 mm (SWD escape from the module only)
- u-blox ANNA-B112 on the top edge per SIM appendix B.2 (edge version): package 1.55 mm from the edge,
  copper keep-out on all layers, ANT_GND1 strip to the edge

## Shell
- `shell/out/front.step`, `back.step`, `cap_15/25/35.step` (twist-cap fit variants), `button.step` (x4)
- First run of 5: `back_1of5.step` .. `back_5of5.step`, star + edition number debossed beside the cap
- Fasteners: 2x M1.7 x 10 self-tapping, from the back

## Before ordering
- [ ] JLC's assembly preview: check part rotations (SOT-23, crystal, connector are the usual offenders)
- [ ] Email u-blox support for the ANNA-B112 B.2 reference Gerbers and compare the antenna area
- [ ] Confirm the LCD ribbon's contacts face down after the fold (AFA07-S14FCA-00 is bottom-contact)
- [ ] First run is 5 units: U1 comes from JLC stock (`RUN_QTY` in export_fab.py), order 5 LCDs from BuyDisplay
