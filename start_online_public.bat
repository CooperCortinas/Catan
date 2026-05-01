@echo off
set "ROOT=%~dp0"
start "Catan Online Server" cmd /k ""%ROOT%run_online_catan.bat""
timeout /t 2 /nobreak >nul
start "Catan Cloudflare Tunnel" cmd /k ""%ROOT%run_cloudflare_tunnel.bat""
