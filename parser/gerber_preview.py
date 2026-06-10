#!/usr/bin/env python3
"""
gerber_preview.py — Multi-layer Gerber PCB Preview Server (v3)

Uses gerbonara for rendering (replaces pygerber).
- Accurate copper fill / thermal relief rendering
- SVG output (vector, scales perfectly, no bitmap artifacts)
- Unified bounding box via force_bounds (all layers pixel-aligned)
- No Cairo/cairosvg dependency needed

Usage:
    cd Test/
    uvicorn parser.gerber_preview:app --reload --port 5050
"""

from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, Response, FileResponse
from fastapi.templating import Jinja2Templates
from gerbonara import GerberFile
import json as _json

# ── Paths ──────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent.parent   # Test/
GERBER_DIR   = BASE_DIR / "gerbers"
TEMPLATE_DIR = BASE_DIR / "templates"
OUTPUT_DIR   = BASE_DIR / "output"

# ── Layer colors (fg = feature color, bg = background) ─────────────
# All layers use bg='none' (transparent) so they overlay cleanly
LAYER_COLORS = {
    "Cu":          {"fg": "#1a1a1a",    "bg": "none"},    # dark traces
    "Mask":        {"fg": "#2d8c3c88",  "bg": "none"},    # semi-transparent green
    "Paste":       {"fg": "#99999966",  "bg": "none"},    # semi-transparent grey
    "Silkscreen":  {"fg": "#e0e0e0",    "bg": "none"},    # white text
}

# Board background color (shown behind all layers)
BOARD_BG_COLOR = "#88c563"


def detect_layer_type(filename: str) -> str:
    """Detect the Gerber layer type from the filename (fallback method)."""
    name = filename.lower()
    if "cu" in name:
        return "Cu"
    elif "mask" in name:
        return "Mask"
    elif "paste" in name:
        return "Paste"
    elif "silk" in name:
        return "Silkscreen"
    return "Unknown"


def detect_layer_type_by_content(filepath: str) -> str:
    """
    Detect the Gerber layer type by reading the file's X2 attributes.
    Uses %TF.FileFunction header (Gerber X2 standard), falls back to filename.

    Returns: 'Cu', 'Mask', 'Paste', 'Silkscreen', or 'Unknown'
    """
    try:
        gf = GerberFile.open(filepath)
        file_attrs = getattr(gf, 'file_attrs', {})
        file_func = file_attrs.get('.FileFunction', ())

        if file_func:
            func_name = file_func[0].lower()
            if func_name == 'copper':
                return 'Cu'
            elif func_name == 'soldermask':
                return 'Mask'
            elif func_name == 'paste':
                return 'Paste'
            elif func_name in ('legend', 'silkscreen'):
                return 'Silkscreen'
            elif func_name == 'profile':
                return 'EdgeCuts'
    except Exception:
        pass

    # Fallback: detect by filename
    return detect_layer_type(Path(filepath).name)


def find_copper_layer() -> str | None:
    """
    Scan gerbers/ directory and find the copper layer file.
    Uses content-based detection first, filename fallback second.
    Returns the filename of the copper layer, or None.
    """
    if not GERBER_DIR.exists():
        return None

    for gbr in sorted(GERBER_DIR.glob("*.gbr")):
        layer_type = detect_layer_type_by_content(str(gbr))
        if layer_type == 'Cu':
            return gbr.name

    return None


def get_layer_bounds(filepath: str):
    """Get bounding box using gerbonara. Returns (min_x, min_y, max_x, max_y) or None."""
    try:
        gf = GerberFile.open(filepath)
        bb = gf.bounding_box()
        if bb is None or bb == (None, None):
            return None
        min_x, min_y = float(bb[0][0]), float(bb[0][1])
        max_x, max_y = float(bb[1][0]), float(bb[1][1])
        return (min_x, min_y, max_x, max_y)
    except Exception:
        return None


def compute_union_bounds():
    """Compute union bounding box across all .gbr layers."""
    layer_bounds = {}
    for gbr in sorted(GERBER_DIR.glob("*.gbr")):
        bounds = get_layer_bounds(str(gbr))
        if bounds:
            layer_bounds[gbr.name] = bounds

    if not layer_bounds:
        return None, {}

    union = (
        min(b[0] for b in layer_bounds.values()),
        min(b[1] for b in layer_bounds.values()),
        max(b[2] for b in layer_bounds.values()),
        max(b[3] for b in layer_bounds.values()),
    )
    return union, layer_bounds


