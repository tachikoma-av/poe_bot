@echo off

git clone https://github.com/exCore2/ExileCore2.git
xcopy "Plugins" "./ExileCore2/Plugins" /E /Y /C

pause