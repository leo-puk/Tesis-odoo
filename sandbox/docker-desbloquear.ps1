<#
  Arranca Docker Desktop cuando se queda en "Stopped" por sockets viejos.

  Sintoma (log de Docker: %LOCALAPPDATA%\Docker\log\host\com.docker.backend.exe.log):
    backend crashed ... listening on unix://...\Docker\run\dockerInference:
    remove ...: El sistema no tiene acceso al archivo.
  (o lo mismo con ...\docker-secrets-engine\engine.sock)

  Cada arranque deja sockets AF_UNIX que el siguiente no puede borrar. No se
  pueden eliminar, pero si apartar: se renombran sus carpetas y Docker crea otras.
    .\docker-desbloquear.ps1
#>
$ErrorActionPreference = "Stop"
Get-Process | Where-Object { $_.ProcessName -match '^(Docker Desktop|com\.docker\..*|docker-ai)$' } |
  Stop-Process -Force -Confirm:$false -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
foreach ($d in @("$env:LOCALAPPDATA\Docker\run", "$env:LOCALAPPDATA\docker-secrets-engine")) {
  if (Test-Path $d) {
    Rename-Item $d ("{0}.stale-{1}" -f (Split-Path $d -Leaf), $ts)
    Write-Host "apartado $d"
  }
}
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
Write-Host "Docker Desktop lanzado; el motor tarda ~30 s en responder (docker version)."
