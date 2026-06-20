#!/usr/bin/env python3
"""
raster_gcode.py — Raster G-Code Generator

Reads parsed_tracks.json and generates line-by-line raster G-code.
Burns the negative space (white) and skips the traces (black).
"""

import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Configuration ──────────────────────────────────────────────────
PIXELS_PER_MM = 20      # 0.05mm step size (prevents shorts and distortion by providing 75% laser overlap)
FEED_RATE = 1000        # mm/min for drawing moves (G1)
LASER_POWER = 1000      # Max laser power
LASER_DIAMETER = 0.2    # mm - Laser beam diameter for tool compensation

def generate_raster_gcode(input_path: str = None, output_path: str = None, 
                          pixels_per_mm: int = PIXELS_PER_MM,
                          feed_rate: int = FEED_RATE):
    if input_path is None:
        input_path = str(PROJECT_ROOT / "output" / "parsed_tracks.json")
    if output_path is None:
        output_path = str(PROJECT_ROOT / "output" / "output.gcode")

    print(f"[raster] Loading: {input_path}")
    with open(input_path, 'r') as f:
        data = json.load(f)

    tracks = data.get('tracks', [])
    pads = data.get('pads', [])
    bounds = data.get('bounds', {})
    
    offset_x = bounds.get('min_x', 0.0)
    offset_y = bounds.get('min_y', 0.0)
    width_mm = bounds.get('width', 0.0)
    height_mm = bounds.get('height', 0.0)
    
    # Calculate image dimensions
    width_px = int(round(width_mm * pixels_per_mm)) + 2 # slight padding
    height_px = int(round(height_mm * pixels_per_mm)) + 2
    
    print(f"[raster] Rendering bitmap: {width_px} x {height_px} pixels ({pixels_per_mm} px/mm)")

    # Create white image (255 = negative space = burn)
    img = Image.new("L", (width_px, height_px), color=255)
    draw = ImageDraw.Draw(img)
    
    def to_px(val):
        return int(round(val * pixels_per_mm))
        
    # Draw traces in black (0 = copper = skip)
    for track in tracks:
        x1 = to_px(track['x1'] - offset_x)
        y1 = to_px(track['y1'] - offset_y)
        x2 = to_px(track['x2'] - offset_x)
        y2 = to_px(track['y2'] - offset_y)
        # Add LASER_DIAMETER to compensate for beam width (prevents over-etching)
        w_px = max(1, to_px(track.get('width', 0.2) + LASER_DIAMETER))
        
        # Draw the line segment
        draw.line([x1, y1, x2, y2], fill=0, width=w_px)
        
        # Draw circles at the endpoints to create round caps (fixes corner gaps/breaks)
        r = w_px / 2.0
        draw.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=0)
        draw.ellipse([x2 - r, y2 - r, x2 + r, y2 + r], fill=0)
        
    # Draw pads in black
    for pad in pads:
        x = to_px(pad['x'] - offset_x)
        y = to_px(pad['y'] - offset_y)
        # Add LASER_DIAMETER to compensate for beam width
        r = to_px((pad.get('diameter', 1.0) + LASER_DIAMETER) / 2.0)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=0)

    # Draw regions (custom polygons/joints) in black
    regions = data.get('regions', [])
    for reg in regions:
        points = []
        for p in reg['points']:
            points.append((to_px(p[0] - offset_x), to_px(p[1] - offset_y)))
        if points:
            # Draw the filled polygon itself
            draw.polygon(points, fill=0)
            
            # Dilate the polygon to apply tool compensation
            w_px = max(1, to_px(LASER_DIAMETER))
            for i in range(len(points)):
                p1 = points[i]
                p2 = points[(i+1) % len(points)]
                draw.line([p1, p2], fill=0, width=w_px)
                r = w_px / 2.0
                draw.ellipse([p1[0]-r, p1[1]-r, p1[0]+r, p1[1]+r], fill=0)

        
    print("[raster] Generating G-code paths (zigzag raster)...")
    
    gcode = []
    gcode.append(f"; PCB Plotter Raster G-Code")
    gcode.append(f"; Resolution: {pixels_per_mm} px/mm (0.{10//pixels_per_mm}mm step)")
    gcode.append(f"; Work area: {width_mm:.2f} x {height_mm:.2f} mm")
    gcode.append(f"")
    gcode.append("G21          ; Units: millimeters")
    gcode.append("G90          ; Absolute positioning")
    gcode.append("G28          ; Home all axes")
    gcode.append("M5           ; Ensure laser is OFF")
    gcode.append(f"G0 F{feed_rate}   ; Set rapid feed")
    gcode.append(f"G1 F{feed_rate}   ; Set draw feed")
    gcode.append("")
    
    # Iterate pixel rows to generate G-code
    pixels = img.load()
    stats_burn_moves = 0
    stats_skip_moves = 0
    
    for y in range(height_px):
        y_mm = y / pixels_per_mm
        
        # Zig-zag: even rows go L->R, odd rows go R->L
        left_to_right = (y % 2 == 0)
        
        x_start = 0 if left_to_right else width_px - 1
        x_end = width_px if left_to_right else -1
        x_step = 1 if left_to_right else -1
        
        current_state = 0 # 0 = skip, 255 = burn
        segment_start_x = -1
        
        for x in range(x_start, x_end, x_step):
            val = pixels[x, y]
            
            # If state changes, close the previous segment
            if val != current_state:
                if current_state == 255: # We were burning, now we stop
                    x_physical_start = segment_start_x / pixels_per_mm
                    x_physical_end = x / pixels_per_mm
                    
                    gcode.append(f"G0 X{x_physical_start:.3f} Y{y_mm:.3f}")
                    gcode.append(f"M3 S{LASER_POWER}")
                    gcode.append(f"G1 X{x_physical_end:.3f} Y{y_mm:.3f}")
                    gcode.append("M5")
                    stats_burn_moves += 1
                
                # Start new segment
                current_state = val
                segment_start_x = x
                
        # Handle the last segment of the row if we were burning
        if current_state == 255:
            x_physical_start = segment_start_x / pixels_per_mm
            x_physical_end = (x_end - x_step) / pixels_per_mm
            
            gcode.append(f"G0 X{x_physical_start:.3f} Y{y_mm:.3f}")
            gcode.append(f"M3 S{LASER_POWER}")
            gcode.append(f"G1 X{x_physical_end:.3f} Y{y_mm:.3f}")
            gcode.append("M5")
            stats_burn_moves += 1
            
    gcode.append("")
    gcode.append("G0 X0 Y0     ; Return to origin")
    gcode.append("M2           ; Program end")
    
    with open(output_path, 'w') as f:
        f.write('\n'.join(gcode))
        f.write('\n')
        
    print(f"[raster] Generation complete!")
    print(f"  Burn moves: {stats_burn_moves}")
    print(f"  G-code lines: {len(gcode)}")
    print(f"  Output: {output_path}")
    
    return {
        "success": True,
        "burn_moves": stats_burn_moves,
        "gcode_lines": len(gcode),
        "output_file": "output.gcode"
    }

if __name__ == "__main__":
    generate_raster_gcode()
