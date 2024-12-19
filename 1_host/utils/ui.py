from __future__ import annotations
import typing
if typing.TYPE_CHECKING:
  from .gamehelper import PoeBot, Poe2Bot

from typing import List

import time
import random
from math import ceil, dist

from .components import PosXY, Posx1x2y1y2, PoeBotComponent, UiElement
from .temps import StashTempData
from .constants import ULTIMATUM_MODS_SAFE_KEYS, ULTIMATUM_MODS_RUIN_KEYS, HIDEOUT_ALVA_METADATA_KEY, MAP_DEVICE_SLOTS
from .utils import sortByHSV, getInventoryItemCoordinates, INVENTORY_SLOT_CELL_SIZE

INVENTORY_SLOT_CELL_SIZE_MIN = INVENTORY_SLOT_CELL_SIZE * 0.1
class Item:
  raw:dict
  grid_position:Posx1x2y1y2
  screen_position:Posx1x2y1y2
  clipboard_text:str
  source:str # "inventory" "stash"
  map_type: str# white, yellow,red
  item_mods_raw: List[str]
  def __init__(self, poe_bot:PoeBot, item_raw:dict) -> None:
    self.poe_bot = poe_bot
    self.raw = item_raw
    self.render_path:str = item_raw["a"]
    self.render_art:str = item_raw["RenderArt"]
    self.name:str = item_raw["Name"]
    self.unique_name:str = item_raw["unique_name"]
    self.rarity:str = item_raw["rarity"]
    self.items_in_stack:int = item_raw["items_in_stack"]
    self.item_mods:List[str] = item_raw["item_mods"]
    self.item_mods_raw:List[str] = item_raw.get('imr', [])
    self.identified:bool = bool(item_raw["i"])
    self.corrupted:bool = bool(item_raw["c"])
    self.map_tier:int = item_raw["m_t"]
    if self.map_tier != 0:
      if self.map_tier < 6:
        self.map_type = 'white'
      elif self.map_tier < 11:
        self.map_type = 'yellow'
      else:
        self.map_type = 'red'
    links:List[str] = item_raw.get('l', None)
    sockets:str = None
    if links:
      sockets = "".join(links)
    self.links = links
    self.sockets = sockets
    if item_raw['s'] != None:
      self.screen_position = Posx1x2y1y2(*item_raw['s'])
  def getScreenPos(self):
    pos_x, pos_y = random.randint(ceil(self.screen_position.x1+INVENTORY_SLOT_CELL_SIZE_MIN), ceil(self.screen_position.x2-INVENTORY_SLOT_CELL_SIZE_MIN)), random.randint(ceil(self.screen_position.y1+INVENTORY_SLOT_CELL_SIZE_MIN), ceil(self.screen_position.y2-INVENTORY_SLOT_CELL_SIZE_MIN))
    return pos_x, pos_y
  def hover(self, mouse_speed_mult = 1):
    bot_controls = self.poe_bot.bot_controls
    pos_x, pos_y = self.getScreenPos()
    screen_pos_x, screen_pos_y = self.poe_bot.convertPosXY(pos_x, pos_y, safe=False)
    bot_controls.mouse.setPosSmooth(int(screen_pos_x),int(screen_pos_y), mouse_speed_mult=mouse_speed_mult)
    return True
  def click(self, hold_ctrl = False, hold_shift=False, can_click_multiple_times = 0, button="left", hover = True, mouse_speed_mult = 1):
    bot_controls = self.poe_bot.bot_controls
    if hold_ctrl is True: bot_controls.keyboard_pressKey("DIK_LCONTROL")
    if hold_shift is True: bot_controls.keyboard_pressKey("DIK_LSHIFT")
    if hover is True:
      self.hover(mouse_speed_mult = mouse_speed_mult)
      time.sleep(random.randint(10,25)/100)
    iterations = 1
    for i in range(can_click_multiple_times):
      if random.randint(1,10) == 1:
        iterations += 1
    for i in range(iterations):
      bot_controls.mouse.press(button=button)
      if random.randint(0,2) != 0:
        self.hover()
      bot_controls.mouse.release(button=button)
    if hold_ctrl is True or hold_shift is True:
      time.sleep(random.randint(5,7)/100)
    if hold_ctrl is True: bot_controls.keyboard_releaseKey("DIK_LCONTROL")
    if hold_shift is True: bot_controls.keyboard_releaseKey("DIK_LSHIFT")
  def __str__(self) -> str:
    return str(self.raw)
  def getType(self):
    if self.map_tier != 0 and self.map_tier != 17:
      return 'map'
    return None
class StashItem(Item):
  def __init__(self, poe_bot: PoeBot, item_raw: dict, tab_index:int = None) -> None:
    super().__init__(poe_bot, item_raw)
    self.source = "stash"
    if tab_index is not None:
      self.tab_index = tab_index
    else:
      self.tab_index:int = item_raw['tab_index']

    # get from backend
    # get from backend
    # get from backend
    try:
      assignStashItemPositions(item_raw)
      self.grid_position = Posx1x2y1y2(item_raw["LocationTopLeft"]["X"], item_raw["LocationBottomRight"]["X"], item_raw["LocationTopLeft"]["Y"], item_raw["LocationBottomRight"]["Y"] )
      x1 = item_raw["TopLeft"]["X"] + INVENTORY_SLOT_CELL_SIZE_MIN
      x2 = item_raw["BottomRight"]["X"] - INVENTORY_SLOT_CELL_SIZE_MIN
      y1 = item_raw["TopLeft"]["Y"] + INVENTORY_SLOT_CELL_SIZE_MIN
      y2 = item_raw["BottomRight"]["Y"] - INVENTORY_SLOT_CELL_SIZE_MIN
      self.screen_position = Posx1x2y1y2(x1,x2,y1,y2)
    except Exception:
      pass
class InventoryItem(Item):
  def __init__(self, poe_bot: PoeBot, item_raw: dict) -> None:
    super().__init__(poe_bot, item_raw)
    self.source = "inventory"
    self.grid_position = Posx1x2y1y2(*item_raw["g"])
    if item_raw['s'][0] == 0:
      x_offset = 562
      y_offset = 417
      x1 = x_offset + self.grid_position.x1 * INVENTORY_SLOT_CELL_SIZE + INVENTORY_SLOT_CELL_SIZE_MIN
      x2 = x_offset + self.grid_position.x2 * INVENTORY_SLOT_CELL_SIZE - INVENTORY_SLOT_CELL_SIZE_MIN
      y1 = y_offset + self.grid_position.y1 * INVENTORY_SLOT_CELL_SIZE + INVENTORY_SLOT_CELL_SIZE_MIN
      y2 = y_offset + self.grid_position.y2 * INVENTORY_SLOT_CELL_SIZE - INVENTORY_SLOT_CELL_SIZE_MIN
      self.screen_position = Posx1x2y1y2(x1,x2,y1,y2)
    else:  
      self.screen_position = Posx1x2y1y2(*item_raw["s"])
  def getItemClipboardText(self):
    self.hover()
class MapDeviceItem(Item):
  def __init__(self, poe_bot: PoeBot, item_raw: dict) -> None:
    super().__init__(poe_bot, item_raw)
    self.screen_position = Posx1x2y1y2(*item_raw['s'])
class KirakMissionItem(Item):
  def __init__(self, poe_bot: PoeBot, item_raw: dict) -> None:
    super().__init__(poe_bot, item_raw)
    self.tab_index:int = item_raw["ti"]
    self.screen_position = Posx1x2y1y2(*item_raw['s'])
  def click(self, hold_ctrl=False, hold_shift=False, can_click_multiple_times=0, mouse_speed_mult = 2):
    self.poe_bot.ui.kirak_missions.switchTabIndex(self.tab_index)
    return super().click(hold_ctrl, hold_shift, can_click_multiple_times, mouse_speed_mult = mouse_speed_mult)
class PurchaseWindowItem(Item):
  def __init__(self, poe_bot: PoeBot, item_raw: dict) -> None:
    super().__init__(poe_bot, item_raw)
    self.screen_position = Posx1x2y1y2(*item_raw['s'])
class TabSwitchButton:
  pass
