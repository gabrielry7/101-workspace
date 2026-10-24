$ErrorActionPreference='Stop'
$env:PATH=(Join-Path $PSScriptRoot '../.tools/node-v24.21.0-win-x64')+';'+$env:PATH
# Umbrella tests include historical search tests. H8 isolated rebuild itself has no sampler/loaders.
foreach($task in @('test','check','media:verify','composition:verify','design:verify','audit:verify','cohort:verify')){
 if($task -eq 'test'){& npm.cmd test}else{& npm.cmd run $task}
 if($LASTEXITCODE -ne 0){throw "Verification failed: $task"}
}
& npm.cmd run lock:verify -- --rebuild
if($LASTEXITCODE -ne 0){throw 'H8 isolated rebuild verification failed'}
