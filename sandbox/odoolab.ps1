<#
  Control del sandbox DESDE FUERA. Delega en el contenedor de control,
  asi la logica es identica dentro y fuera.
    .\odoolab.ps1 up
    .\odoolab.ps1 status
    .\odoolab.ps1 run scenarios/sample.yaml
    .\odoolab.ps1 run --name t1 --version-inicio 16.0 --version-fin 18.0 --modulos sale_management,stock
    .\odoolab.ps1 down
#>
param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "creado .env desde .env.example" }

$cmd = if ($Args.Count) { $Args[0] } else { "status" }
$rest = if ($Args.Count -gt 1) { $Args[1..($Args.Count-1)] } else { @() }

switch ($cmd) {
  "up" {
    docker compose up -d --build
    docker exec sbx-control sh -lc "true"   # fuerza entrypoint/alias
  }
  "down"    { docker compose down }
  "nuke"    { docker compose down -v; docker rm -f $(docker ps -aq --filter label=odolab.role=fork) 2>$null }
  "shell"   { docker exec -it sbx-control bash }
  "logs"    { docker compose logs -f @rest }
  default   { docker exec -e ODOLAB_HOST_ROOT=$PSScriptRoot sbx-control python -m odoolab.cli $cmd @rest }
}
