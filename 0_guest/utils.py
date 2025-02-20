# util_funcs
import copy
import ctypes
import random
import time
from math import dist

import cv2
import numpy as np
import win32api
import win32con
import win32gui
import win32ui


def accurateSleep(delay_ms):
  target = time.perf_counter_ns() + delay_ms * 1000000
  while time.perf_counter_ns() < target:
    pass


def createLineIterator(P1, P2):
  """
  Produces and array that consists of the coordinates and intensities of each pixel in a line between two points

  Parameters:
      -P1: a numpy array that consists of the coordinate of the first point (x,y)
      -P2: a numpy array that consists of the coordinate of the second point (x,y)
    #   -img: the image being processed

  Returns:
      -it: a numpy array that consists of the coordinates and intensities of each pixel in the radii (shape: [numPixels, 3], row = [x,y,intensity])
  """
  # define local variables for readability
  # imageH = img.shape[0]
  # imageW = img.shape[1]
  P1X = P1[0]
  P1Y = P1[1]
  P2X = P2[0]
  P2Y = P2[1]

  # difference and absolute difference between points
  # used to calculate slope and relative location between points
  dX = P2X - P1X
  dY = P2Y - P1Y
  dXa = np.abs(dX)
  dYa = np.abs(dY)

  # predefine numpy array for output based on distance between points
  # itbuffer = np.empty(shape=(np.maximum(dYa,dXa),3),dtype=np.float32)
  itbuffer = np.empty(shape=(np.maximum(dYa, dXa), 2), dtype=np.float32)  # 2 cos we dont need the result
  itbuffer.fill(np.nan)

  # Obtain coordinates along the line using a form of Bresenham's algorithm
  negY = P1Y > P2Y
  negX = P1X > P2X
  if P1X == P2X:  # vertical line segment
    itbuffer[:, 0] = P1X
    if negY:
      itbuffer[:, 1] = np.arange(P1Y - 1, P1Y - dYa - 1, -1)
    else:
      itbuffer[:, 1] = np.arange(P1Y + 1, P1Y + dYa + 1)
  elif P1Y == P2Y:  # horizontal line segment
    itbuffer[:, 1] = P1Y
    if negX:
      itbuffer[:, 0] = np.arange(P1X - 1, P1X - dXa - 1, -1)
    else:
      itbuffer[:, 0] = np.arange(P1X + 1, P1X + dXa + 1)
  else:  # diagonal line segment
    steepSlope = dYa > dXa
    if steepSlope:
      slope = dX.astype(np.float32) / dY.astype(np.float32)
      if negY:
        itbuffer[:, 1] = np.arange(P1Y - 1, P1Y - dYa - 1, -1)
      else:
        itbuffer[:, 1] = np.arange(P1Y + 1, P1Y + dYa + 1)
      itbuffer[:, 0] = (slope * (itbuffer[:, 1] - P1Y)).astype(int) + P1X
    else:
      slope = dY.astype(np.float32) / dX.astype(np.float32)
      if negX:
        itbuffer[:, 0] = np.arange(P1X - 1, P1X - dXa - 1, -1)
      else:
        itbuffer[:, 0] = np.arange(P1X + 1, P1X + dXa + 1)
      itbuffer[:, 1] = (slope * (itbuffer[:, 0] - P1X)).astype(int) + P1Y

  # Remove points outside of image
  # colX = itbuffer[:,0]
  # colY = itbuffer[:,1]
  # itbuffer = itbuffer[(colX >= 0) & (colY >=0) & (colX<imageW) & (colY<imageH)]

  # Get intensities from img ndarray
  # itbuffer[:,2] = img[itbuffer[:,1].astype(np.uint),itbuffer[:,0].astype(np.uint)]

  return itbuffer


def sortByHSV(img, h1, s1, v1, h2, s2, v2):
  minimap_blurred = cv2.medianBlur(img, 3)
  hsv = cv2.cvtColor(minimap_blurred, cv2.COLOR_BGR2HSV)

  # формируем начальный и конечный цвет фильтра
  h_min = np.array((h1, s1, v1), np.uint8)
  h_max = np.array((h2, s2, v2), np.uint8)

  # накладываем фильтр на кадр в модели HSV
  thresh = cv2.inRange(hsv, h_min, h_max)
  #   kernel = np.ones((5,5),np.uint8)
  #   thresh = cv2.dilate(thresh,kernel,iterations = 2)
  return thresh


