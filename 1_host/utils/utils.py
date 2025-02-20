"""
all the functions which dont require any functions from other libs such as poebot bot controls and so on
"""

import random
from math import atan2, ceil, cos, degrees, radians, sin

import cv2
import numpy as np


def alwaysFalseFunction(*args, **kwargs):
  return False


def alwaysNoneFunction(*args, **kwargs):
  return None


def alwaysTrueFunction(*args, **kwargs):
  return True


def is_cjk(character):
  """ "
  Checks whether character is CJK.

      >>> is_cjk(u'\u33fe')
      True
      >>> is_cjk(u'\ufe5f')
      False

  :param character: The character that needs to be checked.
  :type character: char
  :return: bool
  """
  return any(
    [
      start <= ord(character) <= end
      for start, end in [
        (4352, 4607),
        (11904, 42191),
        (43072, 43135),
        (44032, 55215),
        (63744, 64255),
        (65072, 65103),
        (65381, 65500),
        (131072, 196607),
      ]
    ]
  )


def lineContainsCharacters(line) -> bool:
  for ch in line:
    if is_cjk(ch):
      return True
  return False


def raiseLongSleepException(text):
  print(f"{text} , raiseLongSleepException")
  input("y if run pdb")
  raise Exception(f"{text} , sleep 3600*24")


def getFourPoints(x, y, radius=35):
  """
  five points actually
  [middle, right, left, bot, top]
  """
  arr = []

  arr.append([x, y])
  arr.append([x + radius, y])
  arr.append([x - radius, y])
  arr.append([x, y + radius])
  arr.append([x, y - radius])

  return arr


def createLineIterator(P1, P2, swap_columns=True) -> np.ndarray:
  """
  Produces and array that consists of the coordinates and intensities of each pixel in a line between two points

  Parameters:
      -P1: a numpy array that consists of the coordinate of the first point (x,y)
      -P2: a numpy array that consists of the coordinate of the second point (x,y)
    #   -img: the image being processed

  Returns:
      -it: a numpy array that consists of the coordinates and intensities of each pixel in the radii (shape: [numPixels, 3], row = [x,y,intensity])
  """

  # print(f'#createLineIterator {P1} {P2}')

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
  # swap [[x,y]] to [[y,x]]
  if swap_columns:
    itbuffer[:, 0], itbuffer[:, 1] = itbuffer[:, 1], itbuffer[:, 0].copy()
  itbuffer = itbuffer.astype(int)
  return itbuffer


def createLineIteratorWithValues(P1, P2, img):
  """
  Produces and array that consists of the coordinates and intensities of each pixel in a line between two points
  Parameters:
      -P1: a numpy array that consists of the coordinate of the first point (x,y)
      -P2: a numpy array that consists of the coordinate of the second point (x,y)
      -img: the image being processed
  Returns:
      -it: a numpy array that consists of the coordinates and intensities of each pixel in the radii (shape: [numPixels, 3], row = [x,y,intensity])
  """
  # define local variables for readability
  imageH = img.shape[0]
  imageW = img.shape[1]
  P1 = np.array(P1)
  P2 = np.array(P2)
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
  itbuffer = np.empty(shape=(np.maximum(dYa, dXa), 3), dtype=np.float32)
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
  colX = itbuffer[:, 0]
  colY = itbuffer[:, 1]
  itbuffer = itbuffer[(colX >= 0) & (colY >= 0) & (colX < imageW) & (colY < imageH)]

  # Get intensities from img ndarray
  itbuffer[:, 2] = img[itbuffer[:, 1].astype(int), itbuffer[:, 0].astype(int)]

  return itbuffer


def pointOnCircleByAngleAndLength(angle, length, center=(100, 100)):
  """
  - angle: in rad
  - length: lenth of line
  - center: (x,y) center of the circle
  returns x,y of point
  """
  start_x, start_y = center
  angle = 360 - angle
  x = start_x - int(length * sin(radians(angle)))
  y = start_y - int(length * cos(radians(angle)))
  x, y = ceil(x), ceil(y)
  return x, y


