const fs = require('fs')
const path = require('path')
const { execFileSync } = require('child_process')

exports.default = async function afterPack(context) {
  if (context.electronPlatformName === 'win32') {
    return
  }

  const resourcesDir = context.electronPlatformName === 'darwin'
    ? path.join(
        context.appOutDir,
        context.packager.appInfo.productFilename + '.app',
        'Contents',
        'Resources'
      )
    : path.join(context.appOutDir, 'resources')

  const executable = path.join(resourcesDir, 'pcb-preview-server', 'pcb-preview-server')

  if (fs.existsSync(executable)) {
    fs.chmodSync(executable, 0o755)
  }

  if (context.electronPlatformName === 'darwin') {
    const appPath = path.join(
      context.appOutDir,
      context.packager.appInfo.productFilename + '.app'
    )

    try {
      execFileSync('codesign', ['--force', '--deep', '--sign', '-', appPath], {
        stdio: 'inherit'
      })
    } catch (err) {
      console.warn(`Ad-hoc codesign failed: ${err.message}`)
    }
  }
}