# grabScreen
def grabScreen(region=None, convert_colors="BGR"):
  hwin = win32gui.GetDesktopWindow()

  if region:
    left, top, x2, y2 = region
    width = x2 - left + 1
    height = y2 - top + 1
  else:
    width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
    height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
    left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
    top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)

  hwindc = win32gui.GetWindowDC(hwin)
  srcdc = win32ui.CreateDCFromHandle(hwindc)
  memdc = srcdc.CreateCompatibleDC()
  bmp = win32ui.CreateBitmap()
  bmp.CreateCompatibleBitmap(srcdc, width, height)
  memdc.SelectObject(bmp)
  memdc.BitBlt((0, 0), (width, height), srcdc, (left, top), win32con.SRCCOPY)

  signedIntsArray = bmp.GetBitmapBits(True)
  img = np.fromstring(signedIntsArray, dtype="uint8")
  img.shape = (height, width, 4)

  srcdc.DeleteDC()
  memdc.DeleteDC()
  win32gui.ReleaseDC(hwin, hwindc)
  win32gui.DeleteObject(bmp.GetHandle())
  if convert_colors == "RGB":
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
  elif convert_colors == "GRAY":
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
  elif convert_colors == "BGR":
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
  else:
    pass  # NO CONVERT IMAGE IS BGRA
  return img


def generateCurvePath(px: list, py: list, n: int, steps=5000):
  points = []

  def B(coord, i, j, t):
    if j == 0:
      return coord[i]
    return B(coord, i, j - 1, t) * (1 - t) + B(coord, i + 1, j - 1, t) * t

  for k in range(steps):
    t = float(k) / (steps - 1)
    x = int(B(px, 0, n - 1, t))
    y = int(B(py, 0, n - 1, t))
    try:
      points.append([x, y])
    except IndexError:
      pass
  return points


def de_casteljau(control_points, t):
  """Evaluate the Bézier curve at parameter t using De Casteljau's algorithm."""
  n = len(control_points)
  points = np.array(control_points)

  for r in range(1, n):
    for i in range(n - r):
      points[i] = (1 - t) * points[i] + t * points[i + 1]

  return points[0]


def bezier_curve(control_points, num_points=100):
  """Generate points on the Bézier curve."""
  curve = np.array([de_casteljau(control_points, t) for t in np.linspace(0, 1, num_points)])
  return curve


def generatePointOnPath(start, end, arc_multiplier):
  x = end[0] + arc_multiplier * (abs(end[0] - start[0]) + 50) * 0.01 * random.randint(15, 30)
  y = end[1] + arc_multiplier * (abs(end[1] - start[1]) + 50) * 0.01 * random.randint(15, 30)
  return (int(x), int(y))


def generatePointOnPathAlt(start, end, arc_multiplier):
  diff = 50
  x_range = [min([end[0], start[0]]) + diff, max([end[0], start[0]]) - diff]
  y_range = [min([end[1], start[1]]) + diff, max([end[1], start[1]]) - diff]
  print(x_range, y_range)
  x = random.randint(x_range[0], x_range[1])
  y = random.randint(y_range[0], y_range[1])
  return (int(x), int(y))


def Lerp(startValue, endValue, interpolationFactor):
  return (1 - interpolationFactor) * startValue + interpolationFactor * endValue


# direct inputs
# source to this solution and code:
# http://stackoverflow.com/questions/14489013/simulate-python-keypresses-for-controlling-a-game
# http://www.gamespp.com/directx/directInputKeyboardScanCodes.html
# https://pastebin.com/Qy3E0qwj

sleep_time = 0.1


class Controller:
  def __init__(self):
    self.keyboard = Keyboard()
    self.mouse = Mouse()

  def releaseAll(self):
    self.keyboard.releaseAll()
    self.mouse.releaseAll()


