Write-Host "Building Python Backend..."
.\build_backend.ps1

Write-Host "Installing NPM dependencies..."
npm install

Write-Host "Building Electron Application..."
npm run dist

Write-Host "Build Complete!"
