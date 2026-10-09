"""Circuit netlist: single source of truth for the schematic, PCB nets and BOM.

Every pin decision cites the datasheet it came from (hardware/datasheets/).
Run: .venv/bin/python hardware/circuit.py   -> prints BOM + per-net connections, checks for typos.
"""

# ref: (value, LCSC, footprint, {pin: net})
PARTS = {
    # --- Power: CR2477 -> reverse-polarity P-FET -> VBAT ---
    "BT1": ("CR2477 clip MY-2477-02", "C2979175", "tethos:BAT-SMD_MY-2477-02",
            {"1": "VCELL", "2": "VCELL", "3": "GND"}),   # 1,2 = clip tabs (+); 3 = bare ENIG pad under the cell (-)
    "Q2": ("AO3401A", "C15127", "Package_TO_SOT_SMD:SOT-23",
           # KiCad SOT-23 pins: 1 G, 2 S, 3 D. Drain to cell, source to load, gate to GND
           {"3": "VCELL", "2": "VBAT", "1": "GND"}),
    "C1": ("100uF 6.3V X5R 1206", "C380356", "Capacitor_SMD:C_1206_3216Metric", {"1": "VBAT", "2": "GND"}),
    "C2": ("100uF 6.3V X5R 1206", "C380356", "Capacitor_SMD:C_1206_3216Metric", {"1": "VBAT", "2": "GND"}),

    # --- MCU: u-blox ANNA-B112 (nRF52832). Pin numbers: ANNA-B112 datasheet table 7 ---
    "U1": ("ANNA-B112", "C33688798", "tethos:BULETM-SMD_ANNA-B112", {
        "1": None,           # ANT_PCB: corner version only
        "2": "GND", "3": "GND",             # ANT_GND1/2: grounded for the edge version (SIM B.2)
        "5": "ANT_FEED", "6": "ANT_FEED",   # ANT_INT tied to ANT: use the internal antenna
        "9": "VBAT",
        # Signals only on the outer pad ring so they escape without vias under the module.
        # Bottom row (14-20) and right column (25-31); pin numbers from datasheet table 7.
        "14": "LCD_SCL",     # P0.15
        "15": "LCD_SDA",     # P0.16
        "16": "LCD_RST",     # P0.18
        "19": "LCD_CS",      # P0.03
        "20": "LCD_A0",      # P0.02
        "25": "BTN_C",       # P0.31 (low-drive pin, fine for an input)
        "26": "BTN_D",       # P0.30
        "27": "BTN_A",       # P0.29
        "28": "BTN_B",       # P0.28
        "29": "BUZZ",        # P0.27, 4 kHz PWM counts as low frequency for this pin
        "17": "XL1", "18": "XL2",           # P0.00 / P0.01 LFXO
        "39": "SWDCLK", "40": "SWDIO",      # inner row: the only pins that need vias under the module
        **{str(p): "GND" for p in (4, 7, 8, 10, 11, 32, 33, 41, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52)},
    }),
    "C3": ("4.7uF 10V X5R 0402", "C23733", "Capacitor_SMD:C_0402_1005Metric", {"1": "VBAT", "2": "GND"}),
    "C4": ("100nF 16V X7R 0402", "C1525", "Capacitor_SMD:C_0402_1005Metric", {"1": "VBAT", "2": "GND"}),

    # 32.768 kHz crystal, CL 12.5 pF -> C = 2*CL - (C_pin + C_pcb) ~ 25 - 5 = 20 pF
    "Y1": ("32.768kHz 12.5pF 3215", "C32346", "Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm", {"1": "XL1", "2": "XL2"}),
    "C5": ("20pF C0G 0402", "C1554", "Capacitor_SMD:C_0402_1005Metric", {"1": "XL1", "2": "GND"}),
    "C6": ("20pF C0G 0402", "C1554", "Capacitor_SMD:C_0402_1005Metric", {"1": "XL2", "2": "GND"}),

    # --- LCD: ERC12864FSF-9 via 14-pin 1.0 mm FPC. Pinout: ERC12864-9 datasheet section 4.1 ---
    "J1": ("AFA07-S14FCA-00", "C262720", "Connector_FFC-FPC:JUSHUO_AFA07-S14FCA-00_1x14-1MP_P1.0mm_Horizontal", {
        "1": None, "2": None,              # BLA / BLK: backlight unused (FSTN, sunlight readable)
        "3": "LCD_CS", "4": "LCD_RST", "5": "LCD_A0", "6": "LCD_SCL", "7": "LCD_SDA",
        "8": "VBAT", "9": "GND",
        "10": "LCD_V0", "11": "LCD_XV0",
        "12": None, "13": None,            # NC per datasheet
        "14": "LCD_VG",
        "MP": "GND",                        # connector mounting tabs
    }),
    "C7": ("1uF 25V X5R 0402", "C52923", "Capacitor_SMD:C_0402_1005Metric", {"1": "LCD_V0", "2": "GND"}),
    "C8": ("1uF 25V X5R 0402", "C52923", "Capacitor_SMD:C_0402_1005Metric", {"1": "LCD_XV0", "2": "GND"}),
    "C9": ("1uF 25V X5R 0402", "C52923", "Capacitor_SMD:C_0402_1005Metric", {"1": "LCD_VG", "2": "GND"}),
    "C10": ("1uF 25V X5R 0402", "C52923", "Capacitor_SMD:C_0402_1005Metric", {"1": "VBAT", "2": "GND"}),
    "C11": ("100nF 16V X7R 0402", "C1525", "Capacitor_SMD:C_0402_1005Metric", {"1": "VBAT", "2": "GND"}),

    # --- Buttons: Alps SKRTLAE010. Datasheet p.3: pins 1 and 3 are joined, the switch is between them and 2 ---
    # Inputs use the nRF internal pull-ups; pressing shorts the input to GND.
    "SW1": ("SKRTLAE010", "C110293", "Button_Switch_SMD:SW_Push_1P1T-MP_NO_Horizontal_Alps_SKRTLAE010", {"1": "GND", "2": "BTN_A", "MP": "GND"}),
    "SW2": ("SKRTLAE010", "C110293", "Button_Switch_SMD:SW_Push_1P1T-MP_NO_Horizontal_Alps_SKRTLAE010", {"1": "GND", "2": "BTN_B", "MP": "GND"}),
    "SW3": ("SKRTLAE010", "C110293", "Button_Switch_SMD:SW_Push_1P1T-MP_NO_Horizontal_Alps_SKRTLAE010", {"1": "GND", "2": "BTN_C", "MP": "GND"}),
    "SW4": ("SKRTLAE010", "C110293", "Button_Switch_SMD:SW_Push_1P1T-MP_NO_Horizontal_Alps_SKRTLAE010", {"1": "GND", "2": "BTN_D", "MP": "GND"}),

    # --- Buzzer: MLT-5020 magnetic, low-side N-FET, flyback diode, series R limits coin-cell surge ---
    "BZ1": ("MLT-5020", "C94598", "tethos:BUZ-SMD_L5.0-W5.5-P4.60", {"1": "VBAT", "2": "BZ_R", "3": None}),
    # coil is 12 ohm: 47 ohm series keeps the peak near 50 mA
    "R1": ("47R 0402", "C25118", "Resistor_SMD:R_0402_1005Metric", {"1": "BZ_R", "2": "BZ_D"}),
    "D1": ("1N4148WS", "C2128", "Diode_SMD:D_SOD-323", {"1": "VBAT", "2": "BZ_R"}),
    "Q1": ("2N7002", "C8545", "Package_TO_SOT_SMD:SOT-23", {"3": "BZ_D", "2": "GND", "1": "BUZZ_G"}),
    "R2": ("100R 0402", "C25076", "Resistor_SMD:R_0402_1005Metric", {"1": "BUZZ", "2": "BUZZ_G"}),
    "R3": ("100k 0402", "C25741", "Resistor_SMD:R_0402_1005Metric", {"1": "BUZZ_G", "2": "GND"}),

    # --- Programming: Tag-Connect TC2030-NL (nRF52 DK debug out) ---
    "TP1": ("TC2030-NL", "", "Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical", {
        "1": "VBAT", "2": "SWDIO", "3": None, "4": "SWDCLK", "5": "GND", "6": None}),   # SWD needs no reset/trace
}

