from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
  from .gamehelper import Poe2Bot, PoeBot

import random
import time
from math import ceil, dist
from typing import List

from .components import PoeBotComponent, Posx1x2y1y2, PosXY, UiElement
from .constants import MAP_DEVICE_SLOTS
from .temps import StashTempData
from .utils import INVENTORY_SLOT_CELL_SIZE, getInventoryItemCoordinates, sortByHSV

INVENTORY_SLOT_CELL_SIZE_MIN = INVENTORY_SLOT_CELL_SIZE * 0.1


class Item:
  raw: dict
  grid_position: Posx1x2y1y2
  screen_position: Posx1x2y1y2
  clipboard_text: str
  source: str  # "inventory" "stash"
  map_type: str  # white, yellow,red
  item_mods_raw: List[str]

  def __init__(self, poe_bot: PoeBot, item_raw: dict) -> None:
    self.poe_bot = poe_bot
    self.raw = item_raw
    self.render_path: str = item_raw["a"]
    self.render_art: str = item_raw["RenderArt"]
    self.name: str = item_raw["Name"]
    self.unique_name: str = item_raw["unique_name"]
    self.rarity: str = item_raw["rarity"]
    self.items_in_stack: int = item_raw["items_in_stack"]
    self.item_mods: List[str] = item_raw["item_mods"]
    self.item_mods_raw: List[str] = item_raw.get("imr", [])
    self.identified: bool = bool(item_raw["i"])
    self.corrupted: bool = bool(item_raw["c"])
    self.map_tier: int = item_raw["m_t"]
    if self.map_tier != 0:
      if self.map_tier < 6:
        self.map_type = "white"
      elif self.map_tier < 11:
        self.map_type = "yellow"
      else:
        self.map_type = "red"
    links: List[str] = item_raw.get("l", None)
    sockets: str = None
    if links:
      sockets = "".join(links)
    self.links = links
    self.sockets = sockets
    if item_raw["s"] is not None:
      self.screen_position = Posx1x2y1y2(*item_raw["s"])

  def getScreenPos(self):
    pos_x, pos_y = (
      random.randint(ceil(self.screen_position.x1 + INVENTORY_SLOT_CELL_SIZE_MIN), ceil(self.screen_position.x2 - INVENTORY_SLOT_CELL_SIZE_MIN)),
      random.randint(ceil(self.screen_position.y1 + INVENTORY_SLOT_CELL_SIZE_MIN), ceil(self.screen_position.y2 - INVENTORY_SLOT_CELL_SIZE_MIN)),
    )
    return pos_x, pos_y

  def hover(self, mouse_speed_mult=1):
    bot_controls = self.poe_bot.bot_controls
    pos_x, pos_y = self.getScreenPos()
    screen_pos_x, screen_pos_y = self.poe_bot.convertPosXY(pos_x, pos_y, safe=False)
    bot_controls.mouse.setPosSmooth(int(screen_pos_x), int(screen_pos_y), mouse_speed_mult=mouse_speed_mult)
    return True

  def click(self, hold_ctrl=False, hold_shift=False, can_click_multiple_times=0, button="left", hover=True, mouse_speed_mult=1):
    bot_controls = self.poe_bot.bot_controls
    if hold_ctrl is True:
      bot_controls.keyboard_pressKey("DIK_LCONTROL")
    if hold_shift is True:
      bot_controls.keyboard_pressKey("DIK_LSHIFT")
    if hover is True:
      self.hover(mouse_speed_mult=mouse_speed_mult)
      time.sleep(random.randint(10, 25) / 100)
    iterations = 1
    for i in range(can_click_multiple_times):
      if random.randint(1, 10) == 1:
        iterations += 1
    for i in range(iterations):
      bot_controls.mouse.press(button=button)
      if random.randint(0, 2) != 0:
        self.hover()
      bot_controls.mouse.release(button=button)
    if hold_ctrl is True or hold_shift is True:
      time.sleep(random.randint(5, 7) / 100)
    if hold_ctrl is True:
      bot_controls.keyboard_releaseKey("DIK_LCONTROL")
    if hold_shift is True:
      bot_controls.keyboard_releaseKey("DIK_LSHIFT")

  def __str__(self) -> str:
    return str(self.raw)

  def getType(self):
    if self.map_tier != 0 and self.map_tier != 17:
      return "map"
    return None

  def getDeliriumMods(self):
    return list(filter(lambda mod_raw: "InstilledMapDelirium" in mod_raw, self.item_mods_raw))


class StashItem(Item):
  def __init__(self, poe_bot: PoeBot, item_raw: dict, tab_index: int = None) -> None:
    super().__init__(poe_bot, item_raw)
    self.source = "stash"
    if tab_index is not None:
      self.tab_index = tab_index
    else:
      self.tab_index: int = item_raw["tab_index"]

    # get from backend
    # get from backend
    # get from backend
    try:
      assignStashItemPositions(item_raw)
      self.grid_position = Posx1x2y1y2(
        item_raw["LocationTopLeft"]["X"], item_raw["LocationBottomRight"]["X"], item_raw["LocationTopLeft"]["Y"], item_raw["LocationBottomRight"]["Y"]
      )
      x1 = item_raw["TopLeft"]["X"] + INVENTORY_SLOT_CELL_SIZE_MIN
      x2 = item_raw["BottomRight"]["X"] - INVENTORY_SLOT_CELL_SIZE_MIN
      y1 = item_raw["TopLeft"]["Y"] + INVENTORY_SLOT_CELL_SIZE_MIN
      y2 = item_raw["BottomRight"]["Y"] - INVENTORY_SLOT_CELL_SIZE_MIN
      self.screen_position = Posx1x2y1y2(x1, x2, y1, y2)
    except Exception:
      pass


class InventoryItem(Item):
  def __init__(self, poe_bot: PoeBot, item_raw: dict) -> None:
    super().__init__(poe_bot, item_raw)
    self.source = "inventory"
    self.grid_position = Posx1x2y1y2(*item_raw["g"])
    if item_raw["s"][0] == 0:
      x_offset = 562
      y_offset = 417
      x1 = x_offset + self.grid_position.x1 * INVENTORY_SLOT_CELL_SIZE + INVENTORY_SLOT_CELL_SIZE_MIN
      x2 = x_offset + self.grid_position.x2 * INVENTORY_SLOT_CELL_SIZE - INVENTORY_SLOT_CELL_SIZE_MIN
      y1 = y_offset + self.grid_position.y1 * INVENTORY_SLOT_CELL_SIZE + INVENTORY_SLOT_CELL_SIZE_MIN
      y2 = y_offset + self.grid_position.y2 * INVENTORY_SLOT_CELL_SIZE - INVENTORY_SLOT_CELL_SIZE_MIN
      self.screen_position = Posx1x2y1y2(x1, x2, y1, y2)
    else:
      self.screen_position = Posx1x2y1y2(*item_raw["s"])

  def getItemClipboardText(self):
    self.hover()


class MapDeviceItem(Item):
  def __init__(self, poe_bot: PoeBot, item_raw: dict) -> None:
    super().__init__(poe_bot, item_raw)
    self.screen_position = Posx1x2y1y2(*item_raw["s"])


class KirakMissionItem(Item):
  def __init__(self, poe_bot: PoeBot, item_raw: dict) -> None:
    super().__init__(poe_bot, item_raw)
    self.tab_index: int = item_raw["ti"]
    self.screen_position = Posx1x2y1y2(*item_raw["s"])

  def click(self, hold_ctrl=False, hold_shift=False, can_click_multiple_times=0, mouse_speed_mult=2):
    self.poe_bot.ui.kirak_missions.switchTabIndex(self.tab_index)
    return super().click(hold_ctrl, hold_shift, can_click_multiple_times, mouse_speed_mult=mouse_speed_mult)


class PurchaseWindowItem(Item):
  def __init__(self, poe_bot: PoeBot, item_raw: dict) -> None:
    super().__init__(poe_bot, item_raw)
    self.screen_position = Posx1x2y1y2(*item_raw["s"])


class TabSwitchButton:
  pass