def generateSnakeArray(display=False):
  """
  [[x,y], [x,y], [x,y], [x,y]]
  """
  snake_arr = []

  # x,y
  starting_points = [[0, 0], [11, 0], [0, 4], [11, 4]]
  starting_point = random.choice(starting_points)
  if display:
    print(f"starting point is {starting_point}")

  possible_movement_vectors = ["x", "y"]

  last_value_to_manipulate = "None"
  current_point = {"x": starting_point[0], "y": starting_point[1]}
  snake_arr.append([current_point["x"], current_point["y"]])
  while len(snake_arr) < 60:
    # time.sleep(0.1)
    value_to_manipulate = random.choice(possible_movement_vectors)
    if display:
      print(f"value_to_manipulate {value_to_manipulate}")
    if last_value_to_manipulate == value_to_manipulate:
      next_step = current_point.copy()
      if value_to_manipulate == "y":
        step_vector = "x"
      else:
        step_vector = "y"

      next_step[step_vector] += 1
      can_pass = True
      if next_step["x"] < 0 or next_step["x"] > 11:
        can_pass = False  # cos out of bounds
      if next_step["y"] < 0 or next_step["y"] > 4:
        can_pass = False  # cos out of bounds
      try:
        snake_arr.index([next_step["x"], next_step["y"]])
        can_pass = False  # cos point already exists
      except Exception:
        pass

      if can_pass is True:
        current_point[step_vector] += 1
      else:
        current_point[step_vector] += -1
      snake_arr.append([current_point["x"], current_point["y"]])

    next_step = current_point.copy()
    next_step[value_to_manipulate] += -1
    can_pass = True
    if next_step["x"] < 0 or next_step["x"] > 11:
      can_pass = False  # cos out of bounds
    if next_step["y"] < 0 or next_step["y"] > 4:
      can_pass = False  # cos out of bounds
    try:
      snake_arr.index([next_step["x"], next_step["y"]])
      can_pass = False  # cos point already exists
    except Exception:
      pass

    if can_pass is True:
      step_ = -1  # left or up
    else:
      step_ = 1  # right or down

    for i in range(13):
      next_step = current_point.copy()
      next_step[value_to_manipulate] += step_

      if next_step["x"] < 0 or next_step["x"] > 11:
        break  # cos out of bounds
      if next_step["y"] < 0 or next_step["y"] > 4:
        break  # cos out of bounds

      try:
        snake_arr.index([next_step["x"], next_step["y"]])
        break  # cos point already exists
      except Exception:
        pass
      if display:
        print(current_point)
      current_point[value_to_manipulate] += step_
      snake_arr.append([current_point["x"], current_point["y"]])

    last_value_to_manipulate = value_to_manipulate

  return snake_arr


def cropLine(start, end, borders):
  """
  - start (x,y)
  - end (x,y)
  - borders (x1,x2,y1,y2)
  """
  # print(f'#cropLine {start}, {end}, {borders}')
  points = createLineIterator(np.array(start), np.array(end), swap_columns=False)
  colX = points[:, 0]
  colY = points[:, 1]
  points = points[(colX >= borders[0]) & (colY >= borders[2]) & (colX < borders[1]) & (colY < borders[3])]
  # points[(my_array < 5) | (my_array > 9)]
  # points[(my_array < 5) | (my_array > 9)]
  # i = 0
  # while True:
  #   i += 1
  #   point = points[i]
  #   x = point[0]
  #   y = point[1]
  #   if y < borders[2] or y > borders[3] or x < borders[0] or x > borders[1]:

  #     break
  #   continue
  # return (x,y)
  return points[-1]


def angleOfLine(p1, p2):
  """
  p1: (x,y)

  p2: (x,y)

  315  0   45

  270  p1  90

  225  180 135
  """

  angle = degrees(atan2(-(p2[0] - p1[0]), p2[1] - p1[1]))
  # angle = degrees(atan2(-(p2[1]-p1[1]), p2[0]-p1[0]))
  angle -= 180
  if angle < 0:
    angle += 360.0
  return angle


def getAngle(a, b, c, abs_180=False):
  """b - center"""
  ang = degrees(atan2(c[1] - b[1], c[0] - b[0]) - atan2(a[1] - b[1], a[0] - b[0]))
  # return abs(ang)
  ang = ang + 360 if ang < 0 else ang
  if abs_180 is True:
    if ang > 181:
      ang = 360 - ang
  return ang


def getRandomNumber(avg, diff=0.4) -> float:
  if diff == 0:
    return float(avg)
  min_val_dec_size = 0
  max_val_dec_size = 0

  min_val = avg * (1 - diff)
  max_val = avg * (1 + diff)

  min_val_dec = str(min_val).split(".")
  if len(min_val_dec) != 1:
    min_val_dec_size = len(min_val_dec[1])
  max_val_dec = str(max_val).split(".")
  if len(max_val_dec) != 1:
    max_val_dec_size = len(max_val_dec[1])

  max_dec_size = max([min_val_dec_size, max_val_dec_size])
  if max_dec_size != 0:
    multiplier = 10**max_dec_size
    min_rand_val = int(min_val * multiplier)
    max_rand_val = int(max_val * multiplier)
    return round(random.randint(min_rand_val, max_rand_val) / multiplier, 2)
  else:
    return float(random.randint(min_val, max_val))


