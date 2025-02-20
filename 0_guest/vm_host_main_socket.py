import os
import socket
import time
import uuid

import win32clipboard
from utils import Controller

import json
import subprocess

import win32gui

controller = Controller()


def getWindowLoc(window_name: str):
  try:
    hwnd = win32gui.FindWindow(None, window_name)
    rect = win32gui.GetWindowRect(hwnd)
    return rect
  except:
    return None


def processExists(process_name):
  call = "TASKLIST", "/FI", "imagename eq %s" % process_name
  # use buildin check_output right away
  output = subprocess.check_output(call).decode()
  # check in last line for process name
  last_line = output.strip().split("\r\n")[-1]
  # because Fail message could be translated
  return last_line.lower().startswith(process_name.lower())





def getParam(action_msg: str, param: str):
  return action_msg.split(f"{param}=")[1].split("&")[0]


temp = {}


def loadTemp():
  file = open("./temp.json", encoding="utf-8")
  config = json.load(file)
  file.close()
  global temp
  temp = config


def updateTemp():
  file = open("./temp.json", "w", encoding="utf-8")
  json.dump(temp, file, ensure_ascii=False, indent=4)
  file.close()


try:
  loadTemp()
except:
  pass

default_ok_response = b"1"


def Main():
  mac_address = uuid.getnode()
  mac_address_hex = "".join(["{:02x}".format((mac_address >> elements) & 0xFF) for elements in range(0, 8 * 6, 8)][::-1])
  port = 50007
  host = "0.0.0.0"
  HOST = socket.gethostbyname(socket.gethostname())
  print(f"[Worker] host:port {HOST}:{port} mac_adress: {mac_address_hex}")
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  s.bind((host, port))
  print(f"[Worker] Started on {HOST}:{port}")
  s.listen(1)
  c, addr = s.accept()
  print("[Worker] established connection with: " + str(addr))
  s.close()

  while True:
    action_msg = c.recv(1024).decode()
    ### FROM HERE
    print(f"got action {time.time()}:" + action_msg)
    action = action_msg.split("action=")[1].split("&")[0]
    wait_till_recieved = len(action_msg.split("wtr=1&")) != 1
    if wait_till_recieved:
      c.send(default_ok_response)
    if action == "mouseClick":
      x = action_msg.split("x=")[1].split("&")[0]
      y = action_msg.split("y=")[1].split("&")[0]
      button = action_msg.split("button=")[1].split("&")[0]
      controller.mouse.click(int(x), int(y), button)
      if wait_till_recieved is not True:
        c.send(default_ok_response)
    elif action == "mouseSetCursorPos":
      x = action_msg.split("x=")[1].split("&")[0]
      y = action_msg.split("y=")[1].split("&")[0]
      controller.mouse.setCursorPos(int(x), int(y))
      if wait_till_recieved is not True:
        c.send(default_ok_response)
    elif action == "mouseSetCursorPosSmooth":
      x = action_msg.split("x=")[1].split("&")[0]
      y = action_msg.split("y=")[1].split("&")[0]
      max_time_ms = action_msg.split("mtm=")[1].split("&")[0]
      mouse_speed_mult = action_msg.split("msm=")[1].split("&")[0]
      controller.mouse.setCursorPosSmooth(int(x), int(y), int(max_time_ms), int(mouse_speed_mult))
      if wait_till_recieved is not True:
        c.send(default_ok_response)
    elif action == "mousePress":
      x = action_msg.split("x=")[1].split("&")[0]
      y = action_msg.split("y=")[1].split("&")[0]
      button = action_msg.split("button=")[1].split("&")[0]
      controller.mouse.press(int(x), int(y), button)
      if wait_till_recieved is not True:
        c.send(default_ok_response)
    elif action == "mouseRelease":
      button = action_msg.split("button=")[1].split("&")[0]
      controller.mouse.release(button=button)
      if wait_till_recieved is not True:
        c.send(default_ok_response)
    elif action == "pushButton":
      button_code = action_msg.split("button_code=")[1].split("&")[0]
      controller.keyboard.tapButton(button_code)
      if wait_till_recieved is not True:
        c.send(default_ok_response)
    elif action == "keyboard_pressKey":
      button_code = action_msg.split("button_code=")[1].split("&")[0]
      controller.keyboard.pressKey(button_code)
      if wait_till_recieved is not True:
        c.send(default_ok_response)
    elif action == "keyboard_releaseKey":
      button_code = action_msg.split("button_code=")[1].split("&")[0]
      controller.keyboard.releaseKey(button_code)
      if wait_till_recieved is not True:
        c.send(default_ok_response)
    elif action == "executeCMD":
      task = action_msg.split("task=")[1].split("&")[0]
      os.system(f'cmd /c "{task}"')
      if wait_till_recieved is not True:
        c.send(default_ok_response)
    elif action == "setClipboardText":
      clipboard_text = action_msg.split("clipboard_text=")[1].split("&")[0]
      win32clipboard.OpenClipboard()
      win32clipboard.EmptyClipboard()
      win32clipboard.SetClipboardText(clipboard_text, win32clipboard.CF_TEXT)
      win32clipboard.CloseClipboard()
      if wait_till_recieved is not True:
        c.send(default_ok_response)
    elif action == "restartScript":
      print("[Worker] got restart script")
      if wait_till_recieved is not True:
        c.send(default_ok_response)
      c.close()
      break
    elif action == "releaseAll":
      controller.releaseAll()
      if wait_till_recieved is not True:
        c.send(default_ok_response)
    else:
      print(f"got unknown action: {action}")
      if wait_till_recieved is not True:
        c.send(default_ok_response)


try:
  Main()
except:
  print("releasing all buttons")
  controller.releaseAll()