# ── App ────────────────────────────────────────────────────────────
app = FastAPI(
    title="Antigravity PCB Preview",
    description="Multi-layer Gerber preview (gerbonara SVG rendering)",
    version="0.4.0",
)

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# ── Caches ─────────────────────────────────────────────────────────
_render_cache: dict[str, str] = {}    # filename -> SVG string
_union_bounds = None
_layer_bounds: dict[str, tuple] = {}
_board_dims = None


def _reset_caches():
    """Clear all caches — call after uploading/deleting files."""
    global _union_bounds, _layer_bounds, _board_dims, _render_cache
    _render_cache = {}
    _union_bounds = None
    _layer_bounds = {}
    _board_dims = None


def _ensure_bounds():
    """Lazily compute union bounds on first request."""
    global _union_bounds, _layer_bounds, _board_dims
    if _union_bounds is None:
        _union_bounds, _layer_bounds = compute_union_bounds()
        if _union_bounds:
            w = _union_bounds[2] - _union_bounds[0]
            h = _union_bounds[3] - _union_bounds[1]
            _board_dims = {
                "width_mm": round(w, 2),
                "height_mm": round(h, 2),
                "min_x": round(_union_bounds[0], 4),
                "min_y": round(_union_bounds[1], 4),
                "max_x": round(_union_bounds[2], 4),
                "max_y": round(_union_bounds[3], 4),
            }


# ── Routes ─────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main preview page."""
    if not GERBER_DIR.exists():
        raise HTTPException(status_code=404, detail="gerbers/ folder not found")

    _ensure_bounds()

    files = sorted([f.name for f in GERBER_DIR.iterdir() if f.suffix == ".gbr"])
    renderable = [f for f in files if f in _layer_bounds]

    # Detect copper layer by content
    copper_file = find_copper_layer()

    # Load toolpath mapping data if available
    toolpath_offset = None
    toolpath_path = OUTPUT_DIR / "toolpath.json"
    if toolpath_path.exists():
        try:
            with open(toolpath_path) as f:
                tp_data = _json.load(f)
            toolpath_offset = tp_data.get("offset_applied", {})
        except Exception:
            pass

    return templates.TemplateResponse(
        request,
        "preview.html",
        {
            "files": renderable,
            "board": _board_dims or {},
            "board_bg": BOARD_BG_COLOR,
            "copper_file": copper_file,
            "toolpath_offset": toolpath_offset,
        },
    )


@app.get("/render/{filename}")
async def render_layer(filename: str):
    """
    Render a .gbr file to SVG using gerbonara.
    All layers share the same viewBox via force_bounds.
    Returns image/svg+xml.
    """
    if "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    filepath = GERBER_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"{filename} not found")
    if filepath.suffix != ".gbr":
        raise HTTPException(status_code=400, detail="Only .gbr files")

    # Check cache
    if filename in _render_cache:
        return Response(content=_render_cache[filename], media_type="image/svg+xml")

    _ensure_bounds()

    if filename not in _layer_bounds:
        raise HTTPException(status_code=400, detail=f"{filename} has no geometry")

    try:
        # Detect layer type for color
        layer_type = detect_layer_type(filename)
        colors = LAYER_COLORS.get(layer_type, LAYER_COLORS["Cu"])

        # Render with gerbonara, using union bounds for alignment
        gf = GerberFile.open(str(filepath))
        force = (
            (_union_bounds[0], _union_bounds[1]),
            (_union_bounds[2], _union_bounds[3]),
        )
        svg = gf.to_svg(
            fg=colors["fg"],
            bg=colors["bg"],
            force_bounds=force,
        )
        svg_str = str(svg)

        # Cache
        _render_cache[filename] = svg_str

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Render failed: {str(e)}")

    return Response(content=svg_str, media_type="image/svg+xml")


@app.get("/layers")
async def list_layers():
    """JSON list of available layers."""
    _ensure_bounds()

    if not GERBER_DIR.exists():
        raise HTTPException(status_code=404, detail="gerbers/ folder not found")

    files = sorted([f.name for f in GERBER_DIR.iterdir() if f.suffix == ".gbr"])
    layers = []
    for f in files:
        # Use content-based detection
        lt = detect_layer_type_by_content(str(GERBER_DIR / f))
        has_geometry = f in _layer_bounds
        layers.append({"filename": f, "type": lt, "has_geometry": has_geometry})

    return {"layers": layers, "count": len(layers), "board": _board_dims}


@app.get("/board-info")
async def board_info():
    """Returns PCB board dimensions."""
    _ensure_bounds()
    if not _board_dims:
        raise HTTPException(status_code=404, detail="No board data")
    return _board_dims


