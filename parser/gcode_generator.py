#!/usr/bin/env python3
"""
gcode_generator.py — Phase 4: G-Code Generator

Reads toolpath.json and generates standard G-code for the PCB plotter.

Output: output/output.gcode

Supported G-code commands:
  G21        — units: millimeters
  G90        — absolute positioning
  G28        — home all axes
  G0 Xn Yn   — rapid move (pen up / laser off)
  G1 Xn Yn Fn — linear draw (pen down / laser on) at feed rate F
  M0         — program pause (optional, for pad dwell)
  M2         — program end

Feed rate:
  G0 (rapid): maximum speed, no F needed
  G1 (draw):  configurable, default 1000 mm/min
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Configuration ──────────────────────────────────────────────────
FEED_RATE = 1000        # mm/min for drawing moves (G1)
RAPID_FEED = 3000       # mm/min for rapid moves (some controllers need this)
PAD_DWELL_MS = 200      # milliseconds to dwell on pad locations


def generate_gcode(input_path: str = None, output_path: str = None,
                   feed_rate: int = FEED_RATE):
    """
    Generate G-code from toolpath.

    Args:
        input_path:  Path to toolpath.json
        output_path: Path for output G-code file
        feed_rate:   Drawing feed rate in mm/min
    """
    if input_path is None:
        input_path = str(PROJECT_ROOT / "output" / "toolpath.json")
    if output_path is None:
        output_path = str(PROJECT_ROOT / "output" / "output.gcode")

    print(f"[gcode] Loading: {input_path}")

    with open(input_path, 'r') as f:
        data = json.load(f)

    commands = data.get('commands', [])
    stats = data.get('statistics', {})
    work_area = data.get('work_area', {})

    print(f"[gcode] Processing {len(commands)} toolpath commands...")

    # Build G-code lines
    gcode = []

    # Header
    gcode.append(f"; PCB Plotter G-Code")
    gcode.append(f"; Source: {data.get('source', 'unknown')}")
    gcode.append(f"; Work area: {work_area.get('width', 0)} x {work_area.get('height', 0)} mm")
    gcode.append(f"; Draw moves: {stats.get('draw_moves', 0)}")
    gcode.append(f"; Rapid moves: {stats.get('rapid_moves', 0)}")
    gcode.append(f"; Pad marks: {stats.get('pad_marks', 0)}")
    gcode.append(f"; Feed rate: {feed_rate} mm/min")
    gcode.append(f";")
    gcode.append(f"")

    # Initialization
    gcode.append("G21          ; Units: millimeters")
    gcode.append("G90          ; Absolute positioning")
    gcode.append("G28          ; Home all axes")
    gcode.append("")

    # Track state to avoid redundant commands
    last_type = None
    line_count = 0

    for cmd in commands:
        cmd_type = cmd['type']
        x = cmd.get('x', 0)
        y = cmd.get('y', 0)

        if cmd_type == 'rapid':
            # Rapid move — pen up / laser off
            gcode.append(f"G0 X{x:.4f} Y{y:.4f}")
            last_type = 'rapid'

        elif cmd_type == 'draw':
            # Linear draw — pen down / laser on
            gcode.append(f"G1 X{x:.4f} Y{y:.4f} F{feed_rate}")
            last_type = 'draw'
            line_count += 1

        elif cmd_type == 'pad':
            # Pad flash — dwell at pad location
            gcode.append(f"G0 X{x:.4f} Y{y:.4f}")
            gcode.append(f"G4 P{PAD_DWELL_MS}     ; Pad dwell {PAD_DWELL_MS}ms (D={cmd.get('diameter', 0):.2f}mm)")

    # Footer
    gcode.append("")
    gcode.append("G0 X0 Y0     ; Return to origin")
    gcode.append("M2           ; Program end")

    # Write file
    with open(output_path, 'w') as f:
        f.write('\n'.join(gcode))
        f.write('\n')

    total_lines = len(gcode)
    print(f"[gcode] Generated successfully!")
    print(f"  G-code lines:  {total_lines}")
    print(f"  Draw commands:  {line_count}")
    print(f"  Feed rate:     {feed_rate} mm/min")
    print(f"  Output:        {output_path}")

    return output_path


if __name__ == "__main__":
    generate_gcode()
