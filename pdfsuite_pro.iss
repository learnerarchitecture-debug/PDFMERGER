[Setup]
; Basic installer information
AppName=PDF Suite Pro
AppVersion=2.3
; Publisher should match the creator
Publisher=AYUSH GUPTA
AppPublisher=AYUSH GUPTA
AppPublisherURL=https://github.com/learnerarchitecture-debug/PDFMERGER
; Update the contact info
AppSupportURL=https://github.com/learnerarchitecture-debug/PDFMERGER/issues
AppUpdatesURL=https://github.com/learnerarchitecture-debug/PDFMERGER/issues
; Default installation path
DefaultDirName={app}\PDF Suite Pro
; Default output name
DefaultOutputDirName={pf}
; Setup icon file
SetupIconFile=icons\pdf_suite_pro.ico
; Default setup language
Languages::english
Languages::russian
; Compression level
Compression=lzma
CompressionRate=9
; Allow clicking Next without changing folder
AllowNoDirChange=yes
; Create uninstaller
Uninstallable=yes
; Create a desktop shortcut
TaskIconDesktopIcon=yes
; Create a start menu folder
TaskStartMenuInternet=yes
; Request administrator for installation
PrivilegesRequired=admin
; Output base filename (the actual .exe setup file)
OutputBaseFileName=PDFSuitePro_Installer
; Setup pages
SetupPage=welcome
SetupPage=register
SetupPage=space
SetupPage=install
SetupPage=finish
; Default group name
GroupName=PDF Suite Pro
; Disable language switching
DisableLangSwitch=yes
; Set default prompt for task
AboutText=PDF Suite Pro v2.3 - PDF Merge and Split Tool
AboutText=Created by AYUSH GUPTA
AboutText=A full-featured PDF utility for Windows with modern dark UI.
AboutText=Merge, split, sign, compress, redact and 30+ PDF tools.
AboutText=No installation required - portable application.

[Files]
; Copy the executable and resources
Source: "dist\PDF Suite Pro.exe"; Destinations: "{app}"
; Copy requirements and documentation
Source: "requirements.txt"; Destinations: "{app}"
Source: "INSTALLATION.txt"; Destinations: "{app}"
Source: "README.md"; Destinations: "{app}"
; Copy assets if they exist
Source: "icons\*.*"; Destinations: "{app}"

[Icons]
; Create desktop icon
Name: "{group}\PDF Suite Pro"; Filename: "{app}\PDF Suite Pro.exe"
Name: "DesktopPDF Suite Pro"; Filename: "{app}\PDF Suite Pro.exe"
; Create start menu icon
Name: "{commonappdata}\Microsoft\Windows\Start Menu\Programs\{cm:GroupName}\PDF Suite Pro"; Filename: "{app}\PDF Suite Pro.exe"

[Run]
; Launch the application after installation
Filename: "{app}\PDF Suite Pro.exe"; Description: "Launch PDF Suite Pro"; Flags: nowait

[Messages]
; Custom message for Windows version check
VersionNotSupported="This application requires Windows 7 or later. Your current Windows version is not supported. Please use a supported Windows version (7, 8, 8.1, 10, or 11) to install PDF Suite Pro."

[CustomMessagesEnglish]
VersionNotSupported="This application requires Windows 7 or later. Your current Windows version is not supported. Please use a supported Windows version (7, 8, 8.1, 10, or 11) to install PDF Suite Pro."

[CustomMessagesRussian]
VersionNotSupported="Это приложение требует Windows 7 или более поздней версии. Ваша текущая версия Windows не поддерживается. Пожалуйста, используйте поддерживаемую версию Windows (7, 8, 8.1, 10 или 11) для установки PDF Suite Pro."

[Codes]
; Custom code for Windows version check
function InitializeSetup(): Boolean;
var
    osVersion: string;
    major, minor: integer;
begin
    ; Get Windows version
    osVersion := GetWindowsVersion;
    ; Parse version string (e.g., "10.0.19041" or "6.1.7601")
    if not StringSplit(osVersion, '.', major, minor) then
    begin
        Result := True;
        Exit;
    end;
    
    ; Check major version
    if major < 6 then
    begin
        MessageBox(VersionNotSupported, mbError, MB_OK);
        Result := False;
        Exit;
    end;
    
    ; Windows 6.x = Windows Vista/7/8/8.1/10/11
    ; major=6 means we need to check minor
    if major = 6 then
    begin
        if minor < 1 then
        begin
            MessageBox(VersionNotSupported, mbError, MB_OK);
            Result := False;
            Exit;
        end;
    end;
    
    ; major >= 7 (7, 8, 8.1, 10, 11) - all supported
    Result := True;
end;

function GetWindowsVersion: string;
var
    reg: TRegistry;
    version: string;
begin
    reg := TRegistry.Create;
    try
        reg.RootKey := HKEY_LOCAL_MACHINE;
        reg.OpenKey('SOFTWARE\Microsoft\Windows NT\CurrentVersion', False);
        version := reg.ReadString('CurrentVersion');
        Result := version;
    finally
        reg.Free;
    end;
end;