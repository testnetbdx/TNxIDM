; TNxIDM installer - Inno Setup script, original, no third-party branding.
; Build on Windows after PyInstaller: iscc installer.iss
; Requires dist\TNxIDM\TNxIDM.exe (PyInstaller onedir output) in this folder.
#define MyAppName "TNxIDM"
#define MyAppVersion "1.0"
#define MyAppPublisher "TNxIDM"

[Setup]
AppId={{A1B2C3D4-1111-4000-8000-TNxIDM1000}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=installer-output
OutputBaseFilename=TNxIDM-Setup-v1.0
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\TNxIDM\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\TNxIDM.exe"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\TNxIDM.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\TNxIDM.exe"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