# Things to confirm from datasheets before layout (kept here so they can't be forgotten)
OPEN = [
    "SKRTLAE010 footprint: 2x 0.9 mm guide holes, no copper under the actuator (datasheet p.3 hatched area).",
    "AFA07-S14FCA-00 is bottom-contact: confirm the LCD ribbon's contacts face the PCB after the 180 deg fold (else use the top-contact variant).",
    "ANNA-B112 edge layout follows SIM appendix B.2 from the figures; ask u-blox support for the reference Gerbers to confirm before production.",
    "LCD VDD min is 2.8 V; CR2477 sags below that near end of life. Measure contrast at 2.6-2.8 V on the prototype.",
]


def nets():
    out = {}
    for ref, (_, _, _, pins) in PARTS.items():
        for pin, net in pins.items():
            if net:
                out.setdefault(net, []).append(f"{ref}.{pin}")
    return out


def check():
    problems = []
    for net, conns in nets().items():
        if len(conns) < 2:
            problems.append(f"net {net} has one connection: {conns}")
    return problems


if __name__ == "__main__":
    for net, conns in sorted(nets().items()):
        print(f"{net:10s} {', '.join(conns)}")
    print()
    probs = check()
    print("\n".join(probs) if probs else "every net has 2+ connections")
    print("\nOpen items:\n- " + "\n- ".join(OPEN))
