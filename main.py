# main.py
import webbrowser
import threading
import uvicorn
from parser.gerber_preview import app

def open_browser():
    webbrowser.open("http://localhost:5050")

if __name__ == "__main__":
    # Wait 1.5 seconds for the server to spin up, then open browser
    threading.Timer(1.5, open_browser).start()
    
    # Run the server on localhost
    uvicorn.run(app, host="127.0.0.1", port=5050)
