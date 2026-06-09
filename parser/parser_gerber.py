import re

GERBER_FILE = "Mini Inverter-F_Cu.gbr"

current_x = 0
current_y = 0

tracks = []
pads = []

with open(GERBER_FILE, "r", errors="ignore") as f:
    lines = f.readlines()

for line in lines:
    line = line.strip()

    # Flash pad
    if line.endswith("D03*"):
        m = re.search(r"X(-?\d+)Y(-?\d+)D03\*", line)
        if m:
            x = int(m.group(1))
            y = int(m.group(2))
            pads.append((x, y))

    # Draw line
    elif line.endswith("D01*"):
        m = re.search(r"X(-?\d+)Y(-?\d+)D01\*", line)
        if m:
            x = int(m.group(1))
            y = int(m.group(2))

            tracks.append(
                ((current_x, current_y),
                 (x, y))
            )

            current_x = x
            current_y = y

    # Move without drawing
    elif line.endswith("D02*"):
        m = re.search(r"X(-?\d+)Y(-?\d+)D02\*", line)
        if m:
            current_x = int(m.group(1))
            current_y = int(m.group(2))

print(f"Tracks: {len(tracks)}")
print(f"Pads:   {len(pads)}")

for t in tracks[:10]:
    print("TRACK:", t)

for p in pads[:10]:
    print("PAD:", p)