class Ui:
  poe_bot:PoeBot
  inventory:Inventory
  stash:Stash
  map_device:MapDevice
  trade_window:TradeWindow
  last_clicked_ui_element_pos = [0,0] # [x,y]
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot
    self.inventory = Inventory(poe_bot=poe_bot)
    self.stash = Stash(poe_bot=poe_bot)
    self.trade_window = TradeWindow(poe_bot=poe_bot)
    self.map_device = MapDevice(poe_bot=poe_bot)
    self.world_map = WorldMap(poe_bot=poe_bot)
    self.npc_dialogue = NpcDialogueUi(poe_bot=poe_bot)
    self.resurrect_panel = ResurrectPanel(poe_bot=poe_bot)
    self.kirak_missions = KirakMissions(poe_bot=poe_bot)
    self.purchase_window_hideout = PurchaseWindowHideout(poe_bot=poe_bot)
    self.bandit_dialogue = BanditDialogue(poe_bot=poe_bot)
    self.ultimatum_next_wave_ui = UltimatumNextWaveUi(poe_bot=poe_bot)
    self.ultimatum_initiator_ui = UltimatumInitiatorUi(poe_bot=poe_bot)
    self.incursion_ui = IncursionUi(poe_bot=poe_bot)
    self.escape_control_panel = EscapeControlPanel(poe_bot=poe_bot)
  def closeAll(self):
    bot_controls = self.poe_bot.bot_controls
    self.stash.is_opened = False
    self.inventory.is_opened = False
    self.incursion_ui.visible = False
    bot_controls.keyboard.tap('DIK_SPACE')
    time.sleep(random.randint(5,20)/100)
  def update(self, refreshed_data = None):
    if refreshed_data is None:
      refreshed_data = self.poe_bot.backend.getWorldMapUi()
  def clickMultipleItems(self, items_to_click:List[Item], hold_ctrl=True, add_delay_before_last_clicks = True, skip_items = True, shuffle_items = True, random_sleep = True, mouse_speed_mult = 2):
    bot_controls = self.poe_bot.bot_controls
    print(f'[ui, ] click multiple call at {time.time()}')
    if len(items_to_click) == 0:
      return
    items = items_to_click.copy()
    if hold_ctrl is True:bot_controls.keyboard_pressKey('DIK_LCONTROL')
    if shuffle_items:
      items = items_to_click.copy()
      shuffle_by_x_axis = random.choice([True, False])

      x_axis_reverse = bool(random.randint(0,1))
      y_axis_reverse = bool(random.randint(0,1))
      def sortByXAxis():
        if x_axis_reverse:
          items.sort(key=lambda item: item.screen_position.x2, reverse=x_axis_reverse )
        else:
          items.sort(key=lambda item: item.screen_position.x1, reverse=x_axis_reverse )
      def sortByYAxis():
        if y_axis_reverse:
          items.sort(key=lambda item: item.screen_position.y2, reverse=y_axis_reverse )
        else:
          items.sort(key=lambda item: item.screen_position.y1, reverse=y_axis_reverse )
      if shuffle_by_x_axis != False:
        sortByYAxis()
        sortByXAxis()
      else:
        sortByXAxis()
        sortByYAxis()
      temp_arr = []
      def getItemVal(item:Item):
        val = 0
        if shuffle_by_x_axis != False:
          if x_axis_reverse:
            val = item.screen_position.x2
          else:
            val = item.screen_position.x1
        else:
          if y_axis_reverse:
            val = item.screen_position.y2
          else:
            val = item.screen_position.y1
        return val
      prev_val = getItemVal(items[0])
      direction_reversed = bool(random.choice([1, 0]))
      shuffled_items = []
      while len(items) != 0:
        item = items.pop(0)
        val = getItemVal(item)
        if val != prev_val:
          direction_reversed = not direction_reversed
          prev_val = val
          if direction_reversed:
            temp_arr.reverse()
          shuffled_items.extend(temp_arr)
          temp_arr = []
        temp_arr.append(item)
      direction_reversed = not direction_reversed
      prev_val = val
      if direction_reversed:
        temp_arr.reverse()
      shuffled_items.extend(temp_arr)
      items = shuffled_items



      # to_exec = [
      #   lambda: items.sort(key=lambda item: item.screen_position.x1, reverse=bool(random.randint(0,1)) ),
      #   lambda: items.sort(key=lambda item: item.screen_position.y1, reverse=bool(random.randint(0,1)) )
      # ] 
      # random.shuffle(to_exec)
      # for exec in to_exec:
      #   exec()
      # 

    
    items_indexes = [i for i in range(len(items))]
    if skip_items:
      max_skip_items = int(len(items)/10)
      min_skip_items = 1
      if max_skip_items == 0:
        min_skip_items = 0
      items_to_skip_indexes = random.choices(items_indexes, k = random.randint(min_skip_items,max_skip_items)) 
    else:
      items_to_skip_indexes = []
    for item_index in items_indexes:
      item = items[item_index]
      if item_index in items_to_skip_indexes:
        item.hover(mouse_speed_mult=mouse_speed_mult)        
        continue
      item_screen_pos = item.getScreenPos()
      distance_to_item = dist(self.poe_bot.ui.last_clicked_ui_element_pos, item_screen_pos)
      cells_to_item = distance_to_item / INVENTORY_SLOT_CELL_SIZE
      time.sleep(random.randint(5,10)*0.01*cells_to_item)
      item.click(can_click_multiple_times=3, mouse_speed_mult = mouse_speed_mult)
      if random_sleep is True:
        sleep_time = 0
        sleep_time += self.poe_bot.afk_temp.performShortSleep(return_sleep_val=True)
        print(f'[ui, click multiple] sleep_time {sleep_time}')
        if sleep_time != 0:
          if hold_ctrl: 
            time.sleep(random.randint(1,5)/100)
            self.poe_bot.bot_controls.keyboard_releaseKey('DIK_LCONTROL')
            time.sleep(random.randint(1,5)/100)
          time.sleep(sleep_time)
          if hold_ctrl: 
            self.poe_bot.bot_controls.keyboard_pressKey('DIK_LCONTROL')
            time.sleep(random.randint(1,5)/100)
        if random.randint(1,100000) == 1:
          print(f'random sleep random.randint(1,100000) == 1')
          time.sleep(random.randint(5,15))
      self.poe_bot.ui.last_clicked_ui_element_pos = item_screen_pos
      if random.randint(1,10) == 1:
        time.sleep(random.randint(3,7)/10)
    if add_delay_before_last_clicks:
      time.sleep(random.randint(20,80)/100)
      time.sleep(random.randint(20,80)/100)
      time.sleep(random.randint(20,80)/100)
    for item_index in items_to_skip_indexes:
      item = items[item_index]
      item.click(can_click_multiple_times=1, mouse_speed_mult = int(mouse_speed_mult*1.5))
      time.sleep(random.randint(20,80)/100)
    if hold_ctrl is True:bot_controls.keyboard_releaseKey('DIK_LCONTROL')
class IncursionUiRoom:
  name:str
  index:int
  connected_to_nearby_rooms:List[int]
  connected_to_rooms:List[int]
  completed_analyzing:bool
  connected_to_entrance:bool
  def __init__(self, index) -> None:
    self.index = index
    self.completed_analyzing = False
    self.connected_to_rooms = []
    self.connected_to_nearby_rooms = []
  def __str__(self) -> str:
    return str(f'{self.name} index:{self.index} with entrance: {self.connected_to_entrance} connected to rooms: {self.connected_to_rooms}')
