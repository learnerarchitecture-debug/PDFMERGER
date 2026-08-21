; PDF Suite Pro - NSIS Installer Script
; Compile with: makensis pdfsuite_pro.nsi

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"

; Application info
!define APP_NAME "PDF Suite Pro"
!define APP_VERSION "2.3"
!define APP_PUBLISHER "AYUSH GUPTA"
!define APP_URL "https://github.com/learnerarchitecture-debug/PDFMERGER"
!define APP_EXE "PDF Suite Pro.exe"

; Output
OutFile "PDFSuitePro_Installer.exe"
InstallDir "$PROGRAMFILES\${APP_NAME}"
InstallDirRegKey HKLM "Software\${APP_NAME}" "Install_Dir"

; Request admin privileges
RequestExecutionLevel admin

; Modern UI
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "${NSISDIR}\Contrib\Graphics\Header\modern.bmp"
!define MUI_LICENSEPAGE_TEXT_TOP "Please read the license agreement."
!define MUI_LICENSEPAGE_TEXT_BOTTOM "Click Next to continue."

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Russian"

; Variables
Var Major
Var Minor

; Windows version check function
Function GetWindowsVersion
    Push $R0
    Push $R1
    ReadRegStr $R0 HKLM "SOFTWARE\Microsoft\Windows NT\CurrentVersion" "CurrentVersion"
    StrCpy $R1 $R0 1
    ${If} $R1 == "1"
        ; Windows 10/11 (10.0.x)
        StrCpy $Major 10
        StrCpy $Minor 0
    ${ElseIf} $R1 == "6"
        ; Windows Vista/7/8/8.1 (6.x)
        StrCpy $Major 6
        StrCpy $R1 $R0 3 2
        StrCpy $Minor $R1
    ${Else}
        StrCpy $Major 0
        StrCpy $Minor 0
    ${EndIf}
    Pop $R1
    Pop $R0
FunctionEnd

; Check Windows version on init
Function .onInit
    Call GetWindowsVersion
    ${If} $Major < 6
        MessageBox MB_ICONSTOP "This application requires Windows 7 or later.$\nYour current Windows version is not supported."
        Abort
    ${EndIf}
    ${If} $Major == 6
        ${If} $Minor < 1
            MessageBox MB_ICONSTOP "This application requires Windows 7 or later.$\nYour current Windows version is not supported."
            Abort
        ${EndIf}
    ${EndIf}
FunctionEnd

; Install
Section "MainSection" SEC01
    SetOutPath "$INSTDIR"
    
    ; Copy files
    File "dist\${APP_EXE}"
    File "requirements.txt"
    File "INSTALLATION.txt"
    File "README.md"
    
    ; Write uninstall info
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayName" "${APP_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "URLInfoAbout" "${APP_URL}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "NoModify" "1"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "NoRepair" "1"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "InstallLocation" "$INSTDIR"
    
    WriteRegStr HKLM "Software\${APP_NAME}" "Install_Dir" "$INSTDIR"
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    ; Start Menu shortcut
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
    
    ; Desktop shortcut
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
SectionEnd

; Uninstall
Section "Uninstall"
    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\requirements.txt"
    Delete "$INSTDIR\INSTALLATION.txt"
    Delete "$INSTDIR\README.md"
    Delete "$INSTDIR\uninstall.exe"
    
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    
    Delete "$DESKTOP\${APP_NAME}.lnk"
    
    RMDir "$INSTDIR"
    
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
    DeleteRegKey HKLM "Software\${APP_NAME}"
SectionEnd

; Language strings
LangString LICENSE_English ${LANG_ENGLISH} "PDF Suite Pro - MIT License$\n$\nCopyright (c) 2024 AYUSH GUPTA$\n$\nPermission is hereby granted..."
LangString LICENSE_Russian ${LANG_RUSSIAN} "PDF Suite Pro - MIT License$\n$\nCopyright (c) 2024 AYUSH GUPTA$\n$\nДанная лицензия предоставляет..."