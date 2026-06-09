#!/usr/bin/env python3
"""
toolpath_generator.py — Phase 3: Toolpath Generator

Reads parsed_tracks.json and generates an optimized toolpath:
  - Converts line segments into ordered move/draw commands
  - Optimizes travel order using nearest-neighbor heuristic
  - Minimizes rapid (non-drawing) travel distance

Output: output/toolpath.json

Toolpath command types:
  "rapid"  — fast move to position (pen up / laser off)
  "draw"   — draw line to position (pen down / laser on)
"""

import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def distance(x1, y1, x2, y2):
    """Euclidean distance between two points."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def optimize_toolpath(segments):
    """
    Nearest-neighbor optimization to minimize rapid travel.

    Each segment has a start and end point. We can traverse each
    segment in either direction, so we pick the orientation that
    minimizes travel from the current position.

    Args:
        segments: list of dicts with x1,y1,x2,y2 keys

    Returns:
        Ordered list of (x1,y1,x2,y2,width) tuples
    """
    if not segments:
        return []

    remaining = list(range(len(segments)))
    ordered = []

    # Start from the segment closest to origin
    current_x, current_y = 0.0, 0.0

    while remaining:
        best_idx = None
        best_dist = float('inf')
        best_reversed = False

        for idx in remaining:
            seg = segments[idx]

            # Distance to start of segment
            d_start = distance(current_x, current_y, seg['x1'], seg['y1'])
            # Distance to end of segment (traverse in reverse)
            d_end = distance(current_x, current_y, seg['x2'], seg['y2'])

            if d_start < best_dist:
                best_dist = d_start
                best_idx = idx
                best_reversed = False

            if d_end < best_dist:
                best_dist = d_end
                best_idx = idx
                best_reversed = True

        seg = segments[best_idx]
        remaining.remove(best_idx)

        if best_reversed:
            ordered.append((seg['x2'], seg['y2'], seg['x1'], seg['y1'], seg.get('width', 0.2)))
            current_x, current_y = seg['x1'], seg['y1']
        else:
            ordered.append((seg['x1'], seg['y1'], seg['x2'], seg['y2'], seg.get('width', 0.2)))
            current_x, current_y = seg['x2'], seg['y2']

    return ordered


def generate_toolpath(input_path: str = None, output_path: str = None):
    """
    Generate toolpath from parsed tracks.

    Args:
        input_path:  Path to parsed_tracks.json
        output_path: Path for output toolpath.json
    """
    if input_path is None:
        input_path = str(PROJECT_ROOT / "output" / "parsed_tracks.json")
    if output_path is None:
        output_path = str(PROJECT_ROOT / "output" / "toolpath.json")

    print(f"[toolpath] Loading: {input_path}")

    with open(input_path, 'r') as f:
        data = json.load(f)

    tracks = data.get('tracks', [])
    pads = data.get('pads', [])
    bounds = data.get('bounds', {})

    print(f"[toolpath] Input: {len(tracks)} tracks, {len(pads)} pads")

    # Normalize coordinates: shift so min corner is at origin
    # This makes all coordinates positive for the plotter
    offset_x = bounds.get('min_x', 0)
    offset_y = bounds.get('min_y', 0)

    # Apply offset to tracks
    normalized_tracks = []
    for track in tracks:
        normalized_tracks.append({
            'x1': round(track['x1'] - offset_x, 4),
            'y1': round(track['y1'] - offset_y, 4),
            'x2': round(track['x2'] - offset_x, 4),
            'y2': round(track['y2'] - offset_y, 4),
            'width': track.get('width', 0.2)
        })

    # Apply offset to pads
    normalized_pads = []
    for pad in pads:
        normalized_pads.append({
            'x': round(pad['x'] - offset_x, 4),
            'y': round(pad['y'] - offset_y, 4),
            'diameter': pad.get('diameter', 1.0)
        })

    # Optimize track drawing order
    print("[toolpath] Optimizing travel path (nearest-neighbor)...")
    optimized = optimize_toolpath(normalized_tracks)

    # Build toolpath commands
    commands = []
    current_x, current_y = 0.0, 0.0
    total_rapid_dist = 0.0
    total_draw_dist = 0.0

    # First: draw all traces
    for x1, y1, x2, y2, width in optimized:
        # Rapid move to start of segment (if not already there)
        if abs(current_x - x1) > 0.001 or abs(current_y - y1) > 0.001:
            rapid_dist = distance(current_x, current_y, x1, y1)
            total_rapid_dist += rapid_dist
            commands.append({
                "type": "rapid",
                "x": round(x1, 4),
                "y": round(y1, 4)
            })

        # Draw to end of segment
        draw_dist = distance(x1, y1, x2, y2)
        total_draw_dist += draw_dist
        commands.append({
            "type": "draw",
            "x": round(x2, 4),
            "y": round(y2, 4),
            "width": round(width, 4)
        })
        current_x, current_y = x2, y2

    # Then: mark all pad locations (rapid to each, flash/dwell)
    for pad in normalized_pads:
        rapid_dist = distance(current_x, current_y, pad['x'], pad['y'])
        total_rapid_dist += rapid_dist
        commands.append({
            "type": "rapid",
            "x": round(pad['x'], 4),
            "y": round(pad['y'], 4)
        })
        commands.append({
            "type": "pad",
            "x": round(pad['x'], 4),
            "y": round(pad['y'], 4),
            "diameter": round(pad['diameter'], 4)
        })
        current_x, current_y = pad['x'], pad['y']

    # Return to origin
    commands.append({
        "type": "rapid",
        "x": 0,
        "y": 0
    })

    # Build output
    result = {
        "source": data.get('source_file', 'unknown'),
        "units": "mm",
        "offset_applied": {
            "x": round(offset_x, 4),
            "y": round(offset_y, 4)
        },
        "work_area": {
            "width": round(bounds.get('width', 0), 4),
            "height": round(bounds.get('height', 0), 4)
        },
        "statistics": {
            "total_commands": len(commands),
            "rapid_moves": sum(1 for c in commands if c['type'] == 'rapid'),
            "draw_moves": sum(1 for c in commands if c['type'] == 'draw'),
            "pad_marks": sum(1 for c in commands if c['type'] == 'pad'),
            "total_rapid_distance_mm": round(total_rapid_dist, 2),
            "total_draw_distance_mm": round(total_draw_dist, 2)
        },
        "commands": commands
    }

    # Write output
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"[toolpath] Generated successfully!")
    print(f"  Commands:       {len(commands)}")
    print(f"  Rapid moves:    {result['statistics']['rapid_moves']}")
    print(f"  Draw moves:     {result['statistics']['draw_moves']}")
    print(f"  Pad marks:      {result['statistics']['pad_marks']}")
    print(f"  Rapid travel:   {total_rapid_dist:.2f} mm")
    print(f"  Draw distance:  {total_draw_dist:.2f} mm")
    print(f"  Work area:      {result['work_area']['width']} x {result['work_area']['height']} mm")
    print(f"  Output:         {output_path}")

    return result


if __name__ == "__main__":
    generate_toolpath()