class IncursionUi:
  raw:dict
  visible:bool = False
  incursions_remaining:int = None
  enter_incursion_button_zone = [0,0,0,0]
  enter_incursion_button_middle = [0,0]
  entrance_room_index = 11
  all_rooms:List[IncursionUiRoom] = []

  current_room_str:str
  current_room:IncursionUiRoom

  rewards:List[str] = [None, None]
  architects_names:List[str] = [None, None]

  current_room_can_be_connected_to_rooms:List[IncursionUiRoom]
  """
     0  1
  2 curr 3
     4  5
  """

  """
     3  4
  5 curr 6
     7  8
  """
  current_room_can_be_connected_to_names:List[str]
  """
     0  1
  2 curr 3
     4  5
  """
  """
     3  4
  5 curr 6
     7  8
  """

  incursion_room_possible_connections = {
    0: [2,3,11],
    1: [4,5,11],
    2: [6,3,0],
    3: [6,7,2,4,0,11],
    4: [7,8,3,5,11,1],
    5: [8,4,1],
    6: [2,3,7,9],
    7: [4,3,6,8,9,10],
    8: [10,7,4,5],
    9: [12,10,6,7],
    10: [7,8,9,12],
    11: [0,1,3,4],
    12: [9,10],
  }

  corrupted_data_keys = ["⨘⚥翶", '稀䊼Ȫ', '⢀䟯ŧ']
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot
    self.current_room:IncursionUiRoom = None
  def update(self,refreshed_data=None, update_current_room = True):
    if refreshed_data is None:
      refreshed_data = self.poe_bot.backend.getIncursionUi()
      
      while refreshed_data['irt'] in self.corrupted_data_keys:
        print(f'[IncursionUi.update] found {refreshed_data["irt"]}')
        refreshed_data = self.poe_bot.backend.getIncursionUi()

    self.raw = refreshed_data
    self.visible = bool(refreshed_data['v'])
    if self.visible:
      
      self.incursions_remaining = int(refreshed_data['irt'].split(' ')[0])
      self.enter_incursion_button_zone = refreshed_data['eib_sz']
      self.enter_incursion_button_middle = [int( (self.enter_incursion_button_zone[0] + self.enter_incursion_button_zone[1])/2 ), int( (self.enter_incursion_button_zone[2] + self.enter_incursion_button_zone[3])/2 )]
      self.getRooms()
      if update_current_room is True: self.getCurrentRoom()
  def getCurrentRoom(self):
    self.current_room_str = self.raw['crn']
    self.current_room = next( (r for r in self.all_rooms if r.name == self.current_room_str), None)
    if not self.current_room:
      return True
    self.current_room_can_be_connected_to_names = []
    self.current_room_can_be_connected_to_rooms = []
    
    broken_connect_room_str = 'Locked Door to \n<default>{Unlock this door with a Stone of Passage}'
    room_index = 2
    for can_be_connected_room_str in self.raw['crc']:
      room_index += 1
      if can_be_connected_room_str == broken_connect_room_str:
        self.current_room_can_be_connected_to_rooms.append(None)
        continue
      text:str
      if "Locked Door to " in can_be_connected_room_str:
        text = can_be_connected_room_str.split('\n')[0].split('Locked Door to ')[1]
        connected = False
      else:
        text = can_be_connected_room_str.split("Unlocked Door to ")[1]
        connected = True
      room = next( (r for r in self.all_rooms if r.name == text))
      self.current_room_can_be_connected_to_names.append(text)
      self.current_room_can_be_connected_to_rooms.append(room)
    self.rewards = []
    self.architects_names = []
    for text in self.raw['cruur']:
      if "<default>" in text:
        next_room = text.split(' to ')[-1].split(')}')[0]
        self.rewards.append(next_room)
        self.architects_names.append(text.split("\n")[0])
      else:
        self.rewards.append(None)
  def getRooms(self, update_rooms_connections = True):
    pos_x, pos_y = self.poe_bot.convertPosXY(100,100)
    self.poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    all_rooms = [IncursionUiRoom(i) for i in range(13)]
    game_img = self.poe_bot.getImage()
    # incursion_room_connections_lines_borders = sortByHSV(game_img, 23, 54, 182, 33, 102, 255)
    # plt.imshow(incursion_room_connections_lines_borders); plt.show()
    # incursion_room_connections_lines_borders = sortByHSV(game_img, 28, 54, 182, 33, 102, 255)
    # plt.imshow(incursion_room_connections_lines_borders); plt.show()
    incursion_room_connections_lines_borders = sortByHSV(game_img, 28, 54, 232, 33, 102, 255)
    # plt.imshow(incursion_room_connections_lines_borders); plt.show()

    """
        12
      9 10
      6 7 8
    2 3 4 5
      0 11 1
      
    """
    incursion_room_possible_connections = {
      0: [2,3,11],
      1: [4,5,11],
      2: [6,3,0],
      3: [6,7,2,4,0,11],
      4: [7,8,3,5,11,1],
      5: [8,4,1],
      6: [2,3,7,9],
      7: [4,3,6,8,9,10],
      8: [10,7,4,5],
      9: [12,10,6,7],
      10: [7,8,9,12],
      11: [0,1,3,4],
      12: [9,10],
    }
    connections_pos_dict = {
      '0_11':[425,445,485,520], # x1 x2 y1 y2
      '0_2':[305,340,450,460], # x1 x2 y1 y2
      '0_3':[380,415,450,460], # x1 x2 y1 y2
      '1_11':[575,595,485,520], # x1 x2 y1 y2
      '1_4':[605,640,450,460], # x1 x2 y1 y2
      '1_5':[680,715,450,460], # x1 x2 y1 y2
      '2_3':[350,370,405,435], # x1 x2 y1 y2
      '2_6':[305,340,375,385], # x1 x2 y1 y2
      '3_11':[455,490,450,475], # x1 x2 y1 y2
      '3_4':[500,520,405,435], # x1 x2 y1 y2
      '3_6':[380,415,375,385], # x1 x2 y1 y2
      '3_7':[455,490,375,385], # x1 x2 y1 y2
      '4_11':[530,570,450,475], # x1 x2 y1 y2
      '4_5':[650,670,405,435], # x1 x2 y1 y2
      '4_7':[530,570,375,385], # x1 x2 y1 y2
      '4_8':[605,640,375,385], # x1 x2 y1 y2
      '5_8':[680,715,375,385], # x1 x2 y1 y2
      '6_7':[425,445,335,355], # x1 x2 y1 y2
      '6_9':[380,415,300,310], # x1 x2 y1 y2
      '7_10':[530,570,300,310], # x1 x2 y1 y2
      '7_8':[575,595,335,355], # x1 x2 y1 y2
      '7_9':[455,490,300,310], # x1 x2 y1 y2
      '8_10':[605,640,300,310], # x1 x2 y1 y2
      '9_10':[500,520,255,285], # x1 x2 y1 y2
      '9_12':[455,490,229,239], # x1 x2 y1 y2
      '10_12':[530,570,229,239], # x1 x2 y1 y2
    }
    connections_dict = {}
    for key in list(connections_pos_dict.keys()):
      screen_zone = connections_pos_dict[key]
      sorted_hsv_connection = incursion_room_connections_lines_borders[screen_zone[2]:screen_zone[3], screen_zone[0]:screen_zone[1]]
      # plt.imshow(room_img_hsv_sorted);plt.show()
      connection_exists = len(sorted_hsv_connection[sorted_hsv_connection != 0]) > 1
      # print(f'{key}: connected: {connection_exists} {screen_zone}')
      connections_dict[key] = connection_exists

    for key in list(incursion_room_possible_connections.keys()):
      rooms_can_be_connected_to = incursion_room_possible_connections[key]
      connected_to_rooms = []
      for room_can_be_connected_to in rooms_can_be_connected_to:
        if key > room_can_be_connected_to:
          connection_key = f"{room_can_be_connected_to}_{key}"
        else:
          connection_key = f"{key}_{room_can_be_connected_to}"
        if connections_dict[connection_key]:
          connected_to_rooms.append(room_can_be_connected_to)
      print(f'room {key} is connected to {connected_to_rooms}')
      all_rooms[key].connected_to_nearby_rooms = connected_to_rooms

    all_incursion_connections = []
    rooms_sorted_by_nearby_connected = sorted(all_rooms, key=lambda room: len(room.connected_to_nearby_rooms), reverse=True)
    for room in rooms_sorted_by_nearby_connected:
      # print(f"{room.index} {room.connected_to_nearby_rooms} {room.connected_to_rooms} {room.completed_analyzing}")
      if not room.connected_to_nearby_rooms: 
        room.connected_to_rooms = [room.index]
        continue

      checked_rooms = set([room.index])
      init_chain = [room.index]
      init_chain.extend(room.connected_to_nearby_rooms)
      current_chain = set(init_chain)
      rooms_to_check = room.connected_to_nearby_rooms[:]
      while rooms_to_check:
        current_room = rooms_to_check.pop(0)
        # print(f'checking room {current_room}')
        if current_room in checked_rooms: continue
        checked_rooms.add(current_room)
        current_room_nearby = all_rooms[current_room].connected_to_nearby_rooms[:]
        not_checked_rooms = list(filter(lambda room_index: room_index not in checked_rooms , current_room_nearby))
        rooms_to_check.extend(not_checked_rooms)
        list(map(lambda room_index: current_chain.add(room_index), not_checked_rooms))
      # print(f'current_chain {current_chain}')
      room.connected_to_rooms = list(current_chain)#+[room.index]

    for room in all_rooms:
      room.connected_to_entrance = self.entrance_room_index in room.connected_to_rooms
    room_index = 0
    for room in self.raw['r']:
      all_rooms[room_index].name = room['n']
      room_index+=1

    for room in all_rooms: print(room)

    self.all_rooms = all_rooms
  def clickEnterIncursion(self):
    poe_bot = self.poe_bot
    bot_controls = self.poe_bot.bot_controls
    screen_pos_x, screen_pos_y = self.enter_incursion_button_middle
    pos_x, pos_y = poe_bot.convertPosXY(screen_pos_x, screen_pos_y, safe = False)
    time.sleep(random.randint(5,20)/100)
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    time.sleep(random.randint(10,15)/100)
    bot_controls.mouse.press()
    for i in range(3): bot_controls.mouse.setPosSmooth(pos_x+random.randint(-5,+5), pos_y+random.randint(-5,+5))
    bot_controls.mouse.release()
    time.sleep(random.randint(10,15)/100)
  def takeItemizedTemple(self):
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    inventory = poe_bot.ui.inventory

    inventory_free_slots = inventory.getEmptySlots()
    if len(inventory_free_slots) == 0:
      poe_bot.raiseLongSleepException('no empty slots in inventory')
    inventory_free_slot = inventory_free_slots[0]
    pos_x, pos_y =  random.randint(415+50,600-50), random.randint(615+5,640-5)
    pos_x, pos_y = poe_bot.convertPosXY(pos_x,pos_y, safe = False)
    bot_controls.mouse.setPosSmooth(pos_x,pos_y)
    time.sleep(random.randint(20,40)/100)
    bot_controls.mouse.click()
    time.sleep(random.randint(20,40)/100)

    while True:
      time.sleep(random.randint(20,40)/100)
      inventory.update()
      if inventory.is_opened is True:
        break
    pos_x, pos_y = inventory.getItemCoordinates(item_pos_x=inventory_free_slot[0], item_pos_y=inventory_free_slot[1])
    pos_x, pos_y = poe_bot.convertPosXY(pos_x,pos_y, safe = False)
    bot_controls.mouse.setPosSmooth(pos_x,pos_y)
    time.sleep(random.randint(20,40)/100)
    bot_controls.mouse.click()
    time.sleep(random.randint(20,40)/100)
    self.poe_bot.ui.closeAll()
    time.sleep(random.randint(20,40)/100)
  def open(self):
    alva_entity = next( (e for e in self.poe_bot.game_data.entities.npcs if e.path == HIDEOUT_ALVA_METADATA_KEY ), None)
    if not alva_entity:
      time.sleep(random.randint(30,50)/10)
      self.poe_bot.refreshAll()
      alva_entity = next( (e for e in self.poe_bot.game_data.entities.npcs if e.path == HIDEOUT_ALVA_METADATA_KEY ), None)
      if alva_entity is None:
        self.poe_bot.helper_functions.enterNearestPortal()
    open_incursion_ui_iter = 0
    while self.visible is False:
      open_incursion_ui_iter += 1
      if open_incursion_ui_iter == 50:
        self.poe_bot.raiseLongSleepException('cannot open incursion ui for 50 iters')
      if open_incursion_ui_iter % 5 == 0:
        self.poe_bot.ui.closeAll()
        continue
      self.poe_bot.refreshInstanceData()
      alva_entity = next( (e for e in self.poe_bot.game_data.entities.npcs if e.path == HIDEOUT_ALVA_METADATA_KEY ), None)
      alva_entity.click(hold_ctrl=True)
      time.sleep(1)
      self.update(update_current_room=False)
  def __str__(self) -> str:
    return_str = f"IncursionUI visible:{self.visible}"
    if self.visible:
      return_str += f" incursions remaining:{self.incursions_remaining}"
      return_str +=  f"\ncurrent room name: {self.current_room} rewards: {self.rewards} architects:{self.architects_names}"
      return_str +=  f"\ncurrent room can be connected to rooms {self.current_room_can_be_connected_to_names}"
    return str(return_str)
