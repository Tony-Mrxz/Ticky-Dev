; installer/Ticky.iss
;
; Per-user installer for the PyInstaller "onedir" build. It ships dist\Ticky
; verbatim, so the payload is exactly what `python -m PyInstaller Ticky.spec`
; produced - nothing is installed at runtime, no download is needed.
;
; Build with build_installer.ps1 (it compiles the app, stages the offline
; speech model, then passes /DAppVersion and /DBundleDir to ISCC).

#define MyAppName "Ticky"
#ifndef AppVersion
  #define AppVersion "1.3.0"
#endif
#ifndef BundleDir
  #define BundleDir "..\dist\Ticky"
#endif

[Setup]
; Never regenerate: upgrading or uninstalling an existing install only works
; while this id matches the one already recorded in the registry.
AppId={{B4E7A2C9-6D31-4F0A-9E5B-7C1D8E2A4F63}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher=Mrxz
AppCopyright=Copyright (c) 2026 Lalith Sai A (Mrxz)

; Per-user install: {localappdata} needs no elevation and keeps Windows happy
; that nothing touched a system directory.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\Ticky
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
DisableWelcomePage=no

UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\Ticky.exe
SetupIconFile=..\ticky.ico
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#MyAppName}

; Ticky is a 64-bit PyInstaller build; SMTC and the notch rely on Windows 10+.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.10240

; 502 MB in, 219 MB out. The speech model is float weights that barely
; compress, so a slower level would only buy a few megabytes.
Compression=lzma2
SolidCompression=yes

; A running Ticky holds Ticky.exe open; let Setup close it before overwriting.
CloseApplications=yes
RestartApplications=no

OutputDir=output
OutputBaseFilename=Ticky-Setup-{#AppVersion}

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
Name: "autostart"; Description: "Start Ticky when I sign in"; GroupDescription: "Additional options:"; Flags: checkedonce

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\Ticky.exe"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\Ticky.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "Ticky"; ValueData: """{app}\Ticky.exe"""; \
    Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\Ticky.exe"; Description: "Launch Ticky now"; \
    Flags: postinstall nowait skipifsilent

[UninstallRun]
; Ticky keeps its notch window and tray icon alive, so it must be stopped
; before its files go.
Filename: "{sys}\taskkill.exe"; Parameters: "/IM Ticky.exe /F"; \
    RunOnceId: "KillTicky"; Flags: runhidden

; Every file in {app} comes from the onedir bundle, so uninstall can remove the
; directory outright. The user's look and AI settings live in
; ~/.ticky_config.json, outside {app}, and are deliberately kept.

[Code]
// The login item can also be created by Ticky's own "start with Windows"
// setting, long after setup ran. Clear it on uninstall only when it really
// points into this install - a developer's entry pointing at a source checkout
// is not ours to remove.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Target: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'Ticky', Target) and
       (Pos(Lowercase(ExpandConstant('{app}')), Lowercase(Target)) > 0) then
    begin
      if not RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'Ticky') then
        Log('Login item points at this install but could not be removed');
    end;
  end;
end;
