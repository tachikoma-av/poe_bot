from __future__ import annotations
import typing
from typing import List
if typing.TYPE_CHECKING:
  from .gamehelper import PoeBot, Entity

import time
from math import dist
import matplotlib.pyplot as plt
import random

from .components import PoeBotComponent
from .constants import INCURSION_CLOSED_DOOR_PATH_KEY, INCURSION_EXIT_PORTAL_PATH_KEY
import numpy as np

class Encounter(PoeBotComponent):
  def __init__(self, poe_bot: PoeBot) -> None:
    super().__init__(poe_bot)
  def do(self):
    self.poe_bot.raiseLongSleepException('encounter.do is not defined')
class Bossroom(Encounter):
  def __init__(
      self, 
      poe_bot: PoeBot, 
      transition_entity:Entity, 
      boss_render_names:List[str],
      activator_inside_bossroom_path:str = None,
      refresh_terrain_data_in_bossroom = False, 
      leave_bossroom_after_clear = True,
      clear_room_custom_break_function = lambda *args, **kwargs: False,
      need_to_leave_bossroom_through_transition = True,
      transitions_inside_bossroom = [],
      activate_boss_in_center = False,
    ) -> None:
    super().__init__(poe_bot)
    self.refresh_terrain_data_in_bossroom = refresh_terrain_data_in_bossroom
    self.transition_entity = transition_entity
    self.activator_inside_bossroom_path = activator_inside_bossroom_path
    self.activated_activator_in_bossroom = False
    self.exit_transition_entity:Entity = None
    self.boss_render_names = boss_render_names
    self.killed_boss_entities:List[Entity] = []
    self.leave_bossroom_after_clear = leave_bossroom_after_clear
    self.need_to_leave_bossroom_through_transition = need_to_leave_bossroom_through_transition 
    self.clear_room_custom_break_function = clear_room_custom_break_function
    self.transitions_inside_bossroom = transitions_inside_bossroom
    self.activate_boss_in_center = activate_boss_in_center
    self.boss_is_on_unpassable = False
    print(vars(self))
  def seekForBosses(self):
    map_bosses = list(filter(lambda e: e.life.health.current != 0 and e.render_name in self.boss_render_names and self.poe_bot.game_data.terrain.checkIfPointPassable(e.grid_position.x, e.grid_position.y) , self.poe_bot.game_data.entities.unique_entities))
    return map_bosses
  def activateBossroomActivatorIfFoundOrPresented(self):
    if self.activator_inside_bossroom_path is not None and self.activated_activator_in_bossroom is False:
      activator:Entity = next((e for e in self.poe_bot.game_data.entities.all_entities if e.path == self.activator_inside_bossroom_path), None)
      if activator:
        if activator.is_targetable is True:
          activator.clickTillNotTargetable()
        else:
          print('activator is not targetable')
        self.activated_activator_in_bossroom = True
        return True
    return False
  def enterBossroom(self):
    print('entering bosroom encounter')
    print(self.transition_entity.raw)
    while True:
      res = self.poe_bot.mover.goToPoint(
        point=[self.transition_entity.grid_position.x, self.transition_entity.grid_position.y],
        min_distance=30,
        release_mouse_on_end=False,
        custom_break_function=self.poe_bot.loot_picker.collectLoot,
        step_size=random.randint(25,33)
      )
      if res is None:
        break
    self.poe_bot.mover.enterTransition(self.transition_entity)
    self.onEnteringBossroom()
  def onEnteringBossroom(self):
    if self.refresh_terrain_data_in_bossroom:
      self.poe_bot.refreshAll(refresh_visited=False)
    self.poe_bot.refreshInstanceData()
    exit_transitions = list(filter(lambda e: e.id != self.transition_entity.id, self.poe_bot.game_data.entities.area_transitions))
    exit_transitions = sorted(exit_transitions, key=lambda entity: entity.distance_to_player)
    if len(exit_transitions) != 0:
      exit_transition_test = exit_transitions[0]
      print(f'exit_transition_test {exit_transition_test.raw}')
    self.exit_pos_x, self.exit_pos_y = self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y
    print(f'entered bossroom exit_pos_x, exit_pos_y {self.exit_pos_x, self.exit_pos_y}')
    self.poe_bot.game_data.terrain.getCurrentlyPassableArea()
  def killBossEntityIfFound(self, mover=None):
    if self.activateBossroomActivatorIfFoundOrPresented():
      return False
    unique_entities = self.seekForBosses()
    if len(unique_entities) != 0:
      print("#killBossEntityIfFound found boss entity, killing it")
      for unique_entity in unique_entities:
        self.killBoss(unique_entity)
      return True
    return False
  def killBoss(self, entity:Entity, clear_around_radius = 150):
    poe_bot = self.poe_bot
    mover = self.poe_bot.mover
    if self.activate_boss_in_center != False:
      print(f'will activate boss in center')
      bossroom_center = self.poe_bot.pather.utils.getCenterOf(self.poe_bot.game_data.terrain.currently_passable_area)
    start_time = time.time()

    print(f'#bossroom.killBoss {start_time} {entity.raw}')
    boss_entity = entity
    boss_entity_id = boss_entity.id

    if boss_entity.is_targetable is False or boss_entity.is_attackable is False:
      print(f'boss is not attackable or not targetable, going to it and activating it')
      if self.activate_boss_in_center != False:
        pos_to_go_x, pos_to_go_y = bossroom_center[0], bossroom_center[1]
      else:
        pos_to_go_x, pos_to_go_y = boss_entity.grid_position.x, boss_entity.grid_position.y
      # get to activation point
      while True:
        self.activateBossroomActivatorIfFoundOrPresented()
        res = mover.goToPoint(
          (pos_to_go_x, pos_to_go_y),
          min_distance=15,
          release_mouse_on_end=False,
          step_size=random.randint(25,33),
        )
        if res is None:
          break
      # running and killing till it's activated
      while True:
        if start_time + 120 < time.time():
          print(f'killing boss for more than 120 seconds')
          poe_bot.on_stuck_function() 
        boss_entity = list(filter(lambda e: e.id == boss_entity_id, poe_bot.game_data.entities.all_entities))
        if len(boss_entity) == 0:
          print(f'len(boss_entity) == 0 corpse disappeared:')
          return True
        boss_entity = boss_entity[0]
        if boss_entity.life.health.current == 0:
          print(f'boss is dead')
          return True
        if boss_entity.is_targetable != True or boss_entity.is_attackable != True:
          print(f'boss is not attackable or not targetable')
          print(f'going to it clearing around it {boss_entity.raw}')
          killed_someone = poe_bot.combat_module.clearLocationAroundPoint(
            {"X":pos_to_go_x, "Y":pos_to_go_y}, 
            detection_radius=clear_around_radius, 
            # ignore_keys=self.current_map.entities_to_ignore_in_bossroom_path_keys
          )
          if killed_someone is False:
            point = poe_bot.game_data.terrain.pointToRunAround(
              point_to_run_around_x=pos_to_go_x,
              point_to_run_around_y=pos_to_go_y,
              distance_to_point=15,
            )
            mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
          poe_bot.refreshInstanceData(reset_timer=killed_someone)
        else:
          print(f'boss is attackable and targetable, going to kill it')
          poe_bot.combat_module.killUsualEntity(boss_entity, max_kill_time_sec=30)
          if self.activate_boss_in_center != True:
            pos_to_go_x, pos_to_go_y = boss_entity.grid_position.x, boss_entity.grid_position.y
    else:
      print(f'boss is attackable and targetable, going to kill it')
      if boss_entity.distance_to_player > 40:
        while True:
          res = mover.goToPoint(
            (boss_entity.grid_position.x, boss_entity.grid_position.y),
            min_distance=35,
            # custom_break_function=collectLootIfFound,
            release_mouse_on_end=False,
            step_size=random.randint(25,33),
            # possible_transition = self.current_map.possible_transition_on_a_way_to_boss
          )
          if res is None:
            break
      poe_bot.combat_module.killUsualEntity(boss_entity)
    # self.temp.killed_map_bosses_render_names.append(entity.render_name)
    self.killed_boss_entities.append(entity)
  def clearBossroom(self):
    poe_bot = self.poe_bot
    mover = self.poe_bot.mover
    loot_picker = self.poe_bot.loot_picker
    def custom_break_function_nested(*args, **kwargs):
      if self.killBossEntityIfFound() is True:
        return True
      res = self.clear_room_custom_break_function(self.poe_bot.mover)
      # if res is not False: return res
      return res
    print(f'going to clear the bossroom {self.transition_entity}')
    unique_entities = self.seekForBosses()
    if len(unique_entities) != 0:
      print(f'unique_entities: {unique_entities}')
      for entity in unique_entities:
        self.killBoss(entity=entity)
    else:
      print(f'unique_entities empty, exploring and killing uniques')
      grid_pos_to_go_x, grid_pos_to_go_y = poe_bot.game_data.terrain.getFurtherstPassablePoint()
      _i = 0
      while True:
        _i += 1
        if _i == 100:
          poe_bot.helper_functions.relog()
          raise Exception('stuck on exploring bossroom')
        res = mover.goToPoint(
          point=[grid_pos_to_go_x, grid_pos_to_go_y],
          min_distance=50,
          release_mouse_on_end=False,
          custom_break_function=custom_break_function_nested,
          step_size=random.randint(25,33)
        )
        if res is None or res is True:
          break
      unique_entities = self.seekForBosses()
      print(f'unique_entities after explore: {unique_entities}')
      for entity in unique_entities:
        self.killBoss(entity=entity)
    poe_bot.refreshInstanceData()
    loot_picker.collectLootWhilePresented()
    print(f'[Bossroom encounter] bossroom cleared')
  def leaveBossroom(self):
    print(f'#[Bossroom.leaveBossroom]  at {time.time()}')
    poe_bot = self.poe_bot
    mover = self.poe_bot.mover
    if self.need_to_leave_bossroom_through_transition is False:
      print("self.need_to_leave_bossroom_through_transition is False")
      poe_bot.refreshAll(refresh_visited=False)
      poe_bot.game_data.terrain.getCurrentlyPassableArea()
    else:
      bossroom_leave_iteration = 0
      while True:
        bossroom_leave_iteration += 1
        if bossroom_leave_iteration == 50:
          print("bossroom_leave_iteration == 50, stuck, relog")
          poe_bot.on_stuck_function()
          raise Exception('look_for_exit_transition > 100:')

        print(f'going to leave bossroom')
        print(f'exit_pos_x, exit_pos_y {self.exit_pos_x, self.exit_pos_y}')
        while True:
          print(f'going 100 to exit point {self.exit_pos_x, self.exit_pos_y}')
          res = mover.goToPoint(
            point=[self.exit_pos_x, self.exit_pos_y],
            min_distance=100,
            release_mouse_on_end=False,
            custom_continue_function=self.poe_bot.combat_module.build.usualRoutine,
            custom_break_function=self.killBossEntityIfFound,
            step_size=random.randint(25,33)
          )
          poe_bot.loot_picker.collectLootWhilePresented()
          if res is None:
            break
        while True:
          print(f'going 30 to exit point {self.exit_pos_x, self.exit_pos_y}')
          res = mover.goToPoint(
            point=[self.exit_pos_x, self.exit_pos_y],
            min_distance=30,
            release_mouse_on_end=False,
            custom_break_function=self.killBossEntityIfFound,
            step_size=random.randint(25,33)
          )

          poe_bot.loot_picker.collectLootWhilePresented()
          if res is None:
            break
        # exit_transitions = list(filter(lambda e: e.id != bossroom_id and dist((e.grid_position.x, e.grid_position.y), (exit_pos_x, exit_pos_y)) < 40, poe_bot.game_data.entities.area_transitions))
        exit_transitions = list(filter(lambda e: e.id != self.transition_entity.id and poe_bot.game_data.terrain.checkIfPointPassable(e.grid_position.x, e.grid_position.y), poe_bot.game_data.entities.area_transitions))
        
        if len(exit_transitions) == 0:
          print('exit transition is not visible or doesnt exist')
          grid_pos_to_go_x, grid_pos_to_go_y = self.poe_bot.game_data.terrain.getFurtherstPassablePoint()
          #TODO infinite loop if failure onenter transition
          while True:
            res = mover.goToPoint(
              point=[grid_pos_to_go_x, grid_pos_to_go_y],
              min_distance=50,
              release_mouse_on_end=False,
              custom_break_function=self.killBossEntityIfFound,
              step_size=random.randint(25,33)
            )
            if res is None:
              break
          continue
        
        exit_transition = exit_transitions[0]
        mover.enterTransition(exit_transition)
        self.exit_transition_entity = exit_transition
        # self.temp.visited_transitions_ids.append(exit_transition.id)
        print('left the bossroom')
        break
    poe_bot.game_data.terrain.getCurrentlyPassableArea() # to refresh currently passable area
  def doEncounter(self):
    self.enterBossroom()
    self.clearBossroom()
    if self.leave_bossroom_after_clear:
      self.leaveBossroom()
