$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$portableNode = Join-Path $PWD '.tools/node-v24.21.0-win-x64'
if (Test-Path (Join-Path $portableNode 'node.exe')) { $env:PATH = "$portableNode;$env:PATH" }
$env:ASTRO_TELEMETRY_DISABLED = '1'
$utf8 = New-Object System.Text.UTF8Encoding($false)
$steps = @(
  @{ Name='bindings'; Args=@('run','composition:bindings') },
  @{ Name='bindings-replay'; Args=@('run','composition:replay') },
  @{ Name='tests'; Args=@('test') },
  @{ Name='check'; Args=@('run','check') },
  @{ Name='validate'; Args=@('run','validate') },
  @{ Name='build'; Args=@('run','build') },
  @{ Name='media-verify'; Args=@('run','media:verify') },
  @{ Name='composition-verify'; Args=@('run','composition:verify') },
  @{ Name='media-replay'; Args=@('run','media:replay') }
)
foreach ($step in $steps) {
  $output = & npm.cmd @($step.Args) 2>&1
  $code = $LASTEXITCODE
  $body = ($output | ForEach-Object { ([string]$_ -replace '\x1B\[[0-9;]*[A-Za-z]', '').TrimEnd() }) -join "`n"
  [IO.File]::WriteAllText((Join-Path $PWD "docs/evidence/h4-$($step.Name).txt"), $body.TrimEnd() + "`n", $utf8)
  Write-Output "$($step.Name): exit $code"
  if ($code -ne 0) { Write-Output $body; exit $code }
}
$base='e2b83d441776bcc7d643ffa2f0c3dee4e648b62d'
$protected=@('src/contracts','src/planner','src/taxonomy','src/upstream','src/validation','src/media','src/layouts','src/pages/h3-media-pilot.astro','scripts/load-media-pilot.ts','scripts/render-h3-pilot.ts','scripts/seal-media-pilot.ts','scripts/verify-media-pilot.ts','contracts','fixtures','data/reference','data/derived/planner-v1','data/derived/taxonomy-v1','data/derived/media-v1','public/media','taxonomy','package-lock.json','docs/evidence/h3*','docs/h3-report.md','docs/h3-providers.md','docs/101_business_website_compiler_pipeline_v0_2.md')
$changed=& git -c safe.directory=C:/Users/gabri/101-design-compiler diff --name-only $base -- @protected
if ($LASTEXITCODE -ne 0 -or $changed) { throw "Protected H0-H3 artifacts changed: $changed" }
& git -c safe.directory=C:/Users/gabri/101-design-compiler diff --check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$paths=@('data/derived/composition-v1/restaurante-bindings.json','docs/evidence/h4/browser-audit.json')
$receipt=@{h3_commit=$base;protected_h0_h3_unchanged=$true;node=(& node --version).Trim();npm=(& npm.cmd --version).Trim();runtime='LOCAL_ASTRO_LAB_ONLY';status='PASSED';files=@($paths|ForEach-Object{@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLowerInvariant()}})}
[IO.File]::WriteAllText((Join-Path $PWD 'docs/evidence/h4-verification.json'),(($receipt|ConvertTo-Json -Depth 8)-replace "`r`n","`n")+"`n",$utf8)
Write-Output 'H4 lab checks passed. H0-H3 protected; commercial runtime absent; documentary media gap retained.'
