#define AppName "PDF Suite Pro"
#define AppVersion "4.1"
#define AppPublisher "AYUSH GUPTA"
#define AppURL "https://github.com/learnerarchitecture-debug/PDFMERGER"
#define SourceExe "dist\PDF Suite Pro.exe"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/issues
DefaultDirName={pf}\{#AppName}
DefaultGroupName={#AppName}
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\PDF Suite Pro.exe
OutputBaseFilename=PDFSuitePro_Installer
OutputDir=.
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
Uninstallable=yes
DisableDirPage=no
DisableProgramGroupPage=yes
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
Source: "{#SourceExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\PDFSuiteCLI.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"
Source: "INSTALLATION.txt"; DestDir: "{app}"
Source: "README.md"; DestDir: "{app}"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\PDF Suite Pro.exe"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\PDF Suite Pro.exe"

[Run]
Filename: "{app}\PDF Suite Pro.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[CustomMessages]
english.VersionNotSupported="This application requires Windows 7 or later. Your current Windows version is not supported. Please use a supported Windows version (7, 8, 8.1, 10, or 11) to install PDF Suite Pro."
russian.VersionNotSupported="Это приложение требует Windows 7 или более поздней версии. Ваша текущая версия Windows не поддерживается. Пожалуйста, используйте поддерживаемую версию Windows (7, 8, 8.1, 10 или 11) для установки PDF Suite Pro."

[Code]
function GetWindowsMajorMinor(var Major, Minor: Integer): Boolean;
var
  Ver: string;
  Parts: array of string;
begin
  Result := False;
  Ver := GetWindowsVersion;
  if Ver = '' then Exit;
  
  Parts := SplitString(Ver, '.');
  if GetArrayLength(Parts) < 2 then Exit;
  
  Major := StrToIntDef(Parts[0], 0);
  Minor := StrToIntDef(Parts[1], 0);
  Result := True;
end;

function GetWindowsVersion: string;
var
  Reg: TRegistry;
begin
  Result := '';
  Reg := TRegistry.Create;
  try
    Reg.RootKey := HKLM;
    if Reg.OpenKeyReadOnly('SOFTWARE\Microsoft\Windows NT\CurrentVersion') then
    begin
      Result := Reg.ReadString('CurrentVersion');
    end;
  finally
    Reg.Free;
  end;
end;

function InitializeSetup(): Boolean;
var
  Major, Minor: Integer;
begin
  if not GetWindowsMajorMinor(Major, Minor) then
  begin
    Result := True;
    Exit;
  end;
  
  if Major < 6 then
  begin
    MsgBox(ExpandConstant('{cm:VersionNotSupported}'), mbError, MB_OK);
    Result := False;
  end
  else if Major = 6 then
  begin
    if Minor < 1 then
    begin
      MsgBox(ExpandConstant('{cm:VersionNotSupported}'), mbError, MB_OK);
      Result := False;
    end
    else
      Result := True;
  end
  else
    Result := True;
end;