class Mouse:
  keymap = {
    "left": 0x01,
    "right": 0x02,
    "middle": 0x04,
  }
  maxInterpolationDistance = 2560
  minInterpolationDelay = 0
  maxInterpolationDelay = 500
  last_cursor_pos = [0, 0]

  def __init__(self) -> None:
    self.pressed = []
    self.getMousePosition()

  def releaseAll(self):
    print("releasing all mouse keys")
    currently_pressed_buttons = set(copy.copy(self.pressed))
    print(f"currently_pressed_buttons {currently_pressed_buttons}")
    cpb = set(currently_pressed_buttons)
    for b in cpb:
      self.release(button=b)

  def getMousePosition(self) -> tuple:
    """
    returns (x,y) of current mouse pos
    """
    self.last_cursor_pos = win32api.GetCursorPos()
    return self.last_cursor_pos

  def setCursorPos(self, x, y, smooth=True, curvy=True):
    """
    accepts x,y and moves the mouse right in the position
    smooth means that itll try to move mouse smoothly, kinda trying to be the same as human like speed rather than machine
    """
    print("moving mouse: ", x, y)
    mouse_move(x, y)
    self.last_cursor_pos = (x, y)
    time.sleep(0.005)
    return

  def setCursorPosSmooth(self, x, y, max_time_ms: int = -1, mouse_speed_mult: int = 1):
    """
    accepts x,y and moves the mouse right in the position
    smooth means that itll try to move mouse smoothly, kinda trying to be the same as human like speed rather than machine
    """
    start = self.last_cursor_pos
    end = (x, y)
    print(f"moving mouse smooth from : {start} to {end} max_time_ms {max_time_ms} at {time.time()}")
    distance = dist(start, end)
    # print(f'distance {distance}')
    if max_time_ms != -1:
      mouse_speed = max_time_ms
    else:
      max_interpolation_delay = self.maxInterpolationDelay
      if mouse_speed_mult != 1:
        max_interpolation_delay = self.maxInterpolationDelay * mouse_speed_mult
      normalized_distance = min([distance / self.maxInterpolationDistance, 1.0])
      # print(f'normalized_distance {normalized_distance}')
      interpolatedValue = Lerp(self.minInterpolationDelay, max_interpolation_delay, normalized_distance)
      # print(f'interpolatedValue {interpolatedValue }')
      mouse_speed = random.randint(25, 50) + interpolatedValue

    # print(f'mouse speed {mouse_speed} at {time.time()}')
    arc_multiplier = random.choice([-1, 1])
    path = [start, generatePointOnPath(start, end, arc_multiplier), generatePointOnPath(start, end, arc_multiplier), end]
    # print(f'path {path} at {time.time()}')

    steps_count = int(dist(start, end) * 1.5 + 2)
    # print(f'steps_count {steps_count} at {time.time()}')

    coord_x = list(map(lambda point: point[0], path))
    coord_y = list(map(lambda point: point[1], path))
    line_points = generateCurvePath(coord_x, coord_y, len(path), steps_count)
    # print(f"generated curve points at {time.time()}")
    # print(f"generated curve points {line_points}")
    prev_point = [-1, -1]
    new_line_points = []
    for point in line_points:
      if point != prev_point:
        new_line_points.append(point)
        prev_point = point
    # print(f"sorted curve points at {time.time()}")
    # print(f"generated curve points {new_line_points}")
    print(f"started moving mouse at {time.time()}")
    points_count = len(new_line_points)
    print(f"points_count {points_count} mouse speed {mouse_speed}")
    delay_per_move = 1
    if mouse_speed < points_count:
      if mouse_speed != 0:
        points_per_move = points_count / mouse_speed
        can_use_points_count = int(points_count / points_per_move) - 1
        new_line_points_indexes = random.choices(list(range(points_count - 1)), k=can_use_points_count)
        new_line_points_indexes.sort()
        randomized_new_line_points = list(map(lambda p_index: new_line_points[p_index], new_line_points_indexes))
        new_line_points = randomized_new_line_points
        new_line_points.append((x, y))
        # print(f'more points than time, points_per_move {points_per_move} {can_use_points_count} {len(new_line_points)}')
      else:
        new_line_points = (x, y)
    else:
      delay_per_move = mouse_speed / points_count
      # print(f'time is more than points {delay_per_move}')
    for point in new_line_points:
      target = time.perf_counter_ns() + delay_per_move * 1000000
      mouse_move(point[0], point[1])
      while time.perf_counter_ns() < target:
        pass

    print(f"finished moving mouse at {time.time()}")
    # print(f"time_arr {time_arr}")

    self.last_cursor_pos = (x, y)
    return

  def press(self, x=None, y=None, button="left"):
    print(f"pressing mouse button {button}")
    if x is None:
      pass
      # x, y = self.last_cursor_pos
    elif x > 0 and y > 0:
      self.setCursorPosSmooth(x, y)
    click_down(button=button)
    self.pressed.append(button)
    return

  def release(self, x=None, y=None, button="left"):
    print(f"releasing mouse button {button}")
    if x is None:
      pass
      # x, y = self.last_cursor_pos
    elif x > 0 and y > 0:
      self.setCursorPosSmooth(x, y)

    click_up(button=button)
    try:
      b_index = self.pressed.index(button)
      self.pressed.pop(b_index)
    except:
      pass
    return

  def click(self, x, y, button="left", delay=True):
    # TODO add slight move!

    if x is None:
      pass
      # x, y = self.last_cursor_pos
    elif x > 0 and y > 0:
      self.setCursorPosSmooth(x, y)

    self.press(button=button)
    time.sleep(random.randint(2, 3) / 100)
    self.release(button=button)


