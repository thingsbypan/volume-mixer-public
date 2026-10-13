$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$compiler = Join-Path $env:LOCALAPPDATA 'electron-builder\Cache\nsis-3.0.4.1\nsis-3.0.4.1-1mx3n\makensis.exe'
if (-not (Test-Path -LiteralPath $compiler)) { $compiler = (Get-Command makensis.exe -ErrorAction Stop).Source }
New-Item -ItemType Directory -Force installer | Out-Null
& $compiler installer.nsi
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }

