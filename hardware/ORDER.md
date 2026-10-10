# First run: 5 units (1/5 .. 5/5)

Prices are rough, USD, before shipping and import fees. Check every total before you pay.

## 1. JLCPCB: one cart, ships together (~$110-160)

### Boards + assembly
Upload `pcb/fab/gerbers.zip`.

| Setting | Value |
|---|---|
| Layers | 4 |
| Size | auto (48.4 x 38.4 mm) |
| Quantity | 5 |
| Thickness | 0.8 mm |
| Color | any (it's inside the case), green is cheapest |
| Surface finish | ENIG (the battery touches a bare pad) |
| Via covering | Tented |
| Mark on PCB | leave the default |
| Everything else | default |

Turn on **PCB Assembly**:

| Setting | Value |
|---|---|
| Type | Standard (parts on both sides) |
| Assembly side | Both sides |
| Quantity | 5 |
| Tooling holes | Added by JLCPCB |

Then upload `pcb/fab/bom.csv` and `pcb/fab/cpl.csv`.
- All 17 parts should match by LCSC number. U1 (C33688798) needs at least 5 in stock.
- TP1 is not in the files on purpose. It's only pads for the programming cable.
- **Placement preview:** check that every part's dots and pin 1 line up with its pads. U1, Y1, Q1, Q2, D1 and J1 are the ones to look at. Send me a screenshot of the preview and I'll check it.

### 3D printing (JLC3DP, same cart)
STLs are in `shell/out/`. Use SLA resin. Black with a paint-pen filled number looks best; white or translucent also works.

| File | Qty |
|---|---|
| front.stl | 5 |
| back_1of5.stl .. back_5of5.stl | 1 each |
| cap_25.stl | 5 |
| cap_15.stl, cap_35.stl | 1 each (fit test: tighter / looser) |
| button.stl | 24 (20 + spares, they're tiny) |

## 2. BuyDisplay (~$15 + ~$20 shipping)
| Item | Qty |
|---|---|
| ERC12864FSF-9, FSTN positive, white backlight | 7 (2 spares, the ribbon is fragile) |

## 3. DigiKey: programming tools, bought once (~$90)
| Item | Part # | Qty |
|---|---|---|
| Nordic nRF52 DK (loads the software, and I write the firmware on it before the boards arrive) | NRF52-DK | 1 |
| Tag-Connect cable, 10-pin Cortex | TC2030-CTX-NL | 1 |
| Tag-Connect retaining clip | TC2030-CLIP-3PACK | 1 |

## 4. Amazon (~$25)
| Item | Qty |
|---|---|
| CR2477 coin cells (Murata, Panasonic or Toshiba) | 10 |
| M1.7 x 10 mm self-tapping screws (or an M1.7 assortment) | 10+ |
| Ball chain keychains, 2.4 mm | 5+ |
| Clear PET/Mylar sheet or Kapton tape, for the battery pull-tabs | 1 |

## Assembly at home (~5 min per unit)
1. Slide the LCD ribbon into J1 and close the latch.
2. Drop the LCD into the front shell, then lay the board on top.
3. Put 4 buttons in the side holes.
4. Close with the numbered back and 2 screws.
5. Insert the cell with the pull-tab and twist the cap shut.