class Keyboard:
  keymap = {
    "DIK_ESCAPE": 0x01,
    "DIK_1": 0x02,
    "DIK_2": 0x03,
    "DIK_3": 0x04,
    "DIK_4": 0x05,
    "DIK_5": 0x06,
    "DIK_6": 0x07,
    "DIK_7": 0x08,
    "DIK_8": 0x09,
    "DIK_9": 0x0A,
    "DIK_0": 0x0B,
    "DIK_MINUS": 0x0C,
    "DIK_EQUALS": 0x0D,
    "DIK_BACK": 0x0E,
    "DIK_TAB": 0x0F,
    "DIK_Q": 0x10,
    "DIK_W": 0x11,
    "DIK_E": 0x12,
    "DIK_R": 0x13,
    "DIK_T": 0x14,
    "DIK_Y": 0x15,
    "DIK_U": 0x16,
    "DIK_I": 0x17,
    "DIK_O": 0x18,
    "DIK_P": 0x19,
    "DIK_LBRACKET": 0x1A,
    "DIK_RBRACKET": 0x1B,
    "DIK_RETURN": 0x1C,
    "DIK_LCONTROL": 0x1D,
    "DIK_A": 0x1E,
    "DIK_S": 0x1F,
    "DIK_D": 0x20,
    "DIK_F": 0x21,
    "DIK_G": 0x22,
    "DIK_H": 0x23,
    "DIK_J": 0x24,
    "DIK_K": 0x25,
    "DIK_L": 0x26,
    "DIK_SEMICOLON": 0x27,
    "DIK_APOSTROPHE": 0x28,
    "DIK_GRAVE": 0x29,
    "DIK_LSHIFT": 0x2A,
    "DIK_BACKSLASH": 0x2B,
    "DIK_Z": 0x2C,
    "DIK_X": 0x2D,
    "DIK_C": 0x2E,
    "DIK_V": 0x2F,
    "DIK_B": 0x30,
    "DIK_N": 0x31,
    "DIK_M": 0x32,
    "DIK_COMMA": 0x33,
    "DIK_PERIOD": 0x34,
    "DIK_SLASH": 0x35,
    "DIK_RSHIFT": 0x36,
    "DIK_MULTIPLY": 0x37,
    "DIK_LMENU": 0x38,
    "DIK_SPACE": 0x39,
    "DIK_CAPITAL": 0x3A,
    "DIK_F1": 0x3B,
    "DIK_F2": 0x3C,
    "DIK_F3": 0x3D,
    "DIK_F4": 0x3E,
    "DIK_F5": 0x3F,
    "DIK_F6": 0x40,
    "DIK_F7": 0x41,
    "DIK_F8": 0x42,
    "DIK_F9": 0x43,
    "DIK_F10": 0x44,
    "DIK_NUMLOCK": 0x45,
    "DIK_SCROLL": 0x46,
    "DIK_NUMPAD7": 0x47,
    "DIK_NUMPAD8": 0x48,
    "DIK_NUMPAD9": 0x49,
    "DIK_SUBTRACT": 0x4A,
    "DIK_NUMPAD4": 0x4B,
    "DIK_NUMPAD5": 0x4C,
    "DIK_NUMPAD6": 0x4D,
    "DIK_ADD": 0x4E,
    "DIK_NUMPAD1": 0x4F,
    "DIK_NUMPAD2": 0x50,
    "DIK_NUMPAD3": 0x51,
    "DIK_NUMPAD0": 0x52,
    "DIK_DECIMAL": 0x53,
    "DIK_OEM_102": 0x56,
    "DIK_F11": 0x57,
    "DIK_F12": 0x58,
    "DIK_F13": 0x64,
    "DIK_F14": 0x65,
    "DIK_F15": 0x66,
    "DIK_KANA": 0x70,
    "DIK_ABNT_C1": 0x73,
    "DIK_CONVERT": 0x79,
    "DIK_NOCONVERT": 0x7B,
    "DIK_YEN": 0x7D,
    "DIK_ABNT_C2": 0x7E,
    "DIK_NUMPADEQUALS": 0x8D,
    "DIK_PREVTRACK": 0x90,
    "DIK_AT": 0x91,
    "DIK_COLON": 0x92,
    "DIK_UNDERLINE": 0x93,
    "DIK_KANJI": 0x94,
    "DIK_STOP": 0x95,
    "DIK_AX": 0x96,
    "DIK_UNLABELED": 0x97,
    "DIK_NEXTTRACK": 0x99,
    "DIK_NUMPADENTER": 0x9C,
    "DIK_RCONTROL": 0x9D,
    "DIK_MUTE": 0xA0,
    "DIK_CALCULATOR": 0xA1,
    "DIK_PLAYPAUSE": 0xA2,
    "DIK_MEDIASTOP": 0xA4,
    "DIK_VOLUMEDOWN": 0xAE,
    "DIK_VOLUMEUP": 0xB0,
    "DIK_WEBHOME": 0xB2,
    "DIK_NUMPADCOMMA": 0xB3,
    "DIK_DIVIDE": 0xB5,
    "DIK_SYSRQ": 0xB7,
    "DIK_RMENU": 0xB8,
    "DIK_PAUSE": 0xC5,
    "DIK_HOME": 0xC7,
    "DIK_UP": 0xC8,
    "DIK_PRIOR": 0xC9,
    "DIK_LEFT": 0xCB,
    "DIK_RIGHT": 0xCD,
    "DIK_END": 0xCF,
    "DIK_DOWN": 0xD0,
    "DIK_NEXT": 0xD1,
    "DIK_INSERT": 0xD2,
    "DIK_DELETE": 0xD3,
    "DIK_LWIN": 0xDB,
    "DIK_RWIN": 0xDC,
    "DIK_APPS": 0xDD,
    "DIK_POWER": 0xDE,
    "DIK_SLEEP": 0xDF,
    "DIK_WAKE": 0xE3,
    "DIK_WEBSEARCH": 0xE5,
    "DIK_WEBFAVORITES": 0xE6,
    "DIK_WEBREFRESH": 0xE7,
    "DIK_WEBSTOP": 0xE8,
    "DIK_WEBFORWARD": 0xE9,
    "DIK_WEBBACK": 0xEA,
    "DIK_MYCOMPUTER": 0xEB,
    "DIK_MAIL": 0xEC,
    "DIK_MEDIASELECT": 0xED,
  }

  def __init__(self) -> None:
    self.pressed = []

  def releaseAll(self):
    currently_pressed_buttons = set(copy.copy(self.pressed))
    for b in currently_pressed_buttons:
      self.releaseKey(b)

  def getValidButtons(self):
    return [button for button in self.keymap.keys()]

  def isValidButton(self, button):
    return button in self.keymap.keys()

  def buttonToKey(self, button):
    return self.keymap[button]

  def tapButton(self, button):
    butt = self.buttonToKey(button)
    pressKey(butt)
    time.sleep(0.007)
    # time.sleep(random.randint(2,4)/100)
    releaseKey(butt)

  def pressKey(self, button):
    butt = self.buttonToKey(button)
    pressKey(butt)

    self.pressed.append(button)

  def releaseKey(self, button):
    butt = self.buttonToKey(button)
    releaseKey(butt)
    try:
      b_index = self.pressed.index(button)
      self.pressed.pop(b_index)
    except:
      pass