class NpcDialogueUi:
  poe_bot:PoeBot
  raw:dict
  visible:bool = False
  screen_zone:Posx1x2y1y2|None
  choices:List[NpcDialogueLineChoice]|None
  rewards:List[Item]|None
  text: str|None

  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot
    self.reset()
  def reset(self):
    self.visible = False
    self.screen_zone = None
    self.rewards = None
    self.choices = None
    self.text = None
  def update(self, refreshed_data: dict|None = None):
    if refreshed_data is None:
      refreshed_data = self.poe_bot.backend.getNpcDialogueUi()
    self.reset()
    self.raw = refreshed_data
    if refreshed_data['v'] != 1:
      return
    self.visible = bool(refreshed_data['v'])
    if refreshed_data['rw'] != None:
      self.rewards = list(map(lambda i_raw: Item(poe_bot=self.poe_bot, item_raw=i_raw),refreshed_data['rw']))
    elif refreshed_data['ch'] != None:
      self.choices = list(map(lambda l_raw: NpcDialogueLineChoice(poe_bot=self.poe_bot, raw=l_raw),refreshed_data['ch']))
    elif refreshed_data['t'] != None:
      self.text = refreshed_data['t']
class NpcDialogueLineChoice(UiElement):
  def __init__(self, poe_bot: PoeBot, raw: dict) -> None:
    self.screen_zone = Posx1x2y1y2(*raw['sz'])
    self.text:str = raw['t']
    super().__init__(poe_bot, self.screen_zone)
class EscapeControlPanel:
  poe_bot:PoeBot
  charecter_selection_button_zone = [425,600,333,343] # [x1 x2 y1 y2]
  exit_to_login_screen_button_zone = [425,600,303,313] # [x1 x2 y1 y2]
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot
class UltimatumNextWaveUi:
  x1, x2, y1, y2 = 0,0,0,0
  choices_screen_zone = [0,0,0,0]
  choices = ['???', '???', '???']
  choices_middles = [(0,0),(0,0),(0,0)]
  accept_trial_button_pos_middle = [0,0]
  visible = False
  raw = dict()
  round = 0
  def __init__(self,poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot 
    self.ultimatum_mods_safe_keys = ULTIMATUM_MODS_SAFE_KEYS
    self.ultimatum_mods_ruin_keys = ULTIMATUM_MODS_RUIN_KEYS


  def update(self, refreshed_data = None):
    if refreshed_data is None:
      refreshed_data = self.poe_bot.backend.getUltimatumNextWaveUi()
    self.visible = bool(refreshed_data['v'])
    if self.visible:
      self.choices_screen_zone = refreshed_data['ch_sz']
      self.accept_trial_button_pos_middle = [
        int( (self.choices_screen_zone[0] + self.choices_screen_zone[1] )/2),
        int(self.choices_screen_zone[3] + 30)
      ]
      self.x1,self.x2,self.y1,self.y2 = refreshed_data['sz']
      self.round = int(refreshed_data['r'].split("{")[1].split("/")[0])
      self.detectChoicesMiddles()
      self.choices = refreshed_data['ch']
      for _i in range(100):
        if _i == 50:
          self.poe_bot.raiseLongSleepException('_i == 50 in ultimatumnextwaveui update')
        if "???" in self.choices:
          print(f'??? in choices, refreshing area and hovering over mods')
          self.refreshAreaAndHoverOverMods()
          refreshed_data = self.poe_bot.backend.getUltimatumNextWaveUi()
          self.choices = refreshed_data['ch']
        else:
          break
  def __str__(self) -> str:
    return str(f"ultimatum visible {self.visible}, round: {self.round}, choices: {self.choices}")
  def detectChoicesMiddles(self):
    self.choices_middles = []
    mode_choice_size = int((self.choices_screen_zone[1]-self.choices_screen_zone[0])/3)
    mode_choice_size_diff = int(mode_choice_size/2)
    modes_choice_zone_middle_y = int((self.choices_screen_zone[3] + self.choices_screen_zone[2])/2)
    for _i in range(3):
      self.choices_middles.append( (self.choices_screen_zone[0]+(mode_choice_size*_i)+mode_choice_size_diff, modes_choice_zone_middle_y))

  def refreshAreaAndHoverOverMods(self):
    self.poe_bot.backend.forceRefreshArea()
    for choice_middle in self.choices_middles:
      pos_x, pos_y = self.poe_bot.convertPosXY(choice_middle[0], choice_middle[1])
      self.poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)

  def getBestMod(self,ultimatum_possible_coices):
    for mod_priority in self.ultimatum_mods_ruin_keys[::-1]:
      ultimatum_possible_coices = sorted(ultimatum_possible_coices, key=lambda i: mod_priority in i)

    
    for mod_priority in self.ultimatum_mods_safe_keys[::-1]:
      mod_priority = mod_priority.replace("IV", "4")
      ultimatum_possible_coices = sorted(ultimatum_possible_coices, key=lambda i: mod_priority in i.replace("IV", "4"), reverse=True)
    print(f'chooseBestMod ultimatum_possible_coices_sorted {ultimatum_possible_coices}')
    best_choice = ultimatum_possible_coices[0]

    for mod in self.ultimatum_mods_ruin_keys[::-1]:
      if mod in best_choice:
        self.poe_bot.raiseLongSleepException(f'best_choice {best_choice} is in ruin keys')
    print(f'chooseBestMod {best_choice} ')
    return best_choice 

  def chooseBestMod(self):
    ultimatum_possible_coices = self.choices[:]
    return self.getBestMod(ultimatum_possible_coices=ultimatum_possible_coices)
    # for mod_priority in self.ultimatum_mods_ruin_keys[::-1]:
    #   ultimatum_possible_coices = sorted(ultimatum_possible_coices, key=lambda i: mod_priority in i)

    
    # for mod_priority in self.ultimatum_mods_safe_keys[::-1]:
    #   mod_priority = mod_priority.replace("IV", "4")
    #   ultimatum_possible_coices = sorted(ultimatum_possible_coices, key=lambda i: mod_priority in i.replace("IV", "4"), reverse=True)
    # print(f'chooseBestMod ultimatum_possible_coices_sorted {ultimatum_possible_coices}')
    # best_choice = ultimatum_possible_coices[0]

    # for mod in self.ultimatum_mods_ruin_keys[::-1]:
    #   if mod in best_choice:
    #     self.poe_bot.raiseLongSleepException(f'best_choice {best_choice} is in ruin keys')
    # print(f'chooseBestMod {best_choice} ')
    # return best_choice
  
  def chooseMod(self,mod_str:str, accept_trial = True):
    print(f'clicking on mod {mod_str}')
    best_choice_index = self.choices.index(mod_str)
    best_choice_screen_pos = self.choices_middles[best_choice_index]
    pos_x, pos_y = self.poe_bot.convertPosXY(best_choice_screen_pos[0], best_choice_screen_pos[1])
    self.poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    self.update()
    if self.visible is False: return
    self.poe_bot.bot_controls.mouse.click()
    if accept_trial:
      self.acceptTrial()

  def acceptTrial(self):
    pos_x, pos_y = self.poe_bot.convertPosXY(self.accept_trial_button_pos_middle[0], self.accept_trial_button_pos_middle[1])
    self.poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    time.sleep(random.randint(10,20)/100)
    self.update()
    if self.visible is False: return
    self.poe_bot.bot_controls.mouse.click()
