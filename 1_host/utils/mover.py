from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
  from .gamehelper import PoeBot, Entity

import _thread

import numpy as np
import random
import time
from math import dist
import matplotlib.pyplot as plt

from .utils import alwaysFalseFunction, createLineIterator, getAngle, angleOfLine
from .constants import DOOR_KEYWORDS

# doors have component triggerable blockade

class Mover:
  poe_bot:PoeBot
  entity_to_go = None
  distance_to_target: float
  distance_to_entity: float
  opened_doors = []

  def __init__(self, poe_bot:PoeBot, debug = False, move_type = "mouse") -> None:
    self.poe_bot = poe_bot
    self.debug = debug
    self.default_continue_function = alwaysFalseFunction
    self.extra_points_count = 4
    self.setMoveType(move_type=move_type)
  def setMoveType(self, move_type):
    if move_type == "mouse":
      self.move_func = self.moveUsingMouse
      self.extra_points_count = 4
    elif move_type == "wasd":
      self.move_func = self.moveWASD
      self.extra_points_count = 0
    else:
      raise Exception(f'unknown move type {move_type}, supposed to be either "mouse" or "wasd"')
    self.move_type = move_type
  def enterTransition(self, transition:Entity, necropolis_ui = False, screen_pos_offset = [0,0], entered_distance_sign = 100, check_for_loading = False):
    '''
    main idea is that the the current transition is gonna become further than the other
    or have "grace_period" buff
    '''
    poe_bot = self.poe_bot

    print(f'#enterTransition {transition}')
    transition_id = transition.id
    # if transition['distance_to_player'] > 30: return False
    i = 0
    distance_to_player = 99999999
    entered = False
    attemps_limit = 20


    def getTransitionEntranceScreenPos():
      if i >= 5:
        # print(f"if i >= 5: {i} in enterTransition")
        path = poe_bot.pather.generatePath((int(poe_bot.game_data.player.grid_pos.y), int(poe_bot.game_data.player.grid_pos.x)), (transition.grid_position.y, transition.grid_position.x) )
        point = path[int(len(path)/2)]
        pos_to_click = poe_bot.getPositionOfThePointOnTheScreen(point[0], point[1])
        print(f'middle point {point} screen pos {pos_to_click}')
        pos_x,pos_y = poe_bot.convertPosXY(int(pos_to_click[0]), int(pos_to_click[1]))
      else:
        transition.updateLocationOnScreen()
        pos_to_click = (transition.location_on_screen.x+screen_pos_offset[0], transition.location_on_screen.y+screen_pos_offset[1])
        pos_x, pos_y = poe_bot.convertPosXY(pos_to_click[0], pos_to_click[1])
      print(f'pos_x, pos_y {pos_x, pos_y}')
      return pos_x, pos_y

    pos_x, pos_y = getTransitionEntranceScreenPos()
    poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    if poe_bot.bot_controls.mouse.pressed['left'] != False:
      poe_bot.bot_controls.mouse.release(wait_till_executed=False)
    total_attempts = 0
    while entered is False:
      i += 1
      # print(f"i += 1 {i} in enterTransition")
      total_attempts += 1
      print(f'attempting to get into transition number {total_attempts}')

      if total_attempts > 7 and total_attempts % 2 == 0:
        poe_bot.ui.closeAll()
      poe_bot.refreshInstanceData(raise_if_loading=True)
      new_transition = next( (e for e in poe_bot.game_data.entities.all_entities if e.id == transition_id), None)
      if new_transition != None and (new_transition.world_position.x != 0 and new_transition.world_position.y != 0 and new_transition.world_position.z != 0):
        print(f'updating transition')
        transition = new_transition

      if total_attempts > attemps_limit:
        print(f'#enterTransition len(total_attempts) > {attemps_limit}, stuck')
        # import pdb;pdb.set_trace()
        self.poe_bot.logger.writeLine(f'stuck in enterTransition {transition.raw}')
        self.poe_bot.on_stuck_function()

      if "grace_period" in poe_bot.game_data.player.buffs:
        print(f'grace period, entered')
        break
      if check_for_loading and poe_bot.game_data.invites_panel_visible != True:
        print(f'[mover.enterTransition] loading on enter transition')
        break


      # player_is_on_passable_cell = poe_bot.game_data.terrain.checkIfPointPassable(poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y, 5)
      # if player_is_on_passable_cell is False:
      #   print(f'player_is_on_passable_cell is False')
      #   break

      if poe_bot.league == "Necropolis":
        visible_labels = poe_bot.backend.getVisibleLabels()
        necropolis_tablets = list(filter(lambda e: e.path == "Metadata/Terrain/Leagues/Necropolis/Objects/NecropolisCorpseMarker", poe_bot.game_data.entities.all_entities))
        necropolis_tablet_to_click = None
        entity_to_click = next( (e for e in poe_bot.game_data.entities.all_entities if e.id == transition_id), None)
        if entity_to_click is not None:
          for necropolis_tablet in necropolis_tablets:
            tablet_distance = dist( (necropolis_tablet.grid_position.x, necropolis_tablet.grid_position.y), (entity_to_click.grid_position.x, entity_to_click.grid_position.y))
            if tablet_distance < 20:
              print(f'tablet_distance < 20 between {necropolis_tablet.raw} and {entity_to_click.raw}')
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
              time.sleep(random.randint(2,4)/100)
              print(f'click_necropolis_tablet_iter click mouse at {pos_x, pos_y} at {time.time()}')
              poe_bot.bot_controls.mouse.click()
              visible_labels = poe_bot.backend.getVisibleLabels()
              necropolis_tablet_visible_label = next( (l for l in visible_labels if l['id'] == necropolis_tablet_to_click.id), None)
              if necropolis_tablet_visible_label is None:
                print(f'necropolis_tablet_to_click tablet label disappeared {necropolis_tablet_to_click.raw}')
                break
      distance_to_player = dist((int(poe_bot.game_data.player.grid_pos.y), int(poe_bot.game_data.player.grid_pos.x)), (transition.grid_position.y, transition.grid_position.x))
      print(f'distance_to_player {distance_to_player}')
      if distance_to_player > entered_distance_sign:
        print(f'distance to player > {entered_distance_sign}, entered?')
        break
      pos_x, pos_y = getTransitionEntranceScreenPos()
      poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      poe_bot.last_action_time = 0
      poe_bot.refreshInstanceData(reset_timer=True)
      if "grace_period" in poe_bot.game_data.player.buffs:
        print(f'grace period, entered after hover')
        break

      if check_for_loading and poe_bot.game_data.invites_panel_visible != True:
        print(f'[mover.enterTransition] loading on enter transition')
        break
      pos_x, pos_y = getTransitionEntranceScreenPos()
      if i >= 6: i = 0
      poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      print(f'do click click')
      if poe_bot.bot_controls.mouse_pressed['left'] != True:
        poe_bot.bot_controls.mouse.press()
      poe_bot.bot_controls.mouse.release()
      if distance_to_player < 25:
        print(f'sleep')
        last_action_time_backup = poe_bot.last_action_time
        for _i in range(10):
          iter_started_at = time.time()
          if necropolis_ui is True:
            print(f'checking if necropolis ui appeared')
            necropolis_pop_up_ui = poe_bot.backend.getNecropolisPopupUI()
            if necropolis_pop_up_ui.get('v', 0) == 1:
              necropolis_pop_up_ui_screen_zone = necropolis_pop_up_ui.get('eb_sz', 0)
              if necropolis_pop_up_ui_screen_zone is None:
                poe_bot.raiseLongSleepException('necropolis popupui appeared but enter button pos is null')
              print(f'necropolis ui is visible zone is {necropolis_pop_up_ui_screen_zone}, clicking')
              x_pos, y_pos = poe_bot.convertPosXY(
                random.randint(necropolis_pop_up_ui_screen_zone[0]+10, necropolis_pop_up_ui_screen_zone[1]-10),
                random.randint(necropolis_pop_up_ui_screen_zone[2]+5, necropolis_pop_up_ui_screen_zone[3]-5),
                safe=False
              )
              poe_bot.bot_controls.mouse.setPosSmooth(x_pos,y_pos)
              time.sleep(0.1)
              poe_bot.bot_controls.mouse.click()
              time.sleep(0.1)
              for _check_necropolis_ui_disappeared_iterations in range(20):
                necropolis_pop_up_ui = poe_bot.backend.getNecropolisPopupUI()
                if necropolis_pop_up_ui.get('v', 0) == 0:
                  print(f'necropolis popupui disappeared')
          poe_bot.refreshInstanceData(reset_timer=True)
          if "grace_period" in poe_bot.game_data.player.buffs:
            print(f'grace period, entered after hover')
            entered = True
            break
          if check_for_loading and poe_bot.game_data.invites_panel_visible != True:
            print(f'[mover.enterTransition] loading on enter transition')
            break
          pos_x, pos_y = getTransitionEntranceScreenPos()
          poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
          # time.sleep(0.03)
        poe_bot.last_action_time = last_action_time_backup
    print(f'seems like we entered {transition}')
    if check_for_loading:
      pass
    pos_x,pos_y = poe_bot.convertPosXY(100,100)
    poe_bot.bot_controls.mouse.setPosSmooth(pos_x,pos_y)
    return True
  def openNearestDoor(self, distance_to_door = 15):
    door_type = 0
    poe_bot = self.poe_bot
    opened_doors = self.opened_doors
    doors_nearby = list(filter(lambda entity: entity.is_targetable is True and entity.is_opened is False and entity.distance_to_player < distance_to_door and entity.id not in opened_doors and  any(keyword in entity.path for keyword in DOOR_KEYWORDS)  ,poe_bot.game_data.entities.all_entities))
    
    if len(doors_nearby) == 0:
      # this door is fucked up, its shown as opened from doordadevent
      doors_nearby = list(filter(lambda entity: ("Metadata/MiscellaneousObjects/DoodadEventDrivenBlocking" in entity.path) and entity.id not in opened_doors and entity.distance_to_player < distance_to_door ,poe_bot.game_data.entities.all_entities))
      # doors_nearby = list(filter(lambda entity: entity['AnimatedPropertiesMetadata'] and  "Doors/Vault/HeistVaultLockpicking" in entity['AnimatedPropertiesMetadata'] , doors_nearby))
    # ignore the fake one
    doors_nearby = list(filter(lambda entity: entity.path and not "ScepterDoorLightSpawned" in entity.path , doors_nearby))
    if len(doors_nearby) > 0:
      door_to_open = doors_nearby[0]
      print(f"opening door {door_to_open}")
      if door_to_open.is_opened is True and door_type != 3:
        opened_doors.append(door_to_open.id)
        return False
      # hover on door to make it move towards the door
      door_entity = next((e for e in poe_bot.game_data.entities.all_entities if e.id == door_to_open.id), None)
      
      if door_entity is None:
        print(f'door disappeared')
        return True
      if door_entity.distance_to_player > 10 and door_entity.isInLineOfSight() != True:
        print(f'door {door_entity.raw} is not in line of sight')
        return False
      pos_x,pos_y = int(door_entity.location_on_screen.x), int(door_entity.location_on_screen.y)
      print(f'pos on screen to open DoodadEvent from poe helper {pos_x,pos_y}')
      pos_x,pos_y = poe_bot.convertPosXY(pos_x,pos_y-13)
      print(f'pos on screen to open DoodadEvent {pos_x,pos_y}')
      poe_bot.bot_controls.mouse.setPosSmooth(int(pos_x),int(pos_y))

      for i in range(random.randint(333,444)):
        if i > 20:
          return False
        poe_bot.refreshInstanceData()
        door_entity = next((e for e in poe_bot.game_data.entities.all_entities if e.id == door_to_open.id), None)
        if door_entity is None:
          print(f'door disappeared')
          break
        print(door_entity)
        if door_entity.is_opened == True:
          print('door became opened')
          break
        pos_x,pos_y = int(door_entity.location_on_screen.x), int(door_entity.location_on_screen.y)
        print(f'pos on screen to open DoodadEvent from poe helper {pos_x,pos_y}')
        pos_x,pos_y = poe_bot.convertPosXY(pos_x,pos_y-13)
        print(f'pos on screen to open DoodadEvent {pos_x,pos_y}')
        poe_bot.bot_controls.mouse.setPosSmooth(int(pos_x),int(pos_y))
        poe_bot.bot_controls.mouse.click()
      opened_doors.append(door_to_open.id)

      return True
  def passThroughNearbyTransition(self, distance_to_transition = 15):
    poe_bot = self.poe_bot
    transitions_nearby = list(filter(lambda entity: entity.is_targetable is True and entity.distance_to_player < distance_to_transition,poe_bot.game_data.entities.area_transitions))
    if len(transitions_nearby) != 0:
      transitions_nearby.sort(key=lambda e: e.distance_to_player)
      nearest_transition = transitions_nearby[0]
      self.enterTransition(nearest_transition)
      return True
    return False
  def goToPoint(
      self,
      point, # end (x,y)
      min_distance = 30,
      release_mouse_on_end = True, 
      release_mouse_on_start = False,
      randomize_grid_pos_to_go = True, 
      random_val = 1, 
      custom_break_function = alwaysFalseFunction,
      custom_continue_function = None,
      heist_transition = False,
      step_size = random.randint(30,35),
      possible_transition = False,
      time_limit = 5 * 60
    ):
    poe_bot = self.poe_bot
    bot_controls = self.poe_bot.bot_controls
    repeating_distances_counter = 0
    attempts_to_unstuck = 0
    previous_distance = 1.0
    first_step = 0
    _t = ""
    _t += f"#goToPoint point: {point}, min_distance: {min_distance}, release_mouse_on_end:{release_mouse_on_end}, release_mouse_on_start:{release_mouse_on_start}\n"
    _t += f"randomize_grid_pos_to_go: {randomize_grid_pos_to_go}, random_val: {random_val}\n"
    _t += f"custom_break_function:{custom_break_function}, custom_continue_function:{custom_continue_function}\n"
    _t += f"heist_transition: {heist_transition}, step_size: {step_size}"
    _t += f"possible_transition: {possible_transition}"
    print(_t)
    start_time = time.time()
    cropPath = self.poe_bot.pather.cropPath
    arrived = False

    custom_continue_function = custom_continue_function or self.default_continue_function 
    # if custom_continue_function is None:
    #   print(f'using self.default_continue_function which is {self.default_continue_function}')
    #   custom_continue_function = self.default_continue_function or custom_continue_function

    if release_mouse_on_start is True: 
      poe_bot.bot_controls.mouse.release()
      time.sleep(0.1)
      pos_x,pos_y = poe_bot.convertPosXY(random.randint(10,15),random.randint(10,15))
      print(pos_x,pos_y)
      poe_bot.bot_controls.mouse.setPosSmooth(int(pos_x),int(pos_y))
      time.sleep(0.1)
    custom_break_function_result = custom_break_function(self) 
    if custom_break_function_result is not False:
      return custom_break_function_result
    grid_pos_to_go_y, grid_pos_to_go_x = point[1], point[0]
    if randomize_grid_pos_to_go:
      grid_pos_to_go_y += random.randint(-random_val, +random_val)
      grid_pos_to_go_x += random.randint(-random_val, +random_val)
    print(f'end pos to go {grid_pos_to_go_x} {grid_pos_to_go_y} ')
    self.distance_to_target = dist((grid_pos_to_go_y, grid_pos_to_go_x), [poe_bot.game_data.player.grid_pos.y,poe_bot.game_data.player.grid_pos.x])
    if self.distance_to_target < min_distance and release_mouse_on_end is False:
      print(f'useless call of gotopoint arrived = True')
      arrived = True 
    
    path = []
    path = poe_bot.pather.generatePath((int(poe_bot.game_data.player.grid_pos.y), int(poe_bot.game_data.player.grid_pos.x)), (grid_pos_to_go_y, grid_pos_to_go_x) )
    # reset timer
    poe_bot.last_action_time = 0 # reset action delay
    while arrived is False:
      poe_bot.refreshInstanceData()
      # check if arrived
      distance_to_target = dist((grid_pos_to_go_y, grid_pos_to_go_x), [poe_bot.game_data.player.grid_pos.y,poe_bot.game_data.player.grid_pos.x])
      self.distance_to_target = distance_to_target
      print(f'[Mover] distance_to_target: {self.distance_to_target} at {time.time()}')
      # when almost arrived
      if self.distance_to_target < min_distance:
        print(f'{min_distance} points to target, almost arrived player_pos: {poe_bot.game_data.player.grid_pos}')
        self.move(grid_pos_x = point[0], grid_pos_y = point[1])
        # arrived, stop
        if release_mouse_on_end is True:
          print("# TODO check if mouse already released")
          print(f'trying to release mouse')
          last_mouse_pos_x, last_mouse_pos_y = -1, -1
          for i in range(random.randint(3,5)):
            poe_bot.last_action_time = 0 # reset action delay
            poe_bot.refreshInstanceData()
            path = createLineIterator(np.array((int(poe_bot.game_data.player.grid_pos.x), int(poe_bot.game_data.player.grid_pos.y))),np.array((grid_pos_to_go_x, grid_pos_to_go_y)))
            self.distance_to_target = dist((grid_pos_to_go_y, grid_pos_to_go_x), [poe_bot.game_data.player.grid_pos.y,poe_bot.game_data.player.grid_pos.x])
            print(f'distance_to_target on releasing mouse {self.distance_to_target}')
            if self.distance_to_target < 20:
              print(f'breaking cos distance_to_target < 20 {self.distance_to_target} ')
              break
            current_path = cropPath(path, step_size,step_size, current_pos_x=int(poe_bot.game_data.player.grid_pos.x), current_pos_y=int(poe_bot.game_data.player.grid_pos.y), max_path_length=100, extra_points_count=self.extra_points_count)
            if len(current_path) == 0:
              print('len(current_path) == 0 in release_mouse_cycles, generating new path')
              if self.distance_to_target < 30:
                print(f'lineiterator cos distance_to_target {self.distance_to_target}')
                path = createLineIterator(np.array((int(poe_bot.game_data.player.grid_pos.x), int(poe_bot.game_data.player.grid_pos.y))),np.array((grid_pos_to_go_x, grid_pos_to_go_y)))
              else:
                print(f'astar cos distance_to_target {self.distance_to_target}')
                path = poe_bot.pather.generatePath((int(poe_bot.game_data.player.grid_pos.y), int(poe_bot.game_data.player.grid_pos.x)), (grid_pos_to_go_y, grid_pos_to_go_x) )
              # reset timer
              poe_bot.last_action_time = 0 # reset action delay
              continue
            
            pos_to_click = poe_bot.getPositionOfThePointOnTheScreen(current_path[-1][0], current_path[-1][1])
            pos_x,pos_y = poe_bot.convertPosXY(int(pos_to_click[0]), int(pos_to_click[1]))
            if pos_x == last_mouse_pos_x and pos_y == last_mouse_pos_y:
              print(f'nothing changed seems like release here is useless')
              break
            last_mouse_pos_x, last_mouse_pos_y = pos_x,pos_y
            poe_bot.bot_controls.mouse.setPosSmooth(pos_x,pos_y, wait_till_executed=False)
            print(f'setting cursor on releasing mouse {pos_x,pos_y}')
            time.sleep(random.randint(7,14)/100)
          poe_bot.last_action_time = 0 # reset action delay
          poe_bot.refreshInstanceData()
          current_path = cropPath(path, step_size,step_size, current_pos_x=int(poe_bot.game_data.player.grid_pos.x), current_pos_y=int(poe_bot.game_data.player.grid_pos.y), max_path_length=100, extra_points_count=self.extra_points_count)
          self.distance_to_target = dist((grid_pos_to_go_y, grid_pos_to_go_x), [poe_bot.game_data.player.grid_pos.y ,poe_bot.game_data.player.grid_pos.x])
          if len(current_path) == 0 and self.distance_to_target > 0:
            print('len(current_path) == 0 in release_mouse_on_end, generating new path')
            if self.distance_to_target < 30:
              print(f'lineiterator cos distance_to_target {self.distance_to_target}')
              path = createLineIterator(np.array((int(poe_bot.game_data.player.grid_pos.x), int(poe_bot.game_data.player.grid_pos.y))),np.array((grid_pos_to_go_x, grid_pos_to_go_y)))
            else:
              print(f'astar cos distance_to_target {self.distance_to_target}')
              path = poe_bot.pather.generatePath((int(poe_bot.game_data.player.grid_pos.y), int(poe_bot.game_data.player.grid_pos.x)), (grid_pos_to_go_y, grid_pos_to_go_x) )
            # reset timer
            poe_bot.last_action_time = 0 # reset action delay
            continue
         
          self.move(grid_pos_x = grid_pos_to_go_x, grid_pos_y = grid_pos_to_go_y)
          time.sleep(random.randint(3,6)/100)
          poe_bot.bot_controls.mouse.release()
          time.sleep(0.01)
          print(f'realeased mouse')
        break

      mover_move_time = time.time() - start_time
      if self.poe_bot.debug: print(f'mover_move_time {mover_move_time}')
      if mover_move_time > time_limit:
        print(f'[Mover.move] stuck cos exceed of time {time_limit} sec')
        if self.poe_bot.on_stuck_function is None:
          poe_bot.raiseLongSleepException('we are stuck hard, help!')
        else:
          self.poe_bot.on_stuck_function()

      # /unstuck
      if self.openNearestDoor() is True: 
        continue
       
      if possible_transition is True and self.passThroughNearbyTransition() is True: 
        continue
        

      if True:
        if previous_distance == self.distance_to_target:
          repeating_distances_counter += 1
        else:
          repeating_distances_counter = 0
          previous_distance = self.distance_to_target
        if self.poe_bot.debug: print(f'repeating_distances_counter {repeating_distances_counter}')
        if repeating_distances_counter == 4 or repeating_distances_counter == 7:
          print('releasing mouse, cos maybe its stuck')
          bot_controls.mouse_pressed['left'] = False

        if repeating_distances_counter >= 13:
          if repeating_distances_counter % 10 == 0:
            print(f'repeating_distances_counter % 10 == 0, push space button')
            bot_controls.keyboard.tap('DIK_SPACE', wait_till_executed=True)

          if attempts_to_unstuck > 15:
            self.poe_bot.logger.writeLine('stuck in goToPoint')
            if self.poe_bot.on_stuck_function is None:
              poe_bot.raiseLongSleepException('we are stuck hard, help!')
            else:
              self.poe_bot.on_stuck_function()
          attempts_to_unstuck += 1
          poe_bot.bot_controls.mouse.release()
          print(f'we are stuck for {repeating_distances_counter} cycles')
          if heist_transition is True: # heist only
            print('clicking No')
            pos_x,pos_y = poe_bot.convertPosXY(370,405)
            poe_bot.bot_controls.mouse.setPosSmooth(int(pos_x),int(pos_y))
            time.sleep(0.01)
            poe_bot.bot_controls.mouse.click()
          time.sleep(random.randint(2,9)/100)

          point = poe_bot.game_data.terrain.pointToRunAround(
            point_to_run_around_x=self.poe_bot.game_data.player.grid_pos.x,
            point_to_run_around_y=self.poe_bot.game_data.player.grid_pos.y,
            distance_to_point=15,
            check_if_passable=True
          )
          print(f'[Mover] stuck, moving to {point}')
          self.move(grid_pos_x = point[0], grid_pos_y = point[1])
          continue
      current_path = cropPath(path, int(step_size*1.7),step_size, current_pos_x=int(poe_bot.game_data.player.grid_pos.x), current_pos_y=int(poe_bot.game_data.player.grid_pos.y), max_path_length=int(step_size*1.5), extra_points_count=self.extra_points_count)
      # print(f'len(current_path) {len(current_path)}')
      if len(current_path) == 0:
        print('[Mover] len(current_path) == 0, generating new path')
        path = poe_bot.pather.generatePath((int(poe_bot.game_data.player.grid_pos.y), int(poe_bot.game_data.player.grid_pos.x)), (grid_pos_to_go_y, grid_pos_to_go_x) )
        # reset timer
        poe_bot.last_action_time = 0 # reset action delay
        continue

      self.grid_pos_to_step_x, self.grid_pos_to_step_y = current_path[-1][1], current_path[-1][0]
      self.current_cropped_path = current_path
      self.nearest_passable_point = [self.current_cropped_path[0][1], self.current_cropped_path[0][0]] # [x,y]

      # custom functions
      custom_break_function_result = custom_break_function(self) 
      if custom_break_function_result is not False:
        return custom_break_function_result

      if first_step == 2 and custom_continue_function(self) is True:
        continue


      # if bot_controls.mouse_pressed['left'] is True and custom_continue_function(self) is True:
      #   continue

      pos_to_click = poe_bot.getPositionOfThePointOnTheScreen(current_path[-1][0], current_path[-1][1])
      pos_x,pos_y = poe_bot.convertPosXY(pos_to_click[0], pos_to_click[1])
      self.pos_x,self.pos_y = pos_x,pos_y
      prev_pos_to_click = [pos_to_click[0], pos_to_click[1]]
      print(f'[Mover] making step to {pos_x,pos_y}')
      if first_step == 0:
        print(f'[Mover] making first step, placing a mouse on {pos_x,pos_y} and going ')
        first_step = 1
        poe_bot.last_action_time = 0 # reset action delay
        poe_bot.bot_controls.mouse.setPosSmooth(int(pos_x),int(pos_y), wait_till_executed=False)
        # continue
      else:
        first_step = 2

      self.move(grid_pos_x=current_path[-1][1], grid_pos_y=current_path[-1][0])
      # self.move(screen_pos_x=int(pos_to_click[0]), screen_pos_y=int(pos_to_click[1]))
      # poe_bot.move(int(pos_to_click[0]), int(pos_to_click[1]))
      time.sleep(0.01)

    poe_bot.last_action_time = 0 # reset action delay
    self.reset()
    return None
  def goToEntity(
      self,
      entity_to_go:Entity, 
      min_distance = 20, 
      release_mouse_on_end = False, 
      custom_continue_function = alwaysFalseFunction, 
      custom_break_function = alwaysFalseFunction,
      step_size = random.randint(30,35)
    ):
    
    poe_bot = self.poe_bot
    poe_bot.last_action_time = 0

    if entity_to_go.distance_to_player < min_distance:
      print(f"#goToEntity {entity_to_go.distance_to_player} entity['distance_to_player'] < min_distance, useless call")
      return None

    self.entity_to_go = entity_to_go
    entity_to_go_id = entity_to_go.id
    entity_pos = [entity_to_go.grid_position.x, entity_to_go.grid_position.y]



    def custom_continue_fucntion_nested(self:Mover):
      res = custom_continue_function(self)
      return res
      # for example attack functions

    def custom_break_function_nested(self:Mover):
      current_entity = list(filter(lambda entity: entity.id == entity_to_go_id, poe_bot.game_data.entities.all_entities))
      if len(current_entity) == 0:
        print('entity doesnt exist anymore')
        return 'doesnt_exist' # if doesnt exist
      current_entity = current_entity[0]
      distance_from_end_path = dist(entity_pos, [current_entity.grid_position.x, current_entity.grid_position.y ]) # rebuild path
      if distance_from_end_path > 15:
        print(f'seems like entity_to_go moved far away from a target distance_from_end_path {distance_from_end_path}, rebuilding path')
        return 'rebuild_path'
      self.distance_to_entity = dist(entity_pos, [poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y ])
      res = custom_break_function(self)
      # if res is not False: return res
      return res

    while True:
      res = self.goToPoint(
        entity_pos, # end (x,y)
        min_distance = min_distance, # -1 to run around entity
        release_mouse_on_end = release_mouse_on_end, 
        release_mouse_on_start = False,
        randomize_grid_pos_to_go = False, 
        random_val = 1, 
        custom_break_function = custom_break_function_nested,
        custom_continue_function = custom_continue_fucntion_nested,
        heist_transition = False,
        step_size = step_size
      )
      if res == "rebuild_path":
        entity = list(filter(lambda e: e.id == entity_to_go_id, poe_bot.game_data.entities.all_entities))[0]
        entity_pos = [entity.grid_position.x, entity.grid_position.y]
        continue
      elif res == "doesnt_exist":
        pass
      self.reset()
      return res
  def goToEntitysPoint(
      self,
      entity_to_go:Entity, 
      min_distance = 20, 
      release_mouse_on_end = False, 
      custom_continue_function = None, 
      custom_break_function = alwaysFalseFunction,
      step_size = random.randint(30,35)
    ):
    
    poe_bot = self.poe_bot
    poe_bot.last_action_time = 0
    if custom_continue_function is None:
      custom_continue_function = self.default_continue_function
    
    entity_pos = [entity_to_go.grid_position.x, entity_to_go.grid_position.y]

    if entity_to_go.distance_to_player < min_distance:
      print(f"#goToEntity {entity_to_go.distance_to_player} entity['distance_to_player'] < min_distance, useless call")
      return None

    while True:
      res = self.goToPoint(
        entity_pos, # end (x,y)
        min_distance = min_distance, # -1 to run around entity
        release_mouse_on_end = release_mouse_on_end, 
        release_mouse_on_start = False,
        randomize_grid_pos_to_go = False, 
        random_val = 1, 
        custom_break_function = custom_break_function,
        custom_continue_function = custom_continue_function,
        heist_transition = False,
        step_size = step_size
      )
      self.reset()
      return res
  def move(self, grid_pos_x = None, grid_pos_y = None, screen_pos_x = None, screen_pos_y = None):
    self.move_func(grid_pos_x,grid_pos_y, screen_pos_x, screen_pos_y)
  def moveUsingMouse(self, grid_pos_x = None, grid_pos_y = None, screen_pos_x = None, screen_pos_y = None):
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    if grid_pos_x != None and grid_pos_y != None:
      pos_x, pos_y = poe_bot.getPositionOfThePointOnTheScreen(grid_pos_y, grid_pos_x)
      pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
    elif screen_pos_x != None and screen_pos_y != None:
      pos_x, pos_y = poe_bot.convertPosXY(screen_pos_x, screen_pos_y)
    
    if bot_controls.mouse.pressed['left'] != True:
      bot_controls.mouse.press(pos_x,pos_y)
    else:
      bot_controls.mouse.setPosSmooth(pos_x,pos_y, wait_till_executed=False)
    return (pos_x,pos_y)
  def moveWASD(self, grid_pos_x = None, grid_pos_y = None, screen_pos_x = None, screen_pos_y = None):
    print(f'[Mover.moveWASD] {grid_pos_x, grid_pos_y}, {screen_pos_x, screen_pos_y}')
    if grid_pos_x != None and grid_pos_y != None:
      print(f'grid pos pp {self.poe_bot.game_data.player.grid_pos.toList()}')

      angle = angleOfLine(
        self.poe_bot.game_data.player.grid_pos.toList(),
        [grid_pos_x, grid_pos_y],
      )
    elif screen_pos_x != None and screen_pos_y != None:
      print(f'screen pos cp {self.poe_bot.game_window.center_point}')
      angle = angleOfLine(
        self.poe_bot.game_window.center_point,
        [screen_pos_x, screen_pos_y],
      ) - 45
      if angle < 0:
        angle += 360

    # we have an angle to move

    print(f'[Mover.moveWASD] exact angle to move {angle}')
    angle_mult = angle // 45
    angle_leftover = angle % 45

    if angle_leftover > 22.5:
      angle_mult += 1

    nearest_angle = int(angle_mult * 45)
    if nearest_angle == 360:
      nearest_angle = 0
    print(f'[Mover.moveWASD] gonna move by angle {nearest_angle}')

    buttons_to_press = DIRECTIONS_AND_KEYS[nearest_angle]

    pressed_movement_keys_atm = list(filter(lambda k: k in MOVEMENT_KEYS, self.poe_bot.bot_controls.keyboard.pressed))
    keys_to_release = list(filter(lambda k: k not in buttons_to_press, pressed_movement_keys_atm))
    keys_to_press = list(filter(lambda k: k not in pressed_movement_keys_atm, buttons_to_press))


    queue = []
    list(map(lambda k: queue.append(lambda: self.poe_bot.bot_controls.keyboard_releaseKey(k, wait_till_executed=False)), keys_to_release))
    list(map(lambda k: queue.append(lambda: self.poe_bot.bot_controls.keyboard_pressKey(k, wait_till_executed=False)), keys_to_press))

    random.shuffle(queue)

    for action in queue:
      action()
    return (0,0) #TODO ????????
  def stopMoving(self):
    if self.move_type == "mouse":
      self.poe_bot.bot_controls.mouse.release()
    elif self.move_type == "wasd":
      pressed_movement_keys = list(filter(lambda k: k in MOVEMENT_KEYS, self.poe_bot.bot_controls.keyboard.pressed))
      queue = []
      list(map(lambda k: queue.append(lambda: self.poe_bot.bot_controls.keyboard_releaseKey(k, wait_till_executed=False)), pressed_movement_keys))
      random.shuffle(queue)
      for f in queue:
        f()      

  def reset(self):
    self.entity_to_go = None
    self.distance_to_target = 0
    self.distance_to_entity = 0
    # self.grid_pos_to_step_x = None
    # self.grid_pos_to_step_y = None

MOVEMENT_KEYS = [
  "DIK_A", "DIK_W", "DIK_D", "DIK_S"
]

DIRECTIONS_AND_KEYS = {
  0: ["DIK_A", "DIK_W"],
  45: ["DIK_W"],
  90: ["DIK_W", "DIK_D"],
  135: ["DIK_D"],
  180: ["DIK_D", "DIK_S"],
  225: ["DIK_S"],
  270: ["DIK_S", "DIK_A"],
  315: ["DIK_A"],
}

ALL_DIRECTIONS_ANGLES = list(DIRECTIONS_AND_KEYS.keys()) + [360]