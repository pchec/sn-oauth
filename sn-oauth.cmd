@echo off
rem Launcher for Windows. Bootstraps on first run, then runs sn-oauth.
setlocal
set "HERE=%~dp0"
if not exist "%HERE%.venv\Scripts\sn-oauth.exe" (
  powershell -ExecutionPolicy Bypass -File "%HERE%bootstrap\install.ps1"
)
"%HERE%.venv\Scripts\sn-oauth.exe" %*
