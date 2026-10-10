"""Single source of truth for board outline and part placement.

Coordinates in mm, viewed from the FRONT (screen side): X right, Z up, origin at board center.
"Back" parts are on the battery side of the PCB. The PCB generator and the shell CAD both import this.
"""

# Shell
W, H, D = 52.0, 42.0, 18.4
WALL = 1.6
FRONT_WALL = 1.2

# Board: inner cavity minus 0.2 mm clearance per side
BOARD_W = W - 2 * WALL - 0.4      # 48.4
BOARD_H = H - 2 * WALL - 0.4      # 38.4
BOARD_R = 7.5
BOARD_T = 0.8

# Depth stack (Y from front face)
Y_LCD = FRONT_WALL                 # 1.2 .. 4.2
LCD_T = 3.0
LCD_GAP = 3.1                      # LCD back to PCB front: J1 (HDGC 1.0-B-14PWB, 2.85 mm) + ribbon lives here
Y_PCB = Y_LCD + LCD_T + LCD_GAP    # 6.5 .. 7.3
Y_PCB_BACK = Y_PCB + BOARD_T
CLIP_H = 8.3
Y_SPLIT = 11.0                     # front/back shell split plane (behind the side buttons)

# name: (x, z, w, h, side, note)   w/h are footprint extents in X/Z
PARTS = {
    "LCD1": (0.0, 0.0, 43.5, 33.6, "front", "ERC12864FSF-9, normal orientation (6:00 viewing), tail exits the bottom"),
    "J1":   (0.0, 6.1, 16.0, 6.65, "front", "HDGC 1.0-B-14PWB dual-contact, pads at z 8.5, opening faces down at z 2.8"),
    "U1":   (-8.0, 14.4, 6.5, 6.5, "back", "ANNA-B112 on the straight top edge, u-blox SIM App. B.2 (edge version)"),
    "Y1":   (-1.8, 13.0, 3.2, 1.5, "back", "32.768 kHz crystal, next to XL1/XL2"),
    "BT1":  (3.0, -2.0, 37.0, 22.9, "back", "CR2477 clip MY-2477-02; cell 24.5 dia"),
    "BZ1":  (19.0, 13.0, 5.0, 5.0, "back", "MLT-5020 buzzer, sound hole in back shell top"),
    "TP1":  (8.0, 15.0, 7.0, 3.0, "back", "SWD pads (TC2030-NL)"),
    "SW_A": (-21.75, 7.5, 3.4, 4.5, "back", "top-left button"),
    "SW_B": (-21.75, -9.5, 3.4, 4.5, "back", "bottom-left button"),
    "SW_C": (21.75, 7.5, 3.4, 4.5, "back", "top-right button"),
    "SW_D": (21.75, -9.5, 3.4, 4.5, "back", "bottom-right button"),
    "C_BULK": (-4.0, -17.0, 7.0, 1.6, "back", "2x 100uF 1206"),
}

CELL = (3.0, -2.0, 24.5 / 2)       # x, z, radius
CAP_OPENING_R = 14.5
# No screws through the board (it is all screen on the front). The back shell screws into two
# bosses on the front shell's bottom wall; the board has edge notches so it slides past them.
# The board is clamped between the front ledge and ribs on the back shell.
BOSS_CENTERS = [(-14.0, -15.5), (14.0, -15.5)]   # x, z; M1.7 x 10 self-tapping from the back (head must fit inside the tapered back face)
BOSS_R = 1.7
NOTCH_R = BOSS_R + 0.2

# LCD ribbon: exits the bottom edge, folds 180 deg behind the LCD, runs up in the LCD/PCB gap into J1.
LCD_VA = (40.2, 26.4)
LCD_VA_Z = 1.92                    # visual area sits 1.92 mm above the glass centre (datasheet p.6)
RIBBON_W = 15.0

# u-blox ANNA-B112 SIM appendix B.2, figures 29/30 (edge version): package edge 1.55 mm from the board edge,
# no copper on any layer from the board edge to 3.1 mm inside the package edge line, spanning 3.485 mm
# beyond the antenna end of the module and 1.499 mm under it. Antenna end of U1 points to -X (front view).
ANT_EDGE_GAP = 1.55
ANT_KEEPOUT = (-8.0 - 3.25 - 3.485, 19.2 - 1.55 - 3.1, -8.0 - 3.25 + 1.499, 19.2)   # x0, z0, x1, z1
