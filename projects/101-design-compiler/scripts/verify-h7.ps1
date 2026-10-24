$ErrorActionPreference='Stop'
$env:PATH=(Join-Path $PSScriptRoot '../.tools/node-v24.21.0-win-x64')+';'+$env:PATH
foreach($task in @('test','check','build','media:replay','media:verify','composition:replay','composition:verify','design:replay','design:verify','audit:verify','cohort:replay','cohort:verify')){
 if($task -eq 'test'){& npm.cmd test}else{& npm.cmd run $task}
 if($LASTEXITCODE -ne 0){throw "H7 verification failed: $task"}
}