SendInput = ctypes.windll.user32.SendInput
# C struct redefinitions
PUL = ctypes.POINTER(ctypes.c_ulong)


class KeyBdInput(ctypes.Structure):
  _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort), ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", PUL)]


class HardwareInput(ctypes.Structure):
  _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_short), ("wParamH", ctypes.c_ushort)]


class MouseInput(ctypes.Structure):
  _fields_ = [
    ("dx", ctypes.c_long),
    ("dy", ctypes.c_long),
    ("mouseData", ctypes.c_ulong),
    ("dwFlags", ctypes.c_ulong),
    ("time", ctypes.c_ulong),
    ("dwExtraInfo", PUL),
  ]


class Input_I(ctypes.Union):
  _fields_ = [("ki", KeyBdInput), ("mi", MouseInput), ("hi", HardwareInput)]


class Input(ctypes.Structure):
  _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]


# Actuals Functions
def pressKey(hexKeyCode):
  extra = ctypes.c_ulong(0)
  ii_ = Input_I()
  ii_.ki = KeyBdInput(0, hexKeyCode, 0x0008, 0, ctypes.pointer(extra))
  x = Input(ctypes.c_ulong(1), ii_)
  ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def releaseKey(hexKeyCode):
  extra = ctypes.c_ulong(0)
  ii_ = Input_I()
  ii_.ki = KeyBdInput(0, hexKeyCode, 0x0008 | 0x0002, 0, ctypes.pointer(extra))
  x = Input(ctypes.c_ulong(1), ii_)
  ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


