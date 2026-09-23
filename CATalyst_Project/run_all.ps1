$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path "$Root\.venv\Scripts\python.exe")) {
    py -3 -m venv "$Root\.venv"
}

& "$Root\.venv\Scripts\python.exe" -m pip install -q -r "$Root\requirements-dev.txt"

if (-not (Test-Path "$Root\frontend\node_modules")) {
    Push-Location "$Root\frontend"
    npm install
    Pop-Location
}

Start-Process powershell -ArgumentList '-NoExit','-Command',"Set-Location '$Root'; & '$Root\.venv\Scripts\python.exe' -m uvicorn backend.module1_data_simulation.app:app --port 8001"
Start-Process powershell -ArgumentList '-NoExit','-Command',"Set-Location '$Root'; & '$Root\.venv\Scripts\python.exe' -m uvicorn backend.module2_intelligence.app.main:app --port 8002"
Start-Process powershell -ArgumentList '-NoExit','-Command',"Set-Location '$Root'; & '$Root\.venv\Scripts\python.exe' -m uvicorn backend.module3_orchestrator.app:app --port 8003"
Start-Process powershell -ArgumentList '-NoExit','-Command',"Set-Location '$Root\frontend'; npm run dev"

Write-Host ''
Write-Host 'CATalyst is starting...' -ForegroundColor Yellow
Write-Host 'Module 1: http://127.0.0.1:8001/docs'
Write-Host 'Module 2: http://127.0.0.1:8002/docs'
Write-Host 'Module 3: http://127.0.0.1:8003/docs'
Write-Host 'Frontend: http://127.0.0.1:5173'
Write-Host ''
