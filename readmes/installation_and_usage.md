# 0_guest
## How to install:
- install .NET SDK 8.0 x64 https://dotnet.microsoft.com/en-us/download/dotnet/8.0
- install VC 2015 Redistributable https://www.microsoft.com/en-US/download/details.aspx?id=48145
- install python - 0_guest/1_install_python.bat
- install libraries - 0_guest/2_install_venv.bat

- install exilecore2 - 0_guest/3_install_ex2_hud.bat 
OR
- copy 0_guest/Plugins folder inside your exilecore2 instance

## Important:
- be sure to disable firewall and disable turning off the monitor
- be sure to set the game resolution to 1024x768, otherwise it may cause unexpected behaiviour
- if you have vpn, make sure that you dont pass connections through ports 50006,50007


# 1_host
## How to install:
- install python - 1_host/scripts/1_install_python.bat
- install libraries - 1_host/scripts/2_install_venv.bat
<!-- install VC 2015 Redistributable https://www.microsoft.com/en-US/download/details.aspx?id=48145 -->

## Important:
- be sure to disable firewall and disable turning off the monitor


# Usage
- run start.bat from 0_guest on your virtual machine
- run ExileApi with plugin from 0_guest/Plugins/ShareData on your virtual machine
- run poe2_mapper.bat but you need your own build or u know to code ;)
- works

usage sample raw: https://www.youtube.com/watch?v=4HEG2ryBzrQ

