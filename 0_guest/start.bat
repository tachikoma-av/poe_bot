@echo off
:infinity_loop
"%cd%\venv\Scripts\python.exe" "vm_host_main_socket.py"
goto infinity_loop