class EssenceEncounter(Encounter):
  def __init__(self, poe_bot, encounter_entity:Entity):
    super().__init__(poe_bot)
    self.encounter_entity = encounter_entity
  def doEncounter(self):
    poe_bot = self.poe_bot
    inventory = poe_bot.ui.inventory
    mover = self.poe_bot.mover
    # debug
    # poe_bot.refreshInstanceData()
    # go to around essence


    essence_monolith = self.encounter_entity
    print(f'#[EssenceEncounter.doEncounter] nearby {essence_monolith} call at {time.time()}')
    essence_opened = False
    essence_monolith_id = essence_monolith.id
    grid_pos_x = essence_monolith.grid_position.x
    grid_pos_y = essence_monolith.grid_position.y


    while True:
      res = mover.goToEntitysPoint(
        entity_to_go=essence_monolith,
        min_distance=75,
        custom_break_function=poe_bot.loot_picker.collectLoot,
        release_mouse_on_end=False,
        step_size=random.randint(25,33)
      )
      if res is None:
        break

    '''corruption start'''
    # valuable_essences = ["Misery", "Envy", "Dread", "Scorn"]
    # visible_labels = poe_bot.backend.getVisibleLabels()

    # essence_label = list(filter(lambda label:label['id'] == essence_monolith_id,visible_labels))[0]
    # essence_label_id = essence_label['id']
    # print(f'essence_label {essence_label}')
    # essence_texts = ' '.join(essence_label['texts'])

    # shrieking_count = len(essence_texts.split("Shrieking"))-1
    # screaming_count = len(essence_texts.split("Screaming"))-1
    # deafening_count = len(essence_texts.split("Deafening"))-1
    # remnant_of_corruption_count = len(essence_texts.split('Remnant of Corruption'))-1

    # print(f'screaming_count {screaming_count}')
    # print(f'shrieking_count {shrieking_count}')
    # print(f'deafening_count {deafening_count}')

    # valuable_mods_count = shrieking_count + screaming_count + deafening_count + remnant_of_corruption_count
    # if any(list(map(lambda string: string in essence_texts, ["Horror", "Delirium", "Hysteria"]))):
    #   valuable_mods_count += 2
    # print(f'valuable_mods_count {valuable_mods_count}')
    # if mapper.settings.essences_do_all is False and valuable_mods_count < 1:
    #   print(f'not worth to open this essence')
    #   mapper.temp.essences_to_ignore_ids.append(essence_label_id)
    #   return True
    '''corruption end'''
    poe_bot.combat_module.clearLocationAroundPoint({"X": essence_monolith.grid_position.x, "Y": essence_monolith.grid_position.y}, detection_radius=45)
    poe_bot.refreshInstanceData()
    essence_mobs = list(filter(lambda e: e.grid_position.x == essence_monolith.grid_position.x and e.grid_position.y == essence_monolith.grid_position.y and e.rarity == 'Rare', poe_bot.game_data.entities.all_entities))
    
    essences = list(filter(lambda entity: essence_monolith_id == entity.id,poe_bot.game_data.entities.all_entities))
    if len(essences) == 0:
      print(f'[EssenceEncounter.doEncounter] len(essences) == 0 after we arrived')
      return False

    print(f'[EssenceEncounter.doEncounter] essence_mobs {essence_mobs}')

    # opening essence
    essence_monolith = essences[0]
    poe_bot.combat_module.build.prepareToFight(essence_monolith)

    '''corruption start'''
    # need_to_corrupt = False
    # if any(list(map(lambda key: key in essence_texts, valuable_essences))) is True:
    #   need_to_corrupt = True

    # essence_mods_len = shrieking_count + screaming_count
    # print(f'essences_count in essence: {essence_mods_len}, min essences to corrupt {mapper.settings.essences_min_to_corrupt}')
    # if essence_mods_len >= mapper.settings.essences_min_to_corrupt:
    #   need_to_corrupt = True

    # # need_to_corrupt = True;print('#debug remove need_to_corrupt = True')
    # if 'Remnant of Corruption' in essence_texts or "Corrupted" in essence_label['texts']:
    #   need_to_corrupt = False
    # print(f'need_to_corrupt {need_to_corrupt}')


    # print(f'mapper.settings.essences_can_corrupt {mapper.settings.essences_can_corrupt} need_to_corrupt {need_to_corrupt}')
    # # if False:
    # if mapper.settings.essences_can_corrupt is True and need_to_corrupt is True:
    #   inventory_items = inventory.update()
    #   remnants_of_corruptions = list(filter(lambda item: item.name == 'Remnant of Corruption', inventory.items))
    #   if len(remnants_of_corruptions) != 0:
    #     print(f'have {len(remnants_of_corruptions)} remnantofcorruption, corrupting it')
    #     essence_corrupted = False
    #     while True:
          
    #       # get to it
    #       print('going to essence to corrupt it')
    #       while True:
    #         poe_bot.refreshInstanceData()
    #         poe_bot.last_action_time = 0
    #         res = mover.goToPoint(
    #           point=(grid_pos_x, grid_pos_y),
    #           min_distance=30,
    #           custom_continue_function=build.usualRoutine,
    #           release_mouse_on_end=True,
    #           # release_mouse_on_end=False,
    #           step_size=random.randint(25,33)
    #         )
    #         if res is None:
    #           break

    #       visible_labels = poe_bot.backend.getVisibleLabels()
    #       updated_essence_label = list(filter(lambda label: label['id'] == essence_label_id, visible_labels))[0]
    #       print(f'updated_essence_label {updated_essence_label}')
          

    #       poe_bot.bot_controls.keyboard_pressKey('DIK_LSHIFT')
    #       inventory.open()
    #       remnant_of_corruptions = remnants_of_corruptions[0]
    #       remnant_of_corruptions.hover()
    #       time.sleep(random.randint(2,4)/100)
    #       remnant_of_corruptions.click(button='right')
    #       poe_bot.bot_controls.keyboard_pressKey('DIK_LSHIFT')
    #       for i in range(10):
    #         visible_labels = poe_bot.backend.getVisibleLabels()
    #         updated_essence_labels = list(filter(lambda label: label['id'] == essence_label_id, visible_labels))
    #         if len(updated_essence_labels) == 0:
    #           print(f'seems like we opened essence:(')
    #           essence_corrupted = True
    #           break
    #         updated_essence_label = updated_essence_labels[0]
    #         print(f'updated_essence_label {updated_essence_label}')
    #         if 'Corrupted' in updated_essence_label['texts']:
    #           print(f'essence is corrupted, success')
    #           essence_corrupted = True
    #           break
    #         essence_label_center = [ (updated_essence_label['p_o_s']['x1'] + updated_essence_label['p_o_s']['x2'])/2, (updated_essence_label['p_o_s']['y1'] + updated_essence_label['p_o_s']['y2'])/2 ]
    #         if essence_label_center[0] > 512:
    #           essence_label_center[0] = 512
    #         item_pos_x,item_pos_y = poe_bot.convertPosXY(essence_label_center[0],essence_label_center[1])
    #         bot_controls.mouse.setPosSmooth(int(item_pos_x),int(item_pos_y))
    #         time.sleep(random.randint(2,4)/100)
    #         bot_controls.mouse.click()
            
    #         visible_labels = poe_bot.backend.getVisibleLabels()
    #         updated_essence_label = next( (label for label in visible_labels if label['id'] == essence_label_id), None)
    #         if updated_essence_label == None:
    #           print(f'essence opened by itself')
    #           essence_corrupted = True
    #           essence_opened = True
    #           break
    #         updated_essence_label = list(filter(lambda label: label['id'] == essence_label_id, visible_labels))[0]
    #         print(f'updated_essence_label {updated_essence_label}')
    #       poe_bot.bot_controls.keyboard_releaseKey('DIK_LSHIFT')
    #       for i in range(random.randint(2,3)):
    #         poe_bot.bot_controls.keyboard.tap('DIK_SPACE', wait_till_executed=False)
    #       if essence_corrupted is True:
    #         break


    #   else:
    #     print('dont have remnant of corruption')
    '''corruption end'''

    _i = 0
    while essence_opened is False and len(essences) != 0:
      _i += 1
      if _i > 50:
        poe_bot.helper_functions.relog()
        raise Exception('cannot open essence monolith for 50 iterations')
      essences = list(filter(lambda entity: essence_monolith_id == entity.id,poe_bot.game_data.entities.all_entities))
      # if len(essences) == 0:
      #   break
      essence_monolith = essences[0]
      print(f'[EssenceEncounter.doEncounter] essence_monolith {essence_monolith}')
      if essence_monolith.distance_to_player > 40:
        print(f'[EssenceEncounter.doEncounter] essence_monolith distance to player is too far away, getting closer')
        mover.goToEntitysPoint(
          entity_to_go=essence_monolith, 
          release_mouse_on_end=False,
          # release_mouse_on_end=True,
          step_size=random.randint(25,33)
        )
        continue
      pos_x, pos_y = poe_bot.convertPosXY(essence_monolith.location_on_screen.x,essence_monolith.location_on_screen.y)
      print(f'[EssenceEncounter.doEncounter] opening essence on {pos_x, pos_y}')
      poe_bot.bot_controls.mouse.setPosSmooth(pos_x,pos_y)
      # time.sleep(random.randint(5,7)/100)
      poe_bot.bot_controls.mouse.click()
      # time.sleep(random.randint(7,10)/100)
      poe_bot.refreshInstanceData()
      poe_bot.last_action_time = 0
      essences = list(filter(lambda entity: essence_monolith_id == entity.id,poe_bot.game_data.entities.all_entities))
      if len(essences) == 0 or essences[0].is_targetable is False :
        break
    print('[EssenceEncounter.doEncounter] essence opened')
    if len(essence_mobs) != 0:
      main_essence_mob = essence_mobs[0]
      print(f'[EssenceEncounter.doEncounter] main_essence_mob {main_essence_mob}')
      # entities_to_kill = list(filter(lambda e: e.path == main_essence_mob.path and e.distance_to_player < 40 and e.rarity == 'Rare', poe_bot.game_data.entities.all_entities))
      entities_to_kill = list(filter(lambda e: e.path == main_essence_mob.path and e.distance_to_player < 40 and e.rarity == 'Rare' and e.is_attackable is True, poe_bot.game_data.entities.all_entities))
      print(f'[EssenceEncounter.doEncounter] entities_to_kill {entities_to_kill}')
      for entity in entities_to_kill:
        poe_bot.combat_module.killTillCorpseOrDisappeared(entity)
    else:
      point_to_run_around = {"X": essence_monolith.grid_position.x, "Y": essence_monolith.grid_position.y}
      poe_bot.combat_module.clearLocationAroundPoint(point_to_run_around)
    poe_bot.refreshInstanceData()
    print(f'#[EssenceEncounter.doEncounter] nearby {essence_monolith} return at {time.time()}')
