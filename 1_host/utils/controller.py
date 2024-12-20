import socket
import pickle
import _thread
import time
import random
import struct

class VMHostPuppeteer:
  def __init__(self, host: str, port = 50007, debug = False, backend_type = 'custom_guest # or local') -> None:
    self.host = host
    self.port = port
    self.debug = debug
    self.mouse = Mouse(self)
    self.keyboard = Keyboard(self)
    self.mouse_pressed = self.mouse.pressed
    # self.screen = Screen()
    # self.clipboard = Clipboard()
    self.sending = False
    self.connected = False
    self.connect()

  def connect(self):
    if self.connected != False:
      return
    print(f'[Controller] establishing connection with {(self.host, self.port)}')
    self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.s.settimeout(5)
    try:
      self.s.connect((self.host, self.port))
      if self.debug: print(f'[Controller] established connection with {(self.host, self.port)}')
      self.connected = True
    except socket.error:
      text = f'couldnt connect to {self.host}, maybe start.bat on guest isnt launched? or ip is wrong'
      print(text)
      print(text)
      print(text)
      print(text)
      print(text)
      print(text)
      print(text)
      print(text)
      print(text)
      print(text)
      raise Exception(text)
  def setReleasedAll(self):
    self.mouse.setReleased()
  def disconnect(self):
    self.s.close()
    self.connected = False
  def sendCommand(self, command:str, wait_till_recieved = True, recv_buffer_size = 64):
    i_count = 0
    if wait_till_recieved != False:
      command += "&wtr=1&"
    while self.sending:
      time.sleep(0.001)
      if self.debug: print(f'[Controller] debug blocking')
    self.sending = True
    if self.connected != True:
      self.connect()
    while True:
      i_count += 1
      if i_count == 12:
        raise Exception('i_count == 12: on sendCommand')
      try:
        # if self.debug: 
        print(f'[Controller] debug sending {command} at {time.time()}')
        self.s.send(command.encode())
        data = self.s.recv(recv_buffer_size)
        if self.debug: print(f'[Controller] debug finished {command} at {time.time()}')
        self.sending = False
        print(f'[Controller] debug recieved response for {command} at {time.time()}')
        return data
      except Exception as e:
        print(f'send command exception i_count:{i_count}')
        print(e.__str__())

  def sendCommandToRecieveBytes(self, command:str, recv_buffer_size = 4):
    i_count = 0
    while self.sending:
      time.sleep(0.001)
      if self.debug: print(f'[Controller] debug blocking')
    self.sending = True
    if self.connected != True:
      self.connect()
    while True:
      i_count += 1
      if i_count == 12:
        raise Exception('i_count == 12: on sendCommand')
      try:
        # if self.debug: 
        print(f'[Controller] debug sending {command} at {time.time()}')
        self.s.send(command.encode())
        data_size_raw = self.s.recv(recv_buffer_size)
        print(f'[Controller] data_size_raw {data_size_raw}')
        data_size = struct.unpack('>I', data_size_raw)[0]
        print(f'[Controller] data_size {data_size}')
        received_payload = b""
        reamining_payload_size = data_size
        while reamining_payload_size != 0:
          received_payload += self.s.recv(reamining_payload_size)
          reamining_payload_size = data_size - len(received_payload)
        data = pickle.loads(received_payload)
        if self.debug: print(f'[Controller] debug finished {command} at {time.time()}')
        self.sending = False
        return data
      except Exception as e:
        print(f'send command exception i_count:{i_count}')
        print(e.__str__())

  def mouseClick(self, x=-1,y=-1, button = 'left', wait_till_executed = True):
    if x!= -1 and y!= -1:
      self.mouse.internalAssignCursorPos(x,y)
    action_msg = f'action=mouseClick&x={x}&y={y}&button={button}'
    self.sendCommand(command=action_msg, wait_till_recieved=not wait_till_executed)
    self.mouse_pressed[button] = False # TODO if needed?
  def mouseSetCursorPos(self, x,y, wait_till_executed = True):
    action_msg = f'action=mouseSetCursorPos&x={x}&y={y}'
    self.sendCommand(command=action_msg, wait_till_recieved=not wait_till_executed)
  def mouseSetCursorPosSmooth(self, x,y, wait_till_executed = True, max_time_ms=-1, mouse_speed_mult = 1):
    action_msg = f'action=mouseSetCursorPosSmooth&x={x}&y={y}&mtm={max_time_ms}&msm={mouse_speed_mult}'
    self.sendCommand(command=action_msg, wait_till_recieved=not wait_till_executed)
  def mousePress(self, x=-1,y=-1, button = 'left', wait_till_executed = True):
    action_msg = f'action=mousePress&x={x}&y={y}&button={button}'
    self.sendCommand(command=action_msg, wait_till_recieved=not wait_till_executed)
  def mouseRelease(self,button = 'left', wait_till_executed = True):
    action_msg = f'action=mouseRelease&button={button}'
    self.sendCommand(command=action_msg, wait_till_recieved=not wait_till_executed)

  def pushButton(self, button:str, wait_till_executed = True):
    action_msg = f'action=pushButton&button_code={button}'
    self.sendCommand(command=action_msg, wait_till_recieved=not wait_till_executed)
  def keyboard_pressKey(self, button:str, wait_till_executed = True):
    action_msg = f'action=keyboard_pressKey&button_code={button}'
    self.keyboard.pressed.add(button)
    self.sendCommand(command=action_msg, wait_till_recieved=not wait_till_executed)
  def keyboard_releaseKey(self, button:str, wait_till_executed = True):
    action_msg = f'action=keyboard_releaseKey&button_code={button}'
    if button in self.keyboard.pressed:
      self.keyboard.pressed.remove(button)
    else:
      print(f'[Controller.keyboard_releaseKey] releasing key {button} which is not in list of pressed')
    self.sendCommand(command=action_msg, wait_till_recieved=not wait_till_executed)
  def releaseAll(self, wait_till_executed = True):
    action_msg = f'action=releaseAll'
    self.setReleasedAll()
    self.sendCommand(command=action_msg, wait_till_recieved=not wait_till_executed)
  def restartScript(self, reconnect = True):
    '''
    restarts the script on the remote machine, TODO
    breaks the while loop of recieving on the guest
    '''
    action_msg = f'action=restartScript&'
    print('[Controller] sending reboot to worker')
    self.sendCommand(command=action_msg)
    print('[Controller] sent reboot to worker')
    self.setReleasedAll()
    self.connected = False
    if reconnect != False:
      self.connect()
  def getScreen(self, x1 = None, y1 = None, x2 = None, y2 = None): # TODO x1 x2 y1 y2
    '''
    sends x1 x2 y1 y2
    returns a unpickled numpy array image
    '''
    if x1 is None:
      action_msg = 'action=getFullScreen'
    else:
      action_msg = f'action=getPartialScreen&x1={x1}&y1={y1}&x2={x2}&y2={y2}&'
    img = self.sendCommandToRecieveBytes(command=action_msg)
    if self.debug: print('got screenshot from')
    return img
  def getWindowLoc(self, window_name:str):
    '''
    sends x1 x2 y1 y2
    returns a unpickled numpy array image
    '''
    action_msg = f'action=getWindowLoc&window_name={window_name}&'
    img = self.sendCommandToRecieveBytes(command=action_msg)
    if self.debug: print('[Controller] got screenshot from')
    return img
  def getSortedByHSV(self, x1, y1, x2, y2, h1, s1, v1, h2, s2, v2):
    '''
    accepts x1 x2 y1 y2 h1, s1, v1, h2, s2, v2

    [[x,y], [x,y], [x,y], [x,y], [x,y]]
    returns unpickled #TODO???
    array of points which match the hsv threshhold in x1x2y1y2 
    
    '''
    action_msg = f'action=getSortedByHSV&x1={x1}&y1={y1}&x2={x2}&y2={y2}&h1={h1}&s1={s1}&v1={v1}&h2={h2}&s2={s2}&v2={v2}&'
    img = self.sendCommandToRecieveBytes(command=action_msg)
    if self.debug: print('[Controller] got sorted hsv points')
    return img
  def getClipboardText(self):
    '''
    accepts x1 x2 y1 y2 h1, s1, v1, h2, s2, v2

    [[x,y], [x,y], [x,y], [x,y], [x,y]]
    returns unpickled #TODO???
    array of points which match the hsv threshhold in x1x2y1y2 
    
    '''

    action_msg = f'action=getClipboardText&'
    img = self.sendCommandToRecieveBytes(command=action_msg)
    if self.debug: print('[Controller] got clipboard text')
    return img
  def setClipboardText(self, clipboard_text:str, wait_till_executed:bool = True):
    '''
    accepts x1 x2 y1 y2 h1, s1, v1, h2, s2, v2

    [[x,y], [x,y], [x,y], [x,y], [x,y]]
    returns unpickled #TODO???
    array of points which match the hsv threshhold in x1x2y1y2 
    
    '''
    action_msg = f'action=setClipboardText&clipboard_text={clipboard_text}'
    self.sendCommand(command=action_msg, wait_till_recieved=not wait_till_executed)
  def taskKill(self,task_name):
    self.connect()
    action_msg = f'action=taskKill&task_name={task_name}'
    self.sendCommand(command=action_msg, wait_till_recieved=False)

  def checkProxy(self):
    action_msg = f'action=checkProxy&'
    img = self.sendCommandToRecieveBytes(command=action_msg)
    if self.debug: print('[Controller] checked proxy')
    return img
  def executeCMD(self, task):
    action_msg = f'action=executeCMD&task={task}'
    self.sendCommand(command=action_msg, wait_till_recieved=False)
