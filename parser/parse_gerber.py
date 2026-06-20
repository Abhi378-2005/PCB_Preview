#!/usr/bin/env python3
"""
parse_gerber.py — Phase 2: Gerber Parser

Reads a Gerber file (F_Cu copper layer) and extracts:
  - Line segments (trace draws, D01 operations)
  - Flash pads (D03 operations) as point locations with aperture size

Output: output/parsed_tracks.json

Uses gerbonara library for robust Gerber parsing.
"""

import json
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from gerbonara import GerberFile
    from gerbonara.graphic_objects import Line, Arc, Flash
    from gerbonara.apertures import CircleAperture, RectangleAperture, ObroundAperture
except ImportError:
    print("ERROR: gerbonara not installed. Run: pip install gerbonara")
    sys.exit(1)


def parse_gerber(gerber_path: str, output_path: str = None):
    """
    Parse a Gerber file and extract geometry as line segments and pads.

    Args:
        gerber_path: Path to the .gbr file
        output_path: Path for output JSON (default: output/parsed_tracks.json)
    """
    if output_path is None:
        output_path = str(PROJECT_ROOT / "output" / "parsed_tracks.json")

    print(f"[parse_gerber] Loading: {gerber_path}")

    # Parse the Gerber file
    gerber = GerberFile.open(gerber_path)

    # Collect all geometry
    tracks = []    # line segments
    pads = []      # flash pads
    arcs = []      # arc segments
    regions_list = []

    # Track bounding box for info
    min_x = float('inf')
    min_y = float('inf')
    max_x = float('-inf')
    max_y = float('-inf')

    def update_bounds(x, y, r=0.0):
        nonlocal min_x, min_y, max_x, max_y
        min_x = min(min_x, x - r)
        min_y = min(min_y, y - r)
        max_x = max(max_x, x + r)
        max_y = max(max_y, y + r)

    def get_aperture_width(obj):
        """Extract the effective width/diameter of an aperture in mm."""
        ap = obj.aperture
        if isinstance(ap, CircleAperture):
            return float(ap.diameter)
        elif isinstance(ap, RectangleAperture):
            return float(max(ap.w, ap.h))
        elif isinstance(ap, ObroundAperture):
            return float(max(ap.w, ap.h))
        else:
            # For complex apertures, try to get a reasonable size
            try:
                return float(ap.diameter)
            except AttributeError:
                return 0.2  # default trace width

    for obj in gerber.objects:
        if isinstance(obj, Line):
            # Line segment (trace)
            # gerbonara uses mm by default
            x1 = float(obj.x1)
            y1 = float(-obj.y1)  # Gerber Y is inverted vs physical
            x2 = float(obj.x2)
            y2 = float(-obj.y2)

            width = get_aperture_width(obj)

            tracks.append({
                "type": "line",
                "x1": round(x1, 4),
                "y1": round(y1, 4),
                "x2": round(x2, 4),
                "y2": round(y2, 4),
                "width": round(width, 4)
            })

            update_bounds(x1, y1, width / 2)
            update_bounds(x2, y2, width / 2)

        elif isinstance(obj, Arc):
            # Arc segment — approximate as line for now
            x1 = float(obj.x1)
            y1 = float(-obj.y1)
            x2 = float(obj.x2)
            y2 = float(-obj.y2)

            width = get_aperture_width(obj)

            arcs.append({
                "type": "arc",
                "x1": round(x1, 4),
                "y1": round(y1, 4),
                "x2": round(x2, 4),
                "y2": round(y2, 4),
                "width": round(width, 4)
            })

            # Also add as a line for toolpath generation
            tracks.append({
                "type": "line",
                "x1": round(x1, 4),
                "y1": round(y1, 4),
                "x2": round(x2, 4),
                "y2": round(y2, 4),
                "width": round(width, 4)
            })

            update_bounds(x1, y1, width / 2)
            update_bounds(x2, y2, width / 2)

        elif isinstance(obj, Flash):
            # Flashed pad
            x = float(obj.x)
            y = float(-obj.y)

            width = get_aperture_width(obj)

            pads.append({
                "type": "pad",
                "x": round(x, 4),
                "y": round(y, 4),
                "diameter": round(width, 4)
            })

            update_bounds(x, y, width / 2)

        elif type(obj).__name__ == 'Region':
            # Filled polygon
            poly_points = []
            for seg in obj.iter_segments():
                p1, p2, arc = seg
                x1, y1 = float(p1[0]), float(-p1[1])
                poly_points.append((x1, y1))
                update_bounds(x1, y1, 0)
                
            if poly_points:
                regions_list.append({
                    "type": "region",
                    "points": [(round(p[0], 4), round(p[1], 4)) for p in poly_points]
                })

    # Build output structure
    result = {
        "source_file": os.path.basename(gerber_path),
        "units": "mm",
        "bounds": {
            "min_x": round(min_x, 4),
            "min_y": round(min_y, 4),
            "max_x": round(max_x, 4),
            "max_y": round(max_y, 4),
            "width": round(max_x - min_x, 4),
            "height": round(max_y - min_y, 4)
        },
        "statistics": {
            "total_tracks": len(tracks),
            "total_pads": len(pads),
            "total_arcs": len(arcs)
        },
        "tracks": tracks,
        "pads": pads
    }

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Write JSON
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    # Print summary
    print(f"[parse_gerber] Parsed successfully!")
    print(f"  Tracks:  {len(tracks)}")
    print(f"  Pads:    {len(pads)}")
    print(f"  Arcs:    {len(arcs)}")
    print(f"  Bounds:  ({result['bounds']['min_x']}, {result['bounds']['min_y']}) "
          f"to ({result['bounds']['max_x']}, {result['bounds']['max_y']})")
    print(f"  Size:    {result['bounds']['width']} x {result['bounds']['height']} mm")
    print(f"  Output:  {output_path}")

    return result


if __name__ == "__main__":
    # Default: parse the F_Cu layer
    gerber_dir = PROJECT_ROOT / "gerbers"
    gerber_file = gerber_dir / "Mini Inverter-F_Cu.gbr"

    if not gerber_file.exists():
        # Try to find any .gbr file
        gbr_files = list(gerber_dir.glob("*F_Cu*.gbr"))
        if gbr_files:
            gerber_file = gbr_files[0]
        else:
            print(f"ERROR: No F_Cu Gerber file found in {gerber_dir}")
            sys.exit(1)

    parse_gerber(str(gerber_file))