def generateSession(total_play_duration_h: int = 12, min_long_sleep_duration_h: int = 8, sessions_count: int = 4):
  session = []

  sessions_left = sessions_count

  play_duration_h = total_play_duration_h
  sleep_duration_h = 24 - play_duration_h
  avg_play_time = round(play_duration_h / sessions_left, 2)
  print(f"[generateSession] avg_play_time {avg_play_time}")
  if not min_long_sleep_duration_h <= 0:
    play_time = getRandomNumber(avg_play_time)
    sleep_time = getRandomNumber(min_long_sleep_duration_h, diff=0.1)
    play_duration_h = round(play_duration_h - play_time, 2)
    sleep_duration_h = round(sleep_duration_h - sleep_time, 2)
    session.append(play_time)
    session.append(sleep_time)
    sessions_left -= 1

  avg_sleep_time = round(sleep_duration_h / sessions_left, 2)
  print(f"[generateSession] avg_sleep_time {avg_sleep_time}")
  for i in range(sessions_left):
    play_time = getRandomNumber(avg_play_time)  # avg 3.4
    sleep_time = getRandomNumber(avg_sleep_time)
    # print(f'[generateSession] play_duration_h {play_duration_h}, play_time {play_time}')
    play_duration_h = round(play_duration_h - play_time, 2)
    sleep_duration_h = round(sleep_duration_h - sleep_time, 2)
    session.append(play_time)
    session.append(sleep_time)

  if play_duration_h != 0:
    # print(f'[generateSession] play_duration_h {play_duration_h}')
    avg_overflow = play_duration_h / sessions_count
    indexes = range(0, len(session), 2)
    for index in indexes:
      session[index] = round(session[index] + avg_overflow, 2)
  if sleep_duration_h != 0:
    # print(f'[generateSession] sleep_duration_h {sleep_duration_h}')
    avg_overflow = sleep_duration_h / sessions_count
    indexes = range(1, len(session), 2)
    for index in indexes:
      session[index] = round(session[index] + avg_overflow, 2)
  print(f"[generateSession] generated session {session}")
  print(f"[generateSession] generated session total_play {sum(session[::2])} total_sleep {sum(session[1::2])}")
  return session


INVENTORY_SLOT_CELL_SIZE = 38


def getInventoryItemCoordinates(x, y, inventory_or_stash="inventory"):
  # 1024x768
  if inventory_or_stash == "inventory":
    x_offset = 562
    y_offset = 417
  elif inventory_or_stash == "stash":
    x_offset = 12
    y_offset = 90
  elif inventory_or_stash == "vendor_buy_window":
    x_offset = 50
    y_offset = 186
  elif inventory_or_stash == "trade_window_give":
    x_offset = 50
    y_offset = 380
  elif inventory_or_stash == "trade_window_take":
    x_offset = 50
    y_offset = 145
  else:
    raise Exception("unknown inventory_or_stash type")
  inventory_item_pos_x = x_offset + x * INVENTORY_SLOT_CELL_SIZE + INVENTORY_SLOT_CELL_SIZE * (random.randint(2, 8) / 10)
  inventory_item_pos_y = y_offset + y * INVENTORY_SLOT_CELL_SIZE + INVENTORY_SLOT_CELL_SIZE * (random.randint(2, 8) / 10)
  return inventory_item_pos_x, inventory_item_pos_y


def sortByHSV(img, h1, s1, v1, h2, s2, v2, blur_lvl=0):
  if blur_lvl > 0:
    minimap_blurred = cv2.medianBlur(img, blur_lvl)
  else:
    minimap_blurred = img
  hsv = cv2.cvtColor(minimap_blurred, cv2.COLOR_BGR2HSV)

  # формируем начальный и конечный цвет фильтра
  h_min = np.array((h1, s1, v1), np.uint8)
  h_max = np.array((h2, s2, v2), np.uint8)

  # накладываем фильтр на кадр в модели HSV
  thresh = cv2.inRange(hsv, h_min, h_max)
  # kernel = np.ones((5,5),np.uint8)
  # thresh = cv2.dilate(thresh,kernel,iterations = 2)
  return thresh


def extendLine(start, end, multiplier):
  """
  accepts:
    -start: [x,y]
    -end: [x,y]
    -multiplier: int
  returns:
    - point [x,y] of the extended line
  """
  point_x = start[0] - ((start[0] - end[0]) * multiplier)
  point_y = start[1] - ((start[1] - end[1]) * multiplier)
  point = [point_x, point_y]
  return point


if __name__ == "__main__":
  img = np.zeros((20, 20), dtype=int)
  vals = createLineIteratorWithValues(np.array([1, 1]), np.array([10, 10]), img)
  # vals[:,2] # to get the values actually

  point = extendLine([100, 100], [200, 200], 1.6)
  pass