@app.get("/toolpath")
async def get_toolpath():
    """Return toolpath.json data for animation."""
    toolpath_path = OUTPUT_DIR / "toolpath.json"
    if not toolpath_path.exists():
        raise HTTPException(status_code=404, detail="No toolpath. Run conversion first.")

    with open(toolpath_path) as f:
        return _json.load(f)


@app.post("/upload")
async def upload_gerbers(files: List[UploadFile] = File(...)):
    """
    Upload one or more .gbr files.
    Saves to gerbers/ directory and resets all caches.
    """
    GERBER_DIR.mkdir(parents=True, exist_ok=True)

    uploaded = []
    rejected = []

    for file in files:
        # Only accept .gbr files
        if not file.filename or not file.filename.lower().endswith(".gbr"):
            rejected.append(file.filename or "unknown")
            continue

        # Security: strip path components, keep only the filename
        safe_name = Path(file.filename).name
        if not safe_name or safe_name.startswith("."):
            rejected.append(file.filename)
            continue

        # Read content and save
        content = await file.read()
        dest = GERBER_DIR / safe_name
        dest.write_bytes(content)
        uploaded.append(safe_name)

    # Reset caches so next request recomputes bounds + renders
    _reset_caches()

    return JSONResponse(content={
        "uploaded": uploaded,
        "rejected": rejected,
        "total": len(uploaded),
    })


@app.delete("/clear")
async def clear_gerbers():
    """
    Delete all .gbr files from gerbers/ directory.
    Resets all caches.
    """
    removed = []
    if GERBER_DIR.exists():
        for gbr in GERBER_DIR.glob("*.gbr"):
            gbr.unlink()
            removed.append(gbr.name)

    _reset_caches()

    return JSONResponse(content={
        "removed": removed,
        "total": len(removed),
    })


@app.post("/convert-gcode")
async def convert_gcode():
    """
    Find the copper layer (by content detection), run the full pipeline:
      parse_gerber → toolpath_generator → gcode_generator
    Returns JSON with conversion status and stats.
    """
    # Import pipeline modules
    from parser.parse_gerber import parse_gerber
    from parser.toolpath_generator import generate_toolpath
    from parser.gcode_generator import generate_gcode

    # Find copper layer
    copper_file = find_copper_layer()
    if not copper_file:
        raise HTTPException(
            status_code=400,
            detail="No copper layer (.gbr with FileFunction=Copper) found. "
                   "Upload an F_Cu.gbr file first."
        )

    copper_path = str(GERBER_DIR / copper_file)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    parsed_path = str(OUTPUT_DIR / "parsed_tracks.json")
    toolpath_path = str(OUTPUT_DIR / "toolpath.json")
    gcode_path = str(OUTPUT_DIR / "output.gcode")

    try:
        # Step 1: Parse gerber
        parsed = parse_gerber(copper_path, parsed_path)

        # Step 2: Generate optimized toolpath
        toolpath = generate_toolpath(parsed_path, toolpath_path)

        # Step 3: Generate G-code
        generate_gcode(toolpath_path, gcode_path)

        # Read generated G-code for stats
        with open(gcode_path, 'r') as f:
            gcode_lines = f.readlines()

        return JSONResponse(content={
            "success": True,
            "copper_file": copper_file,
            "detection_method": "content (TF.FileFunction)",
            "stats": {
                "tracks_parsed": parsed["statistics"]["total_tracks"],
                "pads_parsed": parsed["statistics"]["total_pads"],
                "toolpath_commands": toolpath["statistics"]["total_commands"],
                "gcode_lines": len(gcode_lines),
                "rapid_distance_mm": toolpath["statistics"]["total_rapid_distance_mm"],
                "draw_distance_mm": toolpath["statistics"]["total_draw_distance_mm"],
                "work_area": toolpath["work_area"],
            },
            "output_file": "output.gcode",
        })

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"G-code conversion failed: {str(e)}"
        )


@app.get("/download-gcode")
async def download_gcode():
    """
    Download the generated G-code file.
    """
    gcode_path = OUTPUT_DIR / "output.gcode"
    if not gcode_path.exists():
        raise HTTPException(
            status_code=404,
            detail="No G-code file found. Run conversion first."
        )

    return FileResponse(
        path=str(gcode_path),
        filename="output.gcode",
        media_type="text/plain",
    )


def main():
    """Entry point — starts the server and opens the browser."""
    import threading
    import webbrowser
    import uvicorn

    def open_browser():
        webbrowser.open("http://localhost:5050")

    threading.Timer(1.5, open_browser).start()
    uvicorn.run(
        "parser.gerber_preview:app",
        host="127.0.0.1",
        port=5050,
    )


if __name__ == "__main__":
    main()
