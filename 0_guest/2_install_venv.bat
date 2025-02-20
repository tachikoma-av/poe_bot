@echo off
setlocal enabledelayedexpansion

echo Installing venv...
python -m venv venv

call venv\Scripts\activate
echo Installing pip...
python -m ensurepip --default-pip
python -m pip install --upgrade pip setuptools wheel
echo Installing libs...
pip install -r requirements.txt

pause