@echo off
title PDF Suite Pro - Installer
color 0A

echo.
echo ========================================
echo   PDF Suite Pro v4.1 - Installer
echo   Creator: AYUSH GUPTA
echo   https://github.com/learnerarchitecture-debug/PDFMERGER
echo ========================================
echo.

:: Check for admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Please run as Administrator!
    echo Right-click this file and select "Run as administrator"
    pause
    exit /b 1
)

:: Check Windows version
ver | findstr /r /c:" 10\." >nul
if %errorLevel% equ 0 goto :win_ok
ver | findstr /r /c:" 6\.1" >nul
if %errorLevel% equ 0 goto :win_ok
ver | findstr /r /c:" 6\.2" >nul
if %errorLevel% equ 0 goto :win_ok
ver | findstr /r /c:" 6\.3" >nul
if %errorLevel% equ 0 goto :win_ok

echo [ERROR] This application requires Windows 7 or later.
echo Your current Windows version is not supported.
pause
exit /b 1

:win_ok
echo [OK] Windows version check passed.

:: Set paths
set "APPDIR=%ProgramFiles%\PDF Suite Pro"
set "EXENAME=PDF Suite Pro.exe"
set "SRCEXE=dist\%EXENAME%"

:: Check if source executable exists
if not exist "%SRCEXE%" (
    echo [ERROR] Source executable not found: %SRCEXE%
    echo Please build it first with:
    echo   pyinstaller --onefile --noconsole --name "PDF Suite Pro" pdf_tool.py
    pause
    exit /b 1
)

:: Create install directory
echo [INFO] Creating installation directory...
if not exist "%APPDIR%" mkdir "%APPDIR%"

:: Copy files
echo [INFO] Copying files...
copy /y "%SRCEXE%" "%APPDIR%\" >nul
if exist "dist\PDFSuiteCLI.exe" copy /y "dist\PDFSuiteCLI.exe" "%APPDIR%\" >nul
copy /y "requirements.txt" "%APPDIR%\" >nul
copy /y "INSTALLATION.txt" "%APPDIR%\" >nul
copy /y "README.md" "%APPDIR%\" >nul

:: Create desktop shortcut
echo [INFO] Creating desktop shortcut...
powershell -Command ^
    "$ws = New-Object -ComObject WScript.Shell; ^
    $sc = $ws.CreateShortcut('%USERPROFILE%\Desktop\PDF Suite Pro.lnk'); ^
    $sc.TargetPath = '%APPDIR%\%EXENAME%'; ^
    $sc.Save()" 2>nul

:: Create Start Menu shortcut
echo [INFO] Creating Start Menu shortcut...
if not exist "%ProgramData%\Microsoft\Windows\Start Menu\Programs\PDF Suite Pro" (
    mkdir "%ProgramData%\Microsoft\Windows\Start Menu\Programs\PDF Suite Pro"
)
powershell -Command ^
    "$ws = New-Object -ComObject WScript.Shell; ^
    $sc = $ws.CreateShortcut('%ProgramData%\Microsoft\Windows\Start Menu\Programs\PDF Suite Pro\PDF Suite Pro.lnk'); ^
    $sc.TargetPath = '%APPDIR%\%EXENAME%'; ^
    $sc.Save()" 2>nul

:: Write uninstaller
echo [INFO] Creating uninstaller...
(
    echo @echo off
    echo title PDF Suite Pro - Uninstaller
    echo color 0C
    echo.
    echo ========================================
    echo   PDF Suite Pro - Uninstaller
    echo ========================================
    echo.
    echo This will remove PDF Suite Pro from your system.
    echo.
    set /p confirm=Are you sure? (y/N): 
    if /i not "%confirm%"=="y" exit /b
    echo.
    echo Removing files...
    rmdir /s /q "%APPDIR%"
    echo Removing shortcuts...
    del /q "%USERPROFILE%\Desktop\PDF Suite Pro.lnk" 2>nul
    del /q "%ProgramData%\Microsoft\Windows\Start Menu\Programs\PDF Suite Pro\PDF Suite Pro.lnk" 2>nul
    rmdir "%ProgramData%\Microsoft\Windows\Start Menu\Programs\PDF Suite Pro" 2>nul
    echo.
    echo Uninstall complete.
    pause
) > "%APPDIR%\uninstall.bat"

:: Register in Windows Apps & Features
reg add "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF Suite Pro" /v DisplayName /t REG_SZ /d "PDF Suite Pro" /f >nul
reg add "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF Suite Pro" /v UninstallString /t REG_SZ /d "\"%APPDIR%\uninstall.bat\"" /f >nul
reg add "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF Suite Pro" /v DisplayVersion /t REG_SZ /d "4.1" /f >nul
reg add "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF Suite Pro" /v Publisher /t REG_SZ /d "AYUSH GUPTA" /f >nul
reg add "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF Suite Pro" /v URLInfoAbout /t REG_SZ /d "https://github.com/learnerarchitecture-debug/PDFMERGER" /f >nul
reg add "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF Suite Pro" /v InstallLocation /t REG_SZ /d "%APPDIR%" /f >nul
reg add "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF Suite Pro" /v NoModify /t REG_DWORD /d 1 /f >nul
reg add "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF Suite Pro" /v NoRepair /t REG_DWORD /d 1 /f >nul

echo.
echo ========================================
echo Installation complete!
echo ========================================
echo.
echo Installed to: %APPDIR%
echo Desktop shortcut created
echo Start Menu shortcut created
echo Uninstaller: %APPDIR%\uninstall.bat
echo Registered in Windows Apps & Features
echo.
echo Launch PDF Suite Pro now? (Y/n)
set /p launch=
if /i "%launch%" neq "n" (
    start "" "%APPDIR%\%EXENAME%"
)
pause