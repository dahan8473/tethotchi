# Tethos Pet: parts list

Netlist and pin assignments live in `circuit.py`; placement in `layout.py`. Prices: JLC/LCSC at ~100 qty, checked 2026-10-09.

## On the board (JLC assembles)
| Ref | Part | LCSC | Unit | Notes |
|---|---|---|---|---|
| U1 | u-blox ANNA-B112 (nRF52832 SiP, internal antenna) | C33688798 / DigiKey consigned | $7.50-8.60 | FCC XPYANNAB1, IC 8595A-ANNAB1. JLC stock ~29: buy 110 from DigiKey and consign. Edge antenna layout per SIM App. B.2 |
| Y1 | Epson Q13FC1350000400, 32.768 kHz, 12.5 pF | C32346 (basic) | $0.14 | |
| C5, C6 | 20 pF C0G 0402 | C1554 (basic) | <$0.01 | crystal load |
| J1 | JUSHUO AFA07-S14FCA-00, 14P 1.0 mm slide-lock, 2.5 mm tall | C262720 | $0.10 | on the front side, under the LCD |
| C7-C10 | 1 µF 25 V X5R 0402 | C52923 (basic) | <$0.01 | LCD V0 / XV0 / VG / VDD |
| C4, C11 | 100 nF 0402 | C1525 (basic) | <$0.01 | |
| C3 | 4.7 µF 10 V 0402 | C23733 (basic) | $0.02 | module VCC |
| C1, C2 | 100 µF 6.3 V X5R 1206 | C380356 | $0.08 ea | bulk for BLE TX + buzzer on a coin cell |
| BT1 | MYOUNG MY-2477-02 CR2477 clip | C2979175 | $0.29 | (-) is an ENIG pad under the cell |
| Q2 | AO3401A P-FET | C15127 | $0.08 | reverse-battery protection |
| SW1-4 | Alps SKRTLAE010 side-push | C110293 | $0.12 ea | pin 2 = signal, 1+3 = GND |
| BZ1 | MLT-5020 magnetic buzzer | C94598 | $0.25 | |
| R1 | 47 Ω 0402 | C25118 | <$0.01 | limits buzzer surge (coil is 12 Ω) |
| Q1, D1, R2, R3 | 2N7002, 1N4148WS, 100 Ω, 100 kΩ | C8545, C2128, C25076, C25741 (basic) | $0.04 | buzzer driver |
| TP1 | Tag-Connect TC2030-NL footprint | none | $0 | flashing |

## Off the board
| Item | Source | Unit |
|---|---|---|
| LCD ERC12864FSF-9 (1.7", 128x64, ST7567, FSTN) | BuyDisplay | $1.95-2.18 |
| CR2477 | Battery Junction (Toshiba bulk) | $1.42 |
| Shell: front, back, twist cap, 4 button plungers | JLC3DP SLA | ~$2-4 |
| 2x M1.7 x 10 self-tapping screws | Amazon | ~$0.05 |
| Ball chain, pull-tab | Amazon | ~$0.26 |

## Estimated per-unit cost (110 units)
| | |
|---|---|
| Board parts | ~$11.30-12.40 |
| PCB + assembly (4-layer, ENIG, setup/stencil/extended-part fees spread over 110) | ~$2.00-3.00 |
| Off-board (LCD, cell, shell, screws, chain) | ~$5.70-7.90 |
| **Total** | **~$19-23** |

The module is the swing item: the ANNA-B112 is ~$1.30 more than the BT832 I first estimated, which is out of stock.

## Stack-up (front to back)
front wall 1.2 + LCD 3.0 + gap 2.8 (J1 + ribbon) + PCB 0.8 + battery clip 8.3 + clearance 0.5 + cap 1.5 = **18.1 mm**
