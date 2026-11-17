param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
$ErrorActionPreference = 'Stop'
$r2Root = $PSScriptRoot
$r2Python = $env:R2_PYTHON
if (-not $r2Python) {
    $r2VirtualPython = Join-Path $r2Root '.venv\Scripts\python.exe'
    $r2LocalConfig = Join-Path $r2Root 'runtime.local.json'
    if (Test-Path -LiteralPath $r2VirtualPython) {
        $r2Python = $r2VirtualPython
    } elseif (Test-Path -LiteralPath $r2LocalConfig) {
        $r2Python = (Get-Content -LiteralPath $r2LocalConfig -Raw | ConvertFrom-Json).python
    }
}
if (-not $r2Python -or -not (Test-Path -LiteralPath $r2Python)) {
    throw 'Set R2_PYTHON to a Python 3.12+ executable with lxml installed, or install into .venv.'
}
Push-Location -LiteralPath $r2Root
try {
    & $r2Python -m r2 @Arguments
    $r2Exit = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $r2Exit
