const { app, BrowserWindow, dialog } = require('electron')
const { spawn } = require('child_process')
const fs = require('fs')
const path = require('path')
const net = require('net')

let mainWindow
let pyProc = null

const createPyProc = async () => {
  let port = await getFreePort()
  
  // Try to find the executable. When packaged, it is in process.resourcesPath.
  // In development, it is in dist/pcb-preview-server.
  let exeName = process.platform === 'win32' ? 'pcb-preview-server.exe' : 'pcb-preview-server';
  let script = path.join(process.resourcesPath, 'pcb-preview-server', exeName)
  let isPackaged = fs.existsSync(script)

  if (!isPackaged) {
    script = path.join(__dirname, 'backend-dist', 'pcb-preview-server', exeName)
  }

  if (!fs.existsSync(script)) {
    script = path.join(__dirname, 'dist', 'pcb-preview-server', exeName)
  }

  if (!fs.existsSync(script)) {
    dialog.showErrorBox(
      'Backend not found',
      `The bundled PCB preview server could not be found at:\n${script}`
    )
    app.quit()
    return
  }

  if (process.platform !== 'win32') {
    try {
      fs.chmodSync(script, 0o755)
    } catch (err) {
      console.warn(`Could not update backend executable permissions: ${err.message}`)
    }
  }

  console.log(`Starting Python server at ${script} on port ${port}`)
  pyProc = spawn(script, ['--port', port, '--no-browser'])

  pyProc.on('error', (err) => {
    dialog.showErrorBox(
      'Backend failed to start',
      `The PCB preview server could not be started.\n\n${err.message}`
    )
    app.quit()
  })

  pyProc.stdout.on('data', (data) => {
    console.log(`stdout: ${data}`);
  });

  pyProc.stderr.on('data', (data) => {
    console.error(`stderr: ${data}`);
  });

  if (pyProc != null) {
    console.log('Python server process spawned')
    
    // Give it a moment to start up
    setTimeout(() => {
      createWindow(port)
    }, 2000)
  }
}

const exitPyProc = () => {
  if (pyProc) {
    pyProc.kill()
    pyProc = null
  }
}

const getFreePort = () => {
  return new Promise(res => {
    const srv = net.createServer(function(sock) {
      sock.end('Hello world\n');
    });
    srv.listen(0, function() {
      let port = srv.address().port;
      srv.close();
      res(port);
    });
  });
}

const createWindow = (port) => {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  })

  mainWindow.loadURL(`http://localhost:${port}`)

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

app.whenReady().then(createPyProc)

app.on('will-quit', exitPyProc)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
