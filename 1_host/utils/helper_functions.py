from __future__ import annotations
import typing
import os
import pickle
from typing import List


# readability
if typing.TYPE_CHECKING:
  from .gamehelper import PoeBot, Entity
  from .controller import VMHostPuppeteer
  from .ui import InventoryItem

'''
all the functions which require any functions from other libraries
'''


import time
import random
from math import dist

import numpy as np

# readability
from .utils import getInventoryItemCoordinates, getFourPoints
from .constants import IGNOREKEYWORDSTOSEARCH, KEYWORDSTOSEARCH, shitty_uniques_metadatas

class HelperFunctions:
  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot

  def checkIfEntityOnCurrenctlyPassableArea(self, grid_pos_x, grid_pos_y, radius = 10):
    poe_bot = self.poe_bot
    # print(e.grid_position.y, e.grid_position.x)
    currently_passable_area = poe_bot.game_data.terrain.currently_passable_area
    currently_passable_area_around_entity = currently_passable_area[grid_pos_y-radius:grid_pos_y+radius, grid_pos_x-radius:grid_pos_x+radius]
    nearby_passable_points = np.where(currently_passable_area_around_entity != 0)
    if len(nearby_passable_points[0]) > 1:
      return True
    else:
      return False
    
  def needToExplore(self, point_to_go, radius = 35)-> bool:
    poe_bot = self.poe_bot
    five_points = getFourPoints(point_to_go[0],point_to_go[1], radius=radius)
    need_to_explore = False
    for point in five_points:
      if poe_bot.game_data.terrain.visited_area[point[1], point[0]] == 0:
        need_to_explore = True
    return need_to_explore
  def lvlUpGem(self):
    '''
    returns 
    1 if success
    0 if did nothing
    '''
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    gems_to_level_info = poe_bot.backend.getGemsToLevelInfo()
    if len(gems_to_level_info) == 0:
      return 0
    gem_to_level = gems_to_level_info[0]

    pos_x,pos_y = poe_bot.convertPosXY(int(gem_to_level['center_location']['X'] + 49),int(gem_to_level['center_location']['Y']), safe=False)
    bot_controls.mouse.setPosSmooth(pos_x,pos_y)
    time.sleep(random.randint(5,20)/100)
    bot_controls.mouse.click()
    return 1
  def getToMainMenu(self, close_all_ui = True):
    print('#getToMainMenu going to main menu')
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    if close_all_ui:
      for _i in range(random.randint(2,4)):
        self.poe_bot.ui.closeAll()
    
    bot_controls.keyboard.tap('DIK_ESCAPE')
    time.sleep(random.randint(20,40)/100)
    exit_to_login_screen_button_zone = [425,600,303,313] # [x1 x2 y1 y2]
    pos_x, pos_y = poe_bot.convertPosXY(random.randint(exit_to_login_screen_button_zone[0],exit_to_login_screen_button_zone[1]), random.randint(exit_to_login_screen_button_zone[2],exit_to_login_screen_button_zone[3]))
    for _gettomainmenu_iter in range(1):
      poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      time.sleep(random.randint(5,15)/100)
      poe_bot.bot_controls.mouse.click()
      time.sleep(random.randint(20,50)/100)
    time.sleep(random.randint(5,7))
    game_state = poe_bot.backend.getPartialData()['g_s']
    print(f'game_state {game_state}')
    if game_state == 0 or game_state == 20:
      # poe_bot.helper_functions.dumpError('game_crash_f_cv2img', poe_bot.getImage())
      poe_bot.raiseLongSleepException('game crashed')
    i = 0  
    while game_state != 1:
      print(f'game_state {game_state} iteration: {i}')
      i += 1
      if i == 99:
        poe_bot.helper_functions.dumpError('cannot_load_main_menu_f_cv2img', poe_bot.getImage())
        poe_bot.raiseLongSleepException('#getToMainMenu cannot get to main menu')
      time.sleep(0.1)
      game_state = poe_bot.backend.getPartialData()['g_s']
      if game_state == 1:
        break
  def logIn(self, log_in_cooldown = 0):
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    password = poe_bot.password

    print(f'clicking on this operation requires account to be logged in #TODO check if visible and text')
    partial_data = poe_bot.backend.getPartialData()
    screen_pos = partial_data['w']
    stash_item_pos_x,stash_item_pos_y = screen_pos[0]+500, screen_pos[2]+400
    for i in range(random.randint(2,4)):
      bot_controls.mouse.setPosSmooth(int(stash_item_pos_x),int(stash_item_pos_y))
      time.sleep(random.randint(10,15)/100)
      bot_controls.mouse.click()
    time.sleep(random.randint(10,15)/10)

    for log_in_iter in range(1):
      print(f'attempt to log in {log_in_iter}')
      if password and password != "None":
        print("going to input password")
        print(f'game window {poe_bot.game_window}')
        partial_data = poe_bot.backend.getPartialData()
        screen_pos = partial_data['w']
        print(f'partial data screen pos {screen_pos}')
        stash_item_pos_x,stash_item_pos_y = screen_pos[0]+490, screen_pos[2]+531
        for i in range(3):
          bot_controls.mouse.setPosSmooth(int(stash_item_pos_x),int(stash_item_pos_y))
          time.sleep(random.randint(10,15)/100)
          bot_controls.mouse.click()
          time.sleep(random.randint(10,15)/100)
        print("#inputPassword")
        bot_controls.setClipboardText(password)
        time.sleep(random.randint(20,40)/100)
        bot_controls.keyboard_pressKey('DIK_LCONTROL')
        time.sleep(random.randint(20,40)/100)
        bot_controls.keyboard.tap("DIK_A")
        time.sleep(random.randint(20,40)/100)
        bot_controls.keyboard.tap("DIK_V")
        time.sleep(random.randint(20,40)/100)
        bot_controls.keyboard_releaseKey('DIK_LCONTROL')
        time.sleep(random.randint(20,40)/100)
      else:
        print('no need to input')
      print("#logIn")
      bot_controls.keyboard.tap('DIK_RETURN')
      game_state = poe_bot.backend.getPartialData()['g_s']
      if game_state == 0:
        poe_bot.raiseLongSleepException('game crashed')

      i = 0  
      while game_state != 10:
        print(f'waiting till character selection window to appear game_state {game_state} iteration: {i} {time.time()}')
        i += 1
        if i == 100:
          game_img = poe_bot.getImage()
          poe_bot.helper_functions.dumpError('cannot_log_in_f_cv2img', game_img)
          poe_bot.raiseLongSleepException('onDisconnectFunc cannot get to char select screen after main menu')
        time.sleep(0.5)
        game_state = poe_bot.backend.getPartialData()['g_s']
      print(f'got onto char selection screen')
      time.sleep(random.randint(60,80)/10)
      print(f'clicking log in')
      bot_controls.keyboard.tap('DIK_RETURN')
      time.sleep(random.randint(60,80)/10)
      break
    poe_bot.on_disconnect_function = None
    game_state = poe_bot.backend.getPartialData()['g_s']
    if game_state == 0:
      poe_bot.raiseLongSleepException('game crashed')
    i = 0  
    while game_state != 20:
      print(f'game_state {game_state} iteration: {i}')
      i += 1
      if i == 50:
        print(f'clicking log in 2nd time')
        bot_controls.keyboard.tap('DIK_RETURN')
        time.sleep(random.randint(60,80)/10)
      if i == 99:
        poe_bot.helper_functions.dumpError('cannot_choose_character_f_cv2img', poe_bot.getImage())
        poe_bot.raiseLongSleepException('onDisconnectFunc cannot get to game from main char select screen')
      time.sleep(0.1)
      game_state = poe_bot.backend.getPartialData()['g_s']
    print('logged in')
    is_loading = True
    while is_loading:
      time.sleep(0.5)
      is_loading = poe_bot.backend.getPartialData()["IsLoading"]
      print(f'is_loading {is_loading} {time.time()}')
    time.sleep(random.randint(50,100)/10)
    # poe_bot.raiseLongSleepException('supposed to be in game, remove me if ok')
  def getToCharSelectionFromGame(self, close_all_ui = True):
    self.poe_bot.logger.writeLine(f'getting to char selection screen from game')
    poe_bot = self.poe_bot
    bot_controls = self.poe_bot.bot_controls
    bot_controls.releaseAll()
    if close_all_ui:
      for _i in range(random.randint(2,4)):
        self.poe_bot.ui.closeAll()
    bot_controls.keyboard.tap('DIK_ESCAPE')
    time.sleep(random.randint(20,40)/100)
    exit_to_login_screen_button_zone = self.poe_bot.ui.escape_control_panel.charecter_selection_button_zone
    pos_x, pos_y = poe_bot.convertPosXY(random.randint(exit_to_login_screen_button_zone[0],exit_to_login_screen_button_zone[1]), random.randint(exit_to_login_screen_button_zone[2],exit_to_login_screen_button_zone[3]))
    for _gettomainmenu_iter in range(1):
      poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      time.sleep(random.randint(5,15)/100)
      poe_bot.bot_controls.mouse.click()
      time.sleep(random.randint(20,50)/100)

    # or /exit
    # bot_controls.keyboard.tap('DIK_RETURN')
    # time.sleep(random.randint(3,7)/10)
    # bot_controls.keyboard.tap('DIK_SLASH')
    # time.sleep(random.randint(5,15)/100)
    # bot_controls.keyboard.tap('DIK_E')
    # time.sleep(random.randint(5,15)/100)
    # bot_controls.keyboard.tap('DIK_X')
    # time.sleep(random.randint(5,15)/100)
    # bot_controls.keyboard.tap('DIK_I')
    # time.sleep(random.randint(5,15)/100)
    # bot_controls.keyboard.tap('DIK_T')
    # time.sleep(random.randint(3,7)/10)
    # bot_controls.keyboard.tap('DIK_RETURN')
    time.sleep(random.randint(5,7))
    i = 0  
    game_state = poe_bot.backend.getPartialData()['g_s']
    while game_state != 10:
      print(f'waiting till character selection window to appear game_state {game_state} iteration: {i} {time.time()}')
      i += 1
      if i == 100:
        game_img = poe_bot.getImage()
        poe_bot.helper_functions.dumpError('cannot_log_in_f_cv2img', game_img)
        poe_bot.raiseLongSleepException('onDisconnectFunc cannot get to char select screen after main menu')
      time.sleep(0.5)
      game_state = poe_bot.backend.getPartialData()['g_s']
    print(f'got onto char selection screen')
  def getIntoWorldFromCharSelection(self):
    poe_bot = self.poe_bot
    bot_controls = self.poe_bot.bot_controls
    print(f'clicking log in')
    bot_controls.keyboard.tap('DIK_RETURN')
    time.sleep(random.randint(60,80)/10)
    poe_bot.on_disconnect_function = None
    game_state = poe_bot.backend.getPartialData()['g_s']
    if game_state == 0:
      poe_bot.raiseLongSleepException('game crashed')
    i = 0  
    while game_state != 20:
      print(f'game_state {game_state} iteration: {i}')
      i += 1
      if i == 50:
        print(f'clicking log in 2nd time')
        bot_controls.keyboard.tap('DIK_RETURN')
        time.sleep(random.randint(60,80)/10)
      if i == 99:
        poe_bot.helper_functions.dumpError('cannot_get_to_game_world_from_char_selection_f_cv2img', poe_bot.getImage())
        poe_bot.raiseLongSleepException('onDisconnectFunc cannot get to game from main char select screen')
      time.sleep(0.1)
      game_state = poe_bot.backend.getPartialData()['g_s']
    print('logged in')
    is_loading = True
    while is_loading:
      time.sleep(0.5)
      is_loading = poe_bot.backend.getPartialData()["IsLoading"]
      print(f'is_loading {is_loading} {time.time()}')
    time.sleep(random.randint(50,100)/10)
  def relog(self):
    self.relogThroughCharSelectionScreen()
  def relogThroughCharSelectionScreen(self):
    self.poe_bot.logger.writeLine(f'relogging through char select screen')
    bot_controls = self.poe_bot.bot_controls
    bot_controls.releaseAll()
    self.getToCharSelectionFromGame()
    self.getIntoWorldFromCharSelection()
    raise Exception('logged in, success')
  def relogThroughLogInScreen(self):
    self.poe_bot.logger.writeLine(f'relogging through log in screen')
    bot_controls = self.poe_bot.bot_controls
    bot_controls.releaseAll()
    self.getToMainMenu()
    relog_cooldown_secs = random.randint(60,180)
    print(f'relog cooldown: ', relog_cooldown_secs)
    time.sleep(relog_cooldown_secs)
    self.logIn()
    raise Exception('logged in, success')
  def clickNecropolisTabletIfPresentedNearEntity(self, entity:Entity):
    poe_bot = self.poe_bot
    visible_labels = poe_bot.backend.getVisibleLabels()
    necropolis_tablets = list(filter(lambda e: e.path == "Metadata/Terrain/Leagues/Necropolis/Objects/NecropolisCorpseMarker", poe_bot.game_data.entities.all_entities))
    necropolis_tablet_to_click = None
    for necropolis_tablet in necropolis_tablets:
      tablet_distance = dist( (necropolis_tablet.grid_position.x, necropolis_tablet.grid_position.y), (entity.grid_position.x, entity.grid_position.y))
      if tablet_distance < 20:
        print(f'tablet_distance < 20 between {necropolis_tablet.raw} and {entity.raw}')
        necropolis_tablet_to_click = necropolis_tablet
        break
    if necropolis_tablet_to_click:
      print(f'gonna click {necropolis_tablet_to_click.raw}')
      necropolis_tablet_visible_label = next( (l for l in visible_labels if l['id'] == necropolis_tablet_to_click.id), None)
      can_click_necropolis_tablet = True
      if necropolis_tablet_visible_label is None:
        print(f'bug? no visible labels for necropolis table {necropolis_tablet_to_click.raw} visible_labels: {visible_labels}')
        can_click_necropolis_tablet = False
      click_necropolis_tablet_iter = 0
      while can_click_necropolis_tablet:
        click_necropolis_tablet_iter+=1
        if click_necropolis_tablet_iter % 7 == 0:
          poe_bot.refreshInstanceData(reset_timer=True)
        print(f'click_necropolis_tablet_iter {click_necropolis_tablet_iter}')
        if click_necropolis_tablet_iter > 50:
          poe_bot.helper_functions.dumpError('necropolis_table_on_loot_f_cv2img_visiblelabels', [poe_bot.getImage(), visible_labels])
          poe_bot.on_stuck_function()
          # poe_bot.raiseLongSleepException('couldnt click on necropolis tablet for 50 iterations')
        coords_to_click = ( int( (necropolis_tablet_visible_label["p_o_s"]["y1"] + necropolis_tablet_visible_label["p_o_s"]["y2"])/2 ), int( (necropolis_tablet_visible_label["p_o_s"]["x1"] + necropolis_tablet_visible_label["p_o_s"]["x2"])/2 ) )
        pos_x, pos_y = poe_bot.convertPosXY(coords_to_click[1],coords_to_click[0])
        print(f'#click_necropolis_tablet_iter set mouse at {pos_x, pos_y} at {time.time()}')
        poe_bot.bot_controls.mouse.setPosSmooth(pos_x,pos_y, wait_till_executed=False)
        print(f'click_necropolis_tablet_iter click mouse at {pos_x, pos_y} at {time.time()}')
        poe_bot.bot_controls.mouse.click()

        visible_labels = poe_bot.backend.getVisibleLabels()
        necropolis_tablet_visible_label = next( (l for l in visible_labels if l['id'] == necropolis_tablet_to_click.id), None)
        if necropolis_tablet_visible_label is None:
          print(f'necropolis_tablet_to_click tablet label disappeared {necropolis_tablet_to_click.raw}')
          break
  def waitForPortalNearby(self, wait_for_seconds = 3, distance = 25):
    poe_bot = self.poe_bot
    start_time = time.time()
    time_now = time.time()
    poe_bot.refreshInstanceData()
    nearby_portals = list(filter(lambda e: "Metadata/MiscellaneousObjects/MultiplexPortal" in e.path and e.distance_to_player < distance, poe_bot.game_data.entities.all_entities))
    print(f"#waitForNewPortals {time_now}")
    while time_now < start_time + wait_for_seconds:
      time_now = time.time()
      poe_bot.refreshInstanceData()
      nearby_portals = list(filter(lambda e: "Metadata/MiscellaneousObjects/MultiplexPortal" in e.path and e.distance_to_player < distance, poe_bot.game_data.entities.all_entities))
      print("checking if portals around")
      if len(nearby_portals) != 0:
        print("there is a portal nearby")
        return True
      
    return False
  def dumpError(self, filename, pickle_data):
    folder_dir = './error_dumps'
    if not os.path.exists(folder_dir):
      os.makedirs(folder_dir)
    file_path = f"{folder_dir}/{int(time.time())}_{filename}"
    f = open(file_path, 'wb')
    pickle.dump(pickle_data, f)
    f.close()
    print(f'saved at {file_path}')
  def openPortal(self):
    poe_bot = self.poe_bot
    bot_controls = self.poe_bot.bot_controls

    if poe_bot.debug is True:print(f'#openPortal call {time.time()}')
    inventory = poe_bot.ui.inventory
    inventory.update()
    portal_scrolls:List[InventoryItem] = list(filter(lambda i: i.name == "Portal Scroll", inventory.items))
    bot_controls.mouse.release()
    if len(portal_scrolls) != 0:
      print(f'we have portal scrolls in inventory')
      portal_scroll = portal_scrolls[0]
      inventory.open()
      time.sleep(random.randint(5,20)/100)
      portal_scroll.click(button="right")
      portal_nearby = self.waitForPortalNearby(poe_bot=poe_bot, wait_for_seconds=1)
      poe_bot.ui.closeAll()
      print(f'portal_nearby {portal_nearby}')
    # else:
    #   print(f'we dont have portal scrolls in inventory')
    #   is_portal_gem = checkIfPortalGem(poe_bot=poe_bot)
    #   if is_portal_gem is False:
    #     print(f'is_portal_gem {is_portal_gem} swapping weapons')
    #     time.sleep(random.randint(10,20)/100)
    #     bot_controls.keyboard.tap("DIK_X")
    #   for i in range(random.randint(1,2)):
    #     time.sleep(random.randint(25,35)/100)
    #     bot_controls.keyboard.tap("DIK_R")
    #     portal_nearby = waitForPortalNearby(poe_bot=poe_bot, wait_for_seconds=1)
    #     if portal_nearby is True:
    #       break
    #   is_portal_gem = checkIfPortalGem(poe_bot=poe_bot)
    #   print(f'portal_nearby {portal_nearby}')
    #   if is_portal_gem is True:
    #     print(f'is_portal_gem {is_portal_gem} swapping weapons')
    #     bot_controls.keyboard.tap("DIK_X")
    #     time.sleep(random.randint(10,20)/100)
    
    if poe_bot.debug is True:print(f'#openPortal return {time.time()}')
    return 
  def waitForNewPortals(self, wait_for_seconds = 10, sleep_time=3):
    poe_bot = self.poe_bot
    start_time = time.time()
    time_now = time.time()
    nearby_portals = list(filter(lambda e: "Metadata/MiscellaneousObjects/MultiplexPortal" in e.path, poe_bot.game_data.entities.all_entities))
    nearby_portals_ids = [e.grid_position.x for e in nearby_portals]
    nearby_portals_ids_sum = sum(list(map(lambda e: e.id, nearby_portals)))
    print(f"#waitForNewPortals {time_now}")
    changed = False
    while time_now < start_time + wait_for_seconds:
      time_now = time.time()
      poe_bot.refreshInstanceData()
      current_nearby_portals = list(filter(lambda e: "Metadata/MiscellaneousObjects/MultiplexPortal" in e.path, poe_bot.game_data.entities.all_entities))
      current_portal_ids = [e.grid_position.x for e in current_nearby_portals]
      current_nearby_portals_ids_sum = sum(list(map(lambda e: e.id, current_nearby_portals)))
      print("checking if portals changed")
      if nearby_portals_ids != current_portal_ids:
        print("portals changed")
        changed = True
        break
      elif current_nearby_portals_ids_sum != nearby_portals_ids_sum:
        print("portals changed cos different sum")
        changed = True
        break
      else:
        time.sleep(0.2)
    if changed == True and sleep_time > 0:
      time.sleep(random.randint(int(sleep_time*100*0.8), int(sleep_time*100*1.2))/100)
    return changed
  def sellItems(self,items_to_sell:List[InventoryItem], skip_items = False, shuffle_items = True):
    poe_bot = self.poe_bot
    inventory = self.poe_bot.ui.inventory
    if len(items_to_sell) == 0:
      return True
    i = 0
    print(f'opening trade with lilly')
    while True:
      i += 1
      if i == 40:
        poe_bot.helper_functions.relog()
        raise Exception('cant open trade with buyer_entity')
      inventory.update()
      if inventory.is_opened is True:
        break
      poe_bot.refreshInstanceData(reset_timer=False)
      buyer_entity = next((e for e in poe_bot.game_data.entities.all_entities if 'LillyHideout' in e.path), None)
      if not buyer_entity:
        poe_bot.raiseLongSleepException('buyer entity is null')
      buyer_entity.click(hold_ctrl=True)
      time.sleep(random.randint(50,100)/100)


    self.poe_bot.ui.clickMultipleItems(items_to_sell, skip_items = skip_items, shuffle_items=shuffle_items)

    # accept trade
    pos_x, pos_y = 120, 620
    pos_x,pos_y = poe_bot.convertPosXY(pos_x,pos_y, safe = False)
    print(pos_x,pos_y)
    poe_bot.bot_controls.mouse.setPosSmooth(int(pos_x),int(pos_y))
    time.sleep(random.randint(5,20)/100)
    poe_bot.bot_controls.mouse.click()
    time.sleep(random.randint(5,20)/10)
    poe_bot.ui.closeAll()
    return True
  def getToHideout(self):
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    bot_controls.keyboard.tap('DIK_RETURN')
    time.sleep(1)
    bot_controls.keyboard.tap('DIK_SLASH')
    time.sleep(0.1)
    bot_controls.keyboard.tap('DIK_H')
    time.sleep(0.1)
    bot_controls.keyboard.tap('DIK_I')
    time.sleep(0.1)
    bot_controls.keyboard.tap('DIK_D')
    time.sleep(0.1)
    bot_controls.keyboard.tap('DIK_E')
    time.sleep(0.1)
    bot_controls.keyboard.tap('DIK_O')
    time.sleep(0.1)
    bot_controls.keyboard.tap('DIK_U')
    time.sleep(0.1)
    bot_controls.keyboard.tap('DIK_T')
    time.sleep(1)
    bot_controls.keyboard.tap('DIK_RETURN')

  def getPortals(self):
    return list(filter(lambda entity: 'MultiplexPortal' in entity.path, self.poe_bot.game_data.entities.all_entities))

  def getToPortal(self,check_for_map_device = True, refresh_area = True):
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    
    poe_bot.refreshInstanceData()
    if check_for_map_device is True:
      map_device = next( (e for e in poe_bot.game_data.entities.all_entities if 'MappingDevice' in e.path), None)
      if not map_device:
        raise Exception("No mapping device")
    portals = self.getPortals()
    if len(portals) == 0:
      raise Exception("No portals")
    
    portals.sort(key=lambda e: e.distance_to_player)
    orig_portal_to_enter = portals[0]

    original_area_raw_name = poe_bot.game_data.area_raw_name
    print(f'original_area_raw_name {original_area_raw_name}')
    _i = 0 # iterations
    while True:
      _i += 1
      if _i % 10 == 9:
        poe_bot.ui.closeAll()
        poe_bot.backend.forceRefreshArea()
        time.sleep(0.2)
      if _i > 30:
        poe_bot.raiseLongSleepException('#getToPortal if _i > 30')
      try:
        poe_bot.refreshInstanceData()
      except Exception as e:
        print(e.__str__())
        if e.__str__() in ['Area changed but refreshInstanceData was called before refreshAll', "area is loading on partial request"]:
          if refresh_area is True: poe_bot.refreshAll()
          pos_x, pos_y = poe_bot.convertPosXY(10,10)
          poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
          return True
        else:
          raise e
      if poe_bot.game_data.is_loading == True:
        while True:
          print(f'area is loading, waiting till its loaded')
          pos_x, pos_y = poe_bot.convertPosXY(10,10)
          poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
          time.sleep(random.randint(10,20)/10)
          try:
            poe_bot.refreshInstanceData()
          except Exception as e:
            if e.__str__() == 'Area changed but refreshInstanceData was called before refreshAll':
              if refresh_area is True: poe_bot.refreshAll()
              return True
            else:
              print(e.__str__())
              raise Exception('smth happened on getToPortal')
          if poe_bot.game_data.is_loading == False:
            print(f'area loaded, refreshAll')
            time.sleep(random.randint(10,20)/10)
            if refresh_area is True: poe_bot.refreshAll()
            return True
      if poe_bot.game_data.area_raw_name != original_area_raw_name:
        time.sleep(random.randint(10,20)/10)
        if refresh_area is True: poe_bot.refreshAll()
        break
      portal_to_enter = next((e for e in poe_bot.game_data.entities.all_entities if e.id == orig_portal_to_enter.id), None)
      if portal_to_enter is None:
        print(f'portal doesnt exist anymore, seems like we clicked on it')
        time.sleep(2)
        raise Exception("portal doesnt exist anymore, seems like we clicked on it")
      print(f'portal_to_enter {portal_to_enter}')
      if portal_to_enter.is_targetable is False:
        print("portal.is_targetable is False")
        continue
      if portal_to_enter.isInRoi() is False:
        raise Exception('Portal is too far away')
      print(f'getting into portal {portal_to_enter}')
      # portal_to_enter.hover()
      # portal_to_enter.click(update_screen_pos=True)
      pos_x,pos_y = poe_bot.convertPosXY(int(portal_to_enter.location_on_screen.x),int(portal_to_enter.location_on_screen.y))
      print(pos_x,pos_y)
      bot_controls.mouse.setPosSmooth(int(pos_x),int(pos_y))
      time.sleep(0.4)
      bot_controls.mouse.click()
      print(f'clicked on a portal {portal_to_enter}')
      time.sleep(random.randint(5,20)/10)
  def enterNearestPortal(self):
    print(f'looking to town portals nearby')
    town_portals = self.poe_bot.game_data.entities.town_portals
    if town_portals:
      print(f'found {town_portals}')
      portal_to_hideout = next( (e for e in town_portals if "Hideout" in e.render_name), None)
      if portal_to_hideout:
        print(f'found portal to hideout {portal_to_hideout}')
        self.poe_bot.helper_functions.getToPortal(check_for_map_device=False)
        self.poe_bot.logger.writeLine("got into map area by accident")
        raise Exception('got into map area by accident')
    else:
      self.poe_bot.helper_functions.relog()
      self.poe_bot.helper_functions.getToHideout()
      raise Exception("was not not nearby map device on mapdevice.open, relogged")
