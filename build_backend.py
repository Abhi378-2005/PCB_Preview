import os
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

def remove_generated_dir(path: Path):
    target = path.resolve()
    if PROJECT_ROOT not in [target, *target.parents]:
        raise ValueError(f"Refusing to remove path outside project: {target}")

    if not target.exists():
        return

    def handle_remove_error(function, failed_path, excinfo):
        os.chmod(failed_path, 0o700)
        function(failed_path)

    shutil.rmtree(target, onerror=handle_remove_error)

def main():
    separator = ";" if os.name == "nt" else ":"
    spec_dir = ".pyinstaller-spec"
    os.makedirs(spec_dir, exist_ok=True)
    templates_dir = PROJECT_ROOT / "templates"
    entrypoint = PROJECT_ROOT / "parser" / "gerber_preview.py"

    remove_generated_dir(PROJECT_ROOT / "backend-dist" / "pcb-preview-server")
    remove_generated_dir(PROJECT_ROOT / ".pyinstaller-build" / "pcb-preview-server")

    cmd = [
        "poetry", "run", "pyinstaller",
        "--name", "pcb-preview-server",
        "--specpath", spec_dir,
        "--distpath", str(PROJECT_ROOT / "backend-dist"),
        "--workpath", str(PROJECT_ROOT / ".pyinstaller-build"),
        "--paths", str(PROJECT_ROOT),
        "--add-data", f"{templates_dir}{separator}templates",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.protocols.http.h11_impl",
        "--hidden-import", "uvicorn.protocols.websockets.websockets_impl",
        "--hidden-import", "uvicorn.loops.asyncio",
        "--hidden-import", "jinja2.ext",
        "--hidden-import", "parser.parse_gerber",
        "--hidden-import", "parser.toolpath_generator",
        "--hidden-import", "parser.gcode_generator",
        "--collect-all", "gerbonara",
        "--noconfirm",
        str(entrypoint)
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()
