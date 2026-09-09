# main.py
import webbrowser
import threading
import uvicorn
from parser.gerber_preview import app

# Custom log config that avoids uvicorn's ColourizedFormatter, which crashes
# in frozen (PyInstaller) builds because stdout/stderr lack an `isatty` attribute.
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(levelname)s:     %(message)s",
        },
        "access": {
            "format": "%(asctime)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"level": "INFO"},
        "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
    },
}

def open_browser():
    webbrowser.open("http://localhost:5050")

if __name__ == "__main__":
    # Wait 1.5 seconds for the server to spin up, then open browser
    threading.Timer(1.5, open_browser).start()

    # Run the server on localhost with the frozen-safe log config
    uvicorn.run(app, host="127.0.0.1", port=5050, log_config=LOG_CONFIG)
