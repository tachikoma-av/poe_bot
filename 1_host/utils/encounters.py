from __future__ import annotations

import typing
from typing import List

if typing.TYPE_CHECKING:
  from .gamehelper import Entity, PoeBot

import random
import time
from math import dist
from abc import abstractmethod

from .components import PoeBotComponent


class Encounter(PoeBotComponent):
  def __init__(self, poe_bot: PoeBot) -> None:
    super().__init__(poe_bot)
    # encounter start entity

  @abstractmethod
  def doEncounter(self):
    self.poe_bot.raiseLongSleepException("encounter.do is not defined")


class Bossroom(Encounter):
  def __init__(
    self,
    poe_bot: PoeBot,
    transition_entity: Entity,
    boss_render_names: List[str],
    activator_inside_bossroom_path: str = None,
    refresh_terrain_data_in_bossroom=False,
    leave_bossroom_after_clear=True,
    clear_room_custom_break_function=lambda *args, **kwargs: False,
    need_to_leave_bossroom_through_transition=True,
    transitions_inside_bossroom=[],
    activate_boss_in_center=False,
  ) -> None:
    super().__init__(poe_bot)
    self.refresh_terrain_data_in_bossroom = refresh_terrain_data_in_bossroom
    self.transition_entity = transition_entity
    self.activator_inside_bossroom_path = activator_inside_bossroom_path
    self.activated_activator_in_bossroom = False
    self.exit_transition_entity: Entity = None
    self.boss_render_names = boss_render_names
    self.killed_boss_entities: List[Entity] = []
    self.leave_bossroom_after_clear = leave_bossroom_after_clear
    self.need_to_leave_bossroom_through_transition = need_to_leave_bossroom_through_transition
    self.clear_room_custom_break_function = clear_room_custom_break_function
    self.transitions_inside_bossroom = transitions_inside_bossroom
    self.activate_boss_in_center = activate_boss_in_center
    self.boss_is_on_unpassable = False
    print(vars(self))

  def seekForBosses(self):
    map_bosses = list(
      filter(
        lambda e: e.life.health.current != 0
        and e.render_name in self.boss_render_names
        and self.poe_bot.game_data.terrain.checkIfPointPassable(e.grid_position.x, e.grid_position.y),
        self.poe_bot.game_data.entities.unique_entities,
      )
    )
    return map_bosses

  def activateBossroomActivatorIfFoundOrPresented(self):
    if self.activator_inside_bossroom_path is not None and self.activated_activator_in_bossroom is False:
      activator: Entity = next((e for e in self.poe_bot.game_data.entities.all_entities if e.path == self.activator_inside_bossroom_path), None)
      if activator:
        if activator.is_targetable is True:
          activator.clickTillNotTargetable()
        else:
          print("activator is not targetable")
        self.activated_activator_in_bossroom = True
        return True
    return False

  def enterBossroom(self):
    print("entering bosroom encounter")
    print(self.transition_entity.raw)
    while True:
      res = self.poe_bot.mover.goToPoint(
        point=[self.transition_entity.grid_position.x, self.transition_entity.grid_position.y],
        min_distance=30,
        release_mouse_on_end=False,
        custom_break_function=self.poe_bot.loot_picker.collectLoot,
        step_size=random.randint(25, 33),
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
      print(f"exit_transition_test {exit_transition_test.raw}")
    self.exit_pos_x, self.exit_pos_y = self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y
    print(f"entered bossroom exit_pos_x, exit_pos_y {self.exit_pos_x, self.exit_pos_y}")
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

  def killBoss(self, entity: Entity, clear_around_radius=150):
    poe_bot = self.poe_bot
    mover = self.poe_bot.mover
    if self.activate_boss_in_center is not False:
      print("will activate boss in center")
      bossroom_center = self.poe_bot.pather.utils.getCenterOf(self.poe_bot.game_data.terrain.currently_passable_area)
    start_time = time.time()

    print(f"#bossroom.killBoss {start_time} {entity.raw}")
    boss_entity = entity
    boss_entity_id = boss_entity.id

    if boss_entity.is_targetable is False or boss_entity.is_attackable is False:
      print("boss is not attackable or not targetable, going to it and activating it")
      if self.activate_boss_in_center is not False:
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
          step_size=random.randint(25, 33),
        )
        if res is None:
          break
      # running and killing till it's activated
      while True:
        if start_time + 120 < time.time():
          print("killing boss for more than 120 seconds")
          poe_bot.on_stuck_function()
        boss_entity = list(filter(lambda e: e.id == boss_entity_id, poe_bot.game_data.entities.all_entities))
        if len(boss_entity) == 0:
          print("len(boss_entity) == 0 corpse disappeared:")
          return True
        boss_entity = boss_entity[0]
        if boss_entity.life.health.current == 0:
          print("boss is dead")
          return True
        if boss_entity.is_targetable is not True or boss_entity.is_attackable is not True:
          print("boss is not attackable or not targetable")
          print(f"going to it clearing around it {boss_entity.raw}")
          killed_someone = poe_bot.combat_module.clearLocationAroundPoint(
            {"X": pos_to_go_x, "Y": pos_to_go_y},
            detection_radius=clear_around_radius,
            # ignore_keys=self.current_map.entities_to_ignore_in_bossroom_path_keys
          )
          if killed_someone is False:
            point = poe_bot.game_data.terrain.pointToRunAround(
              point_to_run_around_x=pos_to_go_x,
              point_to_run_around_y=pos_to_go_y,
              distance_to_point=15,
            )
            mover.move(grid_pos_x=point[0], grid_pos_y=point[1])
          poe_bot.refreshInstanceData(reset_timer=killed_someone)
        else:
          print("boss is attackable and targetable, going to kill it")
          poe_bot.combat_module.killUsualEntity(boss_entity, max_kill_time_sec=30)
          if self.activate_boss_in_center is not True:
            pos_to_go_x, pos_to_go_y = boss_entity.grid_position.x, boss_entity.grid_position.y
    else:
      print("boss is attackable and targetable, going to kill it")
      if boss_entity.distance_to_player > 40:
        while True:
          res = mover.goToPoint(
            (boss_entity.grid_position.x, boss_entity.grid_position.y),
            min_distance=35,
            # custom_break_function=collectLootIfFound,
            release_mouse_on_end=False,
            step_size=random.randint(25, 33),
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

    print(f"going to clear the bossroom {self.transition_entity}")
    unique_entities = self.seekForBosses()
    if len(unique_entities) != 0:
      print(f"unique_entities: {unique_entities}")
      for entity in unique_entities:
        self.killBoss(entity=entity)
    else:
      print("unique_entities empty, exploring and killing uniques")
      grid_pos_to_go_x, grid_pos_to_go_y = poe_bot.game_data.terrain.getFurtherstPassablePoint()
      _i = 0
      while True:
        _i += 1
        if _i == 100:
          poe_bot.helper_functions.relog()
          raise Exception("stuck on exploring bossroom")
        res = mover.goToPoint(
          point=[grid_pos_to_go_x, grid_pos_to_go_y],
          min_distance=50,
          release_mouse_on_end=False,
          custom_break_function=custom_break_function_nested,
          step_size=random.randint(25, 33),
        )
        if res is None or res is True:
          break
      unique_entities = self.seekForBosses()
      print(f"unique_entities after explore: {unique_entities}")
      for entity in unique_entities:
        self.killBoss(entity=entity)
    poe_bot.refreshInstanceData()
    loot_picker.collectLootWhilePresented()
    print("[Bossroom encounter] bossroom cleared")

  def leaveBossroom(self):
    print(f"#[Bossroom.leaveBossroom]  at {time.time()}")
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
          raise Exception("look_for_exit_transition > 100:")

        print("going to leave bossroom")
        print(f"exit_pos_x, exit_pos_y {self.exit_pos_x, self.exit_pos_y}")
        while True:
          print(f"going 100 to exit point {self.exit_pos_x, self.exit_pos_y}")
          res = mover.goToPoint(
            point=[self.exit_pos_x, self.exit_pos_y],
            min_distance=100,
            release_mouse_on_end=False,
            custom_continue_function=self.poe_bot.combat_module.build.usualRoutine,
            custom_break_function=self.killBossEntityIfFound,
            step_size=random.randint(25, 33),
          )
          poe_bot.loot_picker.collectLootWhilePresented()
          if res is None:
            break
        while True:
          print(f"going 30 to exit point {self.exit_pos_x, self.exit_pos_y}")
          res = mover.goToPoint(
            point=[self.exit_pos_x, self.exit_pos_y],
            min_distance=30,
            release_mouse_on_end=False,
            custom_break_function=self.killBossEntityIfFound,
            step_size=random.randint(25, 33),
          )

          poe_bot.loot_picker.collectLootWhilePresented()
          if res is None:
            break
        # exit_transitions = list(filter(lambda e: e.id != bossroom_id and dist((e.grid_position.x, e.grid_position.y), (exit_pos_x, exit_pos_y)) < 40, poe_bot.game_data.entities.area_transitions))
        exit_transitions = list(
          filter(
            lambda e: e.id != self.transition_entity.id and poe_bot.game_data.terrain.checkIfPointPassable(e.grid_position.x, e.grid_position.y),
            poe_bot.game_data.entities.area_transitions,
          )
        )

        if len(exit_transitions) == 0:
          print("exit transition is not visible or doesnt exist")
          grid_pos_to_go_x, grid_pos_to_go_y = self.poe_bot.game_data.terrain.getFurtherstPassablePoint()
          # TODO infinite loop if failure onenter transition
          while True:
            res = mover.goToPoint(
              point=[grid_pos_to_go_x, grid_pos_to_go_y],
              min_distance=50,
              release_mouse_on_end=False,
              custom_break_function=self.killBossEntityIfFound,
              step_size=random.randint(25, 33),
            )
            if res is None:
              break
          continue

        exit_transition = exit_transitions[0]
        mover.enterTransition(exit_transition)
        self.exit_transition_entity = exit_transition
        # self.temp.visited_transitions_ids.append(exit_transition.id)
        print("left the bossroom")
        break
    poe_bot.game_data.terrain.getCurrentlyPassableArea()  # to refresh currently passable area

  def doEncounter(self):
    self.enterBossroom()
    self.clearBossroom()
    if self.leave_bossroom_after_clear:
      self.leaveBossroom()


class EssenceEncounter(Encounter):
  def __init__(self, poe_bot, encounter_entity: Entity):
    super().__init__(poe_bot)
    self.encounter_entity = encounter_entity

  def doEncounter(self):
    poe_bot = self.poe_bot
    mover = self.poe_bot.mover
    # debug
    # poe_bot.refreshInstanceData()
    # go to around essence

    essence_monolith = self.encounter_entity
    print(f"#[EssenceEncounter.doEncounter] nearby {essence_monolith} call at {time.time()}")
    essence_opened = False
    essence_monolith_id = essence_monolith.id

    while True:
      res = mover.goToEntitysPoint(
        entity_to_go=essence_monolith,
        min_distance=75,
        custom_break_function=poe_bot.loot_picker.collectLoot,
        release_mouse_on_end=False,
        step_size=random.randint(25, 33),
      )
      if res is None:
        break

    """corruption start"""
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
    """corruption end"""
    poe_bot.combat_module.clearLocationAroundPoint(
      {"X": essence_monolith.grid_position.x, "Y": essence_monolith.grid_position.y}, detection_radius=45
    )
    poe_bot.refreshInstanceData()
    essence_mobs = list(
      filter(
        lambda e: e.grid_position.x == essence_monolith.grid_position.x
        and e.grid_position.y == essence_monolith.grid_position.y
        and e.rarity == "Rare",
        poe_bot.game_data.entities.all_entities,
      )
    )

    essences = list(filter(lambda entity: essence_monolith_id == entity.id, poe_bot.game_data.entities.all_entities))
    if len(essences) == 0:
      print("[EssenceEncounter.doEncounter] len(essences) == 0 after we arrived")
      return False

    print(f"[EssenceEncounter.doEncounter] essence_mobs {essence_mobs}")

    # opening essence
    essence_monolith = essences[0]
    poe_bot.combat_module.build.prepareToFight(essence_monolith)

    """corruption start"""
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
    """corruption end"""

    _i = 0
    while essence_opened is False and len(essences) != 0:
      _i += 1
      if _i > 50:
        poe_bot.helper_functions.relog()
        raise Exception("cannot open essence monolith for 50 iterations")
      essences = list(filter(lambda entity: essence_monolith_id == entity.id, poe_bot.game_data.entities.all_entities))
      # if len(essences) == 0:
      #   break
      essence_monolith = essences[0]
      print(f"[EssenceEncounter.doEncounter] essence_monolith {essence_monolith}")
      if essence_monolith.distance_to_player > 40:
        print("[EssenceEncounter.doEncounter] essence_monolith distance to player is too far away, getting closer")
        mover.goToEntitysPoint(
          entity_to_go=essence_monolith,
          release_mouse_on_end=False,
          # release_mouse_on_end=True,
          step_size=random.randint(25, 33),
        )
        continue
      pos_x, pos_y = poe_bot.convertPosXY(essence_monolith.location_on_screen.x, essence_monolith.location_on_screen.y)
      print(f"[EssenceEncounter.doEncounter] opening essence on {pos_x, pos_y}")
      poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      # time.sleep(random.randint(5,7)/100)
      poe_bot.bot_controls.mouse.click()
      # time.sleep(random.randint(7,10)/100)
      poe_bot.refreshInstanceData()
      poe_bot.last_action_time = 0
      essences = list(filter(lambda entity: essence_monolith_id == entity.id, poe_bot.game_data.entities.all_entities))
      if len(essences) == 0 or essences[0].is_targetable is False:
        break
    print("[EssenceEncounter.doEncounter] essence opened")
    if len(essence_mobs) != 0:
      main_essence_mob = essence_mobs[0]
      print(f"[EssenceEncounter.doEncounter] main_essence_mob {main_essence_mob}")
      # entities_to_kill = list(filter(lambda e: e.path == main_essence_mob.path and e.distance_to_player < 40 and e.rarity == 'Rare', poe_bot.game_data.entities.all_entities))
      entities_to_kill = list(
        filter(
          lambda e: e.path == main_essence_mob.path and e.distance_to_player < 40 and e.rarity == "Rare" and e.is_attackable is True,
          poe_bot.game_data.entities.all_entities,
        )
      )
      print(f"[EssenceEncounter.doEncounter] entities_to_kill {entities_to_kill}")
      for entity in entities_to_kill:
        poe_bot.combat_module.killTillCorpseOrDisappeared(entity)
    else:
      point_to_run_around = {"X": essence_monolith.grid_position.x, "Y": essence_monolith.grid_position.y}
      poe_bot.combat_module.clearLocationAroundPoint(point_to_run_around)
    poe_bot.refreshInstanceData()
    print(f"#[EssenceEncounter.doEncounter] nearby {essence_monolith} return at {time.time()}")


class RitualEncounter(Encounter):
  def __init__(self, poe_bot, encounter_entity: Entity):
    super().__init__(poe_bot)
    self.encounter_entity = encounter_entity

  def doEncounter(self):
    clear_area = 100
    kite_direction_reversed = random.choice([True, False])
    poe_bot = self.poe_bot
    poe_bot.mover.goToEntitysPoint(self.encounter_entity, min_distance=50)
    poe_bot.combat_module.clearAreaAroundPoint(self.encounter_entity.grid_position.toList(), detection_radius=clear_area)
    poe_bot.mover.goToEntitysPoint(self.encounter_entity)
    self.encounter_entity.clickTillNotTargetable()
    while True:
      poe_bot.refreshInstanceData()
      killed_smth = poe_bot.combat_module.clearAreaAroundPoint(self.encounter_entity.grid_position.toList(), detection_radius=69)
      if not killed_smth:
        point_to_run = poe_bot.game_data.terrain.pointToRunAround(
          *self.encounter_entity.grid_position.toList(), reversed=kite_direction_reversed, check_if_passable=True
        )
        poe_bot.mover.move(*point_to_run)
      ritual_entity = next((e for e in poe_bot.game_data.entities.all_entities if e.id == self.encounter_entity.id), None)
      if ritual_entity and ritual_entity.is_opened is False:
        break
    return True


class BreachEncounter(Encounter):
  def __init__(self, poe_bot, encounter_entity: Entity):
    super().__init__(poe_bot)
    self.encounter_entity = encounter_entity

  def doEncounter(self):
    """
    doesnt include clearing the breach, itll just open it and done
    """
    poe_bot = self.poe_bot
    print(f"[BreachEncounter.doEncounter] {self.encounter_entity}")
    poe_bot.mover.goToEntitysPoint(self.encounter_entity)

    def custombreakfunc(*args, **kwargs):
      entity_exists = next((e for e in poe_bot.game_data.entities.all_entities if e.id == self.encounter_entity.id), None)
      if entity_exists is None:
        return True
      return False

    poe_bot.mover.goToEntitysPoint(self.encounter_entity, min_distance=-1, custom_break_function=custombreakfunc)
    return True


class DeliriumEncounter(Encounter):
  def __init__(self, poe_bot, encounter_entity: Entity):
    super().__init__(poe_bot)
    self.encounter_entity = encounter_entity

  def doEncounter(self):
    poe_bot = self.poe_bot
    print(f"[DeliriumEncounter.doEncounter] {self.encounter_entity}")
    poe_bot.mover.goToEntitysPoint(self.encounter_entity)

    def custombreakfunc(*args, **kwargs):
      entity_exists = next((e for e in poe_bot.game_data.entities.all_entities if e.id == self.encounter_entity.id and e.is_opened is not True), None)
      if entity_exists is None:
        return True
      return False

    poe_bot.mover.goToEntitysPoint(self.encounter_entity, min_distance=-1, custom_break_function=custombreakfunc)
    return True


class LegionEncounter(Encounter):
  def __init__(self, poe_bot: PoeBot) -> None:
    super().__init__(poe_bot)

  def findMoreValuableMobInStasisToKill(self, include_normal=False) -> Entity:
    legion_mobs: List[Entity] = []
    generals: List[Entity] = []
    chests: List[Entity] = []
    sergeants: List[Entity] = []
    others: List[Entity] = []
    # iterate over legion mobs
    # sort them by
    for e in self.poe_bot.game_data.entities.attackable_entities:
      if "/LegionLeague/" not in e.path:
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
      mob_to_kill: Entity = sorted_mobs[0]

    return mob_to_kill


class HarbringerEncounter(Encounter):
  def __init__(self, poe_bot: PoeBot, harbringer_entity: Entity) -> None:
    super().__init__(poe_bot)
    self.encounter_entity = harbringer_entity

  def doEncounter(self):
    print(f"[HarbringerEncounter.do] nearby {self.encounter_entity} call at {time.time()}")
    harbringer_id = self.encounter_entity.id
    while True:
      current_harbringers = list(filter(lambda e: harbringer_id == e.id, self.poe_bot.game_data.entities.all_entities))
      if len(current_harbringers) != 0:
        current_harbringer = current_harbringers[0]
        harbringer_bosses = list(filter(lambda e: e.path == "Metadata/Monsters/Avatar/AvatarBossAtlas", self.poe_bot.game_data.entities.all_entities))
        if len(harbringer_bosses) != 0:
          print("[HarbringerEncounter.do] found harbringer bosses nearby")
          sorted_harbringer_bosses = sorted(
            harbringer_bosses,
            key=lambda e: dist((e.grid_position.x, e.grid_position.y), (current_harbringer.grid_position.x, current_harbringer.grid_position.y)),
          )
          nearest_harbringer_boss = sorted_harbringer_bosses[0]
          current_harbringer = nearest_harbringer_boss
        # self.poe_bot.combat_module.clearLocationAroundPoint({"X": current_harbringer.grid_position.x, "Y": current_harbringer.grid_position.y}, detection_radius=50, ignore_keys=['Metadata/Monsters/Avatar/Avatar'])
        self.poe_bot.combat_module.clearAreaAroundPoint(
          current_harbringer.grid_position.toList(), detection_radius=50, ignore_keys=["Metadata/Monsters/Avatar/Avatar"]
        )
        self.poe_bot.refreshInstanceData()
      else:
        print("[HarbringerEncounter.do] no harbringers visible")
        break
    print(f"[HarbringerEncounter.do] nearby {self.encounter_entity} return at {time.time()}")
