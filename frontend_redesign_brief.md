# PCB Preview — Frontend Redesign Brief

> **Purpose of this document:** Give this file to a powerful AI model (e.g. Claude, GPT-4, Gemini) and ask it to produce a detailed design document / theme specification for redesigning the frontend of this project. Everything the model needs to know is below.

---

## 1. What This Project Is

A **web-based Laser PCB Plotter & Control Interface** built as a single-page application. It lets users:
1. Upload Gerber PCB files (`.gbr`)
2. Preview them as layered SVG images on a canvas
3. Generate G-code toolpaths for laser engraving
4. Control a CNC machine (Arduino/GRBL over USB, or ESP32 over WiFi) directly from the browser — jogging, homing, laser firing, and streaming G-code with a live-synced preview

The entire frontend lives in a **single Jinja2 template file**: `templates/preview.html` (~3,800 lines). There is no framework (React/Vue/etc.) — it's vanilla HTML + CSS + JavaScript.

---

## 2. Current Technology Stack

| Layer | Tech |
|:--|:--|
| Template engine | Jinja2 (served by FastAPI) |
| CSS | Vanilla CSS, all in a `<style>` block (~1,570 lines) |
| JavaScript | Vanilla JS in a `<script>` block (~2,100 lines) |
| Font | JetBrains Mono (Google Fonts) |
| Icons | Unicode/Emoji characters (no icon library) |
| Backend data | Jinja2 `{{ }}` variables injected server-side |

---

## 3. Current Design System (CSS Custom Properties)

```css
:root {
  --bg: #0d0f14;           /* Page background — near-black */
  --surface: #161a22;      /* Card/panel backgrounds */
  --border: #2a2f3d;       /* Borders and dividers */
  --accent: #00d4ff;       /* Primary accent — electric cyan */
  --green: #00ff88;        /* Success / "active" / laser-on */
  --text: #e2e8f0;         /* Primary text */
  --muted: #64748b;        /* Secondary/dim text */
  --dim-color: #ff6b35;    /* Dimension annotation color */
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
}
```

**Current aesthetic:** Dark theme, monospace "terminal/hacker" feel. Glassmorphism-light with `rgba()` backgrounds. Subtle grid pattern on the preview viewport. Cyan accent color throughout.

---

## 4. Page Layout Architecture

The page uses a **3-column CSS Grid layout**:

```
┌──────────────────────────────────────────────────┐
│  HEADER: Logo + Title + GRBL Params Button       │
├──────────┬──────────────────────┬────────────────┤
│ LEFT     │  CENTER              │ RIGHT          │
│ SIDEBAR  │  PREVIEW PANEL       │ SIDEBAR        │
│ (280px)  │  (1fr — flexible)    │ (280px)        │
│          │                      │                │
│ • Upload │  • SVG Layer Stack   │ • Machine      │
│ • Layers │  • Canvas Overlay    │   Controls     │
│ • G-code │  • Head Pointer      │ • Connection   │
│   Gen    │  • Dimension Labels  │ • D-pad Jog    │
│ • Scale  │  • Zoom/Pan          │ • Laser        │
│ • Orient │                      │ • Stream       │
│          │  CONTROL PANEL       │ • E-Stop       │
│          │  (below preview)     │ • Position     │
│          │  • D-pad  • Play/    │                │
│          │  • Pos     Pause/    │                │
│          │             Stop     │                │
├──────────┴──────────────────────┴────────────────┤
│  (GRBL Parameters Modal — overlay, hidden)       │
│  (Confirmation Modal — overlay, hidden)          │
└──────────────────────────────────────────────────┘
```

---

## 5. UI Components Inventory

### 5.1 Header
- Logo (36×36px gradient square with icon)
- Title "PCB Layer Preview" + subtitle
- Pulsing green status dot
- "⚙ GRBL Parameters" button (opens modal)

