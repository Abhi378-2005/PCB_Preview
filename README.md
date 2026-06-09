# Antigravity PCB Preview

Multi-layer Gerber PCB preview tool with aligned rendering.

## Quick Start

```bash
# Install dependencies
poetry install

# Run the preview server
poetry run pcb-preview
```

Then open `http://localhost:5050` — drag & drop your `.gbr` files to preview.

## Stack

- **FastAPI** + **Uvicorn** — web server
- **Gerbonara** — Gerber parsing & SVG rendering
- **Jinja2** — HTML templating
- **Poetry** — dependency management
