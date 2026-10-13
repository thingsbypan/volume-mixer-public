@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe -m PyInstaller --noconfirm --windowed --onedir --distpath release-memory-fix --name TrayMixer main.py