class Ui:
  poe_bot: PoeBot
  inventory: Inventory
  stash: Stash
  map_device: MapDevice
  trade_window: TradeWindow
  last_clicked_ui_element_pos = [0, 0]  # [x,y]

  def __init__(self, poe_bot: PoeBot) -> None:
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
    self.escape_control_panel = EscapeControlPanel(poe_bot=poe_bot)
    self.ritual_ui = RitualUi(poe_bot=poe_bot)
    self.anoint_ui = AnointUi(poe_bot=poe_bot)
    self.auction_house = AuctionHouseUi(poe_bot=poe_bot)

  def closeAll(self):
    bot_controls = self.poe_bot.bot_controls
    self.stash.is_opened = False
    self.inventory.is_opened = False
    bot_controls.keyboard.tap("DIK_SPACE")
    time.sleep(random.randint(5, 20) / 100)

  def update(self, refreshed_data=None):
    if refreshed_data is None:
      refreshed_data = self.poe_bot.backend.getWorldMapUi()

  def clickMultipleItems(
    self,
    items_to_click: List[Item],
    hold_ctrl=True,
    add_delay_before_last_clicks=True,
    skip_items=True,
    shuffle_items=True,
    random_sleep=True,
    mouse_speed_mult=2,
    hold_shift=False,
  ):
    bot_controls = self.poe_bot.bot_controls

    def holdButtons():
      if hold_ctrl:
        self.poe_bot.bot_controls.keyboard_pressKey("DIK_LCONTROL")
      if hold_ctrl and hold_shift:
        time.sleep(random.uniform(0.05, 0.10))
      if hold_shift:
        self.poe_bot.bot_controls.keyboard_pressKey("DIK_LSHIFT")

    def releaseButtons():
      if hold_ctrl is True:
        bot_controls.keyboard_releaseKey("DIK_LCONTROL")
      if hold_ctrl and hold_shift:
        time.sleep(random.uniform(0.05, 0.10))
      if hold_shift is True:
        bot_controls.keyboard_releaseKey("DIK_LSHIFT")

    print(f"[ui, ] click multiple call at {time.time()}")
    if len(items_to_click) == 0:
      return
    items = items_to_click.copy()
    holdButtons()
    if shuffle_items:
      items = items_to_click.copy()
      shuffle_by_x_axis = random.choice([True, False])

      x_axis_reverse = bool(random.randint(0, 1))
      y_axis_reverse = bool(random.randint(0, 1))

      def sortByXAxis():
        if x_axis_reverse:
          items.sort(key=lambda item: item.screen_position.x2, reverse=x_axis_reverse)
        else:
          items.sort(key=lambda item: item.screen_position.x1, reverse=x_axis_reverse)

      def sortByYAxis():
        if y_axis_reverse:
          items.sort(key=lambda item: item.screen_position.y2, reverse=y_axis_reverse)
        else:
          items.sort(key=lambda item: item.screen_position.y1, reverse=y_axis_reverse)

      if shuffle_by_x_axis is not False:
        sortByYAxis()
        sortByXAxis()
      else:
        sortByXAxis()
        sortByYAxis()
      temp_arr = []

      def getItemVal(item: Item):
        val = 0
        if shuffle_by_x_axis is not False:
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
      max_skip_items = int(len(items) / 10)
      min_skip_items = 1
      if max_skip_items == 0:
        min_skip_items = 0
      items_to_skip_indexes = random.choices(items_indexes, k=random.randint(min_skip_items, max_skip_items))
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
      time.sleep(random.randint(5, 10) * 0.01 * cells_to_item)
      item.click(can_click_multiple_times=3, mouse_speed_mult=mouse_speed_mult)
      if random_sleep is True:
        sleep_time = 0
        sleep_time += self.poe_bot.afk_temp.performShortSleep(return_sleep_val=True)
        print(f"[ui, click multiple] sleep_time {sleep_time}")
        if sleep_time != 0:
          releaseButtons()
          time.sleep(sleep_time)
          holdButtons()
        if random.randint(1, 100000) == 1:
          print("random sleep random.randint(1,100000) == 1")
          time.sleep(random.randint(5, 15))
      self.poe_bot.ui.last_clicked_ui_element_pos = item_screen_pos
      if random.randint(1, 10) == 1:
        time.sleep(random.uniform(0.30, 0.65))
    if add_delay_before_last_clicks:
      time.sleep(random.randint(20, 80) / 100)
      time.sleep(random.randint(20, 80) / 100)
      time.sleep(random.randint(20, 80) / 100)
    for item_index in items_to_skip_indexes:
      item = items[item_index]
      item.click(can_click_multiple_times=1, mouse_speed_mult=int(mouse_speed_mult * 1.5))
      time.sleep(random.randint(20, 80) / 100)
    releaseButtons()


class Ui2(Ui):
  map_device: MapDevice_Poe2

  def __init__(self, poe_bot):
    super().__init__(poe_bot)
    self.map_device = MapDevice_Poe2(poe_bot)
    self.resurrect_panel = ResurrectPanel2(poe_bot)


class UiComponent(PoeBotComponent):
  def __init__(self, poe_bot):
    super().__init__(poe_bot)
    self.reset()

  def reset(self):
    self.raw = {}
    self.visible = False

  def update(self, data: dict = None):
    self.reset()


class NpcDialogueUi:
  poe_bot: PoeBot
  raw: dict
  visible: bool = False
  screen_zone: Posx1x2y1y2 | None
  choices: List[NpcDialogueLineChoice] | None
  rewards: List[Item] | None
  text: str | None

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.reset()

  def reset(self):
    self.visible = False
    self.screen_zone = None
    self.rewards = None
    self.choices = None
    self.text = None

  def update(self, refreshed_data: dict | None = None):
    if refreshed_data is None:
      refreshed_data = self.poe_bot.backend.getNpcDialogueUi()
    self.reset()
    self.raw = refreshed_data
    if refreshed_data["v"] != 1:
      return
    self.visible = bool(refreshed_data["v"])
    if refreshed_data["rw"] is not None:
      self.rewards = list(map(lambda i_raw: Item(poe_bot=self.poe_bot, item_raw=i_raw), refreshed_data["rw"]))
    elif refreshed_data["ch"] is not None:
      self.choices = list(map(lambda l_raw: NpcDialogueLineChoice(poe_bot=self.poe_bot, raw=l_raw), refreshed_data["ch"]))
    elif refreshed_data["t"] is not None:
      self.text = refreshed_data["t"]


class NpcDialogueLineChoice(UiElement):
  def __init__(self, poe_bot: PoeBot, raw: dict) -> None:
    self.screen_zone = Posx1x2y1y2(*raw["sz"])
    self.text: str = raw["t"]
    super().__init__(poe_bot, self.screen_zone)


class EscapeControlPanel:
  poe_bot: PoeBot
  charecter_selection_button_zone = [425, 600, 333, 343]  # [x1 x2 y1 y2]
  exit_to_login_screen_button_zone = [425, 600, 303, 313]  # [x1 x2 y1 y2]

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot


class WorldMap:
  x1 = 0
  x2 = 0
  y1 = 0
  y2 = 0
  visible = False

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot

  def update(self, refreshed_data=None):
    if refreshed_data is None:
      refreshed_data = self.poe_bot.backend.getWorldMapUi()

    self.x1, self.x2, self.y1, self.y2 = refreshed_data["sz"]
    self.visible = bool(refreshed_data["v"])


class ResurrectPanel:
  x1 = 0
  x2 = 0
  y1 = 0
  y2 = 0
  visible = False

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot

  def update(self, refreshed_data=None):
    if refreshed_data is None:
      refreshed_data = self.poe_bot.backend.getResurrectUi()
    self.x1, self.x2, self.y1, self.y2 = refreshed_data["sz"]
    self.visible = bool(refreshed_data["v"])

  def clickResurrect(self, town=False):
    poe_bot = self.poe_bot
    pos_x, pos_y = random.randint(430, 580), random.randint(225, 235)
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
    time.sleep(random.randint(20, 80) / 100)
    poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    time.sleep(random.randint(20, 80) / 100)
    poe_bot.bot_controls.mouse.click()
    time.sleep(random.randint(30, 60) / 100)
    return True


class ResurrectPanel2(ResurrectPanel):
  def clickResurrect(self, town=False):
    poe_bot = self.poe_bot
    pos_x, pos_y = random.randint(430, 580), random.randint(560, 570)
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
    time.sleep(random.randint(20, 80) / 100)
    poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    time.sleep(random.randint(20, 80) / 100)
    poe_bot.bot_controls.mouse.click()
    time.sleep(random.randint(30, 60) / 100)
    return True


class TradeWindow:
  poe_bot: PoeBot

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot

  def hoverOnTakeItems(self):
    bot_controls = self.poe_bot.bot_controls
    for y in range(12):
      for x in range(5):
        item_pos_x, item_pos_y = getInventoryItemCoordinates(x, y, "trade_window_take")
        bot_controls.mouse.setPosSmooth(int(item_pos_x), int(item_pos_y))

  def clickAccept(self):
    bot_controls = self.poe_bot.bot_controls
    pos_x, pos_y = self.poe_bot.convertPosXY(90, 590)
    bot_controls.mouse.setPosSmooth(int(pos_x), int(pos_y))
    time.sleep(random.randint(10, 15) / 100)
    bot_controls.mouse.click()
    time.sleep(random.randint(10, 15) / 100)

  def clickCancel(self):
    bot_controls = self.poe_bot.bot_controls
    pos_x, pos_y = self.poe_bot.convertPosXY(450, 590)
    bot_controls.mouse.setPosSmooth(int(pos_x), int(pos_y))
    time.sleep(random.randint(10, 15) / 100)
    bot_controls.mouse.click()
    time.sleep(random.randint(10, 15) / 100)


