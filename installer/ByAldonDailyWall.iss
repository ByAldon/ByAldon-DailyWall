; ByAldon DailyWall Inno Setup installer script
; Build the release folder first before compiling this script.

#define MyAppName "ByAldon DailyWall"
#define MyAppVersion "0.6.1"
#define MyAppPublisher "ByAldon"
#define MyAppURL "https://github.com/ByAldon/ByAldon-DailyWall"
#define MyAppExeName "ByAldon DailyWall.exe"
#define ReleaseDir "..\ByAldon DailyWall Release"

[Setup]
AppId={{8D1A499B-A6E6-4B25-9E7D-3D5E9B8248D5}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\ByAldon DailyWall
DisableDirPage=no
DefaultGroupName=ByAldon DailyWall
DisableProgramGroupPage=no
AllowNoIcons=yes
LicenseFile={#ReleaseDir}\LICENSE
SetupIconFile={#ReleaseDir}\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=..\installer-output
OutputBaseFilename=ByAldon-DailyWall-Setup-v0.6.1
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Dirs]
Name: "{app}\assets"
Name: "{app}\assets\wallpapers"
Name: "{app}\assets\wallpapers\original"
Name: "{app}\assets\wallpapers\watermarked"

[Files]
Source: "{#ReleaseDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseDir}\config.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "{#ReleaseDir}\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseDir}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseDir}\assets\icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "{#ReleaseDir}\assets\icon.png"; DestDir: "{app}\assets"; Flags: ignoreversion

[Icons]
Name: "{group}\ByAldon DailyWall"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\Uninstall ByAldon DailyWall"; Filename: "{uninstallexe}"
Name: "{autodesktop}\ByAldon DailyWall"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch ByAldon DailyWall"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\assets\history.json"
Type: filesandordirs; Name: "{app}\assets\wallpapers\original"
Type: filesandordirs; Name: "{app}\assets\wallpapers\watermarked"
Type: dirifempty; Name: "{app}\assets\wallpapers"
Type: dirifempty; Name: "{app}\assets"
Type: dirifempty; Name: "{app}"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    RegDeleteValue(
      HKCU,
      'Software\Microsoft\Windows\CurrentVersion\Run',
      'ByAldonDailyWall'
    );
  end;
end;