# https://github.com/SerpentAI/SerpentAI/blob/dev/serpent/input_controllers/native_win32_input_controller.py
mouse_button_down_mapping = {"left": 0x0002, "middle": 0x0020, "right": 0x0008}

mouse_button_up_mapping = {"left": 0x0004, "middle": 0x0040, "right": 0x0010}


def click_down(button="left", **kwargs):
  extra = ctypes.c_ulong(0)
  ii_ = Input_I()
  ii_.mi = MouseInput(0, 0, 0, mouse_button_down_mapping[button], 0, ctypes.pointer(extra))
  x = Input(ctypes.c_ulong(0), ii_)
  ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def click_up(button="left", **kwargs):
  extra = ctypes.c_ulong(0)
  ii_ = Input_I()
  ii_.mi = MouseInput(0, 0, 0, mouse_button_up_mapping[button], 0, ctypes.pointer(extra))
  x = Input(ctypes.c_ulong(0), ii_)
  ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def mouse_move(coord_x, coord_y):
  x, y = _to_windows_coordinates(coord_x, coord_y)
  extra = ctypes.c_ulong(0)
  ii_ = Input_I()
  ii_.mi = MouseInput(x, y, 0, (0x0001 | 0x8000), 0, ctypes.pointer(extra))
  x = Input(ctypes.c_ulong(0), ii_)
  ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def _to_windows_coordinates(x=0, y=0):
  display_width = win32api.GetSystemMetrics(0)
  display_height = win32api.GetSystemMetrics(1)

  windows_x = (x * 65535) // display_width
  windows_y = (y * 65535) // display_height

  return windows_x, windows_y


if __name__ == "__main__":
  for i in range(10):
    print(time.time())
    grabScreen()
    print(time.time())
  # controller = Controller()
  # controller.mouse.setCursorPos(1,1)
  # controller.mouse.click(-1,-1)
