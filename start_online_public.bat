@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
set "CLOUDFLARED=%ROOT%Cloudflare\cloudflared-windows-amd64.exe"
set "PORT=8765"

echo Settlers Launcher
echo.
echo 1. Start online public game
echo 2. Start desktop game
echo 3. Start online server only
echo 4. Start Cloudflare tunnel only
echo.
set /p "CHOICE=Choose an option [1]: "
if "%CHOICE%"=="" set "CHOICE=1"

if "%CHOICE%"=="1" goto online_public
if "%CHOICE%"=="2" goto desktop
if "%CHOICE%"=="3" goto online_server
if "%CHOICE%"=="4" goto tunnel

echo Unknown option.
pause
exit /b 1

:online_public
start "Catan Online Server" cmd /k ""%PYTHON%" "%ROOT%online_catan.py""
timeout /t 2 /nobreak >nul
start "Catan Cloudflare Tunnel" cmd /k ""%CLOUDFLARED%" tunnel --url http://localhost:%PORT%"
exit /b 0

:desktop
"%PYTHON%" "%ROOT%catan_app.py"
exit /b %ERRORLEVEL%

:online_server
"%PYTHON%" "%ROOT%online_catan.py"
exit /b %ERRORLEVEL%

:tunnel
"%CLOUDFLARED%" tunnel --url http://localhost:%PORT%
exit /b %ERRORLEVEL%
