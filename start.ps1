$taskRoot = $PSScriptRoot
$backendListener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($backendListener) {
    $backendHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 5 -ErrorAction Stop
    if ($backendHealth.security_pipeline -ne 'architecture-v2') {
        throw 'Port 8000 has an outdated backend. Stop that FastAPI process and run ./start.ps1 again; then sign in again.'
    }
    Write-Host 'Reusing the running Architecture-v2 backend.'
} else {
    Start-Process -FilePath 'python' -ArgumentList '-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000','--reload','--reload-dir',('"' + (Join-Path $taskRoot 'backend') + '"') -WorkingDirectory $taskRoot -WindowStyle Hidden
}
if (-not (Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile','-File',('"' + (Join-Path $taskRoot 'scripts\frontend.ps1') + '"') -WorkingDirectory $taskRoot -WindowStyle Hidden
}
Write-Host 'AI Guard starts at http://127.0.0.1:5173. Servers run in background; stop them in Task Manager when finished.'
