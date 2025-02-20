@echo off
cd 1_host

set hostname=WIN-POE1
for /f "tokens=2 delims=[]" %%a in ('ping -n 1 %hostname% ^| findstr "["') do set remote_ip=%%a

REM set remote_ip=

call venv\Scripts\activate
python poe_2_test_all_tcp_endpoints.py %1

PAUSE