### 5.2 Left Sidebar — "Layers" Panel
- **Upload Zone** — drag-and-drop area for `.gbr` files
- **Layer List** — toggleable items with color-coded badges (Cu=red, Mask=purple, Paste=blue, Silk=yellow)
- **Select All / Deselect All** buttons
- **Clear All** (danger button)
- **G-code Generation Section:**
  - Scale selector (1x–10x dropdown)
  - Mode selector (Trace/Fill dropdown)
  - Orientation selector
  - Line spacing, laser diameter inputs
  - Burn speed, rapid speed, laser power inputs
  - "Generate G-code" button
  - "Download .gcode" button
  - G-code stats display (line count, bounds, est. time)

### 5.3 Center — Preview Panel
- **Toolbar:** Zoom controls (−, reset, +), zoom percentage display
- **Viewport:** 
  - Background with subtle cyan grid pattern (CSS `::before`)
  - **Layer Stack** — absolutely positioned SVG `<img>` elements (toggled visible/hidden)
  - **Dimension annotations** — width/height labels with measurement lines
  - **Trail Canvas** — `<canvas>` element for drawing the laser burn path
  - **Head Pointer** — CSS crosshair dot that tracks machine position
  - Pan (mouse drag) and zoom (scroll wheel) interactions

### 5.4 Center — Control Panel (below preview)
- **D-pad** — 3×3 grid of directional buttons (▲▼◀▶ + Home center)
- **Step Size Selector** — dropdown for jog distance
- **Position Readout** — X/Y coordinates in mm
- **Mode Badge** — "JOG" (cyan) or "RUN" (green)
- **Run Controls** — Play/Pause/Stop buttons
- **Progress Bar** — for simulated preview run

### 5.5 Right Sidebar — "Machine Control" Panel
- **Connection Mode Toggle** — USB / WiFi dropdown
- **USB Section:**
  - Port selector dropdown + refresh button
  - Connect button (toggles to "✓ Online")
  - Status indicator (red/green dot + text)
- **WiFi Section (ESP32):**
  - IP address input
  - Connect button
- **D-pad** — compact 3×3 jog grid with ▲▼◀▶ + ⌂ Home
- **Step Selector** — dropdown (0.0125mm to 1.25mm)
- **Position Display** — X/Y machine coordinates
- **Laser Control:**
  - Power slider (0–1000)
  - "FIRE" toggle button
- **Stream G-code** button
- **Emergency Stop** button (red, hidden until streaming)
- **Stream progress bar** + status text

### 5.6 Modals (Overlay Dialogs)
- **Confirmation Modal** — icon + title + message + Cancel/Confirm buttons
- **GRBL Parameters Modal** — full table of all 30+ GRBL `$` parameters, editable inputs, save button, with modified-value highlighting

---

## 6. Key CSS Patterns Used

| Pattern | Where |
|:--|:--|
| `rgba()` translucent backgrounds | All buttons, cards, hover states |
| `border: 1px solid var(--border)` | Every panel and input |
| `border-radius: 6–12px` | Cards, buttons, inputs |
| `transition: all 0.15s` | All interactive elements |
| `transform: scale(0.9)` on `:active` | D-pad buttons press effect |
| `box-shadow: 0 0 Xpx` | Glowing effects on active states |
| CSS Grid | Main layout, D-pads, control panel |
| `position: absolute` layering | Preview viewport (SVGs, canvas, pointer) |
| `backdrop-filter: blur(6px)` | Modal overlay |
| `@keyframes pulse` | Status dot animation |
| `@keyframes spin` | Loading spinner |

---

## 7. Jinja2 Template Variables (Server-Injected Data)

These are injected by the Python backend and **must be preserved** in any redesign:

```python
# In the HTML template, accessed as {{ variable }}:
files           # list of uploaded gerber filenames
board           # object with min_x, min_y, width_mm, height_mm  
toolpath_offset # object with x, y (copper origin offset)
```

Example usage in HTML:
```html
{% for file in files %}
  <div class="layer-item" data-layer-type="{{ file.layer_type }}">
    {{ file.name }}
  </div>
{% endfor %}
```

Example usage in JS:
```javascript
const MAP = {
  board_min_x: {{ board.min_x | tojson }},
  board_w: {{ board.width_mm | tojson }},
  offset_x: {{ toolpath_offset.x | tojson }},
};
```

