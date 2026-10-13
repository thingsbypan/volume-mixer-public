Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
Name "Tray Mixer v1"
OutFile "installer\TrayMixer-v1.0.3-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\Tray Mixer"
RequestExecutionLevel user
SetCompressor /SOLID lzma
VIProductVersion "1.0.3.0"
VIAddVersionKey "ProductName" "Tray Mixer v1"
VIAddVersionKey "FileDescription" "Tray Mixer v1 Setup"
VIAddVersionKey "FileVersion" "1.0.3"
Var TestMode
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
Function .onInit
  SetShellVarContext current
  ${GetParameters} $R0
  ClearErrors
  ${GetOptions} $R0 "/TEST" $R1
  ${IfNot} ${Errors}
    StrCpy $TestMode "1"
  ${EndIf}
FunctionEnd
Section "Tray Mixer"
  SetOutPath "$INSTDIR"
  IfFileExists "$INSTDIR\TrayMixer.exe" 0 copy
  ExecWait '"$INSTDIR\TrayMixer.exe" --quit'
  Sleep 1000
  copy:
  File /r "release-memory-fix\TrayMixer\*.*"
  File "README.md"
  File "LICENSE"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  ${If} $TestMode == "1"
    FileOpen $R0 "$INSTDIR\installer-test.flag" w
    FileClose $R0
  ${EndIf}
  ${If} $TestMode != "1"
    CreateDirectory "$SMPROGRAMS\Tray Mixer"
    CreateShortcut "$SMPROGRAMS\Tray Mixer\Tray Mixer v1.lnk" "$INSTDIR\TrayMixer.exe"
    CreateShortcut "$DESKTOP\Tray Mixer v1.lnk" "$INSTDIR\TrayMixer.exe"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TrayMixer" "DisplayName" "Tray Mixer v1"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TrayMixer" "DisplayVersion" "1.0.3"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TrayMixer" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TrayMixer" "InstallLocation" "$INSTDIR"
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TrayMixer" "NoModify" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TrayMixer" "NoRepair" 1
  ${EndIf}
SectionEnd
Section "Uninstall"
  SetShellVarContext current
  ExecWait '"$INSTDIR\TrayMixer.exe" --quit'
  Sleep 1000
  Delete "$INSTDIR\TrayMixer.exe"
  Delete "$INSTDIR\README.md"
  Delete "$INSTDIR\LICENSE"
  RMDir /r "$INSTDIR\_internal"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  IfFileExists "$INSTDIR\installer-test.flag" skiplinks
  ReadRegStr $R0 HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TrayMixer" "InstallLocation"
  StrCmp $R0 $INSTDIR 0 skiplinks
  Delete "$DESKTOP\Tray Mixer v1.lnk"
  Delete "$SMPROGRAMS\Tray Mixer\Tray Mixer v1.lnk"
  RMDir "$SMPROGRAMS\Tray Mixer"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TrayMixer"
  skiplinks:
  Delete "$INSTDIR\installer-test.flag"
  RMDir "$INSTDIR"
SectionEnd
