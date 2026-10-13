# Volume Mixer

By Pan / Things by Pan — https://things.rocks — thingsbypan@gmail.com

A compact Windows tray mixer with three app faders, a master fader, real peak meters, and optional MIDI control.

## Requirements and installation
Windows 10/11 x64 with an active audio output. Download and run `TrayMixer-v1.0.3-Setup.exe` from GitHub Releases. Installation is per user; no Python, administrator access, paid API, or online service is required. Quit an earlier mixer before upgrading. The installer is unsigned.

## Basic use and configuration
Choose app sessions for App 3, App 2, App 1 and an output for Master. Play audio in an app to expose its session. Master controls that output; it does not change the Windows default. Close/Escape hides the panel; click the tray icon to reopen and use Quit to exit. MIDI Learn accepts absolute CC faders and note-on mute buttons with pickup. Settings and optional setup backups are stored under `%LOCALAPPDATA%\TrayMixer`; no personal mappings are supplied. Uninstall preserves user settings.

## Build from source
Install Python 3.13 x64, create `.venv` with `python -m venv .venv`, then run `.venv\Scripts\python.exe -m pip install -r requirements-lock.txt`. Run `.venv\Scripts\python.exe main.py` or `build.cmd`. Build the installer with NSIS using `build-installer.ps1` (the cached electron-builder compiler is used when present; otherwise install NSIS and put makensis on PATH).

## Checks and limitations
Run `.venv\Scripts\python.exe -m unittest test_midi test_sessions test_audio_memory`. Packaged `--verify-build` checks endpoint access and tray hide/reopen/quit. Audio checks use a separate silent session. Hardware MIDI, unplug/reconnect, and visual scaling need manual testing. No exclusive-mode guarantee, relative MIDI encoders, LED output, default-output switching, or automatic session migration. Missing or ambiguous sessions require selection.

MIT license. Dependencies retain their own licenses.