class UltimatumInitiatorUi:
  x1, x2, y1, y2 = 0,0,0,0
  choices_screen_zone = [0,0,0,0]
  choices = ['???', '???', '???']
  choices_middles = [(0,0),(0,0),(0,0)]
  accept_trial_button_pos_middle = [0,0]
  visible = False
  exists = False
  raw = dict()
  round = 0
  def __init__(self,poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot 
  def update(self, refreshed_data = None):
    visible_labels = self.poe_bot.backend.getVisibleLabels()
    ultimatum_initiator_ui_label = next( (l for l in visible_labels if l['p'] == 'Metadata/Terrain/Leagues/Ultimatum/Objects/UltimatumChallengeInteractable'), None)

    if ultimatum_initiator_ui_label:
      self.exists = True
      refreshed_data = ultimatum_initiator_ui_label
      self.visible = bool(refreshed_data['v'])

      begin_button_center = ( int( (ultimatum_initiator_ui_label['sz'][0] + ultimatum_initiator_ui_label['sz'][1])/2), ultimatum_initiator_ui_label['sz'][3]-12 )
      modes_choice_zone = [
        int( (ultimatum_initiator_ui_label['sz'][0] + ultimatum_initiator_ui_label['sz'][1])/2)-60, 
        int( (ultimatum_initiator_ui_label['sz'][0] + ultimatum_initiator_ui_label['sz'][1])/2)+60, 
        ultimatum_initiator_ui_label['sz'][3]-70, 
        ultimatum_initiator_ui_label['sz'][3]-40
      ]

      mode_choice_zone_middles = []
      mode_choice_size = int((modes_choice_zone[1]-modes_choice_zone[0])/3)
      mode_choice_size_diff = int(mode_choice_size/2)
      modes_choice_zone_middle_y = int((modes_choice_zone[3] + modes_choice_zone[2])/2)

      for _i in range(3):
        mode_choice_zone_middles.append( (modes_choice_zone[0]+(mode_choice_size*_i)+mode_choice_size_diff, modes_choice_zone_middle_y))

      self.begin_button_center = begin_button_center
      self.modes_choice_zone = modes_choice_zone
      self.mode_choice_zone_middles = mode_choice_zone_middles

      self.type = ultimatum_initiator_ui_label['texts'][0]
      self.choices = ultimatum_initiator_ui_label['texts'][1:4]
    else:
      self.visible = False
      self.exists = False

  def hoverOverUltimatumModes(self):
    for choice_middle in self.mode_choice_zone_middles:
      pos_x, pos_y = self.poe_bot.convertPosXY(choice_middle[0], choice_middle[1])
      self.poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      time.sleep(random.randint(10,20)/100)

  def chooseMod(self, choice):
    self.update()
    best_choice_index = self.choices.index(choice)
    pos_x, pos_y = self.poe_bot.convertPosXY(self.mode_choice_zone_middles[best_choice_index][0], self.mode_choice_zone_middles[best_choice_index][1])
    self.poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    time.sleep(random.randint(10,20)/100)
    self.poe_bot.bot_controls.mouse.click()

  def startEncounter(self):
    for i in range(100):
      self.update()
      if self.visible is False:
        print('ecounter started')
        break
      pos_x, pos_y = self.poe_bot.convertPosXY(self.begin_button_center[0], self.begin_button_center[1])
      self.poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      time.sleep(random.randint(10,20)/100)
      self.poe_bot.bot_controls.mouse.click()
      time.sleep(random.randint(50,70)/100)

  def __str__(self) -> str:
    return str(f"UltimatumInitiatorUi exists:{self.exists} visible:{self.visible}")
class WorldMap:
  x1 = 0
  x2 = 0
  y1 = 0
  y2 = 0
  visible = False
  def __init__(self,poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot 
  def update(self, refreshed_data = None):
    if refreshed_data is None:
      refreshed_data = self.poe_bot.backend.getWorldMapUi()
    
    self.x1,self.x2,self.y1,self.y2 = refreshed_data['sz']
    self.visible = bool(refreshed_data['v'])
class ResurrectPanel:
  x1 = 0
  x2 = 0
  y1 = 0
  y2 = 0
  visible = False
  def __init__(self,poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot 

  def update(self, refreshed_data = None):
    if refreshed_data is None:
      refreshed_data = self.poe_bot.backend.getResurrectUi()
    self.x1,self.x2,self.y1,self.y2 = refreshed_data['sz']
    self.visible = bool(refreshed_data['v'])

  def clickResurrect(self, town = False):
    poe_bot = self.poe_bot
    pos_x, pos_y = random.randint(430,580), random.randint(225,235)
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
    time.sleep(random.randint(20,80)/100)
    poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    time.sleep(random.randint(20,80)/100)
    poe_bot.bot_controls.mouse.click()
    time.sleep(random.randint(30,60)/100)
    return True
class TradeWindow:
  poe_bot:PoeBot
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot
  def hoverOnTakeItems(self):
    bot_controls = self.poe_bot.bot_controls
    for y in range(12):
      for x in range(5):
        item_pos_x, item_pos_y = getInventoryItemCoordinates(x, y, 'trade_window_take')
        bot_controls.mouse.setPosSmooth(int(item_pos_x),int(item_pos_y))
  def clickAccept(self):
    bot_controls = self.poe_bot.bot_controls
    pos_x, pos_y = self.poe_bot.convertPosXY(90, 590)
    bot_controls.mouse.setPosSmooth(int(pos_x),int(pos_y))
    time.sleep(random.randint(10,15)/100)
    bot_controls.mouse.click()
    time.sleep(random.randint(10,15)/100)
  def clickCancel(self):
    bot_controls = self.poe_bot.bot_controls
    pos_x, pos_y = self.poe_bot.convertPosXY(450, 590)
    bot_controls.mouse.setPosSmooth(int(pos_x),int(pos_y))
    time.sleep(random.randint(10,15)/100)
    bot_controls.mouse.click()
    time.sleep(random.randint(10,15)/100)
class KirakMissions:
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot
    self.tab_zones = [
      Posx1x2y1y2(440,475,260,270),
      Posx1x2y1y2(490,535,260,270),
      Posx1x2y1y2(550,590,260,270),
    ]

  def assignScreenPosition(self, item_raw):
    # 1024x768
    grid_pos_x = item_raw['g'][0]
    x_offset = 439
    y_offset = 275
    if grid_pos_x > 3:
      y_offset = y_offset + INVENTORY_SLOT_CELL_SIZE
      grid_pos_x = grid_pos_x % 4
    x1 = x_offset + grid_pos_x * INVENTORY_SLOT_CELL_SIZE + INVENTORY_SLOT_CELL_SIZE_MIN
    x2 = x_offset + (grid_pos_x + 1)* INVENTORY_SLOT_CELL_SIZE - INVENTORY_SLOT_CELL_SIZE_MIN
    y1 = y_offset + INVENTORY_SLOT_CELL_SIZE_MIN
    y2 = y_offset + INVENTORY_SLOT_CELL_SIZE - INVENTORY_SLOT_CELL_SIZE_MIN
    item_raw['s'] = [x1,x2,y1,y2]

  def update(self, raw_data=None):
    if raw_data is None:
      raw_data = self.poe_bot.backend.getKirakMissionsUi()
    self.visible:bool = bool(raw_data["v"])
    if self.visible is True:
      self.screen_zone = Posx1x2y1y2(raw_data["sz"][0], raw_data["sz"][1], raw_data["sz"][2], raw_data["sz"][3])
      self.missions_count_by_tier = raw_data["kmv"]
      raw_data['items'] = sorted(raw_data['items'], key = lambda item_raw: item_raw['g'][0])
      raw_data['items'] = sorted(raw_data['items'], key = lambda item_raw: item_raw['ti'])
      for item_raw in raw_data['items']:
        minus_x = 0
        for i in range(item_raw['ti']):
          minus_x += self.missions_count_by_tier[i]
        item_raw['g'][0] -= minus_x
      list(map(lambda item_raw: self.assignScreenPosition(item_raw), raw_data['items']))
      self.items = list(map(lambda item_raw: KirakMissionItem(poe_bot=self.poe_bot, item_raw=item_raw), raw_data['items']))
      self.missions_tab_switchers = []
  
  def open(self):
    self.update()
    if self.visible is True:
      return True
    
    map_device = self.poe_bot.ui.map_device
    map_device.open()

    i = 0 
    while True:
      i+= 1
      if i > 40:
        self.poe_bot.raiseLongSleepException("if i > 40: KirakMissions.open()")


      pos_x = random.randint(380,405)
      pos_y = random.randint(435, 455)
      pos_x, pos_y = self.poe_bot.game_window.convertPosXY(pos_x, pos_y)
      self.poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      time.sleep(random.randint(5,10)/10)
      self.poe_bot.bot_controls.mouse.click()
      time.sleep(random.randint(5,10)/10)
      self.update()
      if self.visible is True:
        time.sleep(random.randint(10,20)/10)
        return True

  def activateItem(self,item:KirakMissionItem):
    item.click()
    self.activate()
    return True

  def activate(self):
    i = 0
    while True:
      i+=1
      if i> 40:
        self.poe_bot.raiseLongSleepException('cant activate kirakmissionui i > 40')
      self.update()
      if self.visible is False:
        break
      pos_x = random.randint(475,550)
      pos_y = random.randint(470,485)
      pos_x, pos_y = self.poe_bot.game_window.convertPosXY(pos_x, pos_y)
      self.poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      time.sleep(random.randint(5,10)/10)
      self.poe_bot.bot_controls.mouse.click()
      time.sleep(random.randint(5,10)/10)
      # necropolis league


  def switchTabIndex(self,index):
    tab_pos = self.tab_zones[index]
    pos_x = random.randint(tab_pos.x1,tab_pos.x2)
    pos_y = random.randint(tab_pos.y1,tab_pos.y2)
    pos_x, pos_y = self.poe_bot.game_window.convertPosXY(pos_x, pos_y)
    self.poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    time.sleep(random.randint(2,5)/10)
    self.poe_bot.bot_controls.mouse.click()
    time.sleep(random.randint(3,7)/10)
    return True
class PurchaseWindowHideout:
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot

  def update(self, raw_data=None):
    if raw_data is None:
      raw_data = self.poe_bot.backend.getPurchaseWindowHideoutUi()
    self.visible:bool = bool(raw_data["v"])
    if self.visible is True:
      self.screen_zone = Posx1x2y1y2(raw_data["sz"][0], raw_data["sz"][1], raw_data["sz"][2], raw_data["sz"][3])
      self.items = list(map(lambda item_raw: KirakMissionItem(poe_bot=self.poe_bot, item_raw=item_raw), raw_data['items']))
class BanditDialogue:
  raw:dict
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot

  def update(self):
    raw_data = self.poe_bot.backend.getBanditDialogueUi()
    self.raw = raw_data
    return raw_data
class MapDevice:
  poe_bot:PoeBot
  activate_button_pos:Posx1x2y1y2
  items:List[MapDeviceItem] = []
  placed_items:List[dict] = []
  is_opened = False
  number_of_slots = 0
  map_device_craft_mod_window_pos: Posx1x2y1y2
  kirak_missions_count: List[int] # [white, yellowe, red]
  raw:dict
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot
  def getInfo(self):
    raw_data = self.poe_bot.backend.mapDeviceInfo()
    self.is_opened = raw_data['IsOpened']
    self.placed_items = raw_data['items']
    self.number_of_slots = raw_data['slots_count']
    if self.is_opened != False:
      activate_button_position = raw_data['a_b_p']
      self.activate_button_pos = Posx1x2y1y2(activate_button_position["x1"], activate_button_position["x2"], activate_button_position["y1"], activate_button_position["y2"])
    else:
      self.activate_button_pos = None
    return raw_data
  def update(self, updated_data = None):
    if updated_data is None:
      updated_data = self.poe_bot.backend.mapDeviceInfo()
    self.is_opened = updated_data['IsOpened']
    self.placed_items = updated_data['items']
    self.number_of_slots = updated_data['slots_count']
    if self.number_of_slots == 4:
      self.placed_items_screen_positions = MAP_DEVICE_SLOTS['4slot']
    elif self.number_of_slots == 5:
      self.placed_items_screen_positions = MAP_DEVICE_SLOTS['5slot']
    elif self.number_of_slots == 6:
      self.placed_items_screen_positions = MAP_DEVICE_SLOTS['5slot']
      # 274 607
    if self.is_opened != False:
      activate_button_position = updated_data['a_b_p']
      self.activate_button_pos = Posx1x2y1y2(activate_button_position["x1"], activate_button_position["x2"], activate_button_position["y1"], activate_button_position["y2"])
      self.items = []
      for item in updated_data['items']:
        if item['Name'] != None:
          self.items.append(MapDeviceItem(self.poe_bot, item))
    else:
      self.activate_button_pos = None
    self.kirak_missions_count = updated_data['k_m_c']
    self.raw:dict = updated_data
  def open(self):
    print(f'[ui.MapDevice.open] call {time.time()}')
    self.update()
    i = 0
    while self.is_opened is False:
      i += 1
      if i > 40:
        self.poe_bot.raiseLongSleepException('map device bugged? while map_device.opened is False:')
      self.poe_bot.refreshInstanceData(reset_timer=True)
      self.poe_bot.game_data.updateLabelsOnGroundEntities()
      if i % 9 == 0:
        self.poe_bot.ui.closeAll()
        continue
      mapping_device = next( (e for e in self.poe_bot.game_data.labels_on_ground_entities if "MappingDevice" in e.path), None)
      if mapping_device is None:
        print(f'[ui.MapDevice.open] no mapping device nearby')
        self.poe_bot.helper_functions.enterNearestPortal()
      if self.is_opened is not True:
        print(f'[ui.MapDevice.open] opening mapping_device: {mapping_device.raw}')
        if mapping_device.location_on_screen.x == 0 and mapping_device.location_on_screen.y == 0:
          self.poe_bot.on_stuck_function()
          self.poe_bot.raiseLongSleepException('mapdevice loc on screen 0,0')
        
        mapping_device.hover(y_offset=-10)
        time.sleep(0.4)
        self.update()
        if self.is_opened == True:
          break
        self.poe_bot.bot_controls.mouse.click()
        time.sleep(random.randint(8,15)/10)
        self.update()
      else:
        break    
    if self.is_opened is not True:
      raise Exception("map_device.opened is not True")
    return True
  def checkIfActivateButtonIsActive(self):
    poe_bot = self.poe_bot
    self.update()
    x1 = self.activate_button_pos.x1 +5
    x2 = self.activate_button_pos.x2 -5
    y1 = self.activate_button_pos.y1 +5
    y2 = self.activate_button_pos.y2 -5
    game_img = poe_bot.getImage()
    activate_button_img = game_img[y1:y2, x1:x2]
    # print('activate_button_img')
    # plt.imshow(activate_button_img);plt.show()
    # plt.imshow(third_skill);plt.show()
    sorted_img = sortByHSV(activate_button_img, 0, 234, 0, 255, 255, 73)
    # plt.imshow(sorted_img);plt.show()
    activate_button_is_active = len(sorted_img[sorted_img != 0]) > 30
    # print(sorted_img[sorted_img != 0])
    print(f"activate_button_is_active {activate_button_is_active}")
    return activate_button_is_active
  def activate(self):
    if self.checkIfActivateButtonIsActive() is False:
      self.poe_bot.raiseLongSleepException("self.checkIfActivateButtonIsActive() is False")
    activate_button_pos = self.activate_button_pos.getCenter()
    pos_x,pos_y = self.poe_bot.convertPosXY(activate_button_pos[0], activate_button_pos[1], safe=False)
    print(f"activate button pos {pos_x, pos_y}")
    print(f"activate button pos {self.activate_button_pos}")
    print(f"activate button pos {self.raw}")
    self.poe_bot.bot_controls.mouse.setPosSmooth(int(pos_x),int(pos_y), mouse_speed_mult=3)
    time.sleep(0.1)
    self.poe_bot.bot_controls.mouse.click()
    time.sleep(0.2)
    _i = 0
    while True:
      time.sleep(0.2)
      _i += 1
      if _i > 20:
        print('map wasnt activated, map device supposed to be closed by itself, but it didnt')
        # self.poe_bot.ui.inventory.clickOnAnEmptySlotInInventory()
        self.poe_bot.raiseLongSleepException('map wasnt activated, map device supposed to be closed by itself, but it didnt')
      try:
        self.update()
      except Exception:
        continue
      if self.is_opened is False:
        break
  def setOption(self, option:str):
    mdi = self.getInfo()
    desired_mod_element_info = list(filter(lambda e: e['text'] == option, mdi['m_d_c']))
    if len(desired_mod_element_info) != 0:
      desired_mod_element_info = desired_mod_element_info[0]
      for i in range(10):
        element_pos = 0 # 0 is visible, -1 is upper, 1 is lower
        if desired_mod_element_info['pos']['y2'] <= mdi['c_m_p']['y1']:
          element_pos = -1
        elif desired_mod_element_info['pos']['y1']+2 > mdi['c_m_p']['y2']:
          element_pos = 1
        # desired_mod_element_info
        to_up = [427,100] # [x,y]
        to_down = [427,294] # [x,y]
        if element_pos != 0:
          print(f'element_pos:{element_pos} #  # 0 is visible, -1 is upper, 1 is lower')
          click_pos = [0,0]
          if element_pos == -1:
            click_pos = to_up
          else:
            click_pos = to_down

          x_pos, y_pos = self.poe_bot.convertPosXY(click_pos[0],click_pos[1])
          self.poe_bot.bot_controls.mouse.setPosSmooth(x_pos,y_pos)
          time.sleep(0.1)
          self.poe_bot.bot_controls.mouse.click()
          mdi = self.getInfo()
          desired_mod_element_info = list(filter(lambda e: e['text'] == option, mdi['m_d_c']))
          desired_mod_element_info = desired_mod_element_info[0]
        else:
          break
      print(f'element_pos after moving it:{element_pos} #  # 0 is visible, -1 is upper, 1 is lower')
      x1 = desired_mod_element_info['pos']['x1'] +10
      x2 = desired_mod_element_info['pos']['x1'] +20
      y1 = desired_mod_element_info['pos']['y1'] +10
      y2 = desired_mod_element_info['pos']['y2'] -10
      game_img = self.poe_bot.getImage()
      element_img = game_img[y1:y2, x1:x2]
      sorted_img = sortByHSV(element_img, 0, 54, 57, 23, 255, 236)
      craft_mode_is_active = len(sorted_img[sorted_img != 0]) > 30
      print(f"{option} craft_mode_is_active {craft_mode_is_active}")
      if craft_mode_is_active is False:
        print(f'[Map device] clicking on {option} to activate it')
        click_pos = []
        click_pos.append( int((desired_mod_element_info['pos']['x1'] + desired_mod_element_info['pos']['x2']) /2) )
        click_pos.append( int((desired_mod_element_info['pos']['y1'] + desired_mod_element_info['pos']['y2']) /2) )
        x_pos, y_pos = self.poe_bot.convertPosXY(click_pos[0],click_pos[1])
        self.poe_bot.bot_controls.mouse.setPosSmooth(x_pos,y_pos)
        time.sleep(0.1)
        self.poe_bot.bot_controls.mouse.click()
      return True
    else:
      print(f'[Map device] option {option} doesnt exist in crafting mods')
      return False
class MapDeviceMap(UiElement):
  def __init__(self, poe_bot, raw):
    self.screen_zone = Posx1x2y1y2(*raw['sz'])
    self.screen_pos = PosXY(int( (self.screen_zone.x1 + self.screen_zone.x2) / 2), int( (self.screen_zone.y1 + self.screen_zone.y2) / 2))
    self.name:str = raw['name']
    self.name_raw:str = raw['name_raw']
    self.icons:List[str] = raw['icons']

    #TODO types of map 
    # self.has_deli = "smth" in self.icons
    # if "smth" in self.icons:
    #   self.

    super().__init__(poe_bot, self.screen_zone, self.screen_pos)
class MapDevice_Poe2(MapDevice):
  def __init__(self, poe_bot:Poe2Bot):
    self.poe_bot = poe_bot
  def reset(self):
    self.is_opened = False
    self.avaliable_maps = []
    self.place_map_window_opened = False
    self.place_map_window_screenzone:Posx1x2y1y2 = None
    self.place_map_window_activate_button_screen_zone:Posx1x2y1y2 = None
    self.place_map_window_items:List[MapDeviceItem] = []

  def update(self, updated_data=None):
    if updated_data == None:
      updated_data = self.poe_bot.backend.mapDeviceInfo()
    self.raw = updated_data
    self.reset()
    self.is_opened:bool = updated_data['wm_o']
    if self.is_opened == False:
      return
    self.avaliable_maps = list(map(lambda m_raw: MapDeviceMap(self.poe_bot, m_raw), updated_data["av_m"]))
    self.place_map_window_opened = updated_data["pmw_o"]
    if self.place_map_window_opened:
      self.place_map_window_screenzone = Posx1x2y1y2(*updated_data["pmw_sz"])
      self.place_map_window_activate_button_screen_zone = Posx1x2y1y2(*updated_data["pmw_ab_sz"])
      self.place_map_window_items = list(map(lambda i_raw: MapDeviceItem(self.poe_bot, i_raw), updated_data["pmw_i"]))
  
  def moveScreenTo(self, map_device_map_element: MapDeviceMap):
    pass


class Inventory:
  '''
  - responsible for all the interactions with inventory
  
  '''
  last_raw_data = None
  temp = None
  poe_bot:PoeBot
  items: List[InventoryItem]
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot
  def update(self,current_inventory_info = None):
    if current_inventory_info is None:
      current_inventory_info = self.poe_bot.backend.getOpenedInventoryInfo()
    self.last_raw_data = current_inventory_info
    self.is_opened = current_inventory_info["IsOpened"]
    self.items = list(map(lambda item_raw: InventoryItem(poe_bot=self.poe_bot, item_raw=item_raw), current_inventory_info["items"]))
    return current_inventory_info
  def stashItems(self, items:List[InventoryItem]):
    self.poe_bot.ui.clickMultipleItems(items)
    for item in items:
      tab_index = None
      item_type = item.getType()
      if item_type is not None:
        tab_index = self.poe_bot.ui.stash.temp.affinities.get(item_type, None)
      self.poe_bot.ui.stash.temp.addItemToTab(item.raw, tab_index)
    self.poe_bot.ui.stash.temp.save()
  def open(self):
    self.update()
    if self.is_opened is True:
      return True
    else:
      self.poe_bot.bot_controls.keyboard.tap('DIK_I')
      time.sleep(random.randint(5,10)/100)
      self.update()
      return True
  #
  def getItemCoordinates(self, item_pos_x = None, item_pos_y = None, item = None):
    '''
    if item is passed, ignore item_pos_x = None, item_pos_y = None
    '''
    if item:
      item_pos_x = item["LocationTopLeft"]["X"]
      item_pos_y = item["LocationTopLeft"]["Y"]
    inventory_item_pos_x, inventory_item_pos_y = getInventoryItemCoordinates(item_pos_x, item_pos_y, 'inventory')
    return inventory_item_pos_x, inventory_item_pos_y
  def getFilledSlots(self, force_update = False):
    '''
    returns [[x,y]] of filled slots
    '''
    if hasattr(self, 'items') is False or force_update is True: self.update()
    self.update()
    items = self.items
      
    filled_inventory_slots = []
    for item in items:
      # print(item)
      item_uses_x = item.grid_position.x2 - item.grid_position.x1 #* item['LocationBottomRight']['Y'] - item['LocationTopLeft']['Y'] 
      item_uses_y = item.grid_position.y2 - item.grid_position.y1 #* item['LocationBottomRight']['Y'] - item['LocationTopLeft']['Y'] 
      for _x in range(item_uses_x):
        add_to_x = item.grid_position.x1 + _x
        for _y in range(item_uses_y):
          add_to_y = item.grid_position.y1 + _y
          filled_inventory_slots.append([add_to_x,add_to_y])
    return filled_inventory_slots
  def getEmptySlots(self, force_update = False):
    if hasattr(self, 'items') is False or force_update is True: self.update()
    all_slots = []
    for x in range(12):
      for y in range(5):
        all_slots.append([x,y])
    filled_slots = self.getFilledSlots()
    return list(filter(lambda slot: not slot in filled_slots, all_slots))
  def clickOnAnEmptySlotInInventory(self,):
    print(f'[Inventory] clickOnAnEmptySlotInInventory at {time.time()}')
    poe_bot = self.poe_bot
    bot_controls = self.poe_bot.bot_controls
    empty_slots = self.getEmptySlots(force_update=True)
    inventory_free_slot = empty_slots[0]
    pos_x, pos_y = self.getItemCoordinates(item_pos_x=inventory_free_slot[0], item_pos_y=inventory_free_slot[1])
    pos_x, pos_y = poe_bot.convertPosXY(pos_x,pos_y, safe = False)
    bot_controls.mouse.setPosSmooth(pos_x,pos_y)
    time.sleep(random.randint(20,40)/100)
    bot_controls.mouse.click()
    time.sleep(random.randint(20,40)/100)

x_offset = 12
y_offset = 90
def assignStashItemPositions(item):
  item["LocationTopLeft"] = {
    "X": 0,
    "Y": 0
  }
  item["LocationBottomRight"] = {
    "X": 0,
    "Y": 0
  }
  item["LocationTopLeft"]["X"] = ceil((item['TopLeft']["X"] - x_offset) / INVENTORY_SLOT_CELL_SIZE)
  item["LocationTopLeft"]["Y"] = ceil((item['TopLeft']["Y"] - y_offset) / INVENTORY_SLOT_CELL_SIZE)

  item["LocationBottomRight"]["X"] = ceil((item['BottomRight']["X"] - x_offset) / INVENTORY_SLOT_CELL_SIZE)
  item["LocationBottomRight"]["Y"] = ceil((item['BottomRight']["Y"] - y_offset) / INVENTORY_SLOT_CELL_SIZE)
class StashTabSwitchButton:
  def __init__(self, poe_bot:PoeBot, pos_x1x2x3x4:list) -> None:
    self.poe_bot = poe_bot
    self.x1 = pos_x1x2x3x4[0]
    self.x2 = pos_x1x2x3x4[1]
    self.y1 = pos_x1x2x3x4[2]
    self.y2 = pos_x1x2x3x4[3]
  def click(self):
    poe_bot = self.poe_bot
    x_offset = 5
    pos_x = random.randint(self.x1+x_offset,self.x2-x_offset)
    y_offset = 5
    pos_y = random.randint(self.y1+y_offset,self.y2-y_offset)
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
    poe_bot.bot_controls.mouse.setPosSmooth(pos_x,pos_y)
    time.sleep(random.randint(5,10)/100)
    poe_bot.bot_controls.mouse.click()
    time.sleep(random.randint(1,8)/10)
class Stash:
  '''
  - responsible for all the interactions with stash
  
  '''
  poe_bot: PoeBot
  temp:StashTempData

  is_opened:bool
  current_tab_index:int
  stash_tab_switch_buttons: List[StashTabSwitchButton]
  items: List[StashItem]
  is_opened = False
  opened_tab_type:str
  # 
  last_raw_data = None
  all_items_sorted:list
  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.temp = StashTempData(unique_id=self.poe_bot.unique_id)
    
    self.reset()
  def reset(self):
    self.stash_tab_switch_buttons = []
  def update(self, raw_stash_data = None):
    if raw_stash_data is None:
      raw_stash_data = self.poe_bot.backend.getOpenedStashInfo()
    self.last_raw_data = raw_stash_data
    self.reset()
    self.is_opened = raw_stash_data["status"] == 'opened'
    self.current_tab_index = raw_stash_data["tab_index"]
    if self.is_opened == True:
      self.total_stash_tab_count:int = raw_stash_data["total_stash_tab_count"]
      self.opened_tab_type = raw_stash_data["stash_tab_type"]
      for pos_x1x2x3x4 in raw_stash_data["s_b_p_ls"]:
        button = StashTabSwitchButton(poe_bot=self.poe_bot, pos_x1x2x3x4=pos_x1x2x3x4)
        self.stash_tab_switch_buttons.append(button)
      self.stash_tab_switch_buttons.sort(key=lambda b:b.x1)
      self.current_tab_items = list(map(lambda item_raw: StashItem(poe_bot=self.poe_bot, item_raw=item_raw, tab_index=self.current_tab_index), raw_stash_data['items']))
    else:
      self.current_tab_items = []
    
    self.getInfo(raw_stash_data)
    return raw_stash_data
  def open(self):
    print(f'[ui.Stash.open] call {time.time()}')
    self.update()
    self.poe_bot.ui.inventory.update()
    if self.is_opened is True and self.poe_bot.ui.inventory.is_opened is True:
      return 'success'
    i = 0
    while self.is_opened is False:
      i += 1
      if i > 14:
        self.poe_bot.raiseLongSleepException('map device bugged? while map_device.opened is False:')
      if i % 5 == 0:
        for _i in range(random.randint(1,3)): self.poe_bot.ui.closeAll()
      self.poe_bot.refreshInstanceData(reset_timer=True)
      self.poe_bot.game_data.updateLabelsOnGroundEntities()
      stash_box = next( (e for e in self.poe_bot.game_data.labels_on_ground_entities if "MiscellaneousObjects/Stash" in e.path), None)
      if stash_box is None:
        print(f'[ui.Stash.open] no stash_box nearby')
        self.poe_bot.helper_functions.enterNearestPortal()
      if self.is_opened is not True:
        print(f'[ui.Stash.open] opening stash_box: {stash_box.raw}')
        if stash_box.location_on_screen.x == 0 and stash_box.location_on_screen.y == 0:
          self.poe_bot.on_stuck_function()
          self.poe_bot.raiseLongSleepException('stash_box loc on screen 0,0')
        stash_box.hover(y_offset=-10)
        time.sleep(0.4)
        self.update()
        if self.is_opened == True:
          break
        self.poe_bot.bot_controls.mouse.click()
        time.sleep(random.randint(8,15)/10)
        self.update()
      else:
        break    
    if self.is_opened is not True:
      raise Exception("[ui.Stash.open] Stash.is_opened is not True")
    return True
  def openTabIndex(self, index:int, method = 'mouse'):
    poe_bot = self.poe_bot
    opened_stash_info = self.update()
    if self.current_tab_index == index:
      print(f"stash.openTabIndex {self.current_tab_index} == {index}")
      return True
    current_tab_index = opened_stash_info['tab_index']
    if method == 'keyboard':
      original_tab_index = current_tab_index
      distance = index - current_tab_index
      if distance < 0:
        key_to_tap = "DIK_NUMPAD4"
      else:
        key_to_tap = "DIK_NUMPAD6"

      for i in range(abs(distance)):
        self.poe_bot.bot_controls.keyboard.tap(key_to_tap)
        time.sleep(random.randint(2,4)/10)
        opened_stash_info = self.update()
        current_tab_index = opened_stash_info['tab_index']
        if current_tab_index == original_tab_index:
          self.poe_bot.bot_controls.keyboard.tap('DIK_NUMLOCK')
          self.poe_bot.bot_controls.keyboard.tap(key_to_tap)
          time.sleep(random.randint(2,4)/10)
    elif method == 'mouse':
      i = 0
      while True:
        i += 1
        if i > 100:
          poe_bot.raiseLongSleepException(f'cannot open stash tab with index {index}')
        self.stash_tab_switch_buttons[index].click()
        time.sleep(random.randint(20,40)/100)
        self.update()
        if self.current_tab_index != index:
          continue
        else:
          break
      return True
  def getAllItems(self)-> List[StashItem]:
    all_items = []
    for stash_tab in self.temp.stash_tabs_data:
      for item in stash_tab['items']:
        item['tab_index'] = stash_tab['tab_index']
        all_items.append(StashItem(poe_bot=self.poe_bot, item_raw=item))
    return all_items
  def updateStashTemp(self, update_premium = False):
    '''
    
    '''
    print(f'stash.updateStashTemp call {time.time()}')
    if self.temp is None:
      raise Exception('.self.temp is None')
    self.open()
    self.temp.unsorted_items = []
    tab_order = [x for x in range(self.total_stash_tab_count)]
    tab_order.pop(tab_order.index(self.current_tab_index))
    random.shuffle(tab_order)
    # 0 tab here
    for i in tab_order:
      self.openTabIndex(i)
      if self.opened_tab_type == "FragmentStash":
        print(f'current stash tab is fragment tab')
        screen_pos_x, screen_pos_y = self.poe_bot.convertPosXY(x=random.randint(245,335), y = random.randint(100,118))
        self.poe_bot.bot_controls.mouse.click()
        time.sleep(random.randint(5,20)/10)
        self.update()
      opened_time = time.time()
      total_sleep_time = sum(list(map(lambda i: random.randint(5,20)/100, self.current_tab_items[:40]))) + random.randint(10,20)/10
      if len(self.current_tab_items) != 0:
        items_to_hover = random.choices(self.current_tab_items, k=int(random.randint(1, len(self.current_tab_items))/10))
        for item in items_to_hover:
          item.hover()
          time.sleep(random.randint(10,20)/10)
      


      sleep_end_time = opened_time + total_sleep_time
      if sleep_end_time > time.time():
        sleep_more_for = sleep_end_time - time.time()
        time.sleep(sleep_more_for)
    print('setting affinities')
    print('trying to detect "map" affinity')
    maps_count = list(map(lambda tab: len(list(filter(lambda item_raw: item_raw['m_t'] != 0, tab['items']))), self.temp.stash_tabs_data))
    maximum_maps_count = max(maps_count)
    if maximum_maps_count != 0:
      tab_with_maximum_maps = self.temp.stash_tabs_data[maps_count.index(maximum_maps_count)]
      tab_with_maximum_maps_index = tab_with_maximum_maps['tab_index']
      print(f'tab_with_maximum_maps {tab_with_maximum_maps_index}')
      self.temp.affinities['map'] = tab_with_maximum_maps_index
    else:
      print('none of stash tabs have maps')
    self.temp.save()
  def unstashItem(self, item:StashItem):
    pass
  def pickItems(self, items:List[StashItem], return_new_items = True)-> List[InventoryItem]:
    inventory = self.poe_bot.ui.inventory
    inventory.update()
    items_grid_position_backup = list(map(lambda i: (i.grid_position.x1, i.grid_position.y1), inventory.items))
    self.poe_bot.ui.clickMultipleItems(items)
    inventory.update()
    new_items = list(filter(lambda i: not (i.grid_position.x1, i.grid_position.y1) in items_grid_position_backup, inventory.items))
    return new_items
  def unstashItems(self, items:List[StashItem]):
    self.pickItems(items=items)
  def getFilledSlots(self, force_update = False):
    '''
    returns [[x,y]] of filled slots
    '''
    if hasattr(self, 'current_tab_items') is False or force_update is True: self.update()
    self.update()
    items = self.current_tab_items
      
    filled_inventory_slots = []
    for item in items:
      # print(item)
      item_uses_x = item.grid_position.x2 - item.grid_position.x1 #* item['LocationBottomRight']['Y'] - item['LocationTopLeft']['Y'] 
      item_uses_y = item.grid_position.y2 - item.grid_position.y1 #* item['LocationBottomRight']['Y'] - item['LocationTopLeft']['Y'] 
      for _x in range(item_uses_x):
        add_to_x = item.grid_position.x1 + _x
        for _y in range(item_uses_y):
          add_to_y = item.grid_position.y1 + _y
          filled_inventory_slots.append([add_to_x,add_to_y])
    return filled_inventory_slots
  def getEmptySlots(self, force_update = False):
    if hasattr(self, 'current_tab_items') is False or force_update is True: self.update()
    all_slots = []
    for x in range(12):
      for y in range(12):
        all_slots.append([x,y])
    filled_slots = self.getFilledSlots()
    return list(filter(lambda slot: not slot in filled_slots, all_slots))
  def placeItemsAcrossStash(self, items_to_stash:List[Item]):
    print(f'placing items across the stash')
    self.open()
    stash_tabs_indexes_sorted = [i for i in range(1,4)]
    random.shuffle(stash_tabs_indexes_sorted)
    stashed_all = False
    map_stash_tab_index = self.poe_bot.ui.stash.temp.affinities.get('map', None)

    if self.current_tab_index in stash_tabs_indexes_sorted:
      try:
        stash_tabs_indexes_sorted.remove(self.current_tab_index)
        stash_tabs_indexes_sorted.insert(0, self.current_tab_index)
      except ValueError:
        print('val err')

    if map_stash_tab_index:
      try:
        stash_tabs_indexes_sorted.remove(map_stash_tab_index)
        stash_tabs_indexes_sorted.append(map_stash_tab_index)
      except ValueError:
        print('val err')

    print(f'indexes {stash_tabs_indexes_sorted}')
    for stash_tab_index in stash_tabs_indexes_sorted:
      self.openTabIndex(stash_tab_index)
      stash_tab_empty_cells = self.getEmptySlots()
      items_to_stash_in_current_tab = []
      if stash_tab_index == map_stash_tab_index:
        # leave 80*1.2 cells for maps
        maps_in_current_stash = list(filter(lambda item: item.getType() == "map", self.current_tab_items))
        maps_count = len(maps_in_current_stash)
        empty_cells_count = len(stash_tab_empty_cells)
        maps_slots_count = 96 #80*1.2
        related_to_maps_slots_count = maps_slots_count - maps_count
        can_use_cells = empty_cells_count -  related_to_maps_slots_count
        print(f'its a map stash tab, so only able to use {can_use_cells} here')
        if can_use_cells <= 0:
          self.poe_bot.raiseLongSleepException('could stash items across stash cos trying to place in map tab')
        stash_tab_empty_cells = stash_tab_empty_cells[:can_use_cells]
        
      for asdsda in stash_tab_empty_cells:
        if len(items_to_stash) == 0:
          stashed_all = True
          break
        items_to_stash_in_current_tab.append(items_to_stash.pop(0))
      print(f'placing {len(items_to_stash_in_current_tab)} items in current stash tab')
      self.poe_bot.ui.clickMultipleItems(items_to_stash_in_current_tab)
      if stashed_all is True:
        break
    if stashed_all is False:
      self.poe_bot.raiseLongSleepException('couldnt stash all items')
  #TODO rewrite below
  def getInfo(self, current_stash_info = None):
    if current_stash_info is None:
      current_stash_info = self.poe_bot.backend.getOpenedStashInfo()
    self.last_raw_data = current_stash_info
    if self.temp is not None and current_stash_info['status'] == 'opened':
      for item in current_stash_info['items']:
        assignStashItemPositions(item)
        item['tab_index'] = current_stash_info['tab_index']
      self.temp.updateTabInfo(current_stash_info)
    return current_stash_info


