$ErrorActionPreference = 'Stop'
$env:PATH = "$PWD\.tools\node-v24.21.0-win-x64;$env:PATH"
$env:ASTRO_TELEMETRY_DISABLED = '1'
$commands = @('test','check','build','design:replay','media:verify','composition:verify','design:verify')
foreach ($task in $commands) {
    & npm.cmd run $task
    if ($LASTEXITCODE -ne 0) { throw "H5 verification failed: $task" }
}
