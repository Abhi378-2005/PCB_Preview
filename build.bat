@echo off
echo Building PCB Preview standalone executable...

python -m poetry run pyinstaller ^
    --name PCB_Preview ^
    --onefile ^
    --noconsole ^
    --add-data "templates;templates" ^
    --hidden-import "uvicorn.logging" ^
    --hidden-import "uvicorn.loops" ^
    --hidden-import "uvicorn.loops.auto" ^
    --hidden-import "uvicorn.protocols" ^
    --hidden-import "uvicorn.protocols.http" ^
    --hidden-import "uvicorn.protocols.http.auto" ^
    --hidden-import "uvicorn.protocols.websockets" ^
    --hidden-import "uvicorn.protocols.websockets.auto" ^
    --hidden-import "parser.parse_gerber" ^
    --hidden-import "parser.toolpath_generator" ^
    --hidden-import "parser.raster_generator" ^
    --hidden-import "parser.gcode_generator" ^
    main.py

echo Build complete! The executable is located in the "dist" folder.
pause