class Keyboard:
  def __init__(self, controller:VMHostPuppeteer) -> None:
    self.controller = controller
    self.pressed = set()
  def pressAndReleaseThread(self, button, delay, thread_finished, wait_till_recieved):
    self.controller.keyboard_pressKey(button, wait_till_executed=wait_till_recieved)
    time.sleep(delay)
    self.controller.keyboard_releaseKey(button, wait_till_executed=wait_till_recieved)
    thread_finished[0] = True

  def tap(self, button, delay = None, wait_till_executed = True):
    self.pressAndRelease(button, delay = delay, wait_till_executed = wait_till_executed)
  def pressAndRelease(self, button, delay = None, wait_till_executed = True, wait_till_recieved = False):
    if not delay:
      delay = random.randint(7,15)/100
    thread_finished = [False]
    _thread.start_new_thread(self.pressAndReleaseThread, (button, delay, thread_finished, wait_till_recieved))
    while wait_till_executed and thread_finished[0] != True:
      time.sleep(0.02)
class Mouse:
  current_pos_x = 0
  current_pos_y = 0
  pressed = {
    "right": False,
    "left": False,
    "middle": False
  }
  def __init__(self, controller:VMHostPuppeteer) -> None:
    self.controller = controller
  def setReleased(self, key: str = None):
    if key != None:
      self.pressed[key] = False
    else:
      for key in self.pressed.keys():
        self.pressed[key] = False
  def setPos(self, x, y, wait_till_executed = True):
    self.controller.mouseSetCursorPos(x,y,wait_till_executed)
    self.internalAssignCursorPos(x,y)
  def setPosSmooth(self, x, y, wait_till_executed = True, max_time_ms=-1, mouse_speed_mult = 1):
    self.controller.mouseSetCursorPosSmooth(x,y,wait_till_executed=wait_till_executed, max_time_ms=max_time_ms, mouse_speed_mult = mouse_speed_mult)
    self.internalAssignCursorPos(x,y)
  def internalAssignCursorPos(self,x,y):
    self.current_pos_x, self.current_pos_y = x,y
    # print(f'[Controller] current mouse pos {self.current_pos_x, self.current_pos_y}')
  def press(self, x=-1,y=-1, button = 'left', force=False, wait_till_executed = True):
    if x != -1 and y != -1:
      self.internalAssignCursorPos(x,y)
    if self.pressed[button] != True or force == True:
      self.controller.mousePress(x,y,button,wait_till_executed)
      self.pressed[button] = True
    else:
      print(f'[Controller] useless call mouse.press, {button} is already pressed')
      if x == -1 and y == -1:
        print('[Controller] useless -1 -1 set cursor pos')
        return
      self.setPosSmooth(x,y)
  def release(self, button = 'left', wait_till_executed = True):
    self.controller.mouseRelease(button=button, wait_till_executed=wait_till_executed)
    self.pressed[button] = False
  def pressAndReleaseThread(self, button, delay, thread_finished):
    self.press(button=button)
    time.sleep(delay)
    self.release(button)
    thread_finished[0] = True
  def pressAndRelease(self,button = 'left', delay = None, wait_till_executed = True):
    if not delay:
      delay = random.randint(7,15)/100
    thread_finished = [False]
    _thread.start_new_thread(self.pressAndReleaseThread, (button, delay, thread_finished))
    while wait_till_executed and thread_finished[0] != True:
      time.sleep(0.01)
  def click(self, button = "left", delay = None, wait_till_executed = True):
    self.pressAndRelease(button=button, delay = delay, wait_till_executed=wait_till_executed)
  def drag(self, p0, p1):
    '''
    - p0 List[x,y]
    - p1 List[x,y]
    '''
    self.setPosSmooth(p0[0], p0[1])
    time.sleep(random.uniform(0.15, 0.4))
    self.press()
    time.sleep(random.uniform(0.15, 0.4))
    self.setPosSmooth(p1[0], p1[1])
    time.sleep(random.uniform(0.15, 0.4))
    self.release()
    return