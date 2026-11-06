# Installs the official Spec Kit CLI into this repository's ignored tool directory.
# Does not initialize a project, edit application dependencies, or change global PATH.
$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$python = Join-Path $root '.tools/spec-kit-venv/Scripts/python.exe'
$specify = Join-Path $root '.tools/spec-kit-venv/Scripts/specify.exe'
$source = 'git+https://github.com/github/spec-kit.git@91261fdcf1738cb095a31ff5bee145f502e3af91'
if (-not (Test-Path -LiteralPath $python)) {
    & python -m venv (Join-Path $root '.tools/spec-kit-venv')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
if (-not (Test-Path -LiteralPath $specify)) {
    & $python -m pip install "specify-cli @ $source"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& $python -c "from importlib.metadata import version; v=version('specify-cli'); print('Spec Kit '+v); assert v == '1.3.0', 'Expected pinned Spec Kit 1.3.0; review before upgrading'"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $specify version
exit $LASTEXITCODE
