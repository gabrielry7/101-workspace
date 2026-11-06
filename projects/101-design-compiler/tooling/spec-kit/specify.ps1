# Project-local launcher. Run setup.ps1 on a new machine first.
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$specify = Join-Path $root '.tools/spec-kit-venv/Scripts/specify.exe'
if (-not (Test-Path -LiteralPath $specify)) {
    Write-Error 'Spec Kit is not installed locally. Run: powershell -NoProfile -ExecutionPolicy Bypass -File tooling/spec-kit/setup.ps1'
    exit 1
}
& $specify @args
exit $LASTEXITCODE
