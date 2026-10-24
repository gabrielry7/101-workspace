param([Parameter(Mandatory=$true)][string]$Repository,[string]$SevenZip='',[string]$DownloadDirectory='',[string]$NodePath='')
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$manifest=Get-Content -LiteralPath (Join-Path $root 'asset-manifest.json') -Raw | ConvertFrom-Json
if(-not $DownloadDirectory){$DownloadDirectory=Join-Path $root '.asset-downloads'}
New-Item -ItemType Directory -Force $DownloadDirectory|Out-Null
if(-not $SevenZip){$SevenZip=(Get-Command 7z -ErrorAction SilentlyContinue).Source}
if(-not $SevenZip){$SevenZip='C:/Program Files/7-Zip/7z.exe'}
if(-not(Test-Path -LiteralPath $SevenZip)){throw 'Install 7-Zip or provide -SevenZip C:/path/to/7z.exe'}
foreach($a in $manifest.archives){
 $path=Join-Path $DownloadDirectory $a.name
 if(-not(Test-Path -LiteralPath $path)){
  & gh release download $manifest.releaseTag --repo $Repository --pattern $a.name --dir $DownloadDirectory
  if($LASTEXITCODE -ne 0){throw "Download failed: $($a.name)"}
 }
 if((Get-Item -LiteralPath $path).Length -ne $a.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $a.sha256){throw "Archive checksum mismatch: $($a.name)"}
}
foreach($first in @($manifest.archives.firstVolume|Select-Object -Unique)){
 & $SevenZip x (Join-Path $DownloadDirectory $first) "-o$root" -y -bsp0
 if($LASTEXITCODE -ne 0){throw 'Archive extraction failed'}
}
if(-not $NodePath){$NodePath=(Get-Command node -ErrorAction SilentlyContinue).Source}
if($NodePath -and (Test-Path (Join-Path $root 'verify-assets.mjs'))){
 & $NodePath (Join-Path $root 'verify-assets.mjs') $root
 if($LASTEXITCODE -ne 0){throw 'Restored asset verification failed'}
 return
}
foreach($f in $manifest.files){
 $path=[IO.Path]::GetFullPath((Join-Path $root $f.path))
 if(-not $path.StartsWith([IO.Path]::GetFullPath($root)+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Unsafe manifest path'}
 if(-not(Test-Path -LiteralPath $path) -or (Get-Item -LiteralPath $path).Length -ne $f.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $f.sha256){throw "Restored file checksum mismatch: $($f.path)"}
}
Write-Output "RESTORATION_PASS files=$($manifest.files.Count) archives=$($manifest.archives.Count)"