class KirakMissions:
  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.tab_zones = [
      Posx1x2y1y2(440, 475, 260, 270),
      Posx1x2y1y2(490, 535, 260, 270),
      Posx1x2y1y2(550, 590, 260, 270),
    ]

  def assignScreenPosition(self, item_raw):
    # 1024x768
    grid_pos_x = item_raw["g"][0]
    x_offset = 439
    y_offset = 275
    if grid_pos_x > 3:
      y_offset = y_offset + INVENTORY_SLOT_CELL_SIZE
      grid_pos_x = grid_pos_x % 4
    x1 = x_offset + grid_pos_x * INVENTORY_SLOT_CELL_SIZE + INVENTORY_SLOT_CELL_SIZE_MIN
    x2 = x_offset + (grid_pos_x + 1) * INVENTORY_SLOT_CELL_SIZE - INVENTORY_SLOT_CELL_SIZE_MIN
    y1 = y_offset + INVENTORY_SLOT_CELL_SIZE_MIN
    y2 = y_offset + INVENTORY_SLOT_CELL_SIZE - INVENTORY_SLOT_CELL_SIZE_MIN
    item_raw["s"] = [x1, x2, y1, y2]

  def update(self, raw_data=None):
    if raw_data is None:
      raw_data = self.poe_bot.backend.getKirakMissionsUi()
    self.visible: bool = bool(raw_data["v"])
    if self.visible is True:
      self.screen_zone = Posx1x2y1y2(raw_data["sz"][0], raw_data["sz"][1], raw_data["sz"][2], raw_data["sz"][3])
      self.missions_count_by_tier = raw_data["kmv"]
      raw_data["items"] = sorted(raw_data["items"], key=lambda item_raw: item_raw["g"][0])
      raw_data["items"] = sorted(raw_data["items"], key=lambda item_raw: item_raw["ti"])
      for item_raw in raw_data["items"]:
        minus_x = 0
        for i in range(item_raw["ti"]):
          minus_x += self.missions_count_by_tier[i]
        item_raw["g"][0] -= minus_x
      list(map(lambda item_raw: self.assignScreenPosition(item_raw), raw_data["items"]))
      self.items = list(map(lambda item_raw: KirakMissionItem(poe_bot=self.poe_bot, item_raw=item_raw), raw_data["items"]))
      self.missions_tab_switchers = []

  def open(self):
    self.update()
    if self.visible is True:
      return True

    map_device = self.poe_bot.ui.map_device
    map_device.open()

    i = 0
    while True:
      i += 1
      if i > 40:
        self.poe_bot.raiseLongSleepException("if i > 40: KirakMissions.open()")

      pos_x = random.randint(380, 405)
      pos_y = random.randint(435, 455)
      pos_x, pos_y = self.poe_bot.game_window.convertPosXY(pos_x, pos_y)
      self.poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      time.sleep(random.randint(5, 10) / 10)
      self.poe_bot.bot_controls.mouse.click()
      time.sleep(random.randint(5, 10) / 10)
      self.update()
      if self.visible is True:
        time.sleep(random.randint(10, 20) / 10)
        return True

  def activateItem(self, item: KirakMissionItem):
    item.click()
    self.activate()
    return True

  def activate(self):
    i = 0
    while True:
      i += 1
      if i > 40:
        self.poe_bot.raiseLongSleepException("cant activate kirakmissionui i > 40")
      self.update()
      if self.visible is False:
        break
      pos_x = random.randint(475, 550)
      pos_y = random.randint(470, 485)
      pos_x, pos_y = self.poe_bot.game_window.convertPosXY(pos_x, pos_y)
      self.poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      time.sleep(random.randint(5, 10) / 10)
      self.poe_bot.bot_controls.mouse.click()
      time.sleep(random.randint(5, 10) / 10)
      # necropolis league

  def switchTabIndex(self, index):
    tab_pos = self.tab_zones[index]
    pos_x = random.randint(tab_pos.x1, tab_pos.x2)
    pos_y = random.randint(tab_pos.y1, tab_pos.y2)
    pos_x, pos_y = self.poe_bot.game_window.convertPosXY(pos_x, pos_y)
    self.poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    time.sleep(random.randint(2, 5) / 10)
    self.poe_bot.bot_controls.mouse.click()
    time.sleep(random.randint(3, 7) / 10)
    return True


class PurchaseWindowHideout:
  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot

  def update(self, raw_data=None):
    if raw_data is None:
      raw_data = self.poe_bot.backend.getPurchaseWindowHideoutUi()
    self.visible: bool = bool(raw_data["v"])
    if self.visible is True:
      self.screen_zone = Posx1x2y1y2(raw_data["sz"][0], raw_data["sz"][1], raw_data["sz"][2], raw_data["sz"][3])
      self.items = list(map(lambda item_raw: KirakMissionItem(poe_bot=self.poe_bot, item_raw=item_raw), raw_data["items"]))


class BanditDialogue:
  raw: dict

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot

  def update(self):
    raw_data = self.poe_bot.backend.getBanditDialogueUi()
    self.raw = raw_data
    return raw_data


class AnointUi(PoeBotComponent):
  def __init__(self, poe_bot):
    super().__init__(poe_bot)
    self.reset()

  def reset(self):
    self.visible = False
    self.screen_zone: Posx1x2y1y2
    self.oils: List[Item] = []
    self.placed_items: List[Item] = []
    self.anoint_button: UiElement = None
    self.anoint_button_screen_zone: Posx1x2y1y2 = None
    self.texts: List[str] = []

  def update(self, data: dict = None):
    self.reset()
    if data is None:
      data = self.poe_bot.backend.getAnointUi()
    self.visible = bool(data["v"])
    if self.visible is False:
      return
    self.screen_zone = Posx1x2y1y2(*data["sz"])
    self.oils = list(map(lambda item_raw: Item(self.poe_bot, item_raw), data["o"]))
    self.placed_items = list(map(lambda item_raw: Item(self.poe_bot, item_raw), data["pi"]))
    self.anoint_button_screen_zone = Posx1x2y1y2(*data["a_b_sz"])
    self.anoint_button = UiElement(self.poe_bot, self.anoint_button_screen_zone)
    self.texts = data["t"]

  def open(self, consumable: InventoryItem):
    self.update()
    if self.visible is True:
      return
    consumable.click(button="right")
    time.sleep(random.uniform(0.30, 0.60))
    self.update()
    if self.visible is False:
      self.poe_bot.raiseLongSleepException(f"cant open anoint ui via item {consumable.raw}")

  def anointItem(self, item: InventoryItem, consumables: List[InventoryItem]):
    anoint_ui = self
    anoint_ui.open(consumables[0])
    item.click(hold_ctrl=True)
    time.sleep(random.uniform(0.30, 0.60))
    self.poe_bot.ui.clickMultipleItems(consumables, hold_ctrl=True, random_sleep=False, skip_items=False)
    anoint_ui.anoint_button.click()
    anoint_ui.update()
    anoint_ui.placed_items[0].click(hold_ctrl=True)


