; Inno Setup Script for Meeting Whisperer
; This script creates a professional Windows installer
; Install Inno Setup from: https://jrsoftware.org/isdl.php

#define MyAppName "Meeting Whisperer"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Meeting Whisperer"
#define MyAppURL "https://github.com/yourusername/meeting-whisperer"
#define MyAppExeName "MeetingWhisperer.exe"
#define SourcePath "dist\MeetingWhisperer"

[Setup]
AppId={{B9E7C8D9-1A2B-3C4D-E5F6-7A8B9C0D1E2F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppPublisher}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\..\LICENSE
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir={#SourcePath}\..\output
OutputBaseFilename=MeetingWhisperer-Setup-{#MyAppVersion}
SetupIconFile={#SourcePath}\..\..\assets\app.ico
SolidCompression=yes
Compression=lzma
InternalCompressLevel=max
WizardResizable=yes
ShowLanguageDialog=no

; Request admin privileges for installation
PrivilegesRequired=admin

; Windows version requirements
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startuprun"; Description: "Start {#MyAppName} on system startup"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copy executable and all dependencies
Source: "{#SourcePath}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourcePath}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourcePath}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFileName: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFileName: "{app}\{#MyAppExeName}"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Flags: nowait postinstall skipifsilent; Description: "Launch {#MyAppName}"

[InstallDelete]
; Delete old versions
Type: filesandordirs; Name: "{app}\*.py"

[Code]
var
  RestartMsg: string;

function IsAdminLoggedOn: Boolean;
begin
  Result := IsAdminInstalling() or IsAdminUser();
end;

function GetEnv(EnvVar: string): string;
var
  HKey: Integer;
begin
  HKey := HKEY_CURRENT_USER;
  
  if RegQueryStringValue(HKey, 'Environment', EnvVar, Result) then
    Exit
  else begin
    HKey := HKEY_LOCAL_MACHINE;
    RegQueryStringValue(HKey, 'System\CurrentControlSet\Control\Session Manager\Environment', EnvVar, Result);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Create shortcuts and associations
    Log('Installation completed');
    
    // Optionally add firewall exception (requires admin)
    if IsAdminLoggedOn then
    begin
      ShellExec('runas', 'netsh.exe', 'advfirewall firewall add rule name="Meeting Whisperer Backend" dir=in action=allow program="' + ExpandConstant('{app}\' + '{#MyAppExeName}') + '" enable=yes', '', SW_HIDE, ewNoWait, RestartMsg);
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    Log('Uninstallation completed');
  end;
end;
