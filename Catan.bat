@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
set "CLOUDFLARED=%ROOT%Cloudflare\cloudflared-windows-amd64.exe"
set "PORT=8765"

echo Settlers Launcher


if "%CHOICE%"=="1" goto online_public


:online_public
start "Catan Online Server" cmd /k ""%PYTHON%" "%ROOT%online_catan.py""
timeout /t 2 /nobreak >nul
start "Catan Cloudflare Tunnel" cmd /k ""%CLOUDFLARED%" tunnel --url http://localhost:%PORT%"
exit /b 0