class MapDevice:
  poe_bot: PoeBot
  activate_button_pos: Posx1x2y1y2
  items: List[MapDeviceItem] = []
  placed_items: List[dict] = []
  is_opened = False
  number_of_slots = 0
  map_device_craft_mod_window_pos: Posx1x2y1y2
  kirak_missions_count: List[int]  # [white, yellowe, red]
  raw: dict

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot

  def getInfo(self):
    raw_data = self.poe_bot.backend.mapDeviceInfo()
    self.is_opened = raw_data["IsOpened"]
    self.placed_items = raw_data["items"]
    self.number_of_slots = raw_data["slots_count"]
    if self.is_opened is not False:
      activate_button_position = raw_data["a_b_p"]
      self.activate_button_pos = Posx1x2y1y2(
        activate_button_position["x1"], activate_button_position["x2"], activate_button_position["y1"], activate_button_position["y2"]
      )
    else:
      self.activate_button_pos = None
    return raw_data

  def update(self, updated_data=None):
    if updated_data is None:
      updated_data = self.poe_bot.backend.mapDeviceInfo()
    self.is_opened = updated_data["IsOpened"]
    self.placed_items = updated_data["items"]
    self.number_of_slots = updated_data["slots_count"]
    if self.number_of_slots == 4:
      self.placed_items_screen_positions = MAP_DEVICE_SLOTS["4slot"]
    elif self.number_of_slots == 5:
      self.placed_items_screen_positions = MAP_DEVICE_SLOTS["5slot"]
    elif self.number_of_slots == 6:
      self.placed_items_screen_positions = MAP_DEVICE_SLOTS["5slot"]
      # 274 607
    if self.is_opened is not False:
      activate_button_position = updated_data["a_b_p"]
      self.activate_button_pos = Posx1x2y1y2(
        activate_button_position["x1"], activate_button_position["x2"], activate_button_position["y1"], activate_button_position["y2"]
      )
      self.items = []
      for item in updated_data["items"]:
        if item["Name"] is not None:
          self.items.append(MapDeviceItem(self.poe_bot, item))
    else:
      self.activate_button_pos = None
    self.kirak_missions_count = updated_data["k_m_c"]
    self.raw: dict = updated_data

  def open(self):
    print(f"[ui.MapDevice.open] call {time.time()}")
    self.update()
    i = 0
    while self.is_opened is False:
      i += 1
      if i > 40:
        self.poe_bot.raiseLongSleepException("map device bugged? while map_device.opened is False:")
      self.poe_bot.refreshInstanceData(reset_timer=True)
      self.poe_bot.game_data.updateLabelsOnGroundEntities()
      if i % 9 == 0:
        self.poe_bot.ui.closeAll()
        continue
      mapping_device = next((e for e in self.poe_bot.game_data.labels_on_ground_entities if "MappingDevice" in e.path), None)
      if mapping_device is None:
        print("[ui.MapDevice.open] no mapping device nearby")
        self.poe_bot.helper_functions.enterNearestPortal()
      if self.is_opened is not True:
        print(f"[ui.MapDevice.open] opening mapping_device: {mapping_device.raw}")
        if mapping_device.location_on_screen.x == 0 and mapping_device.location_on_screen.y == 0:
          self.poe_bot.on_stuck_function()
          self.poe_bot.raiseLongSleepException("mapdevice loc on screen 0,0")

        mapping_device.hover(y_offset=-10)
        time.sleep(0.4)
        self.update()
        if self.is_opened is True:
          break
        self.poe_bot.bot_controls.mouse.click()
        time.sleep(random.randint(8, 15) / 10)
        self.update()
      else:
        break
    if self.is_opened is not True:
      raise Exception("map_device.opened is not True")
    return True

  def checkIfActivateButtonIsActive(self):
    poe_bot = self.poe_bot
    self.update()
    x1 = self.activate_button_pos.x1 + 5
    x2 = self.activate_button_pos.x2 - 5
    y1 = self.activate_button_pos.y1 + 5
    y2 = self.activate_button_pos.y2 - 5
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
    pos_x, pos_y = self.poe_bot.convertPosXY(activate_button_pos[0], activate_button_pos[1], safe=False)
    print(f"activate button pos {pos_x, pos_y}")
    print(f"activate button pos {self.activate_button_pos}")
    print(f"activate button pos {self.raw}")
    self.poe_bot.bot_controls.mouse.setPosSmooth(int(pos_x), int(pos_y), mouse_speed_mult=3)
    time.sleep(0.1)
    self.poe_bot.bot_controls.mouse.click()
    time.sleep(0.2)
    _i = 0
    while True:
      time.sleep(0.2)
      _i += 1
      if _i > 20:
        print("map wasnt activated, map device supposed to be closed by itself, but it didnt")
        # self.poe_bot.ui.inventory.clickOnAnEmptySlotInInventory()
        self.poe_bot.raiseLongSleepException("map wasnt activated, map device supposed to be closed by itself, but it didnt")
      try:
        self.update()
      except Exception:
        continue
      if self.is_opened is False:
        break

  def setOption(self, option: str):
    mdi = self.getInfo()
    desired_mod_element_info = list(filter(lambda e: e["text"] == option, mdi["m_d_c"]))
    if len(desired_mod_element_info) != 0:
      desired_mod_element_info = desired_mod_element_info[0]
      for i in range(10):
        element_pos = 0  # 0 is visible, -1 is upper, 1 is lower
        if desired_mod_element_info["pos"]["y2"] <= mdi["c_m_p"]["y1"]:
          element_pos = -1
        elif desired_mod_element_info["pos"]["y1"] + 2 > mdi["c_m_p"]["y2"]:
          element_pos = 1
        # desired_mod_element_info
        to_up = [427, 100]  # [x,y]
        to_down = [427, 294]  # [x,y]
        if element_pos != 0:
          print(f"element_pos:{element_pos} #  # 0 is visible, -1 is upper, 1 is lower")
          click_pos = [0, 0]
          if element_pos == -1:
            click_pos = to_up
          else:
            click_pos = to_down

          x_pos, y_pos = self.poe_bot.convertPosXY(click_pos[0], click_pos[1])
          self.poe_bot.bot_controls.mouse.setPosSmooth(x_pos, y_pos)
          time.sleep(0.1)
          self.poe_bot.bot_controls.mouse.click()
          mdi = self.getInfo()
          desired_mod_element_info = list(filter(lambda e: e["text"] == option, mdi["m_d_c"]))
          desired_mod_element_info = desired_mod_element_info[0]
        else:
          break
      print(f"element_pos after moving it:{element_pos} #  # 0 is visible, -1 is upper, 1 is lower")
      x1 = desired_mod_element_info["pos"]["x1"] + 10
      x2 = desired_mod_element_info["pos"]["x1"] + 20
      y1 = desired_mod_element_info["pos"]["y1"] + 10
      y2 = desired_mod_element_info["pos"]["y2"] - 10
      game_img = self.poe_bot.getImage()
      element_img = game_img[y1:y2, x1:x2]
      sorted_img = sortByHSV(element_img, 0, 54, 57, 23, 255, 236)
      craft_mode_is_active = len(sorted_img[sorted_img != 0]) > 30
      print(f"{option} craft_mode_is_active {craft_mode_is_active}")
      if craft_mode_is_active is False:
        print(f"[Map device] clicking on {option} to activate it")
        click_pos = []
        click_pos.append(int((desired_mod_element_info["pos"]["x1"] + desired_mod_element_info["pos"]["x2"]) / 2))
        click_pos.append(int((desired_mod_element_info["pos"]["y1"] + desired_mod_element_info["pos"]["y2"]) / 2))
        x_pos, y_pos = self.poe_bot.convertPosXY(click_pos[0], click_pos[1])
        self.poe_bot.bot_controls.mouse.setPosSmooth(x_pos, y_pos)
        time.sleep(0.1)
        self.poe_bot.bot_controls.mouse.click()
      return True
    else:
      print(f"[Map device] option {option} doesnt exist in crafting mods")
      return False


class MapDeviceMap(UiElement):
  def __init__(self, poe_bot, raw):
    self.raw = raw
    self.screen_zone = Posx1x2y1y2(*raw["sz"])
    self.screen_pos = PosXY(int((self.screen_zone.x1 + self.screen_zone.x2) / 2), int((self.screen_zone.y1 + self.screen_zone.y2) / 2))
    self.id: int = raw["id"]
    self.name: str = raw["name"]
    self.name_raw: str = raw["name_raw"]
    self.icons: List[str] = raw["icons"]
    self.can_run = bool(raw["can_run"])
    self.is_boss = False
    self.is_breach = False
    self.is_expedition = False
    self.is_ritual = False
    self.is_delirium = False
    self.is_corruption = False
    self.is_irradiated = False
    self.is_unique = False
    self.is_hideout = False
    self.is_trader = False
    self.is_tower = self.name_raw == "MapLostTowers"
    for icon in self.icons:
      if "AtlasIconContentMapBoss" in icon:
        self.is_boss = True
      if "AtlasIconContentBreach" in icon:
        self.is_breach = True
      if "AtlasIconContentExpedition" in icon:
        self.is_expedition = True
      if "AtlasIconContentRitual" in icon:
        self.is_ritual = True
      if "AtlasIconContentDelirium" in icon:
        self.is_delirium = True
      if "AtlasIconContentCorruption" in icon:
        self.is_corruption = True
      if "AtlasIconContentIrradiated" in icon:
        self.is_irradiated = True
      if "AtlasIconContentUniqueMap" in icon:
        self.is_unique = True
      if "AtlasIconContentHideout" in icon:
        self.is_hideout = True
      if "AtlasIconContentTrader" in icon:
        self.is_trader = True
    if "MapHideout" in self.name_raw:
      self.is_hideout = True
    super().__init__(poe_bot, self.screen_zone, self.screen_pos)

  def dragTo(self):
    poe_bot = self.poe_bot
    drag_from = poe_bot.game_window.convertPosXY(self.screen_pos[0], self.screen_pos[1])
    drag_to = poe_bot.game_window.center_point
    poe_bot.bot_controls.mouse.drag(drag_from, drag_to)
    time.sleep(random.uniform(0.15, 0.35))


