@echo off
"%~dp0Cloudflare\cloudflared-windows-amd64.exe" tunnel --url http://localhost:8765
