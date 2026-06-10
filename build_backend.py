import os
import subprocess

def main():
    separator = ";" if os.name == "nt" else ":"
    cmd = [
        "poetry", "run", "pyinstaller",
        "--name", "pcb-preview-server",
        "--add-data", f"templates{separator}templates",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.protocols.http.h11_impl",
        "--hidden-import", "uvicorn.protocols.websockets.websockets_impl",
        "--hidden-import", "uvicorn.loops.asyncio",
        "--hidden-import", "jinja2.ext",
        "--collect-all", "gerbonara",
        "--noconfirm",
        "parser/gerber_preview.py"
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()