class MapDevice_Poe2(MapDevice):
  poe_bot: Poe2Bot

  def __init__(self, poe_bot: Poe2Bot):
    self.poe_bot = poe_bot

  def reset(self):
    self.world_map_is_opened = False
    self.is_opened = False
    self.avaliable_maps = []
    self.all_maps = []
    self.ziggurat_button: UiElement = None
    self.special_maps: List[Posx1x2y1y2] = []

    # TODO make a class for dropdown?
    self.place_map_window_opened = False
    self.place_map_window_screenzone: Posx1x2y1y2 = None
    self.place_map_window_activate_button_screen_zone: Posx1x2y1y2 = None
    self.place_map_window_items: List[MapDeviceItem] = []

  def update(self, updated_data=None):
    if updated_data is None:
      updated_data = self.poe_bot.backend.mapDeviceInfo()
    self.raw = updated_data
    self.reset()
    self.world_map_is_opened: bool = updated_data["wm_o"]
    self.is_opened: bool = updated_data["ap_o"] and self.world_map_is_opened
    if self.is_opened is False:
      return
    self.all_maps = list(map(lambda m_raw: MapDeviceMap(self.poe_bot, m_raw), updated_data["av_m"]))
    self.avaliable_maps = list(filter(lambda map: map.can_run, self.all_maps))
    self.place_map_window_opened = updated_data["pmw_o"]
    if self.place_map_window_opened:
      self.place_map_window_screenzone = Posx1x2y1y2(*updated_data["pmw_sz"])
      self.place_map_window_activate_button_screen_zone = Posx1x2y1y2(*updated_data["pmw_ab_sz"])
      self.activate_button_pos = self.place_map_window_activate_button_screen_zone
      self.place_map_window_items = list(map(lambda i_raw: MapDeviceItem(self.poe_bot, i_raw), updated_data["pmw_i"]))
      self.place_map_window_text = updated_data["pmw_t"]
    if updated_data.get("z_b_sz", None) is not None:
      self.ziggurat_button = UiElement(self.poe_bot, Posx1x2y1y2(*updated_data["z_b_sz"]))
    if updated_data.get("rg_sz", None) is not None:
      list(map(lambda el: self.special_maps.append(Posx1x2y1y2(*el)), updated_data["rg_sz"]))

  def checkIfActivateButtonIsActive(self):
    self.update()
    activate_button_is_active = True
    if len(self.place_map_window_items) != 1:
      activate_button_is_active = False
    # if self.place_map_window_opened == False:
    #   poe_bot.raiseLongSleepException('checking if activate button is active, but dropdown is not visible')
    # for corner in self.activate_button_pos.getCorners():
    #   if poe_bot.game_window.isInRoi(*corner) == False:
    #     dropdown_zone = self.place_map_window_screenzone
    #     pos_x = int((dropdown_zone.x1 + dropdown_zone.x2)/2)
    #     pos_y = dropdown_zone.y1 + 10
    #     pos_x, pos_y = poe_bot.game_window.convertPosXY(pos_x, pos_y, safe=False)
    #     center_x, center_y = poe_bot.game_window.convertPosXY(*poe_bot.game_window.center_point, safe=False)
    #     center_y = center_y - 100
    #     poe_bot.bot_controls.mouse.drag([pos_x, pos_y], [pos_x, center_y])
    #     time.sleep(random.uniform(0.35,0.75))
    #     self.update()
    #     if any(list(map(lambda c: poe_bot.game_window.isInRoi(*c) == False, self.activate_button_pos.getCorners()))):
    #       poe_bot.raiseLongSleepException(f'corner {corner} is outside of roi')
    #     break
    # # return super().checkIfActivateButtonIsActive(hsv_range = [0, 0, 0, 255, 30, 180])
    # x1 = self.activate_button_pos.x1 +5
    # x2 = self.activate_button_pos.x2 -5
    # y1 = self.activate_button_pos.y1 +5
    # y2 = self.activate_button_pos.y2 -5
    # game_img = poe_bot.getImage()
    # activate_button_img = game_img[y1:y2, x1:x2]
    # # print('activate_button_img')
    # # plt.imshow(activate_button_img);plt.show()
    # # plt.imshow(third_skill);plt.show()
    # sorted_img = sortByHSV(activate_button_img, 0, 0, 0, 255, 30, 180)
    # # plt.imshow(sorted_img);plt.show()
    # activate_button_is_active = not len(sorted_img[sorted_img != 0]) > 30
    # # print(sorted_img[sorted_img != 0])
    # print(f"activate_button_is_active {activate_button_is_active}")
    return activate_button_is_active

  def getRoi(self):
    poe_bot = self.poe_bot
    poe_bot.ui.inventory.update()
    borders = poe_bot.game_window.borders[:]
    borders[2] = 80  # top is lower a bit
    # if inventory is opened, we cant click on it, but can drag to?
    if poe_bot.ui.inventory.is_opened:
      borders[1] = 545
    return borders

  # TODO
  # supposed to drag in direction rather than abusing behavior of convertposxy
  # since if the last drag was done from the map, itll open an invisible dropdown, which will prevent from opening dropdown in future
  # and sometimes it may drag from the icons (ziggurat or burning citadel)
  def moveScreenTo(self, map_obj: MapDeviceMap):
    poe_bot = self.poe_bot
    # map_obj = random.choice(poe_bot.ui.map_device.avaliable_maps)
    print(f"going to drag to {map_obj.id}")
    orig_id = map_obj.id
    map_is_in_roi = poe_bot.game_window.isInRoi(map_obj.screen_pos.x, map_obj.screen_pos.y)
    while map_is_in_roi is False:
      self.update()
      if self.is_opened is False:
        raise poe_bot.raiseLongSleepException("map device closed during dragging to map object")
      map_obj = next((m for m in self.avaliable_maps if m.id == orig_id))
      print(map_obj.raw)
      poe_bot.ui.inventory.update()
      # ignore the inventory panel if it's opened
      x_center = poe_bot.game_window.center_point[0]
      borders = poe_bot.game_window.borders[:]
      borders[2] = 80
      if poe_bot.ui.inventory.is_opened:
        print("inventory is opened, different borders and roi")
        borders[1] = 545
        x_center = int(x_center) / 2
      roi_borders = [
        int((borders[0] + borders[1]) / 2 - 100),
        int((borders[0] + borders[1]) / 2 + 100),
        int((borders[2] + borders[3]) / 2 - 200),
        int((borders[2] + borders[3]) / 2 + 100),
      ]
      print(f"roi borders {roi_borders}")
      print(f"borders {borders}")
      map_is_in_roi = poe_bot.game_window.isInRoi(map_obj.screen_pos.x, map_obj.screen_pos.y, custom_borders=roi_borders)
      if map_is_in_roi:
        break
      print(f"map_obj.screen_pos {map_obj.screen_pos.toList()}")
      drag_from = poe_bot.game_window.convertPosXY(map_obj.screen_pos.x, map_obj.screen_pos.y, custom_borders=borders)

      drag_to = poe_bot.game_window.convertPosXY(x_center, poe_bot.game_window.center_point[1], custom_borders=borders)
      poe_bot.bot_controls.mouse.drag(drag_from, drag_to)
      time.sleep(random.uniform(0.15, 0.35))

    return map_obj

  def open(self):
    def getMapDeviceEntity():
      return next((e for e in self.poe_bot.game_data.entities.all_entities if "MapDevice" in e.path), None)

    print(f"[ui.MapDevice_Poe2.open] call {time.time()}")
    self.update()
    i = 0
    while self.is_opened is False:
      i += 1
      if i > 40:
        self.poe_bot.raiseLongSleepException("map device bugged? while map_device.opened is False:")
      self.poe_bot.refreshInstanceData(reset_timer=True)
      if i % 9 == 0:
        self.poe_bot.ui.closeAll()
        continue
      mapping_device = getMapDeviceEntity()
      if mapping_device is None:
        print("[ui.MapDevice_Poe2.open] no mapping device nearby")
        self.poe_bot.helper_functions.enterNearestPortal()
      if self.is_opened is not True:
        print(f"[ui.MapDevice_Poe2.open] opening mapping_device: {mapping_device.raw}")
        if mapping_device.location_on_screen.x == 0 and mapping_device.location_on_screen.y == 0:
          self.poe_bot.on_stuck_function()
          self.poe_bot.raiseLongSleepException("mapdevice loc on screen 0,0")

        mapping_device.hover()
        time.sleep(0.4)
        self.poe_bot.refreshInstanceData(reset_timer=True)
        mapping_device = getMapDeviceEntity()
        if mapping_device.is_targeted is False:
          continue
        self.update()
        if self.is_opened is True:
          break
        self.poe_bot.bot_controls.mouse.click()
        time.sleep(random.randint(8, 15) / 10)
        self.update()
      else:
        break
    if self.is_opened is not True:
      raise Exception("map_device.opened is not True")
    
    _i = 0
    while len(self.all_maps) == 0:
      _i += 1
      if _i > 10:
        self.poe_bot.raiseLongSleepException("[ui.MapDevice_Poe2.open] len(self.all_maps) == 0 for 10 iterations")
      time.sleep(1)
      self.update()
    return True


