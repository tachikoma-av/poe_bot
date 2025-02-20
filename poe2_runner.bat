cd 1_host

set debug=0
set unique_id=poe2_test
set remote_ip=172.23.107.65

TITLE %remote_ip% %unique_id% %predefined_strategy% %build_name%
call venv\Scripts\activate

:infinity_loop
python poe_2_test.py {'script':'maps','REMOTE_IP':'%remote_ip%','unique_id':'%unique_id%','force_reset_temp':False,'custom_strategy':'','predefined_strategy':'%predefined_strategy%','build':'%build_name%'}
goto :infinity_loop
