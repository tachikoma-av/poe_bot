@echo off
setlocal enabledelayedexpansion
echo Installing python...

winget install Python.Python.3.13 --silent
winget install git.git --silent

pause