class Inventory:
  """
  - responsible for all the interactions with inventory

  """

  last_raw_data = None
  temp = None
  poe_bot: PoeBot
  items: List[InventoryItem]

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot

  def update(self, current_inventory_info=None):
    if current_inventory_info is None:
      current_inventory_info = self.poe_bot.backend.getOpenedInventoryInfo()
    self.last_raw_data = current_inventory_info
    self.is_opened: bool = current_inventory_info["IsOpened"]
    self.items = list(map(lambda item_raw: InventoryItem(poe_bot=self.poe_bot, item_raw=item_raw), current_inventory_info["items"]))
    return current_inventory_info

  def stashItems(self, items: List[InventoryItem]):
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
      self.poe_bot.bot_controls.keyboard.tap("DIK_I")
      time.sleep(random.randint(5, 10) / 100)
      self.update()
      return True

  #
  def getItemCoordinates(self, item_pos_x=None, item_pos_y=None, item=None):
    """
    if item is passed, ignore item_pos_x = None, item_pos_y = None
    """
    if item:
      item_pos_x = item["LocationTopLeft"]["X"]
      item_pos_y = item["LocationTopLeft"]["Y"]
    inventory_item_pos_x, inventory_item_pos_y = getInventoryItemCoordinates(item_pos_x, item_pos_y, "inventory")
    return inventory_item_pos_x, inventory_item_pos_y

  def getFilledSlots(self, force_update=False):
    """
    returns [[x,y]] of filled slots
    """
    if hasattr(self, "items") is False or force_update is True:
      self.update()
    self.update()
    items = self.items

    filled_inventory_slots = []
    for item in items:
      # print(item)
      item_uses_x = item.grid_position.x2 - item.grid_position.x1  # * item['LocationBottomRight']['Y'] - item['LocationTopLeft']['Y']
      item_uses_y = item.grid_position.y2 - item.grid_position.y1  # * item['LocationBottomRight']['Y'] - item['LocationTopLeft']['Y']
      for _x in range(item_uses_x):
        add_to_x = item.grid_position.x1 + _x
        for _y in range(item_uses_y):
          add_to_y = item.grid_position.y1 + _y
          filled_inventory_slots.append([add_to_x, add_to_y])
    return filled_inventory_slots

  def getEmptySlots(self, force_update=False):
    if hasattr(self, "items") is False or force_update is True:
      self.update()
    all_slots = []
    for x in range(12):
      for y in range(5):
        all_slots.append([x, y])
    filled_slots = self.getFilledSlots()
    return list(filter(lambda slot: slot not in filled_slots, all_slots))

  def clickOnAnEmptySlotInInventory(
    self,
  ):
    print(f"[Inventory] clickOnAnEmptySlotInInventory at {time.time()}")
    poe_bot = self.poe_bot
    bot_controls = self.poe_bot.bot_controls
    empty_slots = self.getEmptySlots(force_update=True)
    inventory_free_slot = empty_slots[0]
    pos_x, pos_y = self.getItemCoordinates(item_pos_x=inventory_free_slot[0], item_pos_y=inventory_free_slot[1])
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y, safe=False)
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    time.sleep(random.randint(20, 40) / 100)
    bot_controls.mouse.click()
    time.sleep(random.randint(20, 40) / 100)


class RitualUi(PoeBotComponent):
  def __init__(self, poe_bot):
    super().__init__(poe_bot)
    self.reset()

  def reset(self):
    self.raw: dict = {}
    self.ritual_button_visible = False
    self.ritual_button: UiElement = None
    self.tribute = 0
    self.progress_current = 0
    self.progress_total = 0
    self.visible = False
    self.screen_zone: Posx1x2y1y2 = None
    self.reroll_cost = 1000
    self.reroll_button: UiElement = None
    self.defer_button_text = "defer item"
    self.defer_button: UiElement = None
    self.items = []

  def update(self, data: dict = None):
    if data is None:
      data = self.poe_bot.backend.getRitualUi()
    self.reset()
    self.raw = data
    self.ritual_button_visible = bool(data["rt_b_v"])
    if self.ritual_button_visible is False:
      return
    self.ritual_button = UiElement(self.poe_bot, Posx1x2y1y2(*data["rt_b_sz"]))
    tribute = data.get("t", None)
    if tribute is None:
      tribute = 0
    else:
      tribute = int(tribute.replace(",", ""))
    self.tribute = tribute
    if data["p"] is not None:
      self.progress_current = int(data["p"].split("/")[0])
      self.progress_total = int(data["p"].split("/")[1])
    self.visible = bool(data["v"])
    if self.visible:
      self.screen_zone = Posx1x2y1y2(*data["sz"])
      self.reroll_cost = int(data["r_b"].split("Cost: ")[1].split(" ")[0].replace(",", ""))
      self.reroll_button = UiElement(self.poe_bot, Posx1x2y1y2(*data["r_b_sz"]))
      self.defer_button_text = data["d_b"]
      self.defer_button = UiElement(self.poe_bot, Posx1x2y1y2(*data["d_b_sz"]))
      self.items = list(map(lambda i_raw: Item(poe_bot=self.poe_bot, item_raw=i_raw), data["i"]))


class AuctionHouseUiElement(UiElement):
  def click(self, *args, **kwargs):
    val = super().click(*args, **kwargs)
    time.sleep(0.3)
    self.poe_bot.ui.auction_house.update()
    return val


class AuctionHouseUi(UiComponent):
  def reset(self):
    self.raw = {}
    self.visible = False
    self.screen_zone_raw = None
    self.gold = 0
    self.offered_item_type = ""
    self.wanted_item_type = ""
    self.market_rate_get = 0
    self.market_rate_give = 0
    self.offered_item_stock = []
    self.wanted_item_stock = []
    self.currency_picker = None
    self.current_orders = []

  def open(self):
    poe_bot = self.poe_bot
    self.update()
    if self.visible is True:
      return
    alva_entity = next((e for e in self.poe_bot.game_data.entities.all_entities if e.render_name == "Alva"), None)
    if alva_entity:
      if alva_entity.isInRoi() is False:
        self.poe_bot.mover.goToEntitysPoint(alva_entity, release_mouse_on_end=True)
      while self.visible is False:
        time.sleep(random.uniform(0.15, 0.25))
        self.update()
        poe_bot.refreshInstanceData()
        alva_entity = next((e for e in self.poe_bot.game_data.entities.all_entities if e.render_name == "Alva"))
        if alva_entity.is_targeted:
          alva_entity.click(hold_ctrl=True)
        else:
          alva_entity.hover()
      return True
    else:
      return False

  def update(self, data: dict = None):
    self.reset()
    if data is None:
      data = self.poe_bot.backend.getAuctionHouseUi()
    self.raw = data
    self.visible = bool(data.get("v", 0))
    if not self.visible:
      return
    self.screen_zone_raw = Posx1x2y1y2(*data["sz"])
    self.gold = int(data.get("g", "0").replace(",", ""))
    deal_price_raw = data.get("dc", "0")
    if deal_price_raw == "  ?":
      deal_price_raw = "0"
    self.deal_price = int(deal_price_raw.replace(",", ""))
    self.place_order_button_screen_zone = Posx1x2y1y2(*data["place_order_b_sz"])
    self.place_order_button = AuctionHouseUiElement(self.poe_bot, self.place_order_button_screen_zone)
    self.offered_item_type: str = data.get("o_i_t", "")
    self.wanted_item_type: str = data.get("w_i_t", "")

    self.i_have_field_screen_zone = Posx1x2y1y2(*data["i_h_f_sz"])
    self.i_have_field = UiElement(self.poe_bot, self.i_have_field_screen_zone)
    self.i_want_field_screen_zone = Posx1x2y1y2(*data["i_w_f_sz"])
    self.i_want_field = UiElement(self.poe_bot, self.i_want_field_screen_zone)

    self.i_have_button_screen_zone = Posx1x2y1y2(*data["i_h_b_sz"])
    self.i_have_button = AuctionHouseUiElement(self.poe_bot, self.i_have_button_screen_zone)
    self.i_want_button_screen_zone = Posx1x2y1y2(*data["i_w_b_sz"])
    self.i_want_button = AuctionHouseUiElement(self.poe_bot, self.i_want_button_screen_zone)

    self.market_ratios_texts: List[str] = data.get("market_ratios_texts", [])
    self.market_ratios = []
    for index in range(0, len(self.market_ratios_texts), 2):
      ratio = self.market_ratios_texts[index]
      if "<" in ratio:
        continue
      amount = int(self.market_ratios_texts[index + 1].replace(",", ""))
      take = float(ratio.split(":")[0])
      give = float(ratio.split(":")[1])
      self.market_ratios.append([take, give, amount])

    # for index skipped by 1, take ratio + amount
    self.currency_picker = AuctionHouseUiCurrencyPicker(self.poe_bot, data.get("c_p", {}))
    if data.get("c_o", []) is not None:
      self.current_orders = [AuctionHouseUiOrder(order) for order in data.get("c_o", [])]

  def setFieldValue(self, field: UiElement, value: int):
    bot_controls = self.poe_bot.bot_controls
    self.update()
    field.click()
    self.poe_bot.bot_controls.setClipboardText(str(value))
    bot_controls.keyboard_pressKey("DIK_LCONTROL")
    time.sleep(random.uniform(0.10, 0.2))
    bot_controls.keyboard.pressAndRelease("DIK_A")
    time.sleep(random.uniform(0.10, 0.2))
    bot_controls.keyboard.pressAndRelease("DIK_V")
    time.sleep(random.uniform(0.10, 0.2))
    bot_controls.keyboard_releaseKey("DIK_LCONTROL")
    time.sleep(random.uniform(0.10, 0.2))

  def setWantValue(self, value: int):
    self.setFieldValue(self.i_want_field, value)

  def setHaveValue(self, value: int):
    self.setFieldValue(self.i_have_field, value)


