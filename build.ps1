$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --windowed --onedir --distpath release-memory-fix --name TrayMixer main.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }

