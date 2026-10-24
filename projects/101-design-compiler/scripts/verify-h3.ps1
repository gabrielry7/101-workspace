$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$portableNode = Join-Path $PWD '.tools/node-v24.21.0-win-x64'
if (Test-Path (Join-Path $portableNode 'node.exe')) { $env:PATH = "$portableNode;$env:PATH" }
$env:ASTRO_TELEMETRY_DISABLED = '1'
$utf8 = New-Object System.Text.UTF8Encoding($false)
$h2Commit = 'd3c8be9649a6f323ea47fb48ad64af9521cc39e6'
$steps = @(
  @{ Name = 'contracts-export'; Args = @('run', 'contracts:export') },
  @{ Name = 'media-fixtures'; Args = @('run', 'media:fixtures') },
  @{ Name = 'media-replay'; Args = @('run', 'media:replay') },
  @{ Name = 'tests'; Args = @('test') },
  @{ Name = 'check'; Args = @('run', 'check') },
  @{ Name = 'validate'; Args = @('run', 'validate') },
  @{ Name = 'build'; Args = @('run', 'build') },
  @{ Name = 'pilot-verify'; Args = @('run', 'media:verify') }
)
New-Item -ItemType Directory -Force docs/evidence | Out-Null
foreach ($step in $steps) {
  $output = & npm.cmd @($step.Args) 2>&1
  $code = $LASTEXITCODE
  $body = ($output | ForEach-Object { ([string]$_ -replace '\x1B\[[0-9;]*[A-Za-z]', '').TrimEnd() }) -join "`n"
  [IO.File]::WriteAllText((Join-Path $PWD "docs/evidence/h3-$($step.Name).txt"), $body.TrimEnd() + "`n", $utf8)
  Write-Output "$($step.Name): exit $code"
  if ($code -ne 0) { Write-Output $body; exit $code }
}
& git -c safe.directory=C:/Users/gabri/101-design-compiler diff --check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$protected = @('src/contracts/v1', 'src/planner', 'src/taxonomy', 'src/upstream', 'src/validation', 'contracts/v1', 'contracts/planner', 'contracts/taxonomy', 'contracts/upstream', 'fixtures/v1', 'fixtures/planner', 'data/derived/planner-v1', 'data/derived/taxonomy-v1', 'data/reference', 'taxonomy', 'package-lock.json', 'docs/101_business_website_compiler_pipeline_v0_2.md')
$changed = & git -c safe.directory=C:/Users/gabri/101-design-compiler diff --name-only $h2Commit -- @protected
if ($LASTEXITCODE -ne 0 -or $changed) { throw "Protected H0-H2 files changed: $changed" }
$hashes = @(Get-ChildItem -LiteralPath data/derived/media-v1 -Filter '*.json' | Sort-Object Name | ForEach-Object {
  @{ file = "data/derived/media-v1/$($_.Name)"; sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower() }
})
$receipt = @{
  h2_commit = $h2Commit
  node = (& node --version).Trim(); npm = (& npm.cmd --version).Trim()
  evaluation_time = '2026-10-08T00:00:00Z'; legal_review_date = '2026-10-08'
  protected_h0_h1_h2_unchanged = $true; package_lock_unchanged = $true
  authorized_media_package = 'AUTHORIZED_PILOT_PACKAGE_WITH_GAPS'; media_files = $hashes
}
[IO.File]::WriteAllText((Join-Path $PWD 'docs/evidence/h3-verification.json'), (($receipt | ConvertTo-Json -Depth 8) -replace "`r`n", "`n") + "`n", $utf8)
Write-Output 'Protected H0-H2 artifacts unchanged; real authorized pilot package verified; documentary gap retained.'