class AuctionHouseUiCurrencyPickerCategory(UiElement):
  def __init__(self, poe_bot, data):
    self.text: str = data.get("t", "")
    self.sz = Posx1x2y1y2(*data["sz"])
    super().__init__(poe_bot, self.sz)


class AuctionHouseUiCurrencyPickerElements(UiElement):
  def __init__(self, poe_bot, data):
    self.text: str = data.get("t", "")
    self.sz = Posx1x2y1y2(*data["sz"])
    self.count = int(data.get("c", 0))
    super().__init__(poe_bot, self.sz)


class AuctionHouseUiCurrencyPicker(PoeBotComponent):
  def __init__(self, poe_bot: PoeBot, data):
    super().__init__(poe_bot)
    self.visible = bool(data.get("v", 0))
    if self.visible is False:
      return
    self.sz = Posx1x2y1y2(*data["sz"])
    self.categories = [AuctionHouseUiCurrencyPickerCategory(poe_bot, cat) for cat in data.get("c", [])]
    self.presented_elements = [AuctionHouseUiCurrencyPickerElements(poe_bot, el) for el in data.get("p_e", [])]

  def openCategory(self, category_name: str):
    corresponding_category = next((cat for cat in self.categories if cat.text == category_name))
    corresponding_category.click()
    time.sleep(0.3)
    self.poe_bot.ui.auction_house.update()

  def clickElementWithText(self, element_text: str):
    corresponding_element = next((el for el in self.presented_elements if el.text == element_text))
    corresponding_element.click()
    time.sleep(0.3)
    self.poe_bot.ui.auction_house.update()


class AuctionHouseUiOrder:
  def __init__(self, data):
    self.offered_item = data.get("offered_item", "")
    self.offered_item_size = data.get("offered_item_size", 0)
    self.offered_item_ratio = data.get("offered_item_ratio", 0)
    self.wanted_item = data.get("wanted_item", "")
    self.wanted_item_size = data.get("wanted_item_size", 0)
    self.wanted_item_ratio = data.get("wanted_item_ratio", 0)
    self.is_completed = data.get("is_completed", 0)
    self.is_canceled = data.get("is_canceled", 0)


x_offset = 12
y_offset = 90


def assignStashItemPositions(item):
  item["LocationTopLeft"] = {"X": 0, "Y": 0}
  item["LocationBottomRight"] = {"X": 0, "Y": 0}
  item["LocationTopLeft"]["X"] = ceil((item["TopLeft"]["X"] - x_offset) / INVENTORY_SLOT_CELL_SIZE)
  item["LocationTopLeft"]["Y"] = ceil((item["TopLeft"]["Y"] - y_offset) / INVENTORY_SLOT_CELL_SIZE)

  item["LocationBottomRight"]["X"] = ceil((item["BottomRight"]["X"] - x_offset) / INVENTORY_SLOT_CELL_SIZE)
  item["LocationBottomRight"]["Y"] = ceil((item["BottomRight"]["Y"] - y_offset) / INVENTORY_SLOT_CELL_SIZE)


class StashTabSwitchButton:
  def __init__(self, poe_bot: PoeBot, pos_x1x2x3x4: list) -> None:
    self.poe_bot = poe_bot
    self.x1 = pos_x1x2x3x4[0]
    self.x2 = pos_x1x2x3x4[1]
    self.y1 = pos_x1x2x3x4[2]
    self.y2 = pos_x1x2x3x4[3]

  def click(self):
    poe_bot = self.poe_bot
    x_offset = 5
    pos_x = random.randint(self.x1 + x_offset, self.x2 - x_offset)
    y_offset = 5
    pos_y = random.randint(self.y1 + y_offset, self.y2 - y_offset)
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
    poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    time.sleep(random.randint(5, 10) / 100)
    poe_bot.bot_controls.mouse.click()
    time.sleep(random.randint(1, 8) / 10)


