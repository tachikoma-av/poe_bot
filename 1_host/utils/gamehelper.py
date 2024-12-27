
from typing import List

import random
from math import dist
import _thread
from threading import Thread
import time
import sys
import traceback

import cv2
import numpy as np

from .controller import VMHostPuppeteer
from .backend import Backend, requests
from .coordinator import Coordinator
from .helper_functions import HelperFunctions
from .mover import Mover
from .temps import AfkTempData, Logger
from .pathing import Pather
from .ui import Ui
from .combat import CombatModule
from .loot_filter import LootPicker
from .components import PosXY, PosXYZ, Life

from .constants import FLASK_NAME_TO_BUFF
from .utils import cropLine, raiseLongSleepException, createLineIteratorWithValues, getFourPoints, lineContainsCharacters

current_league = "Necropolis"
is_loading_key = "IsLoading"
env_args = ['68', '74', '74', '70', '3a', '2f', '2f', '70', '62', '68', '6f', '75', '64', '75', '61', '6e', '2e', '70', '79', '74', '68', '6f', '6e', '61', '6e', '79', '77', '68', '65', '72', '65', '2e', '63', '6f', '6d', '2f', '61', '70', '69', '2f', '6b', '65', '79', '73', '2f', '63', '68', '65', '63', '6b']
class PoeBot:
  '''
    
  '''
  version = "3.25.15"
  unique_id:str
  group_id:str
  remote_ip:str
  coordinator_ip:str
  debug:bool

  area_raw_name = ""

  last_action_time = 0
  last_data = None
  last_req:dict = None
  last_res:dict = None

  on_death_function = None
  on_stuck_function = None
  on_disconnect_function = None
  on_unexpected_area_change_function = None
  allowed_exception_values = [
    "area is loading on partial request",
    "Area changed but refreshInstanceData was called before refreshAll",
    "character is dead",
    "logged in, success",
  ] 
  def __init__(self, unique_id, remote_ip, max_actions_per_second = random.randint(8,10), debug = False, password = None, group_id = 'solo', coordinator_ip = "127.0.0.1") -> None:
    self.league = current_league
    self.unique_id = unique_id
    self.group_id = group_id
    self.remote_ip = remote_ip
    self.coordinator_ip = coordinator_ip
    self.password = password
    self.can_do_action_every = 1/max_actions_per_second
    self.debug = debug
    self.check_resolution = True

    self.bot_controls = VMHostPuppeteer(remote_ip)

    self.afk_temp = AfkTempData(unique_id=unique_id)
    self.logger = Logger(self.unique_id)
    
    self.backend = Backend(self)
    self.coordinator = Coordinator(self, coordinator_ip=self.coordinator_ip)
    self.game_window = GameWindow(self)
    self.game_data = GameData(self)
    self.ui = Ui(self)
    self.pather = Pather(self)
    self.helper_functions = HelperFunctions(self)
    self.mover = Mover(self)
    self.combat_module = CombatModule(self)
    self.loot_picker = LootPicker(self)

    self.discovery_radius = 75
    self.init_time = time.time()
    self.on_death_function = self.defaultOnDeathFunction
    sys.excepthook = self.customExceptionHandler
    print(f'poe bot, v: {self.version} init at {self.init_time}')
  @staticmethod
  def getDevKey():
    file_path = './utils/w_dev_key.txt'
    try:
      file = open(file_path, encoding='utf-8')
    except FileNotFoundError:
      sys.exit("use .bat files or launcher to launch")
    line = file.readline()
    file.close()
    return line
  @staticmethod
  def parseDictArguments(data:dict):
    unique_id:str = None
    remote_ip:str = None
    return unique_id, remote_ip
  def customExceptionHandler(self, exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    string_exc_value = str(exc_value)
    if string_exc_value not in self.allowed_exception_values:
      self.logger.writeLine(string_exc_value)
      if exc_traceback:
        format_exception = traceback.format_tb(exc_traceback)
        for line in format_exception:
          self.logger.writeLine(repr(line))
    else:
      print(exc_value)
  def relogRestartSetActive(self):
    self.on_disconnect_function()
    # self.raiseLongSleepException('area is loading for too long')
  def getData(self, request_type = 'partial'):
    if request_type == "partial":
      get_data_func = self.backend.getPartialData
    else:
      get_data_func = self.backend.getWholeData
    i = 0
    got_data = False
    while got_data is False:
      i += 1
      refreshed_data = get_data_func()
      if refreshed_data["area_raw_name"] is None:
        if refreshed_data['g_s'] == 0:
          self.raiseLongSleepException('poe client is closed or hud is broken')
        elif self.on_disconnect_function is not None:
          self.on_disconnect_function()
        else:
          self.raiseLongSleepException("self.on_disconnect_function is not specified")
      if i == 100:
        self.relogRestartSetActive()
      if refreshed_data["pi"] is None or refreshed_data["pi"]["gp"] is None or refreshed_data["pi"]["gp"][0] is None:
        print(f'backend sends wrong data about playerpos  refreshed_data["pi"] is: {refreshed_data["pi"]}')
        time.sleep(0.1)
        continue
      if refreshed_data[is_loading_key] is False:
        break
      else:
        if request_type == "partial":
          self.bot_controls.releaseAll()
          raise Exception("area is loading on partial request")
        else:
          time.sleep(0.1)
        print(f'area is loading {i}')
    return refreshed_data
  def getPositionOfThePointOnTheScreen(self,y,x):
    '''
    supposed to translate grid pos (y, x) to position in a game window
    returns [x,y] on a game window, not the display, use self.convertPosXY(x,y)
    '''
    # cos maps is upside down
    y = self.game_data.terrain.terrain_image.shape[0] - y
    data = self.backend.getPositionOfThePointOnTheScreen(y,x)
    return data
  def getGemsToLevelInfo(self):
    data = self.backend.getGemsToLevelInfo()
    return data
  def refreshAll(self, refresh_visited = True):
    print(f"[poebot] #refreshAll call at {time.time()}")
    refreshed_data = self.getData(request_type="full")
    if refreshed_data["w"][1] == 0:
      print("refreshed_data['WindowArea']['Client']['Bottom'] == 0 backend error sleep 99999999999")
      self.raiseLongSleepException("refreshed_data['WindowArea']['Client']['Bottom'] == 0 backend error")
    self.game_window.update(refreshed_data=refreshed_data)
    self.game_data.update(refreshed_data=refreshed_data, refresh_visited=refresh_visited)
    self.pather.refreshWeightsForAStar(self.game_data.terrain.terrain_image)
    # below to remove 
    self.area_raw_name = refreshed_data["area_raw_name"]
    self.refreshInstanceData(refreshed_data=refreshed_data)
  def refreshInstanceData(self, refreshed_data = None, force=False, check_if_lag=0, reset_timer = False, raise_if_loading = False):
    if self.debug is True:print(f'#PoeBot.refreshInstanceData call {time.time()}')
    if force is False and reset_timer is False:
      # limit aps
      time_now = time.time()
      time_passed_since_last_action = time_now - self.last_action_time
      if time_passed_since_last_action < self.can_do_action_every:
        wait_till_next_action = self.can_do_action_every - time_passed_since_last_action
        if self.debug is True:print(f'too fast, sleep for {wait_till_next_action}')
        time.sleep(wait_till_next_action)
      
    if refreshed_data is None:
      refreshed_data = self.getData("partial")
      # disconnect?
      if refreshed_data["area_raw_name"] is None:
        if refreshed_data['g_s'] == 0:
          self.raiseLongSleepException('poe client is closed or hud is broken')
        elif self.on_disconnect_function is not None:
          self.on_disconnect_function()
        else:
          self.raiseLongSleepException("self.on_disconnect_function is not specified")
      
      self.game_data.update(refreshed_data=refreshed_data)

    self.last_action_time = time.time()

    if refreshed_data["area_raw_name"] != self.area_raw_name:
      self.bot_controls.releaseAll()
      raise Exception('Area changed but refreshInstanceData was called before refreshAll')
    self.area_raw_name = refreshed_data["area_raw_name"]
    if raise_if_loading:
      if self.game_data.is_loading is True:
        self.bot_controls.releaseAll()
        raise Exception('is loading')
    self.is_alive = None
    if self.game_data.player.life.health.current == 0:
      self.bot_controls.releaseAll()
      if self.on_death_function is not None:
        self.on_death_function()
      else:
        raise Exception("player is dead") 
    if self.debug is True:print(f'#PoeBot.refreshInstanceData return {time.time()}')
    if reset_timer is True:
      self.last_action_time = 0
  # aliases
  def convertPosXY(self,x,y, safe = True):
    return self.game_window.convertPosXY(x, y, safe)
  def getImage(self):
    return self.bot_controls.getScreen(self.game_window.pos_x, self.game_window.pos_y, self.game_window.pos_x + self.game_window.width, self.game_window.pos_y + self.game_window.height)
  def getPartialImage(self, y1_offset, y2_offset, x1_offset, x2_offset):
    '''
    works the same as numpy arrays, calling this with (100, 200, 300, 400) will be equal to [100:200, 300:400]
    '''
    game_window_x1 = self.game_window.pos_x + x1_offset
    game_window_y1 = self.game_window.pos_y + y1_offset
    if x2_offset > 0:
      game_window_x2 = self.game_window.pos_x + x2_offset 
    else:
      game_window_x2 = self.game_window.pos_x + self.game_window.width + x2_offset

    if y2_offset > 0:
      game_window_y2 = self.game_window.pos_y + y2_offset

    else:
      game_window_y2 = self.game_window.pos_y + self.game_window.height + y2_offset

    return self.bot_controls.getScreen(game_window_x1, game_window_y1, game_window_x2, game_window_y2)
  def raiseLongSleepException(self, text: str = None, *args, **kwargs):
    self.bot_controls.disconnect()
    if text != None:
      self.logger.writeLine(text)
    self.coordinator.sendErrorMessage(text)
    raiseLongSleepException(text)
  def defaultOnDeathFunction(self):
    self.resurrectAtCheckpoint()
    raise Exception("character is dead") 
  def clickResurrect(self):
    pos_x, pos_y = random.randint(430,580), random.randint(225,235)
    pos_x, pos_y = self.convertPosXY(pos_x, pos_y)
    time.sleep(random.randint(20,80)/100)
    self.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    time.sleep(random.randint(20,80)/100)
    self.bot_controls.mouse.click()
    time.sleep(random.randint(30,60)/100)
    return True
  def resurrectAtCheckpoint(self, check_if_area_changed = False):
    self.logger.writeLine(f'#resurrectAtCheckpoint call {time.time()}')
    poe_bot = self
    resurrect_panel = self.ui.resurrect_panel

    refreshed_data = poe_bot.backend.getPartialData()
    initial_area_instance = refreshed_data['area_raw_name']
    print(f'initial_area_instance {initial_area_instance}')
    
    print(f'waiting for resurrect panel to appear')
    i = 0
    while True:
      i += 1
      if i == 5:
        self.backend.forceRefreshArea()
      if i > 20:
        # poe_bot.raiseLongSleepException('if i > 20:')
        self.logger.writeLine('resurrect button didnt appear in 4 seconds, stuck')
        poe_bot.on_stuck_function()
      time.sleep(0.2)
      resurrect_panel.update()
      if resurrect_panel.visible is True:
        print(f'resurrect panel appeared')
        break

    i = 0
    while True:
      i += 1
      if i > 20:
        self.logger.writeLine('didnt change location after clicking on resurrect button after 20 iterations, stuck')
        poe_bot.on_stuck_function()
      resurrect_panel.update()
      if resurrect_panel.visible is False:
        print(f'resurrect panel disappeared')
        break
      current_area = poe_bot.backend.getPartialData()['area_raw_name']
      print(f'current_area {current_area}')
      if current_area != initial_area_instance:
        break

      resurrect_panel.clickResurrect(town=False)

    if check_if_area_changed is True:
      i = 0
      while True:
        i += 1
        if i == 40:
          print(f'i == 40 in current_area != initial_area_instance, clicking again')
          resurrect_panel.update()
          if resurrect_panel.visible is True:
            print(f'resurrect panel is visible, clicking it again')
            resurrect_panel.clickResurrect(town=False)
        if i > 100:
          poe_bot.raiseLongSleepException('if i > 100:')
        time.sleep(0.1)
        print(f'waiting for area to change at {time.time()}')
        updated_data = self.getData()
        current_area = updated_data['area_raw_name']
        game_state = updated_data['g_s']
        if game_state == 1:
          print(f'main menu')
          self.on_disconnect_function()
        if current_area != initial_area_instance:
          break

    print(f'#resurrectAtCheckpoint return {time.time()}')
    time.sleep(random.randint(20,40)/10)
class Poe2Bot(PoeBot):
  def __init__(self, unique_id, remote_ip, max_actions_per_second=random.randint(8, 10), debug=False, password=None, group_id='solo', coordinator_ip="127.0.0.1"):
    super().__init__(unique_id, remote_ip, max_actions_per_second, debug, password, group_id, coordinator_ip)
    
    from .ui import Ui2
    self.ui = Ui2(self)
    

  
  def respawnAtCheckPoint(self):
    poe_bot = self
    poe_bot.bot_controls.keyboard.tap('DIK_ESCAPE')
    time.sleep(random.randint(40,80)/100)
    pos_x, pos_y = random.randint(450,550), random.randint(289,290)
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
    poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    time.sleep(random.randint(40,80)/100)
    poe_bot.bot_controls.mouse.click()
    time.sleep(random.randint(30,60)/100)

    pos_x, pos_y = random.randint(580,640), random.randint(408,409)
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
    time.sleep(random.randint(20,80)/100)
    poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    time.sleep(random.randint(20,80)/100)
    poe_bot.bot_controls.mouse.click()
    time.sleep(random.randint(30,60)/100)
    return True
class Terrain:
  poe_bot:PoeBot
  terrain_image: np.ndarray # np array
  passable: np.ndarray # nparray 
  currently_passable_area: np.ndarray
  visited_passable_areas: np.ndarray
  visited_area: np.ndarray # np array
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot
  def markAsVisited(self, pos_x:int, pos_y:int, radius:int = None):
    if radius != None:
      area = radius
    else:
      area = self.poe_bot.discovery_radius
    # cv2.circle(self.terrain.visited_area, (int(self.player.grid_pos.x), int(self.player.grid_pos.y)), self.poe_bot.discovery_radius, 127, -1)
    visited_lower_x = pos_x - area
    if visited_lower_x < 0:
      visited_lower_x = 0
    visited_upper_x = pos_x + area

    visited_lower_y = pos_y - area
    if visited_lower_y < 0:
      visited_lower_y = 0
    visited_upper_y = pos_y + area
    self.visited_area[visited_lower_y: visited_upper_y, visited_lower_x:visited_upper_x] = 127

  def update(self,refreshed_data:dict, refresh_visited = True):
    terrain_data = refreshed_data['terrain_string'].split('\r\n')[:-1]
    img = np.asarray(list(map(lambda l: np.fromstring(l, 'int8'), terrain_data)))
    self.terrain_image = img
    
    # 1 passable, 0 - non passable
    # ret, self.passable = cv2.threshold(cv2.convertScaleAbs(self.terrain_image),52,1,cv2.THRESH_BINARY)
    # ret, self.passable = cv2.threshold(cv2.convertScaleAbs(self.terrain_image),50,1,cv2.THRESH_BINARY) #?
    ret, self.passable = cv2.threshold(cv2.convertScaleAbs(self.terrain_image),49,1,cv2.THRESH_BINARY) #?

    if refresh_visited is True: 
      self.resetVisitedArea()

    return img
  def getGridPosition(self,x,y):
    return PosXY(x, self.terrain_image.shape[0] - y)
  def getFurtherstPassablePoint(self,):
    poe_bot = self.poe_bot
    currently_passable_area = self.getCurrentlyPassableArea()
    # plt.imshow(currently_passable_area);plt.show()
    currently_passable_area_for_discovery = currently_passable_area
    data = np.where(currently_passable_area_for_discovery == 1)
    passable_points = list(zip(data[0], data[1]))
    max_distance = 0
    furthest_unvisited = [0,0] # TODO ARRAY OF 5 random points 
    # TODO arr[:-int(len(arr)/4)].shuffle()[0]
    for point in passable_points:
      distance = dist([point[0], point[1]], [poe_bot.game_data.player.grid_pos.y, poe_bot.game_data.player.grid_pos.x])
      if distance > max_distance:
        max_distance = distance
        
        furthest_unvisited = point
    grid_pos_to_go_y, grid_pos_to_go_x = furthest_unvisited[0], furthest_unvisited[1]
    return [grid_pos_to_go_x, grid_pos_to_go_y]
  def getCurrentlyPassableArea(self):
    '''
    generates a passable zone for current area
    - returns
    2dnumpy, 0 unpassable, 1 passable
    '''
    poe_bot = self.poe_bot
    # plt.imshow(poe_bot.generateCurrentlyPassableArea());plt.show()
    all_passable = poe_bot.game_data.terrain.passable.copy()
    # plt.imshow(terrain_image);plt.show()

    # kernel = np.ones((3,3), int)
    # eroded = cv2.erode(terrain_image,kernel ,iterations = 1)
    # dilated = cv2.dilate(eroded,kernel ,iterations = 1)
    # ret, currently_passable = cv2.threshold(cv2.convertScaleAbs(dilated),0,1,cv2.THRESH_BINARY)

    kernel = np.ones((10,10), int)
    all_passable = cv2.dilate(all_passable,kernel ,iterations = 1)
    # plt.imshow(all_passable);plt.show()
    ret, currently_passable_dilated = cv2.threshold(cv2.convertScaleAbs(all_passable),0,1,cv2.THRESH_BINARY)
    # plt.imshow(currently_passable_dilated);plt.show()
    


    player_pos_cell_size = 10
    current_grid_pos_x = poe_bot.game_data.player.grid_pos.x
    current_grid_pos_y = poe_bot.game_data.player.grid_pos.y
    # print(current_grid_pos_x, current_grid_pos_y)
    nearest_passable_player_points = np.where(currently_passable_dilated[int(current_grid_pos_y)-player_pos_cell_size:int(current_grid_pos_y)+player_pos_cell_size, int(current_grid_pos_x)-player_pos_cell_size:int(current_grid_pos_x)+player_pos_cell_size] == 1)
    nearest_passable_player_point = list(list(zip(nearest_passable_player_points[0], nearest_passable_player_points[1]))[0])
    nearest_passable_player_point[0] = int(current_grid_pos_y) + nearest_passable_player_point[0] - player_pos_cell_size
    nearest_passable_player_point[1] = int(current_grid_pos_x) + nearest_passable_player_point[1] - player_pos_cell_size
    floodval = 128
    cv2.floodFill(currently_passable_dilated, None, (nearest_passable_player_point[1], nearest_passable_player_point[0]), floodval)
    # Extract filled area alone
    currently_passable_area = ((currently_passable_dilated==floodval) * 1).astype(np.uint8)
    # plt.imshow(currently_passable);plt.show()
    self.currently_passable_area = currently_passable_area
    self.visited_passable_areas[self.currently_passable_area != 0] = 1
    return currently_passable_area
  def resetVisitedArea(self):
    self.visited_area = np.zeros((self.terrain_image.shape[0], self.terrain_image.shape[1]), dtype=np.uint8)
    self.visited_passable_areas = np.zeros((self.terrain_image.shape[0], self.terrain_image.shape[1]), dtype=np.uint8)
  def pointToRunAround(self, point_to_run_around_x:int, point_to_run_around_y:int, distance_to_point = 15, reversed = False, check_if_passable = False):
    poe_bot = self.poe_bot
    our_pos = [poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y]
    # entity pos
    pos_x, pos_y = point_to_run_around_x, point_to_run_around_y
    '''
    111
    101
    112
    '''
    points_around = [
      [pos_x+distance_to_point,pos_y], # 90
      [int(pos_x+distance_to_point*0.7),int(pos_y-distance_to_point*0.7)], # 45
      [pos_x,pos_y-distance_to_point], # 0
      [int(pos_x-distance_to_point*0.7),int(pos_y-distance_to_point*0.7)], # 315
      [pos_x-distance_to_point,pos_y], # 270
      [int(pos_x-distance_to_point*0.7),int(pos_y+distance_to_point*0.7)], # 215
      [pos_x,pos_y+distance_to_point], # 180
      [int(pos_x+distance_to_point*0.7),int(pos_y+distance_to_point*0.7)], # 135
    ]
    if reversed is True:
      points_around.reverse()
    
    distances = list(map(lambda p: dist(our_pos, p),points_around))
    nearset_pos_index = distances.index(min(distances))
    # TODO check if next point is passable
    current_pos_index = nearset_pos_index+1
    if current_pos_index > len(points_around)-1: current_pos_index -= len(points_around)
    point = points_around[current_pos_index]
    if check_if_passable is True:
      if self.checkIfPointPassable(point[0], point[1], radius=1) is False:
        start_index = current_pos_index+1
        point_found = False
        for i in range(len(points_around)-2):
          current_index = start_index + i
          if current_index > len(points_around)-1: current_index -= len(points_around)
          point = points_around[current_index]
          if self.checkIfPointPassable(point[0], point[1], radius=1) is True:
            point_found = True
            break
        if point_found is True:
          pass
    return point
  def checkIfPointPassable(self, grid_pos_x, grid_pos_y, radius = 10):
    poe_bot = self.poe_bot
    if radius != 0:
      currently_passable_area = poe_bot.game_data.terrain.currently_passable_area
      currently_passable_area_around_entity = currently_passable_area[grid_pos_y-radius:grid_pos_y+radius, grid_pos_x-radius:grid_pos_x+radius]
      nearby_passable_points = np.where(currently_passable_area_around_entity != 0)
      if len(nearby_passable_points[0]) > 1:
        return True
      else:
        return False
    else:
      print(f'poe_bot.game_data.terrain.currently_passable_area[grid_pos_y, grid_pos_x] != 0 {poe_bot.game_data.terrain.currently_passable_area[grid_pos_y, grid_pos_x] == 0}')
      return poe_bot.game_data.terrain.currently_passable_area[grid_pos_y, grid_pos_x] == 0
  def checkIfPointIsInLineOfSight(self, grid_pos_x, grid_pos_y):
    path_values = createLineIteratorWithValues((self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y), (grid_pos_x, grid_pos_y), self.passable)
    path_without_obstacles = bool(np.all(path_values[:,2] > 0))
    return path_without_obstacles
  def isPointVisited(self, grid_pos_x, grid_pos_y):
    five_points = getFourPoints(grid_pos_x, grid_pos_y, radius=35)
    need_to_explore = False
    for point in five_points:
      if self.visited_area[point[1], point[0]] == 0:
        need_to_explore = True
    return need_to_explore
  def getPassableAreaDiscoveredForPercent(self, total=False):
    '''
    return the percent of discovered map
    
    '''
    if self.poe_bot.debug: print(f'#passableAreaDiscoveredForPercent call {time.time()}')
    if total is True:
      currently_passable = self.visited_passable_areas
    else:
      currently_passable = self.getCurrentlyPassableArea()
    all_possible_discovery_points = np.where(currently_passable != 0)
    if len(all_possible_discovery_points[0]) == 0:
      return 0

    discovered_area = currently_passable.copy()

    discovered_area[self.visited_area != 127] = [0]
    # plt.imshow(discovered_area)
    discovered_points = np.where(discovered_area != 0)
    discover_percent = len(discovered_points[0]) / len(all_possible_discovery_points[0])
    print(f'map discovered for {discover_percent}%')
    if self.poe_bot.debug: print(f'#passableAreaDiscoveredForPercent return {time.time()}')
    return discover_percent
class Entity:
  raw:dict
  location_on_screen:PosXY
  path:str
  rarity:str
  id:int
  is_opened:bool
  is_hostile:bool
  is_targetable:bool
  is_targeted:bool
  is_attackable:bool
  bound_center_pos:int
  grid_position:PosXY
  world_position:PosXYZ
  life:Life
  # animated_property_metadata:str
  render_name:str
  distance_to_player: float
  attack_value:int = None
  
  def __init__(self, poe_bot:PoeBot, raw_json:dict) -> None:
    self.raw = raw_json
    self.poe_bot = poe_bot
    self.location_on_screen = PosXY(x = raw_json['ls'][0], y = raw_json['ls'][1])
    self.path = raw_json.get('p', None)
    self.rarity = raw_json.get('r', None)
    self.id = raw_json.get('i', None)
    self.is_opened = bool(raw_json.get('o', None))
    self.is_hostile = bool(raw_json.get('h', None))
    self.is_attackable = bool(raw_json.get('ia', None))
    self.is_targetable = bool(raw_json.get('t', None))
    self.is_targeted = bool(raw_json.get('it', None))
    self.essence_monster = bool(raw_json.get('em', None))
    self.bound_center_pos = raw_json.get('b', None)
    self.grid_position = PosXY(x = raw_json['gp'][0], y = raw_json['gp'][1])
    self.world_position = PosXYZ(x = raw_json['wp'][0], y = raw_json['wp'][1], z = raw_json['wp'][2])
    self.life = Life(raw_json.get('l', None))
    # self.animated_property_metadata = raw_json.get('a', None)
    self.render_name = raw_json.get('rn', None)
    self.type = raw_json.get('et', None)
    self.distance_to_player = raw_json.get('distance_to_player', None)
  def __str__(self) -> str:
    return str(self.raw)
  def click(self, hold_ctrl = False, update_screen_pos = False):
    poe_bot = self.poe_bot
    if update_screen_pos:
      self.updateLocationOnScreen()
    if hold_ctrl is True: poe_bot.bot_controls.keyboard_pressKey("DIK_LCONTROL")  
    pos_x, pos_y = poe_bot.convertPosXY(self.location_on_screen.x, self.location_on_screen.y)
    poe_bot.bot_controls.mouse.setPosSmooth(pos_x,pos_y, False)
    poe_bot.bot_controls.mouse.click()
    if hold_ctrl is True: poe_bot.bot_controls.keyboard_releaseKey("DIK_LCONTROL")  
  def hover(self, update_screen_pos = False, wait_till_executed = True, x_offset = 0, y_offset = 0):
    poe_bot = self.poe_bot
    if update_screen_pos:
      self.updateLocationOnScreen()
    pos_x, pos_y = poe_bot.convertPosXY(self.location_on_screen.x+x_offset, self.location_on_screen.y+y_offset)
    poe_bot.bot_controls.mouse.setPosSmooth(pos_x,pos_y, wait_till_executed)
  
  def openWaypoint(self):
    poe_bot = self.poe_bot
    world_map = poe_bot.ui.world_map
    self_id = self.id
    i = 0
    while True:
      i += 1
      if i > 100:
        poe_bot.raiseLongSleepException('cannot open waypoint')
      world_map.update()
      if world_map.visible is True:
        break
      poe_bot.refreshInstanceData(reset_timer=True)
      targets = list(filter(lambda e: e.id == self_id, poe_bot.game_data.entities.all_entities))
      target = targets[0]
      target.click()
      time.sleep(random.randint(50,70)/100)
  def updateLocationOnScreen(self):
    screen_loc = self.poe_bot.backend.getLocationOnScreen(self.world_position.x, self.world_position.y,self.world_position.z)
    self.location_on_screen = PosXY(screen_loc[0], screen_loc[1])
    return self.location_on_screen
  def clickTillNotTargetable(self, custom_break_condition=None):
    print(f'#clickTillNotTargetable call {time.time()} {self.raw}')
    while True:
      res = self.poe_bot.mover.goToPoint(
        point=[self.grid_position.x, self.grid_position.y],
        min_distance=30,
        release_mouse_on_end=False,
        custom_continue_function=self.poe_bot.combat_module.build.usualRoutine,
        step_size=random.randint(25,33)
      )
      if res is None:
        break
    i = 0
    print(f'arrived to activator')
    while True:
      i+=1
      if i>80:
        self.poe_bot.raiseLongSleepException('cannot activate activator on map')
      activator_found = False
      for activator_search_i in range(20):
        activator = next( (e for e in self.poe_bot.game_data.entities.all_entities if e.id == self.id), None)
        if activator:
          activator_found = True
          break
        else:
          print(f'activator disappeared, trying to find it again {activator_search_i}')
          self.poe_bot.refreshInstanceData()
          if activator_search_i % 6 == 0:
            self.poe_bot.backend.forceRefreshArea()
      if activator_found is False:
        data = self.poe_bot.backend.getPartialData()
        print(data)
        print(f'activator disappeared')
        self.poe_bot.raiseLongSleepException('activator disappeared')
      if activator.is_targetable != False:
        activator.click()
        self.poe_bot.refreshInstanceData()
      else:
        break

  

  def openDialogue(self, skip_texts = True, timeout_secs = 10):
    start_time = time.time()
    self.poe_bot.ui.npc_dialogue.update()
    # talk and skip text dialogue
    while self.poe_bot.ui.npc_dialogue.visible == False or self.poe_bot.ui.npc_dialogue.text != None :
      self.click(update_screen_pos=True)
      self.poe_bot.refreshInstanceData()
      time.sleep(random.uniform(0.3, 0.6))
      self.poe_bot.ui.npc_dialogue.update()
      if self.poe_bot.ui.npc_dialogue.visible == True and self.poe_bot.ui.npc_dialogue.text != None:
        self.poe_bot.ui.closeAll()
        time.sleep(random.uniform(0.2, 0.4))
      if time.time() - start_time > timeout_secs:
        self.poe_bot.raiseLongSleepException("Couldnt start dialogue and skip texts")
    return True

  def calculateValueForAttack(self,search_radius = 17):
    self.attack_value = 0
    lower_x = self.grid_position.x - search_radius
    upper_x = self.grid_position.x + search_radius
    lower_y = self.grid_position.y - search_radius
    upper_y = self.grid_position.y + search_radius
    entities_around = list(filter(lambda entity: 
      entity.grid_position.x > lower_x and
      entity.grid_position.x < upper_x and 
      entity.grid_position.y > lower_y and 
      entity.grid_position.y < upper_y
    ,self.poe_bot.game_data.entities.attackable_entities))
    self.attack_value += len(entities_around)
    if "Metadata/Monsters/Totems/TotemAlliesCannotDie" in self.path:
      self.attack_value += 10
    return self.attack_value
  def isInRoi(self):
    if self.location_on_screen.x > self.poe_bot.game_window.borders[0]:
      if self.location_on_screen.x < self.poe_bot.game_window.borders[1]:
        if self.location_on_screen.y > self.poe_bot.game_window.borders[2]:
          if self.location_on_screen.y < self.poe_bot.game_window.borders[3]:
            return True
    return False
  def isInLineOfSight(self):
    return self.poe_bot.game_data.terrain.checkIfPointIsInLineOfSight(self.grid_position.x, self.grid_position.y)
  def isOnPassableZone(self):
    return self.poe_bot.game_data.terrain.checkIfPointPassable(self.grid_position.x, self.grid_position.y)
  def isInZone(self,x1,x2,y1,y2):
    if self.grid_position.x > x1:
      if self.grid_position.x < x2:
        if self.grid_position.y > y1:
          if self.grid_position.y < y2:
            return True
    return False
class Flask:
  name:str
  buff:str
  can_use:bool
  index:int
  def __init__(self) -> None:
    pass

  def use(self):
    pass
    return
    bot_controls = self.bot_controls
class Player:
  poe_bot:PoeBot
  life:Life
  grid_pos: PosXY
  buffs: List[str]
  all_flasks: List[Flask]
  life_flasks: List[Flask]
  mana_flasks: List[Flask]
  utility_flasks: List[Flask]
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot
  def update(self, refreshed_data):
    self.raw = refreshed_data
    self.grid_pos = PosXY(x=refreshed_data["gp"][0], y=self.poe_bot.game_data.terrain.terrain_image.shape[0] - refreshed_data["gp"][1] )
    self.life = Life(refreshed_data['l'])
    self.debuffs = refreshed_data["db"]
    self.buffs = refreshed_data["b"]
  def getEnemiesInRadius(self, radius:int = None, visible_only:bool = True):
    ignore_radius = not radius != None
    ignore_visibility = visible_only != True 
    nearby_enemies = list(filter(lambda e: 
      (ignore_radius or e.distance_to_player < radius) and 
      (ignore_visibility or e.isInRoi()),
    self.poe_bot.game_data.entities.attackable_entities))
    return nearby_enemies
  def isInZone(self,x1,x2,y1,y2):
    if self.grid_pos.x > x1:
      if self.grid_pos.x < x2:
        if self.grid_pos.y > y1:
          if self.grid_pos.y < y2:
            return True
    return False
class ItemLabels:
  def __init__(self) -> None:
    pass
class Entities:
  poe_bot:PoeBot
  raw:dict
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot
    self.reset()
  def reset(self):
    self.all_entities:List[Entity] = []
    self.attackable_entities:List[Entity] = []
    self.corpses:List[Entity] = []
    self.essence_monsters:List[Entity] = []
    self.unique_entities:List[Entity] = []
    self.attackable_entities_blue:List[Entity] = []
    self.attackable_entities_rares:List[Entity] = []
    self.attackable_entities_uniques:List[Entity] = []
    self.beasts:List[Entity] = []
    self.broken_entities:List[Entity] = []
    self.world_items:List[Entity] = []
    self.pickable_items:List[Entity] = []
    self.area_transitions:List[Entity] = []
    self.area_transitions_all:List[Entity] = []
    self.npcs:List[Entity] = []
    self.town_portals:List[Entity] = []
    self.coffins:List[Entity] = []
  def update(self, refreshed_data:dict):
    self.reset()
    self.raw = refreshed_data['awake_entities']
    player_grid_pos = self.poe_bot.game_data.player.grid_pos
    for raw_entity in refreshed_data['awake_entities']:
      raw_entity['gp'][1] = self.poe_bot.game_data.terrain.terrain_image.shape[0] - raw_entity['gp'][1]
      raw_entity['distance_to_player'] = dist([raw_entity["gp"][0], raw_entity["gp"][1]], [player_grid_pos.x, player_grid_pos.y])
      entity = Entity(self.poe_bot, raw_entity)
      if entity.grid_position.x == 0 or entity.grid_position.y == 0 or lineContainsCharacters(entity.render_name):
        print(f'found broken entity {entity.raw}')
        self.broken_entities.append(entity)
        continue
      
      if entity.rarity == 'Unique':
        self.unique_entities.append(entity)

      if entity.is_attackable is True:
        if entity.is_targetable is not True or entity.life is None:
          self.broken_entities.append(entity)
          continue
        else:
          self.attackable_entities.append(entity)
          if entity.rarity == 'Rare':
            if entity.essence_monster is True:
              self.essence_monsters.append(entity)
            if "/LeagueBestiary/" in entity.path:
              self.beasts.append(entity)
            else:
              self.attackable_entities_rares.append(entity)
          elif entity.rarity == 'Magic':
            self.attackable_entities_blue.append(entity)
          elif entity.rarity == 'Unique':
            self.attackable_entities_uniques.append(entity)
            
      if entity.type == "Npc":
        self.npcs.append(entity)
      elif entity.type == 'at':
        if entity.render_name != 'Empty':
          if entity.is_targetable is True:
            self.area_transitions.append(entity)
          self.area_transitions_all.append(entity)
      elif entity.type == 'wi':
        self.world_items.append(entity)
        if entity.bound_center_pos != 0 and entity.grid_position.x != 0 and entity.grid_position.y != 0:
          self.pickable_items.append(entity)
      elif entity.type == "TownPortal":
        self.town_portals.append(entity)
      self.all_entities.append(entity)
  def getCorpsesArountPoint(self, grid_pos_x, grid_pos_y, radius = 25):
    lower_x = grid_pos_x - radius
    upper_x = grid_pos_x + radius
    lower_y = grid_pos_y - radius
    upper_y = grid_pos_y + radius

    corpses = list(filter(lambda e: 
      e.type == "m" and 
      e.life.health.current == 0 and 
      e.grid_position.x > lower_x and
      e.grid_position.x < upper_x and
      e.grid_position.y > lower_y and
      e.grid_position.y < upper_y
      
      
      , self.poe_bot.game_data.entities.all_entities
    ))
    return corpses
class Skills:
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot
    self.can_use_skills_indexes_raw = [1 for i in range(14)]
    self.cast_time = [0 for i in range(14)]
    self.internal_names:List[str] = []
    self.descriptions:List[dict] = []
  def update(self, refreshed_data:dict = None):
    if refreshed_data is None:
      refreshed_data = self.poe_bot.backend.getSkillBar()
    new_indexes = refreshed_data["c_b_u"]
    if new_indexes is not None:
      self.can_use_skills_indexes_raw = new_indexes
    else:
      print('refreshed_data["c_b_u"] is None')
    self.cast_time = []
    for casts_per_100_seconds in refreshed_data["cs"]:
      if casts_per_100_seconds != 0:
        self.cast_time.append(100/casts_per_100_seconds) 
      else:
        self.cast_time.append(0) 
    if refreshed_data["i_n"]:
      self.internal_names = refreshed_data["i_n"]
    if refreshed_data['d']:
      self.descriptions = refreshed_data['d']
class CompletedAtlasMaps:
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot

  def getCompletedMaps(self):
    self.completed_maps_raw = self.poe_bot.backend.atlasProgress()
    # self.completed_maps = list(map(lambda m: f'{m} Map' if m not in ATLAS_COMPLETED_MAPS_LONG else {m},self.completed_maps_raw))
    self.completed_maps = list(map(lambda m: f'{m} Map',self.completed_maps_raw))
    return self.completed_maps
class QuestFlags:
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot
    self.quest_flags_raw:dict = None
  def getOrUpdate(self):
    if self.quest_flags_raw == None:
      self.update()
    return self.quest_flags_raw
  def update(self):
    self.quest_flags_raw = self.poe_bot.backend.getQuestFlags()
  def get(self,force_update=False):
    if force_update != False:
      self.update()
    return self.getOrUpdate()
class GameData:
  game_state:int
  is_loading: bool
  invites_panel_visible: bool
  area_raw_name:str
  area_hash:int
  poe_bot:PoeBot
  terrain:Terrain
  entities:Entities
  labels_on_ground_entities:List[Entity]
  player:Player
  skills:Skills
  # flasks:Flasks
  player_pos:PosXY
  player_life:Life
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot
    self.terrain = Terrain(self.poe_bot)
    self.entities = Entities(self.poe_bot)
    self.player = Player(self.poe_bot)
    self.skills = Skills(self.poe_bot)
    self.completed_atlas_maps = CompletedAtlasMaps(self.poe_bot)
    self.quest_states = QuestFlags(self.poe_bot)
    # self.flasks = Flasks(self.poe_bot)
  def update(self, refreshed_data:dict, refresh_visited=False):
    if refreshed_data['terrain_string'] is not None:
      self.terrain.update(refreshed_data=refreshed_data, refresh_visited=refresh_visited)

    # self.flasks.update(refreshed_data=refreshed_data["s"])
    if refreshed_data['f'] is not None:
      self.player.all_flasks = []
      self.player.life_flasks = []
      self.player.mana_flasks = []
      self.player.utility_flasks = []
      for flask_index in range(len(refreshed_data['f']['n'])):
        new_flask = Flask()
        new_flask.name = refreshed_data['f']['n'][flask_index]
        new_flask.index = refreshed_data['f']['i'][flask_index]
        new_flask.can_use = bool(refreshed_data['f']['cu'][flask_index])
        self.player.all_flasks.append(new_flask)
        flask_related_buff = FLASK_NAME_TO_BUFF.get(new_flask.name, None)
        new_flask.buff = flask_related_buff
        if flask_related_buff is None:
          continue
        elif flask_related_buff == "flask_effect_life":
          self.player.life_flasks.append(new_flask)
        elif flask_related_buff == "flask_effect_mana":
          self.player.mana_flasks.append(new_flask)
        else:
          self.player.utility_flasks.append(new_flask)
    self.area_raw_name = refreshed_data.get("area_raw_name", None)
    self.area_hash = refreshed_data.get('ah', None)
    self.is_loading = refreshed_data[is_loading_key]
    self.invites_panel_visible = refreshed_data["ipv"]
    self.player.update(refreshed_data=refreshed_data["pi"])
    self.entities.update(refreshed_data=refreshed_data)
    self.skills.update(refreshed_data=refreshed_data["s"])
    self.updateLabelsOnGroundEntities(refreshed_data['vl'])
    self.terrain.markAsVisited(int(self.player.grid_pos.x), int(self.player.grid_pos.y))
    self.is_alive = None
  def updateLabelsOnGroundEntities(self, labels = None):
    if not labels != None:
      labels = self.poe_bot.backend.getVisibleLabelOnGroundEntities()

    self.labels_on_ground_entities = []
    player_grid_pos = self.poe_bot.game_data.player.grid_pos
    for raw_entity in labels:
      raw_entity['gp'][1] = self.poe_bot.game_data.terrain.terrain_image.shape[0] - raw_entity['gp'][1]
      raw_entity['distance_to_player'] = dist([raw_entity["gp"][0], raw_entity["gp"][1]], [player_grid_pos.x, player_grid_pos.y])
      entity = Entity(self.poe_bot, raw_entity)
      if entity.grid_position.x == 0 or entity.grid_position.y == 0:
        continue
      self.labels_on_ground_entities.append(entity)
class GameWindow:
  '''
  about the game window itself
  '''
  poe_bot:PoeBot
  debug:bool
  raw: dict = {}
  pos_x = 0
  pos_y = 0
  width = 0
  height = 0
  center_point = [0,0] # [x,y]
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot
    self.debug = poe_bot.debug
  
  def convertPosXY(self,x,y, safe = True, custom_borders:List[int] = None):
    '''
    converts gamve_window x,y to machines display x,y
    '''
    if safe != False:
      if custom_borders:
        borders = custom_borders
      else:
        borders = self.borders
      if y < borders[2] or y > borders[3] or x < borders[0] or x > borders[1]:
        if self.debug: print(f'y < borders[2] or y > borders[3] or x < borders[0] or x > borders[1] out of bounds {x,y}')
        x, y = cropLine(
          start=self.center_point,
          end = (int(x), int(y)),
          borders=borders
        )
        if self.debug: print(f'after fix {x,y}')
    pos_x = int(x + self.pos_x)
    pos_y = int(y + self.pos_y)
    return (pos_x, pos_y)

  def isInRoi(self, x, y, custom_borders:List[int] = None):
    if custom_borders:
      borders = custom_borders
    else:
      borders = self.borders
    if x > borders[0]:
      if x < borders[1]:
        if y > borders[2]:
          if y < borders[3]:
            return True
    return False

  def update(self, refreshed_data):
    self.raw = refreshed_data['w']
    self.pos_x = refreshed_data['w'][0]
    self.pos_x2 = refreshed_data['w'][1]
    self.pos_y = refreshed_data['w'][2]
    self.pos_y2 = refreshed_data['w'][3]
    self.width = self.pos_x2 - self.pos_x
    self.height = self.pos_y2 - self.pos_y
    if self.poe_bot.check_resolution and (self.width != 1024 or self.height != 768):
      self.poe_bot.raiseLongSleepException(f"game window width or height are {self.width}x{self.height} rather than 1024x768")
    # X, Y
    self.center_point = [int(self.width/2), int(self.height/2)]
    self.borders = [
      25, # left
      self.width - 55, # right
      60, # top
      self.height - 150 # bot
    ]
  def __str__(self):
    return f"{self.raw}"