class UltimatumEncounter(Encounter):
  poe_bot: PoeBot
  ultimatum_altar:Entity
  def __init__(self, poe_bot:PoeBot, ultimatum_altar:Entity = None) -> None:
    self.poe_bot = poe_bot
    self.ultimatum_altar = ultimatum_altar
  def start(self):
    poe_bot = self.poe_bot
    ultimatum_initiator_ui = poe_bot.ui.ultimatum_initiator_ui
    ultimatum_initiator_ui.update()
    ultimatum_initiator_ui.hoverOverUltimatumModes()
    ultimatum_initiator_ui.update()
    if "???" in ultimatum_initiator_ui.choices:
      ultimatum_initiator_ui.update()
      ultimatum_initiator_ui.hoverOverUltimatumModes()

    ultimatum_possible_coices = ultimatum_initiator_ui.choices[:]
    best_choice = poe_bot.ui.ultimatum_next_wave_ui.getBestMod(ultimatum_possible_coices)
    ultimatum_initiator_ui.chooseMod(best_choice)
    ultimatum_initiator_ui.startEncounter()
    return True
  def run(self):
    poe_bot = self.poe_bot
    ultimatum_next_wave_ui = poe_bot.ui.ultimatum_next_wave_ui
    # poe_bot.combat_module.build.auto_flasks.pathfinder = True; print(f'forcing it to use flasks as pathfinder, remove')
    ultimatum_circle_radius = 20
    while True:
      poe_bot.combat_module.build.auto_flasks.useFlasks()
      poe_bot.refreshInstanceData()
      ultimatum_next_wave_ui.update()
      print(ultimatum_next_wave_ui)
      if ultimatum_next_wave_ui.visible:
        print(f'ultimatum tablet appeared, dealing with it')
        best_choice = ultimatum_next_wave_ui.chooseBestMod()
        print(f'choosing mod {best_choice}')
        if best_choice == 'Limited Arena':
          print(f'choice is limited arena, reducing circle radius ')
          ultimatum_circle_radius = 20
        ultimatum_next_wave_ui.chooseMod(best_choice, accept_trial = True)
        if ultimatum_next_wave_ui.visible is False:
          print(f'mod chosen, choose panel disappeared, doing next wave')
        else:
          print(f'mod chosen, waiting 5 sec for panel to disappear')
          for _waitforultimatumpaneldisappears in range(50):
            print(f'checking if ultimatum panel disappeared')
            time.sleep(0.1)
            ultimatum_next_wave_ui.update()
            if ultimatum_next_wave_ui.visible is False:
              print(f'ultimatum panel disappeared')
              break
      else:
        # use flasks if needed, pf especially
        poe_bot.combat_module.build.auto_flasks.useFlasks()
        trialmaster_entity = next( (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/NPC/League/Ultimatum/UltimatumNPC"), None)
        if trialmaster_entity:
          print(f'trialmaster_entity.is_targetable {trialmaster_entity.is_targetable}')
          if trialmaster_entity.is_targetable is True:
            print(f'seems like instance ended')
            break

        # TODO if stones
        stones = []
        if stones:
          print('need to stay in stones')
          nearest_stone:Entity = None # sorted by id or distance to altar?
          entity_to_follow=nearest_stone
        else:
          ultimatum_altar_path = "Metadata/Terrain/Leagues/Ultimatum/Objects/UltimatumChallengeInteractable"
          entity_to_follow:Entity = next( (e for e in poe_bot.game_data.entities.all_entities if e.path == ultimatum_altar_path), None)
          if entity_to_follow:
            ultimatum_altar_pos = (entity_to_follow.grid_position.x, entity_to_follow.grid_position.y)

        
        distance_to_ultimatum_altar = dist(ultimatum_altar_pos, (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y))
        if distance_to_ultimatum_altar > ultimatum_circle_radius:
          self.moveCloserToTarget(ultimatum_altar_pos[0], ultimatum_altar_pos[1])
  def pickupLootAfterUltimatum(self):
    poe_bot = self.poe_bot
    poe_bot.refreshInstanceData()
    pick_highest = False
    first_pick = 3
    i = 0
    min_pickup_duration = 4 # secs
    min_pickup_delay = 0.1
    while i < 100:
      i += 1
    # for i in range(100):
      amount_of_drop_before = poe_bot.loot_picker.loot_filter.getPickableItems()
      # drop_availiable = pickupDropV2(poe_bot, 0, 1)
      if pick_highest is False:
        pick_highest = True
      else:
        pick_highest = False
      drop_availiable = poe_bot.loot_picker.pickupDropV3(pick_highest=pick_highest)
      # TODO sometimes it covers objects
      pos_x,pos_y = poe_bot.convertPosXY(10,10)
      print(pos_x,pos_y)
      poe_bot.bot_controls.mouse.setPosSmooth(int(pos_x),int(pos_y))
      delay_multiplier = 0
      time.sleep(min_pickup_delay + 0.2 * (delay_multiplier + first_pick))
      if first_pick > 0:
        first_pick = 0
      poe_bot.refreshInstanceData()
      poe_bot.combat_module.build.auto_flasks.useFlasks()

      amount_of_drop_after = poe_bot.loot_picker.loot_filter.getPickableItems()

      print(amount_of_drop_after, amount_of_drop_before)
      if amount_of_drop_after != amount_of_drop_before:
        print('seems like the function was succesful')
      if drop_availiable is False:
        break
  def moveCloserToTarget(self, target_grid_pos_x, target_grid_pos_y):
    poe_bot = self.poe_bot
    bot_controls = self.poe_bot.bot_controls
    print(f'getting closer to our target')
    screen_pos_x, screen_pos_y = poe_bot.getPositionOfThePointOnTheScreen(x=target_grid_pos_x, y=target_grid_pos_y)
    pos_x, pos_y = poe_bot.convertPosXY(screen_pos_x, screen_pos_y)
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    bot_controls.keyboard.tap('DIK_T')
  def doUltimatumStashingRoutine(self, keep_scarabs_and_maps = False):
    poe_bot = self.poe_bot
    bot_controls = self.poe_bot.bot_controls
    stash = self.poe_bot.ui.stash
    inventory = self.poe_bot.ui.inventory
    poe_bot.ui.inventory.open()
    key_to_keep = "more Monster Life"
    items_to_sell = []
    items_to_stash = []
    items = poe_bot.ui.inventory.items
    bot_controls.keyboard_pressKey('DIK_LCONTROL')
    time.sleep(0.05)
    prev_clipboard = None
    for item in items:
      if item.name != "Inscribed Ultimatum":
        if keep_scarabs_and_maps:
          if "Scarab" in item.name or "Map" in item.name:
              pass
          else:
            items_to_stash.append(item)
        continue
      while True:
        new_clipboard = bot_controls.getClipboardText()
        item.hover()
        time.sleep(0.05)
        bot_controls.keyboard.tap('DIK_C')
        time.sleep(0.05)
        new_clipboard = bot_controls.getClipboardText()
        print("new_clipboard == prev_clipboard")
        if new_clipboard != None:
          break
      item.clipboard_text = new_clipboard
      if key_to_keep in item.clipboard_text or not "Inscribed Ultimatum" in item.clipboard_text:
        print('keep item')
        items_to_stash.append(item)
      else:
        print(f'recycle item')
        items_to_sell.append(item)
        print(item.clipboard_text)
      time.sleep(0.05)

    bot_controls.keyboard_releaseKey('DIK_LCONTROL')

    poe_bot.ui.closeAll()

    poe_bot.helper_functions.sellItems(items_to_sell=items_to_sell)
    stash.open()
    inventory.update()
    inventory.stashItems(items_to_stash)
    inscribed_ultimatum_keys_to_keep = [
      "Divine Orb",
      "Seven Years Bad Luck",
      "House of Mirrors",
      "Unrequited Love",
      "The Price of Devotion",
      "The Apothecary",
      "Fire Of Unknown Origin",
    ]

    ultimatum_by_keys = {
      30: [],
      70: [],
      120: [],
      200: []
    }

    stash.update()
    items = list(filter(lambda i: i.name == 'Inscribed Ultimatum', stash.current_tab_items))
    bot_controls.keyboard_pressKey('DIK_LCONTROL')
    time.sleep(0.05)
    prev_clipboard = None
    for item in items:
      while True:
        new_clipboard = bot_controls.getClipboardText()
        item.hover()
        time.sleep(0.05)
        bot_controls.keyboard.tap('DIK_C')
        time.sleep(0.05)
        new_clipboard = bot_controls.getClipboardText()
        print("new_clipboard == prev_clipboard")
        if new_clipboard != None:
          break
      item.clipboard_text = new_clipboard
      if any(list(map(lambda k: k in item.clipboard_text, inscribed_ultimatum_keys_to_keep))):
        print(f'keeping item')
      else:
        ultimatum_percentage = int(item.clipboard_text.split("% more Monster Life")[0].split('\n')[-1])
        print(f'item can be recycled, percentage {ultimatum_percentage}')
        ultimatum_by_keys[ultimatum_percentage].append(item)
      print(item.clipboard_text)

      time.sleep(0.05)
    bot_controls.keyboard_releaseKey('DIK_LCONTROL')

    can_recycle_smth = False
    inventory.update()
    items_grid_position_backup = list(map(lambda i: (i.grid_position.x1, i.grid_position.y1), inventory.items))

    for key in list(ultimatum_by_keys.keys()):
      ultimatum_by_key_list = ultimatum_by_keys[key]
      if len(ultimatum_by_key_list) < 4:
        continue
      can_recycle_smth = True
      combinations_count = int(len(ultimatum_by_key_list)/5)
      print(f'can recycle {key} ultimatums sets count: {combinations_count}')
      ultimatum_by_key_list = ultimatum_by_key_list[:combinations_count*5]
      stash.pickItems(ultimatum_by_key_list)

    inventory.update()
    new_items = list(filter(lambda i: not (i.grid_position.x1, i.grid_position.y1) in items_grid_position_backup, inventory.items))

    poe_bot.ui.closeAll()
    if can_recycle_smth:
      poe_bot.helper_functions.sellItems(items_to_sell=new_items, skip_items = False,shuffle_items = False)
  def moveCloserToAltar(self):
    poe_bot = self.poe_bot
    bot_controls = self.poe_bot.bot_controls
    print(f'getting closer to our target')
    screen_pos_x, screen_pos_y = poe_bot.getPositionOfThePointOnTheScreen(self.ultimatum_altar_pos[1], self.ultimatum_altar_pos[0])
    pos_x, pos_y = poe_bot.convertPosXY(screen_pos_x, screen_pos_y)
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    bot_controls.keyboard.tap('DIK_T')
class IncursionEncounter(Encounter):
  def __init__(self, poe_bot:PoeBot) -> None:
    super().__init__(poe_bot)
    self.incursion_doors_temp:List[Entity] = []
    self.incursion_doors_ids_temp:List[int] = []
  def doIncursionRoom(self, incursion_explore_direction, kill_architect_priority, preferable_rooms_to_open_sorted, clear_room = False):
    poe_bot = self.poe_bot
    build = poe_bot.combat_module.build
    inventory = poe_bot.ui.inventory
    print(f'#doIncursionRoom call {incursion_explore_direction} {kill_architect_priority} {preferable_rooms_to_open_sorted} {clear_room}')

    architect_killed = False
    def findDoors():
      closed_doors = list(filter(lambda e: e.path == INCURSION_CLOSED_DOOR_PATH_KEY, poe_bot.game_data.entities.all_entities))
      if closed_doors:
        for door in closed_doors:
          if door.id in self.incursion_doors_ids_temp:
            continue
          print(f'found new door {door}')
          self.incursion_doors_temp.append(door)
          self.incursion_doors_ids_temp.append(door.id)
    def findArchitect():
      return next( (e for e in poe_bot.game_data.entities.unique_entities if e.render_name == kill_architect_priority and e.life.health.current != 0), None)
    def killArchitectAndCollectLoot(*args):
      nonlocal architect_killed
      nonlocal preferable_rooms_to_open_sorted
      findDoors()
      architect_entity = findArchitect()
      if architect_entity:
        print(f'architect found {architect_entity.raw}')
        poe_bot.combat_module.killTillCorpseOrDisappeared(architect_entity)
        architect_killed = True
        return True
      else:
        if preferable_rooms_to_open_sorted != []:
          return poe_bot.loot_picker.collectLoot()
        else:
          return False

    poe_bot.refreshInstanceData()
    poe_bot.game_data.terrain.getCurrentlyPassableArea()
    # plt.imshow(poe_bot.game_data.terrain.currently_passable_area);plt.show()
    exit_portal = None
    look_for_exit_portal_i = 0
    while exit_portal is None:
      look_for_exit_portal_i += 1
      print(f'look_for_exit_portal_i {look_for_exit_portal_i}')
      if look_for_exit_portal_i % 10 == 0:
        poe_bot.backend.forceRefreshArea()

      if look_for_exit_portal_i == 99:
        poe_bot.raiseLongSleepException(f'cannot find portal in incursion {poe_bot.backend.last_data}')
      
      print(f'looking for exit portal')
      exit_portal = next( (e for e in poe_bot.game_data.entities.all_entities if e.path == INCURSION_EXIT_PORTAL_PATH_KEY and e.distance_to_player < 50), None)
      poe_bot.refreshInstanceData()
    print(f'exit portal found {exit_portal.raw}')
    poe_bot.game_data.terrain.getCurrentlyPassableArea()

    enter_point = (exit_portal.grid_position.x, exit_portal.grid_position.y)

    data = np.where(poe_bot.game_data.terrain.currently_passable_area != 0)
    passable_points = list(zip(data[1], data[0])) # [[x,y]] ordered by top->bottom, left->right y-axis inc, x-axis inc
    most_270_degree_points = sorted(passable_points, key=lambda p: p[0]) # left
    most_0_degree_points = sorted(passable_points, key=lambda p: p[1]) # top
    y_offset = most_0_degree_points[0][1]
    y_limit = most_0_degree_points[-1][1]
    x_offset = most_270_degree_points[0][0]
    x_limit = most_270_degree_points[-1][0]

    x1,x2,y1,y2 = x_offset,x_limit,y_offset,y_limit
    incursion_room_zone_points = list(filter(lambda point: point[0]>x1 and point[0]<x2 and point[1]>y1 and point[1]<y2, passable_points))
    middle_x = enter_point[0]
    middle_x_zone = [middle_x-50, middle_x+50]
    middle_zone = [middle_x_zone[0],middle_x_zone[1],y_offset,y_limit] # [x1,x2,y1,y2]
    x1,x2,y1,y2 = middle_zone
    middle_zone_points = list(filter(lambda point: point[0]>x1 and point[0]<x2 and point[1]>y1 and point[1]<y2, incursion_room_zone_points))
    passable_points_in_middle_sorted_by_y = sorted(middle_zone_points, key=lambda p: p[1]) # top
    middle_y = int( (passable_points_in_middle_sorted_by_y[0][1] + passable_points_in_middle_sorted_by_y[-1][1])/2 )
    middle_y_zone = [middle_y-50, middle_y+50]

    left_points = []
    left_incursion_zone = [x_offset,middle_x_zone[0],y_offset,y_limit] # [x1,x2,y1,y2]
    x1,x2,y1,y2 = left_incursion_zone
    # plt.imshow(poe_bot.game_data.terrain.currently_passable_area[y1:y2, x1:x2]);plt.show()

    left_top_zone = [x_offset,middle_x_zone[0],y_offset,middle_y_zone[0]] # [x1,x2,y1,y2]
    x1,x2,y1,y2 = left_top_zone
    points = list(filter(lambda point: point[0]>x1 and point[0]<x2 and point[1]>y1 and point[1]<y2, incursion_room_zone_points))
    points.reverse() # for left or top or left+top
    # points.sort(key=lambda point: point[0], reverse = False) # x axis
    points.sort(key=lambda point: point[1], reverse = False) # y axis
    point = points[0]
    left_points.append(point)
    # plt.imshow(poe_bot.game_data.terrain.currently_passable_area[y1:y2, x1:x2]);plt.show()

    left_middle_zone = [x_offset,middle_x_zone[0],middle_y_zone[0],middle_y_zone[1]] # [x1,x2,y1,y2]
    x1,x2,y1,y2 = left_middle_zone
    points = list(filter(lambda point: point[0]>x1 and point[0]<x2 and point[1]>y1 and point[1]<y2, incursion_room_zone_points))
    points.reverse() # for left or top or left+top
    points.sort(key=lambda point: point[0], reverse = False) # x axis
    # points.sort(key=lambda point: point[1], reverse = False) # y axis
    point = points[0]
    left_points.append(point)

    left_bottom_zone = [x_offset,middle_x_zone[0],middle_y_zone[1],y_limit] # [x1,x2,y1,y2]
    x1,x2,y1,y2 = left_bottom_zone
    points = list(filter(lambda point: point[0]>x1 and point[0]<x2 and point[1]>y1 and point[1]<y2, incursion_room_zone_points))
    points.reverse() # for left or top or left+top
    # points.sort(key=lambda point: point[0], reverse = False) # x axis
    points.sort(key=lambda point: point[1], reverse = True) # y axis
    point = points[0]
    left_points.append(point)

    right_points = []
    right_incursion_zone = [middle_x_zone[1],x_limit,y_offset,y_limit] # [x1,x2,y1,y2]
    x1,x2,y1,y2 = right_incursion_zone
    # plt.imshow(poe_bot.game_data.terrain.currently_passable_area[y1:y2, x1:x2]);plt.show()

    right_top_zone = [middle_x_zone[1],x_limit,y_offset,middle_y_zone[0]] # [x1,x2,y1,y2]
    x1,x2,y1,y2 = right_top_zone
    points = list(filter(lambda point: point[0]>x1 and point[0]<x2 and point[1]>y1 and point[1]<y2, incursion_room_zone_points))
    points.reverse() # for left or top or left+top
    # points.sort(key=lambda point: point[0], reverse = False) # x axis
    points.sort(key=lambda point: point[1], reverse = False) # y axis
    point = points[0]
    right_points.append(point)

    right_middle_zone = [middle_x_zone[1],x_limit,middle_y_zone[0],middle_y_zone[1]] # [x1,x2,y1,y2]
    x1,x2,y1,y2 = right_middle_zone
    points = list(filter(lambda point: point[0]>x1 and point[0]<x2 and point[1]>y1 and point[1]<y2, incursion_room_zone_points))
    points.reverse() # for left or top or left+top
    points.sort(key=lambda point: point[0], reverse = True) # x axis
    # points.sort(key=lambda point: point[1], reverse = False) # y axis
    point = points[0]
    right_points.append(point)

    right_bottom_zone = [middle_x_zone[1],x_limit,middle_y_zone[1],y_limit] # [x1,x2,y1,y2]
    x1,x2,y1,y2 = right_bottom_zone
    points = list(filter(lambda point: point[0]>x1 and point[0]<x2 and point[1]>y1 and point[1]<y2, incursion_room_zone_points))
    points.reverse() # for left or top or left+top
    # points.sort(key=lambda point: point[0], reverse = True) # x axis
    points.sort(key=lambda point: point[1], reverse = True) # y axis
    point = points[0]
    right_points.append(point)

    right_points.reverse()

    
    if random.randint(1,2) == 1: # reverse if needed
      left_points.reverse()
      right_points.reverse()

    incursion_explore_points = left_points + right_points

    # point generation end

    if incursion_explore_direction == 'right': incursion_explore_points.reverse()
    print(f'incursion_explore_points: {incursion_explore_points}')

    # cpa = poe_bot.game_data.terrain.currently_passable_area
    # area_size = 100
    # for point in incursion_explore_points: plt.imshow(cpa[point[1]-area_size:point[1]+area_size, point[0]-area_size:point[0]+area_size]);plt.show()
    architect_points = incursion_explore_points[:int(len(incursion_explore_points)/2)]
    other_points = incursion_explore_points[int(len(incursion_explore_points)/2):]
    for point in architect_points:
      # kill architect if found
      while True:
        res = poe_bot.mover.goToPoint(
          point=point,
          min_distance=50,
          custom_continue_function=build.usualRoutine,
          custom_break_function=killArchitectAndCollectLoot,
          release_mouse_on_end=False,
          # release_mouse_on_end=True,
          step_size=random.randint(25,33)
        )
        if architect_killed is True and preferable_rooms_to_open_sorted == []:
          print(f'no need to go there')
          break
        if res is None:
          break
      if clear_room:
        self.poe_bot.combat_module.clearLocationAroundPoint({"X": point[0], "Y": point[1]}, 70)
      if clear_room == False and architect_killed is True and preferable_rooms_to_open_sorted == []:
        print(f'nothing to do here, leaving')
        break
    
    if clear_room == True or preferable_rooms_to_open_sorted != []:
      print(f'going to explore more')
      for point in other_points:
        # plt.imshow(cpa[point[1]-area_size:point[1]+area_size, point[0]-area_size:point[0]+area_size]);plt.show()
        while True:
          res = poe_bot.mover.goToPoint(
            point=point,
            min_distance=50,
            custom_continue_function=build.usualRoutine,
            custom_break_function=killArchitectAndCollectLoot,
            release_mouse_on_end=False,
            # release_mouse_on_end=True,
            step_size=random.randint(25,33)
          )
          if res is None:
            break
        if clear_room:
          self.poe_bot.combat_module.clearLocationAroundPoint({"X": point[0], "Y": point[1]}, 70)
      poe_bot.ui.inventory.update()
      stones_of_passage = list(filter(lambda i: 'Art/2DItems/QuestItems/Wheel.dds' in i.render_path, inventory.items))
      print(f'have {len(stones_of_passage)} keys')
      print('incursion_doors_temp')
      for door_temp in self.incursion_doors_temp:
        print(door_temp.raw)
      # open preferable doors
      for preferable_door in preferable_rooms_to_open_sorted:
        if len(stones_of_passage) == 0:
          print("have no keys to open more doors")
          break
        door_entity = next( (e for e in self.incursion_doors_temp if e.render_name == preferable_door), None)
        if door_entity:
          while True:
            res = poe_bot.mover.goToPoint(
              point=(door_entity.grid_position.x, door_entity.grid_position.y),
              min_distance=30,
              custom_continue_function=build.usualRoutine,
              custom_break_function=killArchitectAndCollectLoot,
              release_mouse_on_end=False,
              # release_mouse_on_end=True,
              step_size=random.randint(25,33)
            )
            if res is None:
              break
          print(f'arrived to activator')
          poe_bot.ui.inventory.update()
          stones_of_passage = list(filter(lambda i: 'Art/2DItems/QuestItems/Wheel.dds' in i.render_path, inventory.items))
          print(f'have {len(stones_of_passage)} keys left after arrival to activator')
          if len(stones_of_passage) == 0:
            print("have no keys to open more doors")
            break
          activate_door_i = 0
          while True:
            print(f'activate_door_i {activate_door_i}')
            activate_door_i+=1
            if activate_door_i % 10 == 0:
              poe_bot.backend.forceRefreshArea()
            if activate_door_i>80:
              game_img = poe_bot.getImage()
              print(poe_bot.backend.last_data)
              plt.imshow(game_img);plt.show();
              self.poe_bot.raiseLongSleepException('cannot activate activator on map')
            updated_transition = next( (e for e in poe_bot.game_data.entities.all_entities if e.id == door_entity.id), None)
            updated_transition = None
            if updated_transition is not None:
              activated = updated_transition.is_targetable is False
              if activated is True:
                print('entity is not targetable anymore, breaking')
                break
              poe_bot.ui.inventory.update()
              stones = list(filter(lambda i: 'Art/2DItems/QuestItems/Wheel.dds' in i.render_path, inventory.items))
              if len(stones) < len(stones_of_passage):
                print('stone of passage disappeared, break')
                break
              pos_to_click = (updated_transition.location_on_screen.x, updated_transition.location_on_screen.y)
              print(f'entity screen pos {pos_to_click}')
            else:
              door_entity.updateLocationOnScreen()
              pos_to_click = (door_entity.location_on_screen.x, door_entity.location_on_screen.y)
              print(f'converted screen pos {pos_to_click}')
              poe_bot.ui.inventory.update()
              stones = list(filter(lambda i: 'Art/2DItems/QuestItems/Wheel.dds' in i.render_path, inventory.items))
              if len(stones) < len(stones_of_passage):
                print('stone of passage disappeared, break')
                break
            pos_x, pos_y = poe_bot.convertPosXY(pos_to_click[0], pos_to_click[1])
            poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
            poe_bot.bot_controls.mouse.click()
            poe_bot.refreshInstanceData()

          poe_bot.ui.inventory.update()
          stones_of_passage = list(filter(lambda i: 'Art/2DItems/QuestItems/Wheel.dds' in i.render_path, inventory.items))
          print(f'have {len(stones_of_passage)} keys left after opening door')
        else:
          print(f"{preferable_door} door not found")
    print(f'gonna go to portal')
    while True:
      res = poe_bot.mover.goToPoint(
        point=enter_point,
        min_distance=30,
        custom_continue_function=build.usualRoutine,
        custom_break_function=killArchitectAndCollectLoot,
        release_mouse_on_end=False,
        # release_mouse_on_end=True,
        step_size=random.randint(25,33)
      )
      if res is None:
        break
    # leave incursion

    exit_portal = None
    look_for_exit_portal_i = 0
    while exit_portal is None:
      look_for_exit_portal_i += 1
      print(f'look_for_exit_portal_i {look_for_exit_portal_i}')
      if look_for_exit_portal_i % 10 == 0:
        poe_bot.backend.forceRefreshArea()

      if look_for_exit_portal_i == 99:
        poe_bot.raiseLongSleepException(f'cannot find portal in incursion {poe_bot.backend.last_data}')
      
      print(f'looking for exit portal')
      poe_bot.refreshInstanceData()
      portal_entity = next( (e for e in poe_bot.game_data.entities.area_transitions if e.path == INCURSION_EXIT_PORTAL_PATH_KEY), None)
      if portal_entity:
        print(f'exit portal found {portal_entity.raw}')
        poe_bot.mover.enterTransition(portal_entity)
        poe_bot.refreshInstanceData()
        poe_bot.game_data.terrain.getCurrentlyPassableArea()
        break
class LegionEncounter(Encounter):
  def __init__(self, poe_bot: PoeBot) -> None:
    super().__init__(poe_bot)
  def findMoreValuableMobInStasisToKill(self, include_normal = False)->Entity:
    legion_mobs:List[Entity] = []
    generals:List[Entity] = []
    chests:List[Entity] = []
    sergeants:List[Entity] = []
    others:List[Entity] = []
    # iterate over legion mobs
    # sort them by
    for e in self.poe_bot.game_data.entities.attackable_entities:
      if not "/LegionLeague/" in e.path:
        continue
      legion_mobs.append(e)
      if "General" in e.path:
        generals.append(e)
      elif "MonsterChest" in e.path:
        chests.append(e)
      elif "Sergeant" in e.path:
        sergeants.append(e)
      else:
        others.append(e)

    mobs_to_kill = []
    mobs_to_kill.extend(chests)
    mobs_to_kill.extend(generals)
    mobs_to_kill.extend(sergeants)


    sorted_mobs = []
    if len(chests) != 0:
      sorted_mobs = sorted(chests, key=lambda e: e.distance_to_player)
      mob_to_kill = sorted_mobs[0]
    elif len(generals) != 0:
      sorted_mobs = sorted(generals, key=lambda e: e.distance_to_player)
      mob_to_kill = sorted_mobs[0]
    elif len(sergeants) != 0:
      sorted_mobs = sorted(sergeants, key=lambda e: e.distance_to_player)
      mob_to_kill = sorted_mobs[0]
    elif include_normal is True and len(others) != 0:
      sorted_mobs = sorted(others, key=lambda e: e.distance_to_player)
      mob_to_kill = sorted_mobs[0]

    if len(sorted_mobs) == 0:
      mob_to_kill = None
    else:
      mob_to_kill:Entity = sorted_mobs[0]

    return mob_to_kill
class HarbringerEncounter(Encounter):
  def __init__(self, poe_bot: PoeBot, harbringer_entity:Entity) -> None:
    super().__init__(poe_bot)
    self.encounter_entity = harbringer_entity
  def do(self):
    print(f'[HarbringerEncounter.do] nearby {self.encounter_entity} call at {time.time()}')
    harbringer_id = self.encounter_entity.id
    while True:
      current_harbringers = list(filter(lambda e: harbringer_id == e.id, self.poe_bot.game_data.entities.all_entities))
      if len(current_harbringers) != 0:
        current_harbringer = current_harbringers[0]
        harbringer_bosses = list(filter(lambda e: e.path == "Metadata/Monsters/Avatar/AvatarBossAtlas", self.poe_bot.game_data.entities.all_entities))
        if len(harbringer_bosses) != 0:
          print(f'[HarbringerEncounter.do] found harbringer bosses nearby')
          sorted_harbringer_bosses = sorted(harbringer_bosses, key=lambda e: dist( (e.grid_position.x, e.grid_position.y), (current_harbringer.grid_position.x, current_harbringer.grid_position.y) ))
          nearest_harbringer_boss = sorted_harbringer_bosses[0]
          current_harbringer = nearest_harbringer_boss
        # self.poe_bot.combat_module.clearLocationAroundPoint({"X": current_harbringer.grid_position.x, "Y": current_harbringer.grid_position.y}, detection_radius=50, ignore_keys=['Metadata/Monsters/Avatar/Avatar'])
        self.poe_bot.combat_module.clearAreaAroundPoint(current_harbringer.grid_position.toList(), detection_radius=50, ignore_keys=['Metadata/Monsters/Avatar/Avatar'])
        self.poe_bot.refreshInstanceData()
      else:
        print(f'[HarbringerEncounter.do] no harbringers visible')
        break
    print(f'[HarbringerEncounter.do] nearby {self.encounter_entity} return at {time.time()}')