class Stash:
  """
  - responsible for all the interactions with stash

  """

  poe_bot: PoeBot
  temp: StashTempData

  is_opened: bool
  current_tab_index: int
  stash_tab_switch_buttons: List[StashTabSwitchButton]
  items: List[StashItem]
  is_opened = False
  opened_tab_type: str
  #
  last_raw_data = None
  all_items_sorted: list

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.temp = StashTempData(unique_id=self.poe_bot.unique_id)

    self.reset()

  def reset(self):
    self.stash_tab_switch_buttons = []

  def update(self, raw_stash_data=None):
    if raw_stash_data is None:
      raw_stash_data = self.poe_bot.backend.getOpenedStashInfo()
    self.last_raw_data = raw_stash_data
    self.reset()
    self.is_opened = raw_stash_data["status"] == "opened"
    self.current_tab_index = raw_stash_data["tab_index"]
    if self.is_opened is True:
      self.total_stash_tab_count: int = raw_stash_data["total_stash_tab_count"]
      self.opened_tab_type = raw_stash_data["stash_tab_type"]
      for pos_x1x2x3x4 in raw_stash_data["s_b_p_ls"]:
        button = StashTabSwitchButton(poe_bot=self.poe_bot, pos_x1x2x3x4=pos_x1x2x3x4)
        self.stash_tab_switch_buttons.append(button)
      self.stash_tab_switch_buttons.sort(key=lambda b: b.x1)
      self.current_tab_items = list(
        map(lambda item_raw: StashItem(poe_bot=self.poe_bot, item_raw=item_raw, tab_index=self.current_tab_index), raw_stash_data["items"])
      )
    else:
      self.current_tab_items = []

    self.getInfo(raw_stash_data)
    return raw_stash_data

  def open(self):
    print(f"[ui.Stash.open] call {time.time()}")
    self.update()
    self.poe_bot.ui.inventory.update()
    if self.is_opened is True and self.poe_bot.ui.inventory.is_opened is True:
      return "success"
    i = 0
    while self.is_opened is False:
      i += 1
      if i > 14:
        self.poe_bot.raiseLongSleepException("map device bugged? while map_device.opened is False:")
      if i % 5 == 0:
        for _i in range(random.randint(1, 3)):
          self.poe_bot.ui.closeAll()
      self.poe_bot.refreshInstanceData(reset_timer=True)
      self.poe_bot.game_data.updateLabelsOnGroundEntities()
      stash_box = next((e for e in self.poe_bot.game_data.labels_on_ground_entities if "MiscellaneousObjects/Stash" in e.path), None)
      if stash_box is None:
        print("[ui.Stash.open] no stash_box nearby")
        self.poe_bot.helper_functions.enterNearestPortal()
      if self.is_opened is not True:
        print(f"[ui.Stash.open] opening stash_box: {stash_box.raw}")
        if stash_box.location_on_screen.x == 0 and stash_box.location_on_screen.y == 0:
          self.poe_bot.on_stuck_function()
          self.poe_bot.raiseLongSleepException("stash_box loc on screen 0,0")
        stash_box.hover(y_offset=-10)
        time.sleep(0.4)
        self.update()
        if self.is_opened is True:
          break
        self.poe_bot.bot_controls.mouse.click()
        time.sleep(random.randint(8, 15) / 10)
        self.update()
      else:
        break
    if self.is_opened is not True:
      raise Exception("[ui.Stash.open] Stash.is_opened is not True")
    return True

  def openTabIndex(self, index: int, method="mouse"):
    poe_bot = self.poe_bot
    opened_stash_info = self.update()
    if self.current_tab_index == index:
      print(f"stash.openTabIndex {self.current_tab_index} == {index}")
      return True
    current_tab_index = opened_stash_info["tab_index"]
    if method == "keyboard":
      original_tab_index = current_tab_index
      distance = index - current_tab_index
      if distance < 0:
        key_to_tap = "DIK_NUMPAD4"
      else:
        key_to_tap = "DIK_NUMPAD6"

      for i in range(abs(distance)):
        self.poe_bot.bot_controls.keyboard.tap(key_to_tap)
        time.sleep(random.randint(2, 4) / 10)
        opened_stash_info = self.update()
        current_tab_index = opened_stash_info["tab_index"]
        if current_tab_index == original_tab_index:
          self.poe_bot.bot_controls.keyboard.tap("DIK_NUMLOCK")
          self.poe_bot.bot_controls.keyboard.tap(key_to_tap)
          time.sleep(random.randint(2, 4) / 10)
    elif method == "mouse":
      i = 0
      while True:
        i += 1
        if i > 100:
          poe_bot.raiseLongSleepException(f"cannot open stash tab with index {index}")
        self.stash_tab_switch_buttons[index].click()
        time.sleep(random.randint(20, 40) / 100)
        self.update()
        if self.current_tab_index != index:
          continue
        else:
          break
      return True

  def getAllItems(self) -> List[StashItem]:
    all_items = []
    for stash_tab in self.temp.stash_tabs_data:
      for item in stash_tab["items"]:
        item["tab_index"] = stash_tab["tab_index"]
        all_items.append(StashItem(poe_bot=self.poe_bot, item_raw=item))
    return all_items

  def updateStashTemp(self, update_premium=False):
    """ """
    print(f"stash.updateStashTemp call {time.time()}")
    if self.temp is None:
      raise Exception(".self.temp is None")
    self.open()
    self.temp.unsorted_items = []
    can_check_tabs = self.total_stash_tab_count
    if can_check_tabs > 4:
      print(f"[Stash.updateStashTemp] will check only 5 tabs out of {self.total_stash_tab_count}")
      can_check_tabs = 5

    tab_order = [x for x in range(can_check_tabs)]
    tab_order.pop(tab_order.index(self.current_tab_index))
    random.shuffle(tab_order)
    # 0 tab here
    for i in tab_order:
      self.openTabIndex(i)
      if self.opened_tab_type == "FragmentStash":
        print("current stash tab is fragment tab")
        screen_pos_x, screen_pos_y = self.poe_bot.convertPosXY(x=random.randint(245, 335), y=random.randint(100, 118))
        self.poe_bot.bot_controls.mouse.click()
        time.sleep(random.randint(5, 20) / 10)
        self.update()
      opened_time = time.time()
      total_sleep_time = sum(list(map(lambda i: random.randint(5, 20) / 100, self.current_tab_items[:40]))) + random.randint(10, 20) / 10
      if len(self.current_tab_items) != 0:
        items_to_hover = random.choices(self.current_tab_items, k=int(random.randint(1, len(self.current_tab_items)) / 10))
        for item in items_to_hover:
          item.hover()
          time.sleep(random.randint(10, 20) / 10)

      sleep_end_time = opened_time + total_sleep_time
      if sleep_end_time > time.time():
        sleep_more_for = sleep_end_time - time.time()
        time.sleep(sleep_more_for)
    print("setting affinities")
    print('trying to detect "map" affinity')
    maps_count = list(map(lambda tab: len(list(filter(lambda item_raw: item_raw["m_t"] != 0, tab["items"]))), self.temp.stash_tabs_data))
    maximum_maps_count = max(maps_count)
    if maximum_maps_count != 0:
      tab_with_maximum_maps = self.temp.stash_tabs_data[maps_count.index(maximum_maps_count)]
      tab_with_maximum_maps_index = tab_with_maximum_maps["tab_index"]
      print(f"tab_with_maximum_maps {tab_with_maximum_maps_index}")
      self.temp.affinities["map"] = tab_with_maximum_maps_index
    else:
      print("none of stash tabs have maps")
    self.temp.save()

  def unstashItem(self, item: StashItem):
    pass

  def pickItems(self, items: List[StashItem], return_new_items=True) -> List[InventoryItem]:
    inventory = self.poe_bot.ui.inventory
    inventory.update()
    items_grid_position_backup = list(map(lambda i: (i.grid_position.x1, i.grid_position.y1), inventory.items))
    self.poe_bot.ui.clickMultipleItems(items)
    inventory.update()
    new_items = list(filter(lambda i: (i.grid_position.x1, i.grid_position.y1) not in items_grid_position_backup, inventory.items))
    return new_items

  def unstashItems(self, items: List[StashItem]):
    self.pickItems(items=items)

  def getFilledSlots(self, force_update=False):
    """
    returns [[x,y]] of filled slots
    """
    if hasattr(self, "current_tab_items") is False or force_update is True:
      self.update()
    self.update()
    items = self.current_tab_items

    filled_inventory_slots = []
    for item in items:
      # print(item)
      item_uses_x = item.grid_position.x2 - item.grid_position.x1  # * item['LocationBottomRight']['Y'] - item['LocationTopLeft']['Y']
      item_uses_y = item.grid_position.y2 - item.grid_position.y1  # * item['LocationBottomRight']['Y'] - item['LocationTopLeft']['Y']
      for _x in range(item_uses_x):
        add_to_x = item.grid_position.x1 + _x
        for _y in range(item_uses_y):
          add_to_y = item.grid_position.y1 + _y
          filled_inventory_slots.append([add_to_x, add_to_y])
    return filled_inventory_slots

  def getEmptySlots(self, force_update=False):
    if hasattr(self, "current_tab_items") is False or force_update is True:
      self.update()
    all_slots = []
    for x in range(12):
      for y in range(12):
        all_slots.append([x, y])
    filled_slots = self.getFilledSlots()
    return list(filter(lambda slot: slot not in filled_slots, all_slots))

  def placeItemsAcrossStash(self, items_to_stash: List[Item], can_sleep=True):
    print("placing items across the stash")
    self.open()
    stash_tabs_indexes_sorted = [i for i in range(1, 4)]
    random.shuffle(stash_tabs_indexes_sorted)
    stashed_all = False
    map_stash_tab_index = self.poe_bot.ui.stash.temp.affinities.get("map", None)

    if self.current_tab_index in stash_tabs_indexes_sorted:
      try:
        stash_tabs_indexes_sorted.remove(self.current_tab_index)
        stash_tabs_indexes_sorted.insert(0, self.current_tab_index)
      except ValueError:
        print("val err")

    if map_stash_tab_index:
      try:
        stash_tabs_indexes_sorted.remove(map_stash_tab_index)
        stash_tabs_indexes_sorted.append(map_stash_tab_index)
      except ValueError:
        print("val err")

    print(f"indexes {stash_tabs_indexes_sorted}")
    for stash_tab_index in stash_tabs_indexes_sorted:
      self.openTabIndex(stash_tab_index)
      stash_tab_empty_cells = self.getEmptySlots()
      items_to_stash_in_current_tab = []
      if stash_tab_index == map_stash_tab_index:
        # leave 80*1.2 cells for maps
        maps_in_current_stash = list(filter(lambda item: item.getType() == "map", self.current_tab_items))
        maps_count = len(maps_in_current_stash)
        empty_cells_count = len(stash_tab_empty_cells)
        maps_slots_count = 96  # 80*1.2
        related_to_maps_slots_count = maps_slots_count - maps_count
        can_use_cells = empty_cells_count - related_to_maps_slots_count
        print(f"its a map stash tab, so only able to use {can_use_cells} here")
        if can_use_cells <= 0:
          self.poe_bot.raiseLongSleepException("could stash items across stash cos trying to place in map tab")
        stash_tab_empty_cells = stash_tab_empty_cells[:can_use_cells]

      for asdsda in stash_tab_empty_cells:
        if len(items_to_stash) == 0:
          stashed_all = True
          break
        items_to_stash_in_current_tab.append(items_to_stash.pop(0))
      print(f"placing {len(items_to_stash_in_current_tab)} items in current stash tab")
      self.poe_bot.ui.clickMultipleItems(
        items_to_stash_in_current_tab, add_delay_before_last_clicks=can_sleep, skip_items=can_sleep, random_sleep=can_sleep
      )
      if stashed_all is True:
        break
    if stashed_all is False:
      self.poe_bot.raiseLongSleepException("couldnt stash all items")

  # TODO rewrite below
  def getInfo(self, current_stash_info=None):
    if current_stash_info is None:
      current_stash_info = self.poe_bot.backend.getOpenedStashInfo()
    self.last_raw_data = current_stash_info
    if self.temp is not None and current_stash_info["status"] == "opened":
      for item in current_stash_info["items"]:
        assignStashItemPositions(item)
        item["tab_index"] = current_stash_info["tab_index"]
      self.temp.updateTabInfo(current_stash_info)
    return current_stash_info