---

## 8. JavaScript API Endpoints (Must Not Break)

The frontend talks to these FastAPI endpoints:

| Method | Endpoint | Purpose |
|:--|:--|:--|
| POST | `/upload` | Upload `.gbr` files |
| DELETE | `/clear` | Clear all gerber files |
| GET | `/render/{filename}` | Get rendered SVG for a layer |
| GET | `/toolpath` | Get toolpath data for preview |
| POST | `/convert` | Generate G-code |
| GET | `/download-gcode` | Download `.gcode` file |
| GET | `/api/serial/ports` | List USB serial ports |
| POST | `/api/serial/connect` | Connect to Arduino |
| POST | `/api/serial/disconnect` | Disconnect |
| POST | `/api/serial/send` | Send G-code command |
| POST | `/api/serial/stream` | Start streaming G-code |
| GET | `/api/serial/stream-events` | SSE endpoint for live preview sync |
| GET | `/api/serial/status` | Poll connection/streaming status |
| GET | `/api/serial/position` | Get GRBL MPos (X,Y,Z) |
| POST | `/api/serial/stop` | Emergency stop |
| GET | `/api/grbl/params` | Read GRBL $$ parameters |
| POST | `/api/grbl/set-params` | Write GRBL parameters |

---

## 9. Critical JavaScript Functions (Must Be Preserved)

These functions contain core business logic that must survive any redesign:

| Function | Purpose |
|:--|:--|
| `bedToPixel(bx, by)` | Convert bed mm → pixel coords on canvas |
| `gcodeToBed(gx, gy)` | Convert G-code coords → bed coords |
| `moveHead(x, y, isDrawing)` | Move crosshair pointer + draw trail |
| `initTrailCanvas()` | Initialize HiDPI canvas for burn trail |
| `machineJog(axis, dir)` | Jog with soft-limit checks |
| `machineHome()` | Send $H (USB) or G28 (ESP32) |
| `machineStreamGCode()` | Start stream + subscribe to SSE for live sync |
| `machineEmergencyStop()` | Send stop + close SSE |
| `usbConnect()` | Connect to serial port |
| `usbPollStatus()` | Poll position + status every 1.5s |
| `runGCode()` / `executeNextCommand()` | Simulated preview animation |
| `updateActiveCount()` | Count selected copper layers |

---

## 10. What I Want From the Design Model

Ask the model to produce a **detailed design document** that includes:

1. **A new color palette and design tokens** (CSS custom properties) — suggest 2–3 theme options (e.g. "Midnight Blue", "Warm Dark", "Light Mode")
2. **Typography recommendation** — font pairing, sizes, weights
3. **Component-by-component redesign specs** — for each of the components listed in Section 5, provide:
   - New colors, spacing, border-radius
   - Hover/active/disabled states
   - Any new micro-animations
4. **Layout improvements** — should it stay 3-column? Mobile responsiveness?
5. **Icon system recommendation** — replace emoji icons with a proper icon library?
6. **Visual hierarchy improvements** — what should be more prominent vs. de-emphasized?
7. **Specific CSS code** for the new `:root` variables and key component styles
8. **Mockup descriptions** or ASCII wireframes of the new layout

> **Constraint:** The redesign must be CSS-only (plus maybe a new icon library CDN). The HTML structure and all JavaScript functions listed in Sections 8 and 9 must remain unchanged. The Jinja2 template syntax must be preserved.

---

## 11. Reference: What the Current UI Looks Like

The current UI has:
- **Dark background** (#0d0f14) — almost black
- **Cyan/electric blue accent** (#00d4ff) — used everywhere
- **Neon green** (#00ff88) — for success/active states
- **Red** (#ff4444) — for danger/errors
- **Monospace everything** — JetBrains Mono, even for labels
- **Minimal gradients** — only on logo and primary CTA buttons
- **Subtle grid pattern** on the preview canvas background
- **No shadows** except on glowing active states
- **Terminal-like aesthetic** — uppercase labels, letter-spacing, compact

The feel is "developer tool / IDE" which is functional but can be elevated to feel more polished and professional.
