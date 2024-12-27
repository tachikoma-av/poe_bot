from __future__ import annotations
import typing


if typing.TYPE_CHECKING:
  from .gamehelper import PoeBot, Poe2Bot, Entity
  from .mover import Mover

from typing import List
import time
import random
from math import dist, ceil
import _thread

import numpy as np

from .constants import DANGER_ZONE_KEYS, SKILL_KEYS, SKILL_KEYS_WASD, FLASK_NAME_TO_BUFF, AURAS_SKILLS_TO_BUFFS, CONSTANTS
from .utils import extendLine, createLineIteratorWithValues, getAngle

NON_INSTANT_MOVEMENT_SKILLS = [
  "shield_charge",
  "whirling_blades"
]

INSTANT_MOVEMENT_SKILLS = [
  "frostblink",
  "flame_dash"
]



class CombatModule():
  build:Build
  def __init__(self, poe_bot: PoeBot, build:str = None) -> None:
    self.poe_bot = poe_bot
    if build:
      self.build = getBuild(build)(poe_bot)
    else:
      print(f'build is not assigned, using any functions may throw errors')
    self.entities_to_ignore_path_keys:List[str] = []
    self.aura_manager = AuraManager(poe_bot=poe_bot)
  def assignBuild(self, build:str):
    self.build = getBuild(build)(self.poe_bot)
  def killUsualEntity(self, entity:Entity, min_hp = 0, max_kill_time_sec = 90, is_strong = False, step_size = random.randint(30,35)):
    poe_bot = self.poe_bot
    mover = poe_bot.mover
    build = self.build
    print(f'#killUsualEntity {entity}')
    first_attack_time = None
    # if "/LeagueBestiary/" in entity['Path']:
    #   print(f'/LeagueBestiary/ in entity path, forcing min_hp = 1')
    #   min_hp = 1
    if entity.life.health.current == min_hp:
      print('willing to kill dead entity')
      return True
    def killEntityFunctionForMover(mover:Mover):
      nonlocal first_attack_time
      print(f'first_attack_time {first_attack_time}')
      _t = time.time()
      res = build.killUsual(entity, is_strong, max_kill_time_sec)

      if res is False:
        res = build.usualRoutine(mover)

      elif res is True and first_attack_time is None:
        first_attack_time = _t
      return res
    
    def entityIsDead(mover:Mover):
      _t = time.time()

      entity_to_kill = list(filter(lambda e: e.id == entity.id,poe_bot.game_data.entities.attackable_entities))
      if len(entity_to_kill) != 0:
        entity_to_kill = entity_to_kill[0]
        print(f'check first_attack_time {first_attack_time}')
        if first_attack_time is not None:
          print(f'first_attack_time + max_kill_time_sec < _t {first_attack_time} + {max_kill_time_sec} < {_t}')
          if first_attack_time + max_kill_time_sec < _t:
            print(f'killUsualEntity max_kill_time_sec {max_kill_time_sec} passed, breaking')
            return True
      
        if min_hp != 0:
          if entity_to_kill.life.health.current <= min_hp:
            print(f"entity_to_kill.life.health.current <= min_hp <= {min_hp}")
            return True
        return False
      else:
        print('entities_to_kill not found, looks like dead')
        return True
    
    res = build.killUsual(entity, is_strong, max_kill_time_sec)
    if res is True:
      return True
    # get to entity first
    print(f'getting closer to entity')
    mover.goToEntity(
      entity_to_go=entity, 
      min_distance=70, 
      custom_continue_function=build.usualRoutine, 
      custom_break_function=entityIsDead,
      step_size=step_size
    )
    
    print(f'killing it')
    # kill it
    mover.goToEntity(
      entity_to_go=entity, 
      min_distance=-1, 
      custom_continue_function=killEntityFunctionForMover, 
      custom_break_function=entityIsDead,
      step_size=step_size
    )

    is_dead = entityIsDead(mover=mover)
    return is_dead
  def killTillCorpseOrDisappeared(self, entity:Entity, clear_around_radius = 40, max_kill_time_sec = 300, step_size = random.randint(30,35)):
    poe_bot = self.poe_bot
    mover = self.poe_bot.mover
    build = self.build
    entity_to_kill = entity
    entity_to_kill_id = entity_to_kill.id
    if entity_to_kill.is_targetable is False or entity_to_kill.is_attackable is False:
      print(f'entity_to_kill is not attackable or not targetable, going to it and activating it')
      while True:
        res = mover.goToPoint(
          (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y),
          min_distance=20,
          custom_continue_function=build.usualRoutine,
          # custom_break_function=collectLootIfFound,
          release_mouse_on_end=False,
          step_size=step_size,
        )
        if res is None:
          break
      entity_to_kill = next( (e for e in poe_bot.game_data.entities.all_entities if e.id == entity_to_kill_id), None)
      if entity_to_kill is None:
        print(f'entity_to_kill is None corpse disappeared:')
        return True
      last_boss_pos_x, last_boss_pos_y = entity_to_kill.grid_position.x, entity_to_kill.grid_position.y
      while True:
        entity_to_kill = next( (e for e in poe_bot.game_data.entities.all_entities if e.id == entity_to_kill_id), None)
        if entity_to_kill is None:
          print(f'entity_to_kill is None corpse disappeared:')
          return True
        
        if entity_to_kill.life.health.current == 0:
          print(f'entity_to_kill is dead')
          return True
        if entity_to_kill.is_targetable is False or entity_to_kill.is_attackable is False:
          print(f'boss is not attackable or not targetable, going to it clearing around it')
          killed_someone = self.clearLocationAroundPoint({"X":entity_to_kill.grid_position.x, "Y":entity_to_kill.grid_position.y}, detection_radius=clear_around_radius)
          if killed_someone is False:
            point = poe_bot.game_data.terrain.pointToRunAround(
              point_to_run_around_x=last_boss_pos_x,
              point_to_run_around_y=last_boss_pos_y,
              distance_to_point=15,
            )
            mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
            poe_bot.refreshInstanceData()
        else:
          print(f'boss is attackable and targetable, going to kill it')
          self.killUsualEntity(entity_to_kill, max_kill_time_sec=30)
          last_boss_pos_x, last_boss_pos_y = entity_to_kill.grid_position.x, entity_to_kill.grid_position.y
    else:
      print(f'entity_to_kill is attackable and targetable, going to kill it')
      if entity_to_kill.distance_to_player > 40:
        while True:
          res = mover.goToPoint(
            (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y),
            min_distance=35,
            custom_continue_function=build.usualRoutine,
            # custom_break_function=collectLootIfFound,
            release_mouse_on_end=False,
            step_size=step_size,
            # possible_transition = self.current_map.possible_transition_on_a_way_to_boss
          )
          if res is None:
            break
      self.killUsualEntity(entity_to_kill)
  def clearLocationAroundPoint(self, point_to_run_around, detection_radius = 20, till_no_enemies_around = False, ignore_keys = []):
    '''
    point_to_run_around
    {"X":1, "Y":1}
    '''
    poe_bot = self.poe_bot
    mover = poe_bot.mover
    build = self.build
    print(f'#clearLocationAroundPoint around point {point_to_run_around} ignore_keys: {ignore_keys}')
    print(f'going to {point_to_run_around}')
    point_to_go = [point_to_run_around["X"], point_to_run_around["Y"]]
    result = mover.goToPoint(
      point=point_to_go,
      min_distance=40,
      release_mouse_on_end=False,
      custom_continue_function=build.usualRoutine,
      step_size=random.randint(25,33)
    )
    poe_bot.last_action_time = 0
    def enemiesAroundPoint()-> List[Entity]:
      '''
      returns entities around point
      '''
      lower_x = point_to_run_around['X'] - detection_radius
      upper_x = point_to_run_around['X'] + detection_radius
      lower_y = point_to_run_around['Y'] - detection_radius
      upper_y = point_to_run_around['Y'] + detection_radius
      # enemies_around = list(filter(lambda entity:entity['IsTargetable'] is True and  entity['IsHostile'] is True and entity['GridPosition']['X'] > lower_x and entity['GridPosition']['X'] < upper_x and entity['GridPosition']['Y'] > lower_y and entity['GridPosition']['Y'] < upper_y ,  poe_bot.sorted_entities['alive_enemies']))
      enemies_around = list(filter(lambda e:e.grid_position.x > lower_x and e.grid_position.x < upper_x and e.grid_position.y > lower_y and e.grid_position.y < upper_y ,  poe_bot.game_data.entities.attackable_entities))
      enemies_around = list(filter(lambda e:e.isOnPassableZone(),  enemies_around))
      # enemies_around = list(filter(lambda e: e.grid_position.x > lower_x and e.grid_position.x < upper_x and e.grid_position.y > lower_y and e.grid_position.y < upper_y ,  poe_bot.game_data.entities.attackable_entities))
      
      return enemies_around
      
    entities_to_kill = enemiesAroundPoint()
    if len(entities_to_kill) == 0:
      return False
    print(f'entities_to_kill around point {entities_to_kill} ')
    # in theory it may spawn essences with the same metadata but white, not rare
    killed_someone = False
    for entity in entities_to_kill:
      if any(list(map(lambda _k: _k in entity.path, ignore_keys))):
        print(f'skipping {entity.raw} cos its in ignore keys')
        continue
      killed_someone = True
      self.killUsualEntity(entity, min_hp=1, max_kill_time_sec=3)
    return killed_someone
  def clearAreaAroundPoint(self, point, detection_radius = 20, till_no_enemies_around = False, ignore_keys = []):
    point_dict = {"X": point[0], "Y": point[1]}
    return self.clearLocationAroundPoint(point_to_run_around = point_dict, detection_radius = detection_radius, till_no_enemies_around = till_no_enemies_around, ignore_keys = ignore_keys)

class AutoFlasks:
  def __init__(self, poe_bot:PoeBot, hp_thresh = 0.5, mana_thresh = 0.5, pathfinder = False, life_flask_recovers_es = False) -> None:
    self.poe_bot = poe_bot
    self.hp_thresh = hp_thresh
    self.mana_thresh = mana_thresh
    self.utility_flasks_delay = 1
    self.life_flasks_delay = 1
    self.mana_flasks_delay = 1
    self.flask_use_time = [0,0,0,0,0]
    self.can_use_flask_after_by_type = {
      "utility": 0,
      "mana": 0,
      "life": 0,
    }
    self.pathfinder = pathfinder
    self.life_flask_recovers_es = life_flask_recovers_es
    self.utility_flasks_use_order_reversed = random.choice([True, False])

  def useFlask(self, flask_index, flask_type = 'utility'):
    time_now = time.time()
    self.can_use_flask_after_by_type[flask_type] = time_now + random.randint(100,200)/1000
    self.poe_bot.bot_controls.keyboard.pressAndRelease(f'DIK_{flask_index+1}', delay=random.randint(15,35)/100, wait_till_executed=False)
    self.flask_use_time[flask_index] = time_now
  def useFlasks(self):
    if self.useLifeFlask() is True: return True
    if self.useManaFlask() is True: return True
    if self.useUtilityFlasks() is True: return True
    return False
  def useUtilityFlasks(self):
    poe_bot = self.poe_bot
    time_now = time.time()
    # to prevent it from insta flask usage
    if time_now < self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.UTILITY]:
      return False
    
    sorted_flasks = sorted(poe_bot.game_data.player.utility_flasks, key = lambda f: f.index, reverse=self.utility_flasks_use_order_reversed)

    # for flask in poe_bot.game_data.player.utility_flasks:
    for flask in sorted_flasks:
      flask_related_buff = FLASK_NAME_TO_BUFF.get(flask.name, None)
      if flask_related_buff is None:
        continue
      if flask_related_buff == "flask_effect_life" or flask_related_buff == "flask_effect_mana":
        continue
      try:
        if time_now - self.flask_use_time[flask.index] < self.utility_flasks_delay or time_now - self.flask_use_time[flask.index] < 0.5:
          continue
      except Exception:
        try:
          poe_bot.logger.writeLine(f'flask bug {flask.index} {self.flask_use_time}')
        except Exception:
          poe_bot.logger.writeLine(f'flask bug couldnt catch')
        continue
      # check if flask buff is presented
      if flask_related_buff in poe_bot.game_data.player.buffs:
        continue
      # if avaliable on panel
      if flask.can_use is False:
        continue



      # else tap on flask
      print(f'[AutoFlasks] using utility flask {flask.name} {flask.index} at {time.time()}')
      self.useFlask(flask.index)
      # if tapped, return, so it wont look like a flask macro
      return True
    
    return False
  def useLifeFlask(self):
    poe_bot = self.poe_bot
    need_to_use_flask = False
    if self.life_flask_recovers_es == True:
      health_component = poe_bot.game_data.player.life.energy_shield
    else:
      health_component = poe_bot.game_data.player.life.health
    # life flask
    if self.pathfinder is True:
      # print(f'lifeflask pf')
      if "flask_effect_life_not_removed_when_full" not in poe_bot.game_data.player.buffs:
        print(f'[AutoFlasks] using lifeflask pf cos not in buffs')
        need_to_use_flask = True
      elif self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.LIFE] < time.time():
        print(f'[AutoFlasks] using life flask pf upfront')
        need_to_use_flask = True
      if need_to_use_flask == True:
        avaliable_life_flask = next( (f for f in poe_bot.game_data.player.life_flasks if f.can_use != False), None)
        if avaliable_life_flask != None: 
          if avaliable_life_flask.index > 5 or avaliable_life_flask.index < 0: return False
          print(f'[AutoFlasks] using lifeflask pf {avaliable_life_flask.name} {avaliable_life_flask.index}')
          self.useFlask(avaliable_life_flask.index, flask_type=CONSTANTS.FLASKS.FLASK_TYPES.LIFE)
          self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.LIFE] = time.time() + random.randint(270,330)/100
          return True
        else:
          print(f'[AutoFlasks] dont have any avaliable life flask for pf')
          return False
    else:
      if health_component.getPercentage() < self.hp_thresh:
        # if we already have life flask
        if "flask_effect_life" not in poe_bot.game_data.player.buffs and "flask_effect_life_not_removed_when_full" not in poe_bot.game_data.player.buffs:
          if time.time() < self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.LIFE]:
            print(f'[AutoFlasks] reached hp thresh but wont use life flask cos cd')
            return False
          for flask in poe_bot.game_data.player.life_flasks:
            if flask.can_use is True:
              if flask.index > 5 or flask.index < 0: continue
              print(f'[AutoFlasks] using life flask {flask.name} {flask.index} {type(flask.index)}')
              self.useFlask(flask.index, flask_type=CONSTANTS.FLASKS.FLASK_TYPES.LIFE)
              self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.LIFE] = time.time() + (random.randint(40,60)/100)
              return True
    return False
  def useManaFlask(self):
    poe_bot = self.poe_bot
    if len(poe_bot.game_data.player.mana_flasks) == 0:
      return False
    # mana flask
    if poe_bot.game_data.player.life.mana.current / (poe_bot.game_data.player.life.mana.total - poe_bot.game_data.player.life.mana.reserved) < self.mana_thresh:
      # if we already have mana flask
      if "flask_effect_mana" not in poe_bot.game_data.player.buffs and "flask_effect_mana_not_removed_when_full" not in poe_bot.game_data.player.buffs:
        if time.time() < self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.LIFE]:
          print(f'[AutoFlasks] reached mana thresh but wont use life flask cos cd')
          return False
        for flask in poe_bot.game_data.player.mana_flasks:
          if flask.index > 5 or flask.index < 0: continue
          print(f'[AutoFlasks] using mana flask {flask.name} {flask.index}')
          self.useFlask(flask.index, flask_type=CONSTANTS.FLASKS.FLASK_TYPES.MANA)
          self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.MANA] = time.time() + (random.randint(40,60)/100)
          return True

    return False
class AuraManager:
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot
    self.aura_skills = []
    self.blessing_skill:BlessingSkill = None
  def checkAuras(self):
    pass
  def activateAurasIfNeeded(self):
    """
    bool if activated
    """
    if not self.aura_skills:
      aura_keys = AURAS_SKILLS_TO_BUFFS.keys()
      self.aura_skills = []
      for skill_index in range(len(self.poe_bot.game_data.skills.internal_names)):
        skill_name = self.poe_bot.game_data.skills.internal_names[skill_index]
        if skill_name in aura_keys:
          is_blessing = next( (sd for sd in self.poe_bot.game_data.skills.descriptions[skill_index] if "SkillIsBlessingSkill" in sd.keys() or "SupportGuardiansBlessingAuraOnlyEnabledWhileSupportMinionIsSummoned" in sd.keys() ), None)
          if is_blessing:
            self.blessing_skill = BlessingSkill(poe_bot=self.poe_bot, skill_index=skill_index, skill_name=skill_name, display_name=skill_name)
            print(f'{skill_name} is blessing')
            continue
          self.aura_skills.append(skill_name)
      # self.aura_skills = list(filter(lambda skill_name: skill_name in aura_keys, self.poe_bot.game_data.skills.internal_names))
      self.aura_skills = set(self.aura_skills)
    auras_to_activate = []
    for skill in self.aura_skills:
      skill_effect = AURAS_SKILLS_TO_BUFFS[skill]
      if skill_effect in self.poe_bot.game_data.player.buffs:
        print(f'{skill} already activated')
      else:
        print(f'need to activate {skill}')
        auras_to_activate.append(skill)
    print(f'total need to activate {auras_to_activate}')
    if auras_to_activate:
      indexes_to_activate = list(map(lambda skill: self.poe_bot.game_data.skills.internal_names.index(skill), auras_to_activate))
      print(f'indexes to activate {indexes_to_activate}')
      keys_to_activate = list(map(lambda skill_index: SKILL_KEYS[skill_index], indexes_to_activate))
      print(f'keys to activate {keys_to_activate}')
      first_panel_skills = list(filter(lambda key: "DIK_" in key and "CTRL+" not in key, keys_to_activate))
      second_panel_skills = list(filter(lambda key: "CTRL+DIK_" in key, keys_to_activate))
      if second_panel_skills:
        self.poe_bot.bot_controls.keyboard_pressKey('DIK_LCONTROL')
        time.sleep(random.randint(5,15)/100)
        for key in second_panel_skills:
          key_str = key.split('CTRL+')[1]
          self.poe_bot.bot_controls.keyboard.tap(key_str)
          time.sleep(random.randint(10,20)/100)
        self.poe_bot.bot_controls.keyboard_releaseKey('DIK_LCONTROL')
        time.sleep(random.randint(20,40)/100)
      if first_panel_skills:
        for key in first_panel_skills:
          key_str = key
          self.poe_bot.bot_controls.keyboard.tap(key_str)
          time.sleep(random.randint(10,20)/100)
        time.sleep(random.randint(20,40)/100)
      return True
    return False
  def activateBlessingsIfNeeded(self):
    if self.blessing_skill:
      print(f'activating blessing {self.blessing_skill}')
      self.blessing_skill.use()
class CombatManager:
  def __init__(self, poe_bot:PoeBot=None) -> None:
    pass
# Skill bases
class Skill():
  def __init__(
      self, 
      poe_bot:PoeBot, 
      skill_index:int, 
      skill_name = '_deprecated', 
      display_name="unnamed_skill",
      min_mana_to_use = 0,
      sleep_multiplier = 0.5, # if skill will have cast time, it will sleep for some time
      mana_cost = 0,
      life_cost = 0,
    ) -> None:
    self.poe_bot = poe_bot
    self.skill_index = skill_index
    self.display_name = display_name
    self.min_mana_to_use = min_mana_to_use
    self.sleep_multiplier = sleep_multiplier
    self.overriden_cast_time = None
    self.mana_cost = mana_cost
    self.life_cost = life_cost
    self.holding = False

    bot_controls = self.poe_bot.bot_controls
    controller_keys = {
      'keyboard': {
        "press": bot_controls.keyboard_pressKey,
        "release": bot_controls.keyboard_releaseKey,
        "tap": bot_controls.keyboard.pressAndRelease,
      },
      "mouse": {
        "press": bot_controls.mouse.press,
        "release": bot_controls.mouse.release,
        "tap": bot_controls.mouse.click,
      }
    }

    if self.poe_bot.mover.move_type == "wasd":
      self.skill_key_raw = SKILL_KEYS_WASD[self.skill_index]
    else:
      self.skill_key_raw = SKILL_KEYS[self.skill_index]
    
    self.hold_ctrl = False
    key_type = 'mouse'
    if 'DIK' in self.skill_key_raw:
      key_type = "keyboard"
      if "CTRL" in self.skill_key_raw:
        self.hold_ctrl = True
    
    if self.hold_ctrl is True:
      self.skill_key = self.skill_key_raw.split("+")[1]
    else:
      self.skill_key = self.skill_key_raw


    self.key_type = key_type
    self.tap_func = controller_keys[key_type]["tap"]
    self.press_func = controller_keys[key_type]["press"]
    self.release_func = controller_keys[key_type]["release"]
  def update(self):
    '''
    updates the info about last successful usage
    '''
    pass
  def tap(self, wait_till_executed = True, delay = random.randint(5,20)/100, update = True):
    if self.hold_ctrl is True:
      self.poe_bot.bot_controls.keyboard_pressKey('DIK_LCONTROL')
      wait_till_executed = True # to prevent it from missclicking
    self.tap_func(button = self.skill_key, wait_till_executed = wait_till_executed, delay = delay)
    if self.hold_ctrl is True:
      self.poe_bot.bot_controls.keyboard_releaseKey('DIK_LCONTROL')
    if update != False: self.update()
  def press(self, wait_till_executed = True, update = True):
    '''
    for holding the button, smth like LA spam on some mob
    '''
    if self.hold_ctrl is True:
      self.poe_bot.bot_controls.keyboard_pressKey('DIK_LCONTROL')
    self.press_func(button = self.skill_key)
    self.holding = True
    if update != False: self.update()
  def release(self, wait_till_executed = True):
    if self.hold_ctrl is True:
      self.poe_bot.bot_controls.keyboard_releaseKey('DIK_LCONTROL')
    self.release_func(button = self.skill_key)
    self.holding = False
  def checkIfCanUse(self):
    if self.min_mana_to_use != 0 and self.poe_bot.game_data.player.life.mana.current < self.min_mana_to_use:
      print(f'[Skill] cant use skill {self.display_name} cos self.poe_bot.game_data.player.life.mana.current < self.min_mana_to_use')
      return False
    if self.poe_bot.game_data.skills.can_use_skills_indexes_raw[self.skill_index] == 0:
      print(f'[Skill] cant use skill {self.display_name} cos 0 in can_use_skills_indexes_raw')
      return False
    return True
  def use(self, grid_pos_x = 0, grid_pos_y = 0, updated_entity:Entity = None, wait_for_execution = True, force = False):
    '''
    -wait_for_execution: 1
    -force: if True, itll ignore check skill usage on panel

    '''
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    print(f'[Skill {self.display_name}] using  at {time.time()}')
    if force != True and self.checkIfCanUse() != True: return False
    if updated_entity is not None or grid_pos_x != 0 or grid_pos_y != 0: # if we need to move a mouse
      if updated_entity != None: # if its an entity
        screen_pos_x, screen_pos_y = updated_entity.location_on_screen.x, updated_entity.location_on_screen.y
      else:
        screen_pos_x, screen_pos_y = poe_bot.getPositionOfThePointOnTheScreen(y=grid_pos_y,x=grid_pos_x)
      screen_pos_x, screen_pos_y = poe_bot.convertPosXY(screen_pos_x, screen_pos_y)
      bot_controls.mouse.setPosSmooth(screen_pos_x, screen_pos_y,wait_till_executed=False)
    start_time = time.time()
    if wait_for_execution is True:
      if self.overriden_cast_time:
        cast_time = self.overriden_cast_time
      else:
        cast_time = self.getCastTime()
      time_to_sleep = start_time - time.time() + cast_time
      if cast_time > 0:
        self.press(wait_till_executed = wait_for_execution, update=False)
        time.sleep(time_to_sleep*self.sleep_multiplier*(random.randint(9,11)/10))
        self.release(wait_till_executed = wait_for_execution)
      else:
        self.tap( wait_till_executed = wait_for_execution, update=False)
    else:
      self.tap( wait_till_executed = wait_for_execution, update=False)
    self.update()
    print(f'[Skill {self.display_name}] successfully used  at {time.time()}')
    return True
  def moveThenUse(self, grid_pos_x = 0, grid_pos_y = 0, updated_entity:Entity = None, wait_for_execution = True, force = False, use_first = False):
      
    
    use_func = lambda: self.use(grid_pos_x, grid_pos_y, updated_entity, False, force)
    move_func = lambda: self.poe_bot.mover.move()


    '''
    - #TODO check if it's possible to execute use func, like skill is executable and whatever
    - #TODO adjust the time, if wait_for_execution == True so itll:
      either cast skill, move, wait till skill cast time
      or move, release mouse(if mover.move_type == mouse), cast, wait till skill cast time 
    '''

    queue = []
    queue.append(use_func)
    if use_first == True:
      queue.insert(-1, move_func)
    else:
      queue.insert(0, move_func)
    return True
  def getCastTime(self):
    return self.poe_bot.game_data.skills.cast_time[self.skill_index]
  def convertToPos(self,pos_x,pos_y,entity:Entity = None):
    
    if entity is not None:
      x, y = entity.grid_position.x, entity.grid_position.y
    else:
      x, y = pos_x, pos_y
    return x, y
class AreaSkill(Skill):
  def __init__(self, poe_bot: PoeBot, skill_index: int, skill_name='tipo chtobi potom uzat skill po ego internal name', display_name="AreaSkill", area = 15, duration = 4) -> None:
    self.last_use_location = [0, 0] # x, y
    self.last_use_time = 0
    self.area = area
    self.duration = duration
    super().__init__(poe_bot, skill_index, skill_name, display_name)

  def update(self):
    self.last_use_location = [self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y]
    self.last_use_time = time.time()
    
  def use(self, pos_x=0, pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False):
    dot_duration = self.duration
    if dist([self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y], [self.last_use_location[0], self.last_use_location[1]]) > self.area:
      self.last_use_time = 0
    if time.time() - self.last_use_time < dot_duration:
      return False
    res = super().use(pos_x, pos_y, updated_entity, wait_for_execution, force=force)  
    if res is True:
      x,y = self.convertToPos(pos_x, pos_y, updated_entity)
      self.last_use_location = [x,y]
    return res
class SkillWithDelay(Skill):
  def __init__(self, poe_bot: PoeBot, skill_index: int, skill_name='', display_name="SkillWithDelay", min_delay = random.randint(30,40)/10, delay_random = 0.1, min_mana_to_use=0, can_use_earlier = True) -> None:
    self.min_delay = min_delay
    self.delay_random = delay_random
    self.can_use_earlier = can_use_earlier
    
    self.last_use_time = 0
    self.can_be_used_after = 0

    self.internal_cooldown = random.randint(100,125)/100
    super().__init__(poe_bot, skill_index, skill_name, display_name, min_mana_to_use)
  def update(self):
    self.last_use_time = time.time()
    if self.can_use_earlier != False:
      _rv = [1,0,-1]
    else:
      _rv = [1,0]
    self.can_be_used_after = self.last_use_time + self.min_delay + random.choice(_rv) * self.delay_random * self.min_delay
    print(f'[SkillWithDelay {self.display_name}]  can be used after {self.can_be_used_after} {self.last_use_time} {self.min_delay}')
  def canUse(self, force = False):
    if force != True and time.time() < self.can_be_used_after:
      return False
    if force == True and time.time() - self.last_use_time < self.internal_cooldown:
      print(f'[SkillWithDelay {self.display_name}] internal cooldown on force use')
      return False
    return True
  def use(self, pos_x=0, pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False):
    if self.canUse(force) != True:
      return False
    return super().use(pos_x, pos_y, updated_entity, wait_for_execution, False)
class MinionSkillWithDelay(SkillWithDelay):
  
  def __init__(self, poe_bot: PoeBot, skill_index: int, skill_name='', display_name="SkillWithDelay", min_delay=random.randint(30, 40) / 10, delay_random=0.1, min_mana_to_use=0, can_use_earlier=True, minion_path_key:str|None = None) -> None:
    super().__init__(poe_bot, skill_index, skill_name, display_name, min_delay, delay_random, min_mana_to_use, can_use_earlier)
    self.minion_path_key = minion_path_key
  def getMinionsCountInRadius(self, radius:int = 150) -> int:
    if self.minion_path_key == None:
      return 0
    else:
      return len(list(filter(lambda e: e.life.health.current != 0 and not e.is_hostile and e.distance_to_player < radius and self.minion_path_key in e.path , self.poe_bot.game_data.entities.all_entities)))
class MovementSkill(Skill):
  def __init__(self, poe_bot: PoeBot, skill_index: int, skill_name='', display_name="MovementSkill", min_delay = random.randint(30,40)/10, can_extend_path = True) -> None:
    self.min_delay = min_delay
    self.last_use_time = 0
    self.jump_multi = 2
    self.min_move_distance = 20
    self.can_extend_path = can_extend_path
    super().__init__(poe_bot, skill_index, skill_name, display_name)
  def update(self):
    self.last_use_time = time.time()
  def use(self, pos_x=0, pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False, extend_path = True):
    path_without_obstacles = False
    if time.time() - self.last_use_time < self.min_delay:
      return False
    if pos_x != 0 or updated_entity is not None:
      x, y = self.convertToPos(pos_x, pos_y, updated_entity)
      distance_to_next_step = dist( (self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y), (x, y))
      print(f'[Combat Movement Skill] distance_to_next_step {distance_to_next_step}')
      if distance_to_next_step < self.min_move_distance:
        return False
      path_without_obstacles = self.poe_bot.game_data.terrain.checkIfPointIsInLineOfSight(x, y)
      print(f'[Combat Movement Skill] path_without_obstacles {path_without_obstacles}')
      if path_without_obstacles != True:
        return False
      if self.can_extend_path != False and extend_path != False:
        pos_x, pos_y = extendLine( (self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y), (x, y), self.jump_multi)
      else:
        pos_x, pos_y = x, y
    if path_without_obstacles:
      return super().use(pos_x, pos_y, updated_entity, wait_for_execution, force)
    else:
      return False
class MovementSkill_new(SkillWithDelay):
  def __init__(self, poe_bot: PoeBot, skill_index: int, skill_name='', display_name="MovementSkill", min_delay=random.randint(30,40)/10, delay_random=0.1, min_mana_to_use=0, can_use_earlier=True, can_extend_path = True) -> None:
    self.jump_multi = 2
    self.min_move_distance = 20
    self.can_extend_path = can_extend_path
    super().__init__(poe_bot, skill_index, skill_name, display_name, min_delay, delay_random, min_mana_to_use, can_use_earlier)
  def use(self, pos_x=0, pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False, extend_path = True, use_as_movement_skill = True):
    if self.canUse(force) != True:
      return False
    
    if use_as_movement_skill != False:
      if pos_x != 0 or updated_entity is not None:
        x, y = self.convertToPos(pos_x, pos_y, updated_entity)
        distance_to_next_step = dist( (self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y), (x, y))
        print(f'[Combat Movement Skill] distance_to_next_step {distance_to_next_step}')
        if distance_to_next_step < self.min_move_distance:
          return False
        path_without_obstacles = self.poe_bot.game_data.terrain.checkIfPointIsInLineOfSight(x, y)
        print(f'[Combat Movement Skill] path_without_obstacles {path_without_obstacles}')
        if path_without_obstacles != True:
          return False
        if self.can_extend_path != False and extend_path != False:
          pos_x, pos_y = extendLine( (self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y), (x, y), self.jump_multi)
        else:
          pos_x, pos_y = x, y
      if path_without_obstacles:
        return super().use(pos_x, pos_y, updated_entity, wait_for_execution, force)
      else:
        return False
    else:
      return super().use(pos_x, pos_y, updated_entity, wait_for_execution, force)



class BlessingSkill(SkillWithDelay):
  def __init__(self, poe_bot: PoeBot, skill_index: int, skill_name='tipo chtobi potom uzat skill po ego internal name', display_name="SkillWithDelay", min_delay=4, delay_random=0.1, min_mana_to_use=0) -> None:
    super().__init__(poe_bot, skill_index, skill_name, display_name, min_delay, delay_random, min_mana_to_use)
    self.buff_name = AURAS_SKILLS_TO_BUFFS[display_name]
  def use(self, pos_x=0, pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False):
    if self.buff_name not in self.poe_bot.game_data.player.buffs:
      print(f'[Blessing skill] {self.buff_name} is not in buff list, forcing to cast it')
      force = True
    return super().use(pos_x, pos_y, updated_entity, wait_for_execution, force)
# Specific Skills
class DetonateDead(Skill):
  def __init__(self, poe_bot: PoeBot, skill_index: int, skill_name='tipo chtobi potom uzat skill po ego internal name', display_name="DetonateDead", min_mana_to_use=0, desecrate:Skill = None) -> None:
    self.desecrate = desecrate
    self.last_use_time = 0

    self.delay_before_desecrate = 0
    self.delay_after_desecrate = 0
    self.delay_before_dd = 0
    self.delay_after_dd = 0

    super().__init__(poe_bot, skill_index, skill_name, display_name, min_mana_to_use)
  def use(self, grid_pos_x=0, grid_pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False):
    if grid_pos_x != 0 or (updated_entity and updated_entity.life.health.current != 0):
      x,y = self.convertToPos(grid_pos_x, grid_pos_y, updated_entity)
      explosion_radius = 9
      corpses = self.poe_bot.game_data.entities.getCorpsesArountPoint(x,y, radius=explosion_radius)
      if not corpses:
        if self.desecrate:
          print(f'gonna cast desecrate cos there are no corpses around entity or pos')
          if self.desecrate.use(x,y) is False:
            return False
          else:
            print('changed end pos of dd cast')
            updated_entity = None
            grid_pos_x = 0
            grid_pos_y = 0
        else:
          return False
    call_time = time.time()
    grid_pos_x, grid_pos_y = self.convertToPos(grid_pos_x, grid_pos_y, updated_entity)
    updated_entity = None
    # if self.delay_before_dd != 0: time.sleep(self.delay_before_dd)
    res = super().use(grid_pos_x, grid_pos_y, updated_entity, wait_for_execution, force)
    if res is True:
      self.last_use_time = call_time
      # if self.delay_after_dd != 0: time.sleep(self.delay_after_dd)
      # time.sleep(0.15)
    return res
class CreepingFrost(Skill):
  def __init__(self, poe_bot: PoeBot, skill_index: int, skill_name='tipo chtobi potom uzat skill po ego internal name', display_name="CreepingFrost", area = 15) -> None:
    self.last_use_location = [0, 0] # x, y
    self.last_use_time = 0
    self.area = area
    super().__init__(poe_bot, skill_index, skill_name, display_name)

  def update(self):
    self.last_use_location = [self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y]
    self.last_use_time = time.time()

  def use(self, pos_x=0, pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False):
    dot_duration = 4
    if dist([self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y], [self.last_use_location[0], self.last_use_location[1]]) > self.area:
      self.last_use_time = 0
    
    if time.time() - self.last_use_time < dot_duration:
      return False 
    return super().use(pos_x, pos_y, updated_entity, wait_for_execution, force=True)
class ColdSnap(CreepingFrost):
  def __init__(self, poe_bot: PoeBot, skill_index: int, skill_name='tipo chtobi potom uzat skill po ego internal name', display_name="ColdSnap", area = 30) -> None:
    super().__init__(poe_bot, skill_index, skill_name, display_name, area)

  def use(self, pos_x=0, pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False):
    if "frenzy_charge" not in self.poe_bot.game_data.player.buffs and self.checkIfCanUse() is False:
      return False
    return super().use(pos_x, pos_y, updated_entity, wait_for_execution, force)
class Aura(Skill):
  def __init__(self, poe_bot: PoeBot, bind_key=None, use_function=None, use_delay=4, skill_type=1, name="unnamed_skill", mana_cost=0) -> None:
    super().__init__(poe_bot, bind_key, use_function, use_delay, skill_type, name, mana_cost)
class MinionSkill(Skill):
  def __init__(self, poe_bot: PoeBot, bind_key=None, use_function=None, use_delay=4, skill_type=1, name="unnamed_skill", mana_cost=0) -> None:
    super().__init__(poe_bot, bind_key, use_function, use_delay, skill_type, name, mana_cost)
class AttackingSkill(Skill):
  def __init__(self, poe_bot: PoeBot, bind_key=None, use_function=None, use_delay=4, skill_type=1, name="unnamed_skill", mana_cost=0) -> None:
    super().__init__(poe_bot, bind_key, use_function, use_delay, skill_type, name, mana_cost)
class PlagueBearer(Skill):
  last_use_time = 0
  def __init__(self, poe_bot: PoeBot, skill_index: int, skill_name='tipo chtobi potom uzat skill po ego internal name', display_name="plague_bearer", min_mana_to_use=0, sleep_multiplier=0.5) -> None:
    super().__init__(poe_bot, skill_index, skill_name, display_name, min_mana_to_use, sleep_multiplier)

  def checkIfBuffed(self):
    if self.last_use_time + 1 < time.time() and "corrosive_shroud_buff" not in self.poe_bot.game_data.player.buffs:
      self.tap(wait_till_executed=False)
      self.last_use_time = time.time()

  def turnOn(self):
    self.checkIfBuffed()
    if self.last_use_time + 1 < time.time() and 'corrosive_shroud_at_max_damage' in self.poe_bot.game_data.player.buffs:
      self.tap(wait_till_executed=False)
      self.last_use_time = time.time()
      return True
    return False
  def turnOff(self):
    self.checkIfBuffed()
    if self.last_use_time + 1 < time.time() and 'corrosive_shroud_aura' in self.poe_bot.game_data.player.buffs:
      self.tap(wait_till_executed=False)
      self.last_use_time = time.time()
      return

class FrostblinkSkill(MovementSkill_new):
  can_extend_path = False
  def __init__(self, poe_bot: PoeBot, skill_index: int, skill_name='', display_name="MovementSkill", min_delay=random.randint(30, 40) / 10, delay_random=0.1, min_mana_to_use=0, can_use_earlier=True, can_extend_path=True) -> None:
    super().__init__(poe_bot, skill_index, skill_name, display_name, min_delay, delay_random, min_mana_to_use, can_use_earlier, can_extend_path=False)
class WhirlingBladesSkill(MovementSkill_new):
  can_extend_path = False
class ShieldChargeSkill(MovementSkill_new):
  can_extend_path = True
class FlameDashSkill(MovementSkill_new):
  can_extend_path = True
class BlinkArrowSkill(MovementSkill_new):
  can_extend_path = True

# DescribedSkills
class BloodRage(SkillWithDelay):
  def __init__(self, poe_bot: PoeBot, skill_index: int) -> None:
    self.buff_name = 'blood_rage'
    self.min_percentage_of_life_to_use = 0.7
    # if skill_index is None:
    #   poe_bot.game_data.skills

    skill_name=''
    display_name="blood_rage"
    min_delay=random.randint(30, 50) / 10
    delay_random=0.1
    min_mana_to_use=0
    can_use_earlier=True
    super().__init__(poe_bot, skill_index, skill_name, display_name, min_delay, delay_random, min_mana_to_use, can_use_earlier)
  def use(self, pos_x=0, pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False):
    if 'blood_rage' in self.poe_bot.game_data.player.buffs:
      return False
    if self.poe_bot.game_data.player.life.health.getPercentage() < self.min_percentage_of_life_to_use:
      return False
    return super().use(pos_x, pos_y, updated_entity, wait_for_execution, force)

MOVEMENT_SKILLS_DICT = {
  "frostblink": FrostblinkSkill,
  "flame_dash": FlameDashSkill,
  "shield_charge": FrostblinkSkill,
  "whirling_blades": FrostblinkSkill,
  "blink_arrow": FrostblinkSkill,
  "blink_arrow_alt_y": FrostblinkSkill,
  "blink_arrow_alt_x": FrostblinkSkill,
}

def getMovementSkill(skill_str:str):
  skill = MOVEMENT_SKILLS_DICT.get(skill_str, None)
  return skill 
# Builds
class Build:
  poe_bot:PoeBot
  chaos_immune = False
  buff_skills:List[Skill] = []
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot
    self.mover = self.poe_bot.mover
    self.auto_flasks = AutoFlasks(poe_bot=poe_bot)
    # actions done during usual walking
    if getattr(self, "usualRoutine", None) is None: raise NotImplementedError
    # actions how does it behave during killing
    if getattr(self, "killUsual", None) is None: raise NotImplementedError
    # actions how does it behave during killing strong entity, suchs as simulacrum boss or whatever
    if getattr(self, "killStrong", None) is None: self.killStrong = self.killUsual
    # summon zombies, whatever

  def useBuffs(self):
    for buff in self.buff_skills:
      if buff.use() == True:
        return True
    return False


  def staticDefence(self):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()
    mover = self.mover
    detection_range = 30
    danger_zones = list(filter(lambda e: e.distance_to_player < detection_range and any(list(map(lambda key: key in e.path, DANGER_ZONE_KEYS))), poe_bot.game_data.entities.all_entities ))
    if len(danger_zones) != 0:
      print(f'danger zone in range {detection_range}')
      danger_zone_str = list(map(lambda e: e.path, danger_zones))
      print(danger_zone_str)
      if self.chaos_immune is False and any(list(map(lambda s: "/LeagueArchnemesis/ToxicVolatile" in s, danger_zone_str))):
        print(f'dodging caustic orbs')
        # caustic orbs logic
        print("get behind nearest")
        min_move_distance = 35
        distance_to_jump = 15

        caustic_orbs = list(filter(lambda e: "/LeagueArchnemesis/ToxicVolatile" in e.path, danger_zones))
        sorted_caustic_orbs = sorted(caustic_orbs, key=lambda e: e.distance_to_player)
        nearest_caustic_orb = sorted_caustic_orbs[0]

        need_distance = nearest_caustic_orb.distance_to_player + distance_to_jump
        if need_distance < min_move_distance:
          need_distance = min_move_distance
        
        multiplier = need_distance / nearest_caustic_orb.distance_to_player
        grid_pos_x, grid_pos_y = extendLine( (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (nearest_caustic_orb.grid_position.x, nearest_caustic_orb.grid_position.y), multiplier)

        poe_bot.last_action_time = 0
        res = mover.goToPoint(
          point=(int(grid_pos_x), int(grid_pos_y)),
          min_distance=25,
          custom_continue_function=self.usualRoutine,
          # custom_break_function=collectLootIfFound,
          release_mouse_on_end=False,
          step_size=random.randint(25,33)
        )
        print("got behind closest")

        print("going behind center of all others")


        poe_bot.last_action_time = 0
        poe_bot.refreshInstanceData()
        poe_bot.last_action_time = 0

        caustic_orbs = list(filter(lambda e: "/LeagueArchnemesis/ToxicVolatile" in e.path, poe_bot.game_data.entities.all_entities))
        while len(caustic_orbs) != 0:
          print(f'there are still {len(caustic_orbs)} caustic orbs left, going behind them')
          if len(caustic_orbs) == 0:
            print('no caustic orbs left')
            return True

          print(f'playerpos {poe_bot.game_data.player.grid_pos.x} {poe_bot.game_data.player.grid_pos.y}')
          print(f'list(map(lambda e: e.grid_position.x, caustic_orbs)) {list(map(lambda e: e.grid_position.x, caustic_orbs))}  {list(map(lambda e: e.grid_position.y, caustic_orbs))}')
          center_x = sum(list(map(lambda e: e.grid_position.x, caustic_orbs)))/len(caustic_orbs)
          center_y = sum(list(map(lambda e: e.grid_position.y, caustic_orbs)))/len(caustic_orbs)
          caustic_orbs_center = [center_x, center_y]
          print(f'caustic_orbs_center {caustic_orbs_center}')
          caustic_orbs_center_distance_to_player = dist(caustic_orbs_center, (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) )
          need_distance = caustic_orbs_center_distance_to_player + distance_to_jump
          if need_distance < min_move_distance:
            need_distance = min_move_distance
          
          multiplier = need_distance / caustic_orbs_center_distance_to_player
          grid_pos_x, grid_pos_y = extendLine( (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (center_x, center_y), multiplier)

          res = mover.goToPoint(
            point=(int(grid_pos_x), int(grid_pos_y)),
            min_distance=25,
            custom_continue_function=self.usualRoutine,
            # custom_break_function=collectLootIfFound,
            release_mouse_on_end=False,
            step_size=random.randint(25,33)
          )


          poe_bot.last_action_time = 0
          poe_bot.refreshInstanceData()
          poe_bot.last_action_time = 0
          caustic_orbs = list(filter(lambda e: "/LeagueArchnemesis/ToxicVolatile" in e.path, poe_bot.game_data.entities.all_entities))

        # 
        pass
      elif self.chaos_immune is False and any(list(map(lambda s: "Metadata/Monsters/LeagueArchnemesis/LivingCrystal" in s, danger_zone_str))):
        print('dodging living crystals')
        living_crystals = list(filter(lambda e: "Metadata/Monsters/LeagueArchnemesis/LivingCrystal" in e.path and e.distance_to_player < 20, danger_zones))
        if len(living_crystals) != 0:
          center_x = int(sum(list(map(lambda e: e.grid_position.x, living_crystals)))/len(living_crystals))
          center_y = int(sum(list(map(lambda e: e.grid_position.y, living_crystals)))/len(living_crystals))
          possible_points_to_dodge = []
          jump_range = 35
          print(f'living crystal center x:{center_x} y:{center_y}')
          for ix in range(-1,2):
            for iy in range(-1,2):
              possible_points_to_dodge.append([center_x+ix*jump_range, center_y+iy*jump_range])

          random.shuffle(possible_points_to_dodge)
          point_to_dodge = None
          for point in possible_points_to_dodge:
            is_passable = poe_bot.helper_functions.checkIfEntityOnCurrenctlyPassableArea(point[0],point[1])
            if is_passable is True:
              point_to_dodge = point
              break
          if point_to_dodge is None:
            point_to_dodge = [int(poe_bot.game_data.player.grid_pos.x + random.randint(-1,1) * jump_range), poe_bot.game_data.player.grid_pos.y + random.randint(-1,1) * jump_range] 
          res = mover.goToPoint(
            point=(int(point_to_dodge[0]), int(point_to_dodge[1])),
            min_distance=25,
            custom_continue_function=self.usualRoutine,
            # custom_break_function=collectLootIfFound,
            release_mouse_on_end=False,
            step_size=random.randint(25,33)
          )
        else:
          print('they are too far away from us')
    pass
  def pointToRunAround(self, point_to_run_around_x, point_to_run_around_y, distance_to_point = 15):
    poe_bot = self.poe_bot
    our_pos = [poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y]
    # entity pos
    pos_x, pos_y = point_to_run_around_x, point_to_run_around_y

    points_around = [
      [pos_x+distance_to_point,pos_y],
      [int(pos_x+distance_to_point*0.7),int(pos_y-distance_to_point*0.7)],
      [pos_x,pos_y-distance_to_point],
      [int(pos_x-distance_to_point*0.7),int(pos_y-distance_to_point*0.7)],
      [pos_x-distance_to_point,pos_y],
      [int(pos_x-distance_to_point*0.7),int(pos_y+distance_to_point*0.7)],
      [pos_x,pos_y+distance_to_point],
      [int(pos_x+distance_to_point*0.7),int(pos_y+distance_to_point*0.7)],
      [pos_x+distance_to_point,pos_y],
    ]
    distances = list(map(lambda p: dist(our_pos, p),points_around))
    nearset_pos_index = distances.index(min(distances))
    # TODO check if next point is possible
    point = points_around[nearset_pos_index+1]
    return point
  def prepareToFight(self, entity:Entity):
    # actions to do before some strong fight, such as placing totems before the essence opened or whatever
    print("prepareToFight is not defined")
  # def canAttackEntity(self, entity_to_kill:Entity):
  #   if not entity_to_kill:
  #     print('cannot find desired entity to kill')
  #     return False
  #   print(f'entity_to_kill {entity_to_kill}')
  #   if entity_to_kill.life.health.current < 1:
  #     print('entity is dead')
  #     return False
  #   distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y) ) 
  #   print(f'distance_to_entity {distance_to_entity} in killUsual')
  #   if distance_to_entity > min_distance:
  #     print('getting closer in killUsual ')
  #     return False
  def swapWeaponsIfNeeded(self):
    poe_bot = self.poe_bot
    for i in range(99):
    # poe_bot.skills.update()
      portal_gem_in_skills = 'town_portal' in poe_bot.backend.getSkillBar()['i_n']
      print(f'portal_gem_in_skills {portal_gem_in_skills}')
      if portal_gem_in_skills is False:
        print('weapons swapped')
        break
      if i == 10:
        poe_bot.raiseLongSleepException('cannot swap weapon for 10 iterations')
      print('swapping weapons')

      poe_bot.bot_controls.keyboard.tap('DIK_X')
      time.sleep(random.randint(10,20)/10)
    return True
  def usualRoutine(self, mover:Mover = None):
    self.poe_bot.raiseLongSleepException('usualRoutine is not defined in build')

  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = 10, *args, **kwargs):
    pass
  def doPreparations(self):
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls

    for i in range(99):
      # poe_bot.skills.update()
      portal_gem_in_skills = 'town_portal' in poe_bot.backend.getSkillBar()['i_n']
      print(f'portal_gem_in_skills {portal_gem_in_skills}')
      if portal_gem_in_skills is False:
        print('weapons swapped')
        break
      if i == 10:
        poe_bot.raiseLongSleepException('cannot swap weapon for 10 iterations')
      print('swapping weapons')

      poe_bot.bot_controls.keyboard.tap('DIK_X')
      time.sleep(random.randint(10,20)/10)
    poe_bot.combat_module.aura_manager.activateAurasIfNeeded()
class ColdDotElementalist(Build):
  '''
  mapper version of cold dot elementalist
  '''
  poe_bot: PoeBot
  def __init__(self,poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot


    self.auto_flasks = AutoFlasks(poe_bot=poe_bot)
    
    self.shield_charge = None # "new_new_shield_charge"
    self.vortex = None # name: "frost_bolt_nova" animated_property_metadata "a":"Metadata/Effects/Spells/frost_bolt/sml_maelstrom.ao"
    self.creeping_frost = None # name: "arctic_breath" path "Metadata/Monsters/ArcticBreath/ArcticBreathSkull@74" animated_property_metadata "Metadata/Monsters/ArcticBreath/ArcticBreathSkull.ao" "rn":"Arctic Breath Skull"
    self.cold_snap = None #name "new_cold_snap" {"ls":[616,89],"p":"Metadata/Monsters/Daemon/DoNothingDaemon@83","r":"White","i":2041,"o":0,"h":1,"ia":1,"t":0,"b":1,"gp":[557,639],"l":[9224,9224,0,650298,650298,0,1,0],"life":{"Health":{"Total":9224,"Current":9224},"Mana":{"Total":650298,"Current":650298}},"a":"Metadata/Monsters/Daemon/Daemon.ao","rn":"Boring","et":"Daemon"}
    self.vaal_cold_snap = None #"new_vaal_cold_snap" buff "vaal_cold_snap_degen","bonechill","cold_snap_expanding_chilled_ground"
    self.hatred_blessing = None # "hatred" buff "player_aura_cold_damage"
    self.molten_shell = None #"molten_shell_barrier" buff "molten_shell_damage_absorption"
    self.vaal_molten_shell = None
    
    self.debuff_skill = None # name "elemental_weakness"

    self.doPreparations()
    skills_data = poe_bot.backend.getSkillBar()
    skills_on_panel = skills_data['i_n']

    for skill_index in range(len(skills_data['i_n'])):
      skill = skills_data['i_n'][skill_index]

      if skill == '':
        continue
      print(skill, skill_index)
      if skill == 'new_new_shield_charge':
        self.shield_charge = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/100, display_name="shield_charge")
      elif skill == 'hatred':
        self.hatred_blessing = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=9, display_name='hatred_blessing')
      elif skill == 'arctic_breath':
        self.creeping_frost = CreepingFrost(poe_bot=poe_bot, skill_index=skill_index)
      elif skill == 'new_vaal_cold_snap':
        self.vaal_cold_snap = Skill(poe_bot=poe_bot, skill_index=skill_index, display_name='Vaal_cold_snap')
      elif skill == 'new_cold_snap':
        self.cold_snap = ColdSnap(poe_bot=poe_bot, skill_index=skill_index)
      elif skill == 'molten_shell_barrier':
        self.molten_shell = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index)
      elif skill == 'elemental_weakness':
        self.debuff_skill = Skill(poe_bot=poe_bot, skill_index=skill_index, display_name='elemental_weakness')
      
    super().__init__(poe_bot)

  def useBuffs(self):
    poe_bot = self.poe_bot
    if self.hatred_blessing is not None:
        force_use = not 'player_aura_cold_damage' in poe_bot.game_data.player.buffs
        self.hatred_blessing.use(force=force_use)
      # if 'player_aura_cold_damage' not in poe_bot.game_data.player.buffs:
        # self.hatred_blessing.use()

  def useFlasks(self):
    self.auto_flasks.useFlasks()

  def usualRoutine(self, mover:Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()

    # if we are moving
    if mover is not None:
    
      # if no hatred buff, use self.hatred_buff
      self.useBuffs()

      nearby_enemies = list(filter(lambda entity: entity.distance_to_player < 30, poe_bot.game_data.entities.attackable_entities))
      print(f'nearby_enemies: {nearby_enemies}')

      enemies_around = len(nearby_enemies) != 0
      nearest_enemy_distance = 9
      vaal_cold_snap_in_buffs = False
      if enemies_around:
      # if enemies around use molten shell
        if self.molten_shell is not None:
          if nearest_enemy_distance < 15:
            self.molten_shell.use() 
        
        if self.vaal_cold_snap is not None:
          vaal_cold_snap_in_buffs = "vaal_cold_snap_degen" in poe_bot.game_data.player.buffs
          if vaal_cold_snap_in_buffs is False:
            self.vaal_cold_snap.use()
            vaal_cold_snap_in_buffs = True

        if vaal_cold_snap_in_buffs is False:
          if self.cold_snap is not None:
            if self.cold_snap.use(pos_x=mover.grid_pos_to_step_x, pos_y=mover.grid_pos_to_step_y) is True: return True

          if self.creeping_frost is not None:
            if self.creeping_frost.use(pos_x=mover.grid_pos_to_step_x, pos_y=mover.grid_pos_to_step_y) is True: return True

      # use movement skill
      if mover.distance_to_target > 50:
        # bit more logic, take some data from mover, smth like current_path length, distance to next_step in grid pos,
        # distance to next step on screen  
        distance_to_next_step = dist( (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y))
        print(f'distance_to_next_step {distance_to_next_step}')
        if distance_to_next_step > 20:
          path_values = createLineIteratorWithValues((poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y), poe_bot.game_data.terrain.passable)
          path_without_obstacles = np.all(path_values[:,2] > 0)
          print(f'path_without_obstacles {path_without_obstacles}')
          if path_without_obstacles:
            pos_x, pos_y = extendLine( (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y), 2)
            if self.shield_charge.use(pos_x=pos_x, pos_y=pos_y, wait_for_execution=False) is True:
              return True
    # if we are staying and waiting for smth
    else:
      self.staticDefence()

    return False
  
  def killUsual(self, entity:Entity):
    print(f'#build.killUsual {entity}')
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    mover = self.mover

    entity_to_kill_id = entity.id

    self.useFlasks()
    
    min_distance = 30 # distance which is ok to start attacking
    keep_distance = 15 # if our distance is smth like this, kite

    min_hold_duration = random.randint(200,300)/10

    entities_to_kill = list(filter(lambda e: e.id == entity_to_kill_id, poe_bot.game_data.entities.attackable_entities))
    if len(entities_to_kill) == 0:
      print('cannot find desired entity to kill')
      return True

    entity_to_kill = entities_to_kill[0]
    print(f'entity_to_kill {entity_to_kill}')


    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual')
    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False



    start_time = time.time()
    pos_x, pos_y = entity_to_kill.location_on_screen.x, entity_to_kill.location_on_screen.y
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y) 
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    reversed_kite = random.choice([True, False])
    if self.vaal_cold_snap: self.vaal_cold_snap.use(wait_for_execution=False)
    poe_bot.last_action_time = 0
    kite_distance = random.randint(8,13)
    res = True 
    while True:
      poe_bot.refreshInstanceData()
      self.useFlasks()
      self.useBuffs()
      entities_to_kill = list(filter(lambda e: e.id == entity_to_kill_id, poe_bot.game_data.entities.attackable_entities))
      if len(entities_to_kill) == 0:
        print('cannot find desired entity to kill')
        break
      entity_to_kill = entities_to_kill[0]
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break
      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        break
      
      entity_to_kill = entities_to_kill[0]
      print(f'entity_to_kill {entity_to_kill}')

      
      if self.cold_snap.use(updated_entity=entity_to_kill) is False:
        if self.creeping_frost.use(updated_entity=entity_to_kill) is False:
          point = self.poe_bot.game_data.terrain.pointToRunAround(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, kite_distance+random.randint(-1,1), check_if_passable=False, reversed=reversed_kite)
          mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
      if self.vaal_cold_snap: self.vaal_cold_snap.use(wait_for_execution=False)
      if self.molten_shell: self.molten_shell.use() 
      current_time = time.time()

      if current_time  > current_time + min_hold_duration:
        print('exceed time')
        break
    return res
class LightningArrowLightningWarp(Build):
  '''
  build uses bow skill to trigger lightningwarp
  '''
  poe_bot: PoeBot
  def __init__(self,poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot


    self.auto_flasks = AutoFlasks(poe_bot=poe_bot)
    
    self.blood_rage = None # "blood_rage"
    self.lightning_arrow_attack = None 
    self.lightning_arrow_movement = None # "lightning_arrow"
    self.barrage = None # "barrage"

    self.swapWeaponsIfNeeded()
    skills_data = poe_bot.backend.getSkillBar()
    skills_on_panel = skills_data['i_n']

    print(f'assigning movement skill')
    for skill_index in range(len(skills_data['i_n'])):
      skill = skills_data['i_n'][skill_index]
      if skill == '':
        continue
      print(skill, skill_index)
      if skill == 'blood_rage':
        self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/10, display_name="blood_rage")
      elif skill == 'lightning_arrow' or skill == "elemental_hit_alt_x":
        self.lightning_arrow_movement = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1,5)/100, display_name=f"movement_{skill}", min_mana_to_use=25)
    print(f'movement skill {self.lightning_arrow_movement.display_name}')
    print(f'assigning attack skill')
    for skill_index in range(len(skills_data['i_n'])):
      skill = skills_data['i_n'][skill_index]
      if skill == '':
        continue
      print(skill, skill_index)
      if skill == 'lightning_arrow' or skill == "elemental_hit_alt_x" or skill == "'barrage'":
        self.lightning_arrow_attack = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1,5)/100, display_name=f"attack_{skill}")
    print(f'attack skill {self.lightning_arrow_attack.display_name}')
      

    super().__init__(poe_bot)
  def useBuffs(self):
    poe_bot = self.poe_bot
    if self.blood_rage is not None:
      if 'blood_rage' not in poe_bot.game_data.player.buffs:
        self.blood_rage.use()

  def useFlasks(self):
    self.auto_flasks.useFlasks()

  def usualRoutine(self, mover:Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()

    # if we are moving
    if mover is not None:
      self.useBuffs()
      # as a movement skill
      if mover.distance_to_target > 50:
        # bit more logic, take some data from mover, smth like current_path length, distance to next_step in grid pos,
        # distance to next step on screen  
        distance_to_next_step = dist( (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y))
        print(f'distance_to_next_step {distance_to_next_step}')
        if distance_to_next_step > 20:
          path_values = createLineIteratorWithValues((poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y), poe_bot.game_data.terrain.passable)
          path_without_obstacles = np.all(path_values[:,2] > 0)
          print(f'path_without_obstacles {path_without_obstacles}')
          max_distance = mover.distance_to_target
          current_distance = dist( (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y))
          multiply_by = max_distance / current_distance
          if multiply_by > 2:
            multiply_by = 2
          pos_x, pos_y = extendLine( (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y), multiply_by)
          if self.lightning_arrow_movement.use(pos_x=pos_x, pos_y=pos_y, force=True) is True:
            return True

      # distance_difference = dist([poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y], [self.lightning_arrow_attack.last_use_location['X'], self.lightning_arrow_attack.last_use_location['Y']])
      # if distance_difference > 55:
      #   self.lightning_arrow_attack.last_use_time = 0
      
      # # just to attack random mobs
      # if self.lightning_arrow_attack.use(pos_x=mover.grid_pos_to_step_x, pos_y=mover.grid_pos_to_step_y) is True:
      #   return True
    # if we are staying and waiting for smth
    else:
      self.staticDefence()

    return False
  
  def prepareToFight(self, entity: Entity):
    print(f'vg.preparetofight call {time.time()}')
    poe_bot = self.poe_bot
    bot_controls = self.poe_bot.bot_controls
    pos_x, pos_y = entity.location_on_screen.x, entity.location_on_screen.y
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y) 
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    self.lightning_arrow_movement.press()
    start_hold_time = time.time()
    min_hold_duration = random.randint(40,60)/100
    while True:
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      pos_x, pos_y = poe_bot.getPositionOfThePointOnTheScreen(y=entity.grid_position.y, x= entity.grid_position.x)
      pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y) 
      bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      if time.time() > start_hold_time + min_hold_duration:
        break
    self.lightning_arrow_movement.release()

  
  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = 10, *args, **kwargs):
    print(f'#build.killUsual {entity}')
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls


    entity_to_kill_id = entity.id
    self.useFlasks()
    
    min_distance = 30
    max_hold_duration = random.randint(200,300)/100
    max_hold_duration = 300


    entities_to_kill = list(filter(lambda e: e.id == entity_to_kill_id, poe_bot.game_data.entities.attackable_entities))
    if len(entities_to_kill) == 0:
      print('cannot find desired entity to kill')
      return True

    entity_to_kill = entities_to_kill[0]
    print(f'entity_to_kill {entity_to_kill}')

    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual') 
    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    
    start_time = time.time()

    
    pos_x, pos_y = entity_to_kill.location_on_screen.x, entity_to_kill.location_on_screen.y

    # distance_to_jump = 15
    # need_distance = distance_to_entity + distance_to_jump
    # multiplier = need_distance / distance_to_entity
    # pos_x, pos_y = extendLine( (poe_bot.game_window.center_point[0], poe_bot.game_window.center_point[1]), (entity_to_kill.location_on_screen.x, entity_to_kill.location_on_screen.y), multiplier)


    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y) 
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    self.lightning_arrow_attack.press()
    poe_bot.last_action_time = 0
    last_distance_to_entity = distance_to_entity
    res = True
    reset_timer = False
    i = 0
    while True:
      i += 1
      poe_bot.refreshInstanceData(reset_timer=reset_timer)
      # poe_bot.last_action_time = 0
      self.useFlasks()
      entities_to_kill = list(filter(lambda e: e.id == entity_to_kill_id, poe_bot.game_data.entities.attackable_entities))
      if len(entities_to_kill) == 0:
        print('cannot find desired entity to kill')
        break
      entity_to_kill = entities_to_kill[0]
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break
      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        break
      
      if last_distance_to_entity + 5 < distance_to_entity:
        print(f'too far from entity, fast reset')
        reset_timer = True
      else:
        reset_timer = False
      last_distance_to_entity = distance_to_entity
      # if entity is dead, or far away, break, return True, since we need to update the new movement
      # need_distance = distance_to_entity + distance_to_jump
      # multiplier = need_distance / distance_to_entity
      # pos_x, pos_y = extendLine( (poe_bot.game_window.center_point[0], poe_bot.game_window.center_point[1]), (entity_to_kill.location_on_screen.x, entity_to_kill.location_on_screen.y), multiplier)


      pos_x, pos_y = entity_to_kill.location_on_screen.x, entity_to_kill.location_on_screen.y
      pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y) 
      bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      # move mouse to a new position
      current_time = time.time()

      if current_time  > start_time + max_hold_duration:
        print('exceed time')
        break

    self.lightning_arrow_attack.release()
    
    return res
class FrenzyFrostblink(Build):
  '''
  build uses bow skill to trigger lightningwarp
  '''
  poe_bot: PoeBot
  def __init__(self,poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot


    self.auto_flasks = AutoFlasks(poe_bot=poe_bot)
    
    self.blood_rage = None # "blood_rage"
    self.frenzy = None 
    self.frostblink_debuff = None # "lightning_arrow"
    self.hatred_blessing = None

    self.swapWeaponsIfNeeded()
    skills_data = poe_bot.backend.getSkillBar()
    skills_on_panel = skills_data['i_n']

    #TODO
    for skill_index in range(len(skills_data['i_n'])):
      skill = skills_data['i_n'][skill_index]

      if skill == '':
        continue
      print(skill, skill_index)
      if skill == 'blood_rage':
        self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/10, display_name="blood_rage")
      elif skill == 'frenzy':
        self.frenzy = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1,5)/100, display_name="frenzy", min_mana_to_use=1)
      elif skill == 'ice_dash':
        self.frostblink_debuff = AreaSkill(poe_bot=poe_bot, skill_index=skill_index, display_name="frostblink_debuff")
      elif skill == 'hatred' and skill_index < 8:
        print(f'got hatred on first panel, seems to be buff')
        self.hatred_blessing = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=9, display_name='hatred_blessing')
    super().__init__(poe_bot)

  def useBuffs(self):
    poe_bot = self.poe_bot
    if self.blood_rage is not None:
      if 'blood_rage' not in poe_bot.game_data.player.buffs:
        if self.blood_rage.use() is True:
          return True

    if self.hatred_blessing is not None:
        force_use = not 'player_aura_cold_damage' in poe_bot.game_data.player.buffs
        if self.hatred_blessing.use(force=force_use) is True:
          return True

    return False

  def useFlasks(self):
    self.auto_flasks.useFlasks()

  def usualRoutine(self, mover:Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()

    # if we are moving
    if mover is not None:
      self.useBuffs()
      # as a movement skill
      if mover.distance_to_target > 30:
        # bit more logic, take some data from mover, smth like current_path length, distance to next_step in grid pos,
        # distance to next step on screen  
        distance_to_next_step = dist( (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y))
        print(f'distance_to_next_step {distance_to_next_step}')
        if distance_to_next_step > 20:
          path_values = createLineIteratorWithValues((poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y), poe_bot.game_data.terrain.passable)
          path_without_obstacles = np.all(path_values[:,2] > 0)
          print(f'path_without_obstacles {path_without_obstacles}')
          max_distance = mover.distance_to_target
          current_distance = dist( (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y))
          multiply_by = max_distance / current_distance
          if multiply_by > 2:
            multiply_by = 2
          pos_x, pos_y = extendLine( (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y), multiply_by)
          if self.frenzy.use(pos_x=pos_x, pos_y=pos_y, force=True) is True:
            return True

      # distance_difference = dist([poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y], [self.lightning_arrow_attack.last_use_location['X'], self.lightning_arrow_attack.last_use_location['Y']])
      # if distance_difference > 55:
      #   self.lightning_arrow_attack.last_use_time = 0
      
      # # just to attack random mobs
      # if self.lightning_arrow_attack.use(pos_x=mover.grid_pos_to_step_x, pos_y=mover.grid_pos_to_step_y) is True:
      #   return True
    # if we are staying and waiting for smth
    else:
      self.staticDefence()

    return False
  
  def prepareToFight(self, entity: Entity):
    print(f'frenzyfrostblink.preparetofight call {time.time()}')
    poe_bot = self.poe_bot
    bot_controls = self.poe_bot.bot_controls
    pos_x, pos_y = entity.location_on_screen.x, entity.location_on_screen.y
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y) 
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    self.frostblink_debuff.use()
    self.frenzy.press()
    start_hold_time = time.time()
    min_hold_duration = random.randint(40,60)/100
    while True:
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      pos_x, pos_y = poe_bot.getPositionOfThePointOnTheScreen(y=entity.grid_position.y, x= entity.grid_position.x)
      pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y) 
      bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      if time.time() > start_hold_time + min_hold_duration:
        break
    self.frenzy.release()

  
  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = 10, *args, **kwargs):
    print(f'#build.killUsual {entity}')
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls


    entity_to_kill_id = entity.id
    self.useFlasks()
    
    min_distance = 30
    max_hold_duration = random.randint(200,300)/100
    max_hold_duration = 300


    entities_to_kill = list(filter(lambda e: e.id == entity_to_kill_id, poe_bot.game_data.entities.attackable_entities))
    if len(entities_to_kill) == 0:
      print('cannot find desired entity to kill')
      return True

    entity_to_kill = entities_to_kill[0]
    print(f'entity_to_kill {entity_to_kill}')

    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual') 
    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    
    start_time = time.time()

    
    pos_x, pos_y = entity_to_kill.location_on_screen.x, entity_to_kill.location_on_screen.y

    # distance_to_jump = 15
    # need_distance = distance_to_entity + distance_to_jump
    # multiplier = need_distance / distance_to_entity
    # pos_x, pos_y = extendLine( (poe_bot.game_window.center_point[0], poe_bot.game_window.center_point[1]), (entity_to_kill.location_on_screen.x, entity_to_kill.location_on_screen.y), multiplier)


    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y) 
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    self.frenzy.press()
    poe_bot.last_action_time = 0
    last_distance_to_entity = distance_to_entity
    res = True
    reset_timer = False
    i = 0
    while True:
      i += 1
      poe_bot.refreshInstanceData(reset_timer=reset_timer)
      # poe_bot.last_action_time = 0
      self.useFlasks()
      entities_to_kill = list(filter(lambda e: e.id == entity_to_kill_id, poe_bot.game_data.entities.attackable_entities))
      if len(entities_to_kill) == 0:
        print('cannot find desired entity to kill')
        break
      entity_to_kill = entities_to_kill[0]
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break
      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        break
      
      if last_distance_to_entity + 5 < distance_to_entity:
        print(f'too far from entity, fast reset')
        reset_timer = True
      else:
        reset_timer = False
      last_distance_to_entity = distance_to_entity
      # if entity is dead, or far away, break, return True, since we need to update the new movement
      # need_distance = distance_to_entity + distance_to_jump
      # multiplier = need_distance / distance_to_entity
      # pos_x, pos_y = extendLine( (poe_bot.game_window.center_point[0], poe_bot.game_window.center_point[1]), (entity_to_kill.location_on_screen.x, entity_to_kill.location_on_screen.y), multiplier)


      pos_x, pos_y = entity_to_kill.location_on_screen.x, entity_to_kill.location_on_screen.y
      pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y) 
      bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      # move mouse to a new position
      current_time = time.time()

      if current_time  > start_time + max_hold_duration:
        print('exceed time')
        break

    self.frenzy.release()
    
    return res
class PenanceBrandPf(Build):
  '''
  PenanceBrandPf
  '''
  poe_bot: PoeBot
  def __init__(self,poe_bot: PoeBot) -> None:
    self.brand_last_use_time = 0

    self.poe_bot = poe_bot


    self.blood_rage = None # "blood_rage"
    self.penance_brand = None #"penance_brand_alt_x"
    self.plague_bearer = None # "corrosive_shroud"
    self.debuff = None # "despair"
    self.movement_skill = None # "new_new_shield_charge"
    self.malevolance_blessing = None

    self.swapWeaponsIfNeeded()
    skills_data = poe_bot.backend.getSkillBar()
    skills_on_panel = skills_data['i_n']

    #TODO
    for skill_index in range(len(skills_data['i_n'])):
      skill = skills_data['i_n'][skill_index]

      if skill == '':
        continue
      print(skill, skill_index)
      if skill == 'blood_rage':
        self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/10, display_name="blood_rage")
      elif skill == 'penance_brand_alt_x':
        self.penance_brand = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1,5)/100, display_name="penance_brand", min_mana_to_use=0)
      elif skill == 'despair':
        self.debuff = AreaSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill)
      elif skill == 'corrosive_shroud':
        self.plague_bearer = PlagueBearer(poe_bot=poe_bot, skill_index=skill_index, display_name=skill)
      elif skill == "new_new_shield_charge" or skill == "blade_flurry":
        self.movement_skill = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill, min_delay=random.randint(30,50)/100)
      elif skill == 'damage_over_time_aura' and skill_index < 8:
        print(f'got malevolance on first panel, seems to be buff')
        self.malevolance_blessing = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=9, display_name='malevolance_blessing')
    super().__init__(poe_bot)
    self.auto_flasks = AutoFlasks(poe_bot=poe_bot, pathfinder=True)
  def useBuffs(self):
    poe_bot = self.poe_bot
    if self.blood_rage is not None:
      if 'blood_rage' not in poe_bot.game_data.player.buffs:
        if self.blood_rage.use() is True:
          return True

    if self.malevolance_blessing is not None:
      if self.malevolance_blessing.checkIfCanUse() is True:
        force_use = not 'player_aura_damage_over_time' in poe_bot.game_data.player.buffs
        if self.malevolance_blessing.use(force=force_use) is True:
          return True

    return False
  def useFlasks(self):
    self.auto_flasks.useFlasks()
  def usualRoutine(self, mover:Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()
    # if we are moving
    if mover is not None:
      self.useBuffs()
      nearby_enemies = list(filter(lambda e: e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      print(f'nearby_enemies: {nearby_enemies}')
      really_close_enemies = list(filter(lambda e: e.distance_to_player < 20,nearby_enemies))
      min_delay = 3
      if len(really_close_enemies) != 0:
        min_delay = 2
        if self.plague_bearer:
          print(f'can turn plague bearer')
          self.plague_bearer.turnOn()
      # enemies_in_radius = list(filter(lambda e: e.distance_to_player < 35, poe_bot.game_data.entities.attackable_entities))
      
      # if len(enemies_in_radius) > 3:
      #   if self.plague_bearer:
      #       print(f'can turn plague bearer')
      #       self.plague_bearer.turnOn()
      # elif self.plague_bearer:
      #   print(f'can turn off plague bearer')
      #   self.plague_bearer.turnOff()

      if self.brand_last_use_time + min_delay < time.time():
        print('can use brand')
        enemy_to_attack = None
        if len(really_close_enemies) != 0:
          enemy_to_attack = really_close_enemies[0]
        elif len(nearby_enemies):
          nearby_enemies = sorted(nearby_enemies, key=lambda e: e.distance_to_player)
          nearby_enemies = list(filter(lambda e: e.isInLineOfSight() is True, nearby_enemies))
          if len(nearby_enemies) != 0:
            enemy_to_attack = nearby_enemies[0]
        if enemy_to_attack is not None:
          if self.penance_brand.use(updated_entity=enemy_to_attack) is True:
            self.brand_last_use_time = time.time()
            return True
      # use movement skill
      if self.movement_skill and mover.distance_to_target > 50:
        if self.movement_skill.use(mover.grid_pos_to_step_x, mover.grid_pos_to_step_y, wait_for_execution=False) is True:
          return True
    # if we are staying and waiting for smth
    else:
      self.staticDefence()

    return False
  def prepareToFight(self, entity: Entity):
    print(f'frenzyfrostblink.preparetofight call {time.time()}')
    for i in range(random.randint(2,3)):
      self.poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      updated_entity = next( (e for e in self.poe_bot.game_data.entities.all_entities if e.id == entity.id), None)
      if updated_entity is None:
        break

      self.penance_brand.use(updated_entity=updated_entity)
    return True
  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = random.randint(200,300)/10, *args, **kwargs):
    print(f'#build.killUsual {entity}')
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    mover = self.mover
    entity_to_kill_id = entity.id
    debuff_use_time = 0
    self.useFlasks()
    
    min_distance = 40 # distance which is ok to start attacking
    keep_distance = 15 # if our distance is smth like this, kite

    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print('cannot find desired entity to kill')
      return True

    print(f'entity_to_kill {entity_to_kill}')
    
    if entity_to_kill.life.health.current < 0:
      print('entity is dead')
      return True

    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual')
    if is_strong is True and self.vaal_molten_shell:
      self.vaal_molten_shell.use()
    
    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    
    if entity_to_kill.isInLineOfSight() is False:
      print('entity_to_kill.isInLineOfSight() is False')
      return False


    start_time = time.time()
    pos_x, pos_y = entity_to_kill.location_on_screen.x, entity_to_kill.location_on_screen.y
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y) 
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    self.penance_brand.use(updated_entity=entity_to_kill)
    self.brand_last_use_time = time.time()
    poe_bot.last_action_time = 0
    kite_distance = random.randint(18,22)
    res = True
    reversed_run = random.choice([True, False])
    while True:
      skill_used = False
      poe_bot.refreshInstanceData()
      self.useFlasks()

      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print('cannot find desired entity to kill')
        break
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break




      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        break
      current_time = time.time()
      if self.useBuffs() is True:
        skill_used = True

      
      if self.plague_bearer:
        self.plague_bearer.turnOn()

      if self.debuff:
        if current_time > start_time + 2:
          if current_time > debuff_use_time + 4:
            if self.debuff.use(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y) is True:
              debuff_use_time = time.time()
              skill_used = True
      # dd_use_delay = random.randint(40,50)/100 + int(not self.desecrate is None) * 0.5
      brand_use_delay = random.randint(20,30)/10
      print(f'brand_use_delay {brand_use_delay}')
      if skill_used is False and self.brand_last_use_time + brand_use_delay < time.time():
        self.penance_brand.use(updated_entity=entity_to_kill)
        self.brand_last_use_time = time.time()
        # continue
      print('kiting')
      point = self.poe_bot.game_data.terrain.pointToRunAround(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, kite_distance+random.randint(-1,1), check_if_passable=True, reversed=reversed_run)
      mover.move(grid_pos_x = point[0], grid_pos_y = point[1])




      if current_time  > start_time + max_kill_time_sec:
        print('exceed time')
        break
    return res
class DetonateDeadMapper(Build):
  # https://pobb.in/KyL-p2YeCoXi
  # https://pobb.in/B2aDK1fZNWLT
  # https://pobb.in/Q1BhZyO98TWN

  # https://m.youtube.com/watch?v=s--bXXFiurI - gameplay
  '''
  detonate dead with or without corpsewalkers
  '''
  poe_bot: PoeBot
  def __init__(self,poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.last_explosion_loc = [0,1,0,1]
    self.last_explosion_time = 0
    
    self.blood_rage = None # "blood_rage"
    self.shield_charge = None # "new_new_shield_charge"
    self.desecrate = None # name: "desecrate" animated_property_metadata "a":"Metadata/Effects/Spells/frost_bolt/sml_maelstrom.ao"
    self.detonate_dead = None # name: "detonate_dead" animated_property_metadata "a":"Metadata/Effects/Spells/frost_bolt/sml_maelstrom.ao"
    self.vaal_detonate_dead = None # name: "repeating_vaal_detonate_dead" animated_property_metadata "a":"Metadata/Effects/Spells/frost_bolt/sml_maelstrom.ao"
    self.molten_shell = None #"molten_shell_barrier" buff "molten_shell_damage_absorption"
    self.vaal_molten_shell = None #"vaal_molten_shell_barrier"
    self.debuff_skill = None # "arcanist_brand" "fire_weakness" "despair" or brand
    self.blessing_buff = None

    self.swapWeaponsIfNeeded()
    skills_data = poe_bot.backend.getSkillBar()
    skills_on_panel = skills_data['i_n']

    # debuff
    for skill_name in ["arcanist_brand","fire_weakness","despair"]:
      if skill_name in skills_on_panel:
        skill_index = skills_on_panel.index(skill_name)
        self.debuff_skill = AreaSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill_name)
        break

    if "desecrate" in skills_on_panel:
      skill_index = skills_on_panel.index("desecrate")
      self.desecrate = Skill(poe_bot=poe_bot, skill_index=skill_index, display_name='desecrate', sleep_multiplier=0.7)

    for skill_index in range(len(skills_data['i_n'])):
      skill = skills_data['i_n'][skill_index]

      if skill == '':
        continue
      print(skill, skill_index)
      if skill == 'new_new_shield_charge':
        self.shield_charge = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/100, display_name="shield_charge")
      elif skill == 'haste': # TODO replace with "haste"
      # elif skill == 'damage_over_time_aura': # TODO replace with "haste"
        self.blessing_buff = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=8, display_name="player_aura_damage_over_time")
      elif skill == 'blood_rage':
        self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/10, display_name="blood_rage")
      elif skill == 'detonate_dead':
        self.detonate_dead = DetonateDead(poe_bot=poe_bot, skill_index=skill_index, desecrate=self.desecrate)
      elif skill == 'repeating_vaal_detonate_dead':
        self.vaal_detonate_dead = Skill(poe_bot=poe_bot, skill_index=skill_index, display_name='vaal_detonate_dead')
      elif skill == 'molten_shell_barrier':
        self.molten_shell = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index)

    super().__init__(poe_bot)

  def useBuffs(self):
    poe_bot = self.poe_bot
    if self.blood_rage is not None:
      if 'blood_rage' not in poe_bot.game_data.player.buffs and poe_bot.game_data.player.life.health.getPercentage() > 0.7:
        if self.blood_rage.use() is True:
          return True

    if self.blessing_buff is not None:
        # force_use = not 'player_aura_damage_over_time' in poe_bot.game_data.player.buffs
        force_use = not "player_aura_speed" in poe_bot.game_data.player.buffs
        self.blessing_buff.use()
      # if 'player_aura_cold_damage' not in poe_bot.game_data.player.buffs:
        # self.hatred_blessing.use()


  def useFlasks(self):
    self.auto_flasks.useFlasks()

  def usualRoutine(self, mover:Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()

    # if we are moving
    if mover is not None:
      entity_to_explode:Entity = None
      search_radius = 25
      search_angle = 75
      search_angle_half = search_angle/2
      
      self.useBuffs()

      corpses = poe_bot.game_data.entities.getCorpsesArountPoint(poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y, 25)
      if corpses:
        print('found corpses in radius 25 of player')
        if self.last_explosion_time + 1 < time.time():
          print(f'resetting corpse explosions area')
          self.last_explosion_loc = [0,1,0,1]

        list(map(lambda e: e.calculateValueForAttack(search_radius), corpses))
        corpses = list(filter(lambda e: e.attack_value > 2, corpses))
        print(f"{len(corpses)} with attack_value >2")
        corpses = list(filter(lambda e: not e.isInZone(*self.last_explosion_loc), corpses))
        print(f"{len(corpses)} not in last explosion zone")
        if corpses:
          corpses.sort(key=lambda e:e.attack_value, reverse=True)
          entity_to_explode = corpses[0]
          print(f'self.last_explosion_loc {self.last_explosion_loc}')
          print(f'found valuable corpse to explode {entity_to_explode.raw}')
      
      # nearby_enemies = list(filter(lambda entity: entity.distance_to_player < 40, poe_bot.game_data.entities.attackable_entities))
      nearby_enemies = list(filter(lambda e: e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      print(f'nearby_enemies: {nearby_enemies}')

      really_close_enemies = list(filter(lambda e: e.distance_to_player < 20,nearby_enemies))
      if really_close_enemies:
        # if enemies around use molten shell
        if self.molten_shell is not None:
          self.molten_shell.use() 

      if not entity_to_explode:
        if self.desecrate:
          really_close_enemies = list(filter(lambda e: e.distance_to_player < 13,really_close_enemies))
          if len(really_close_enemies) > 5 and not "flask_utility_phase" in self.poe_bot.game_data.player.buffs:
            print(f'len(really_close_enemies) > 5 and not "flask_utility_phase" in self.poe_bot.game_data.player.buffs:')
            nearby_enemies = really_close_enemies
            self.detonate_dead.last_use_time = 0
            list(map(lambda e: e.calculateValueForAttack(search_radius), nearby_enemies))
          
          elif nearby_enemies and self.detonate_dead.last_use_time + 1 < time.time():
            print(f'nearby_enemies and self.detonate_dead.last_use_time + 1 < time.time()')
            # check enemies in cone first
            p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
            p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
            nearby_enemies = list(filter(lambda e: getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < search_angle_half, nearby_enemies))
            list(map(lambda e: e.calculateValueForAttack(search_radius), nearby_enemies))
            nearby_enemies = list(filter(lambda e: e.attack_value > 5, nearby_enemies))
          else:
            nearby_enemies = []

          nearby_enemies = list(filter(lambda e: e.isInLineOfSight(), nearby_enemies))
          if nearby_enemies:
            nearby_enemies.sort(key=lambda e:e.attack_value, reverse=True)
            entity_to_explode = nearby_enemies[0]
      
      
      if entity_to_explode and self.detonate_dead.use(updated_entity=entity_to_explode) is True:
        self.last_explosion_time = time.time()
        self.last_explosion_loc = [entity_to_explode.grid_position.x - 20, entity_to_explode.grid_position.x + 20, entity_to_explode.grid_position.y - 20, entity_to_explode.grid_position.y + 20]
        return True
        # return True



      # use movement skill
      if mover.distance_to_target > 50:
        # bit more logic, take some data from mover, smth like current_path length, distance to next_step in grid pos,
        # distance to next step on screen  
        distance_to_next_step = dist( (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y))
        print(f'distance_to_next_step {distance_to_next_step}')
        if distance_to_next_step > 20:
          path_values = createLineIteratorWithValues((poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y), poe_bot.game_data.terrain.passable)
          path_without_obstacles = np.all(path_values[:,2] > 0)
          print(f'path_without_obstacles {path_without_obstacles}')
          if path_without_obstacles:
            pos_x, pos_y = extendLine( (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y), 2)
            if self.shield_charge.use(pos_x=pos_x, pos_y=pos_y, wait_for_execution=False) is True:
              return True
    # if we are staying and waiting for smth
    else:
      self.staticDefence()

    return False
  
  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = 10, *args, **kwargs):
    print(f'#build.killUsual {entity}')
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    mover = self.mover

    entity_to_kill_id = entity.id
    debuff_use_time = 0
    last_attack_time = 0
    start_attack_time = 0
    attack_cycle_duration = 1
    attack_cycle_cooldown = 1
    attacking = False
    holding_dd = False

    self.useFlasks()
    
    min_distance = 40 # distance which is ok to start attacking
    keep_distance = 15 # if our distance is smth like this, kite

    min_hold_duration = random.randint(200,300)/10

    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print('cannot find desired entity to kill')
      return True

    print(f'entity_to_kill {entity_to_kill}')
    
    if entity_to_kill.life.health.current < 0:
      print('entity is dead')
      return True


    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual')
    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    
    if entity_to_kill.isInLineOfSight() is False:
      print('entity_to_kill.isInLineOfSight() is False')
      return False


    start_time = time.time()
    pos_x, pos_y = entity_to_kill.location_on_screen.x, entity_to_kill.location_on_screen.y
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y) 
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    if is_strong:
      self.vaal_detonate_dead.use()
      self.debuff_skill.use(updated_entity=entity)
    poe_bot.last_action_time = 0
    kite_distance = random.randint(10,14) if self.desecrate is None else random.randint(18,22) 
    res = True
    last_corpse_id = 0
    self.detonate_dead.last_use_time = 0
    reversed_run = random.choice([True, False])
    while True:
      skill_used = False
      poe_bot.refreshInstanceData()
      self.useFlasks()
      self.useBuffs()
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print('cannot find desired entity to kill')
        break
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break
      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        break
      current_time = time.time()
      if self.molten_shell: self.molten_shell.use()

      if current_time > start_time + 2:
        if current_time > debuff_use_time + 4:
          if self.debuff_skill.use(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y) is True:
            debuff_use_time = time.time()
            skill_used = True
      # dd_use_delay = random.randint(40,50)/100 + int(not self.desecrate is None) * 0.5
      dd_use_delay = self.detonate_dead.getCastTime() * 2 # + int(not self.desecrate is None) * 0.5
      print(f'ddusedelay {dd_use_delay}')
      if skill_used is False and self.detonate_dead.last_use_time + dd_use_delay < time.time():
        entity_to_explode = entity_to_kill 
        corpses = poe_bot.game_data.entities.getCorpsesArountPoint(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, 15)
        corpses = list(filter(lambda e: e.id != last_corpse_id, corpses))
        if len(corpses) > 1:
          print(f'dd.killusualentity found {len(corpses)} corpses around entity, will explode the high hp one')
          corpses.sort(key= lambda e: e.life.health.total, reverse=True)
          entity_to_explode = corpses[0]
          last_corpse_id = entity_to_explode.id
          print(entity_to_explode.raw)

        self.detonate_dead.use(updated_entity=entity_to_explode)
        # continue
      print('dd kiting')
      point = self.poe_bot.game_data.terrain.pointToRunAround(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, kite_distance+random.randint(-1,1), check_if_passable=True, reversed=reversed_run)
      mover.move(grid_pos_x = point[0], grid_pos_y = point[1])




      if current_time  > start_time + min_hold_duration:
        print('exceed time')
        break
    if holding_dd: self.detonate_dead.release()
    # self.detonate_dead.release()
    return res
class DetonateDeadSimulacrum(Build):
  '''
  detonate dead 10d ci
  '''
  poe_bot: PoeBot
  def __init__(self,poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    super().__init__(poe_bot)
    self.chaos_immune = True
    self.last_explosion_loc = [0,1,0,1]
    self.last_explosion_time = 0
    
    self.have_arcanist_brand = False
    self.desecrate = None
    self.shield_charge = None # "new_new_shield_charge"
    self.detonate_dead = None # name: "detonate_dead" animated_property_metadata "a":"Metadata/Effects/Spells/frost_bolt/sml_maelstrom.ao"
    self.vaal_detonate_dead = None # name: "repeating_vaal_detonate_dead" animated_property_metadata "a":"Metadata/Effects/Spells/frost_bolt/sml_maelstrom.ao"
    self.molten_shell = None #"molten_shell_barrier" buff "molten_shell_damage_absorption"
    self.vaal_molten_shell = None #"vaal_molten_shell_barrier"
    self.debuff_skill = None # "despair" or brand

    self.swapWeaponsIfNeeded()
    skills_data = poe_bot.backend.getSkillBar()
    skills_on_panel = skills_data['i_n']

    # debuff
    for skill_name in ["arcanist_brand","despair"]:
      if skill_name in skills_on_panel:
        if skill_name == 'arcanist_brand':
          self.have_arcanist_brand = True
        skill_index = skills_on_panel.index(skill_name)
        self.debuff_skill = AreaSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill_name)
        break

    for skill_index in range(len(skills_data['i_n'])):
      skill = skills_data['i_n'][skill_index]

      if skill == '':
        continue
      print(skill, skill_index)
      if skill == 'new_new_shield_charge':
        self.shield_charge = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/100, display_name="shield_charge")
      elif skill == 'detonate_dead' or skill == 'detonate_dead_alt_y':
        self.detonate_dead = DetonateDead(poe_bot=poe_bot, skill_index=skill_index)
      elif skill == 'repeating_vaal_detonate_dead':
        self.vaal_detonate_dead = Skill(poe_bot=poe_bot, skill_index=skill_index, display_name='vaal_detonate_dead')
      elif skill == 'molten_shell_barrier':
        self.molten_shell = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, display_name='molten_shell_barrier')
      elif skill == 'vaal_molten_shell':
        self.vaal_molten_shell = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, display_name='vaal_molten_shell')
      
  def useFlasks(self):
    self.auto_flasks.useFlasks()

  def usualRoutine(self, mover:Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()

    # if we are moving
    if mover is not None:
      entity_to_explode:Entity = None
      search_radius = 25
      search_angle = 75
      search_angle_half = search_angle/2
      

      corpses = poe_bot.game_data.entities.getCorpsesArountPoint(poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y, 25)
      if corpses:
        print('found corpses in radius 25 of player')
        if self.last_explosion_time + 1 < time.time():
          print(f'resetting corpse explosions area')
          self.last_explosion_loc = [0,1,0,1]

        list(map(lambda e: e.calculateValueForAttack(search_radius), corpses))
        corpses = list(filter(lambda e: e.attack_value > 2, corpses))
        print(f"{len(corpses)} with attack_value >2")
        corpses = list(filter(lambda e: not e.isInZone(*self.last_explosion_loc), corpses))
        print(f"{len(corpses)} not in last explosion zone")
        if corpses:
          corpses.sort(key=lambda e:e.attack_value, reverse=True)
          entity_to_explode = corpses[0]
          print(f'self.last_explosion_loc {self.last_explosion_loc}')
          print(f'found valuable corpse to explode {entity_to_explode.raw}')
      
      # nearby_enemies = list(filter(lambda entity: entity.distance_to_player < 40, poe_bot.game_data.entities.attackable_entities))
      nearby_enemies = list(filter(lambda e: e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      print(f'nearby_enemies: {nearby_enemies}')

      really_close_enemies = list(filter(lambda e: e.distance_to_player < 20,nearby_enemies))
      if really_close_enemies:
        # if enemies around use molten shell
        if self.molten_shell is not None:
          self.molten_shell.use() 

      if not entity_to_explode:
        if self.desecrate:
          really_close_enemies = list(filter(lambda e: e.distance_to_player < 13,really_close_enemies))
          if len(really_close_enemies) > 5 and not "flask_utility_phase" in self.poe_bot.game_data.player.buffs:
            print(f'len(really_close_enemies) > 5 and not "flask_utility_phase" in self.poe_bot.game_data.player.buffs:')
            nearby_enemies = really_close_enemies
            self.detonate_dead.last_use_time = 0
            list(map(lambda e: e.calculateValueForAttack(search_radius), nearby_enemies))
          
          elif nearby_enemies and self.detonate_dead.last_use_time + 1 < time.time():
            print(f'nearby_enemies and self.detonate_dead.last_use_time + 1 < time.time()')
            # check enemies in cone first
            p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
            p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
            nearby_enemies = list(filter(lambda e: getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < search_angle_half, nearby_enemies))
            list(map(lambda e: e.calculateValueForAttack(search_radius), nearby_enemies))
            nearby_enemies = list(filter(lambda e: e.attack_value > 5, nearby_enemies))
          else:
            nearby_enemies = []

          nearby_enemies = list(filter(lambda e: e.isInLineOfSight(), nearby_enemies))
          if nearby_enemies:
            nearby_enemies.sort(key=lambda e:e.attack_value, reverse=True)
            entity_to_explode = nearby_enemies[0]
      
      
      if entity_to_explode and self.detonate_dead.use(updated_entity=entity_to_explode) is True:
        self.last_explosion_time = time.time()
        self.last_explosion_loc = [entity_to_explode.grid_position.x - 20, entity_to_explode.grid_position.x + 20, entity_to_explode.grid_position.y - 20, entity_to_explode.grid_position.y + 20]
        return True
        # return True



      # use movement skill
      if mover.distance_to_target > 50 and self.shield_charge:
        # bit more logic, take some data from mover, smth like current_path length, distance to next_step in grid pos,
        # distance to next step on screen  
        distance_to_next_step = dist( (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y))
        print(f'distance_to_next_step {distance_to_next_step}')
        if distance_to_next_step > 20:
          path_values = createLineIteratorWithValues((poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y), poe_bot.game_data.terrain.passable)
          path_without_obstacles = np.all(path_values[:,2] > 0)
          print(f'path_without_obstacles {path_without_obstacles}')
          if path_without_obstacles:
            pos_x, pos_y = extendLine( (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y), 2)
            if self.shield_charge.use(pos_x=pos_x, pos_y=pos_y, wait_for_execution=False) is True:
              return True
    # if we are staying and waiting for smth
    else:
      self.staticDefence()

    return False
  
  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = random.randint(200,300)/10, *args, **kwargs):
    print(f'#build.killUsual {entity}')
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    mover = self.mover

    entity_to_kill_id = entity.id
    debuff_use_time = 0

    self.useFlasks()
    
    min_distance = 40 # distance which is ok to start attacking
    keep_distance = 15 # if our distance is smth like this, kite

    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print('cannot find desired entity to kill')
      return True

    print(f'entity_to_kill {entity_to_kill}')
    
    if entity_to_kill.life.health.current < 0:
      print('entity is dead')
      return True

    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual')
    if is_strong is True and self.vaal_molten_shell:
      self.vaal_molten_shell.use()
    
    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    
    if entity_to_kill.isInLineOfSight() is False:
      print('entity_to_kill.isInLineOfSight() is False')
      return False


    start_time = time.time()
    pos_x, pos_y = entity_to_kill.location_on_screen.x, entity_to_kill.location_on_screen.y
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y) 
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    if is_strong:
      self.debuff_skill.use(updated_entity=entity)
    poe_bot.last_action_time = 0
    kite_distance = random.randint(10,14) if self.desecrate is None else random.randint(18,22) 
    res = True
    last_corpse_id = 0
    self.detonate_dead.last_use_time = 0
    reversed_run = random.choice([True, False])
    while True:
      skill_used = False
      poe_bot.refreshInstanceData()
      self.useFlasks()
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print('cannot find desired entity to kill')
        break
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break




      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        break
      current_time = time.time()
      if self.molten_shell: self.molten_shell.use()

      if is_strong is True and self.vaal_detonate_dead:
        corpses_around_entity = poe_bot.game_data.entities.getCorpsesArountPoint(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, 15)
        if len(corpses_around_entity) > 10:
          if self.vaal_detonate_dead.use() is True:
            skill_used = True


      if current_time > start_time + 2:
        if current_time > debuff_use_time + 2 + int(self.have_arcanist_brand is False) * 5:
          if self.debuff_skill.use(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y) is True:
            debuff_use_time = time.time()
            skill_used = True
      # dd_use_delay = random.randint(40,50)/100 + int(not self.desecrate is None) * 0.5
      dd_use_delay = self.detonate_dead.getCastTime() * 2 # + int(not self.desecrate is None) * 0.5
      print(f'ddusedelay {dd_use_delay}')
      if skill_used is False and self.detonate_dead.last_use_time + dd_use_delay < time.time():
        entity_to_explode = entity_to_kill 
        corpses_around_entity = poe_bot.game_data.entities.getCorpsesArountPoint(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, 25)
        corpses_around_entity = list(filter(lambda e: e.id != last_corpse_id, corpses_around_entity))
        if len(corpses_around_entity) > 1:
          print(f'dd.killusualentity found {len(corpses_around_entity)} corpses around entity, will explode the high hp one')
          corpses_around_entity.sort(key= lambda e: e.life.health.total, reverse=True)
          entity_to_explode = corpses_around_entity[0]
          last_corpse_id = entity_to_explode.id
          print(entity_to_explode.raw)

        self.detonate_dead.use(updated_entity=entity_to_explode)
        # continue
      print('dd kiting')
      point = self.poe_bot.game_data.terrain.pointToRunAround(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, kite_distance+random.randint(-1,1), check_if_passable=True, reversed=reversed_run)
      mover.move(grid_pos_x = point[0], grid_pos_y = point[1])




      if current_time  > start_time + max_kill_time_sec:
        print('exceed time')
        break
    return res
class DetonateDeadSimulacrumOnly(Build):
  '''
  detonate dead 10d ci
  '''
  poe_bot: PoeBot
  def __init__(self,poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    super().__init__(poe_bot)
    self.chaos_immune = True
    self.last_attack_time = 0
    self.attack_delay = 0.7

    self.last_explosion_loc = [0,1,0,1]
    self.last_explosion_time = 0
    
    self.desecrate = None
    self.shield_charge = None # "new_new_shield_charge"
    self.detonate_dead = None # name: "detonate_dead" animated_property_metadata "a":"Metadata/Effects/Spells/frost_bolt/sml_maelstrom.ao"
    self.vaal_detonate_dead = None # name: "repeating_vaal_detonate_dead" animated_property_metadata "a":"Metadata/Effects/Spells/frost_bolt/sml_maelstrom.ao"
    self.molten_shell = None #"molten_shell_barrier" buff "molten_shell_damage_absorption"
    self.vaal_molten_shell = None #"vaal_molten_shell_barrier"
    self.debuff_skill = None # "despair" or brand

    self.swapWeaponsIfNeeded()
    skills_data = poe_bot.backend.getSkillBar()
    skills_on_panel = skills_data['i_n']

    # debuff
    for skill_name in ["arcanist_brand","despair"]:
      if skill_name in skills_on_panel:
        skill_index = skills_on_panel.index(skill_name)
        self.debuff_skill = AreaSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill_name)
        break

    for skill_index in range(len(skills_data['i_n'])):
      skill = skills_data['i_n'][skill_index]

      if skill == '':
        continue
      print(skill, skill_index)
      if skill == 'new_new_shield_charge':
        self.shield_charge = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/100, display_name="shield_charge")
      elif skill == 'detonate_dead':
        self.detonate_dead = DetonateDead(poe_bot=poe_bot, skill_index=skill_index)
      elif skill == 'repeating_vaal_detonate_dead':
        self.vaal_detonate_dead = Skill(poe_bot=poe_bot, skill_index=skill_index, display_name='vaal_detonate_dead')
      elif skill == 'molten_shell_barrier':
        self.molten_shell = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, display_name='molten_shell_barrier')
      elif skill == 'vaal_molten_shell':
        self.vaal_molten_shell = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, display_name='vaal_molten_shell')
      
  def useFlasks(self):
    self.auto_flasks.useFlasks()

  def usualRoutine(self, mover:Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()

    # if we are moving
    if mover is not None:
      nearby_enemies = list(filter(lambda e: e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      nearby_enemies = list(filter(lambda e: e.distance_to_player < 23, nearby_enemies))
      if len(nearby_enemies) > 1 and self.last_attack_time + self.attack_delay < time.time():
        print(f'tapping dd')
        self.detonate_dead.press()
        time.sleep(random.randint(5,12)/100)
        self.detonate_dead.release()
        self.last_attack_time = time.time()
        return True
    # if we are staying and waiting for smth
    else:
      self.staticDefence()

    return False
  
  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = random.randint(200,300)/10, *args, **kwargs):
    print(f'#build.killUsual {entity}')
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    mover = self.mover

    entity_to_kill_id = entity.id
    debuff_use_time = 0

    self.useFlasks()
    
    min_distance = 40 # distance which is ok to start attacking
    keep_distance = 15 # if our distance is smth like this, kite

    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print('cannot find desired entity to kill')
      return True

    print(f'entity_to_kill {entity_to_kill}')
    
    if entity_to_kill.life.health.current < 0:
      print('entity is dead')
      return True

    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual')
    if is_strong is True and self.vaal_molten_shell:
      self.vaal_molten_shell.use()
    
    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    
    if entity_to_kill.isInLineOfSight() is False:
      print('entity_to_kill.isInLineOfSight() is False')
      return False


    start_time = time.time()
    pos_x, pos_y = entity_to_kill.location_on_screen.x, entity_to_kill.location_on_screen.y
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y) 
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    if is_strong:
      self.debuff_skill.use(updated_entity=entity)
    poe_bot.last_action_time = 0
    kite_distance = random.randint(6,10) if self.desecrate is None else random.randint(18,22) 
    res = True
    last_corpse_id = 0
    self.detonate_dead.last_use_time = 0
    reversed_run = random.choice([True, False])
    while True:
      skill_used = False
      poe_bot.refreshInstanceData()
      self.useFlasks()
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print('cannot find desired entity to kill')
        break
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break

      if is_strong is True and self.vaal_molten_shell:
        self.vaal_molten_shell.use()


      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        break
      current_time = time.time()
      if self.molten_shell: self.molten_shell.use()

      if is_strong is True and self.vaal_detonate_dead:
        if current_time > start_time + 2: 
          if self.vaal_detonate_dead.use() is True:
            skill_used = True


      if current_time > start_time + 2:
        if current_time > debuff_use_time + 4:
          if self.debuff_skill.use(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y) is True:
            debuff_use_time = time.time()
            skill_used = True
      # dd_use_delay = random.randint(40,50)/100 + int(not self.desecrate is None) * 0.5
      dd_use_delay = self.detonate_dead.getCastTime() * 2 # + int(not self.desecrate is None) * 0.5
      print(f'ddusedelay {dd_use_delay}')
      if skill_used is False and self.last_attack_time + self.attack_delay < time.time():
        print(f'tapping dd')
        self.detonate_dead.press()
        time.sleep(random.randint(5,12)/100)
        self.detonate_dead.release()
        self.last_attack_time = time.time()
        # continue
      print('dd kiting')
      point = self.poe_bot.game_data.terrain.pointToRunAround(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, kite_distance+random.randint(-1,1), check_if_passable=True, reversed=reversed_run)
      mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
      if current_time  > start_time + max_kill_time_sec:
        print(f'exceed time min_hold_duration {max_kill_time_sec}')
        break
    return res
class VenomGyreBuild(Build):
  '''
  venom gyre
  '''
  poe_bot: PoeBot
  def __init__(self,poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot

    self.venom_gyre_last_hold_time = 0
    self.whirling_blades_casts_after_vg = 0

    self.vaal_venom_gyre = None # "vaal_snapping_adder"
    self.venom_gyre = None # name: "snapping_adder" animated_property_metadata "a":"Metadata/Effects/Spells/frost_bolt/sml_maelstrom.ao"
    self.venom_gyre_manacost = 0
    self.whirling_blades = None # name: "blade_flurry" animated_property_metadata "a":"Metadata/Effects/Spells/frost_bolt/sml_maelstrom.ao"
    self.whirling_blades_manacost = 0
    self.blood_rage = None # "blood_rage"
    self.berserk = None # name: "berserk" animated_property_metadata "a":"Metadata/Effects/Spells/frost_bolt/sml_maelstrom.ao"
    self.totem = None # name: "totem" animated_property_metadata "a":"Metadata/Effects/Spells/frost_bolt/sml_maelstrom.ao"

    self.swapWeaponsIfNeeded()
    skills_data = poe_bot.backend.getSkillBar()
    skills_on_panel = skills_data['i_n']

    for skill_index in range(len(skills_data['i_n'])):
      skill = skills_data['i_n'][skill_index]
      if skill == '':
        continue
      print(skill, skill_index)
      if skill == 'venom_gyre':
        self.venom_gyre = Skill(poe_bot=poe_bot, skill_index=skill_index, display_name='venom_gyre')
        self.venom_gyre_manacost = next( (sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if 'ManaCost' in sd.keys()), 0)
        if self.venom_gyre_manacost != 0:
          self.venom_gyre_manacost = self.venom_gyre_manacost.get('ManaCost', 0)
        print(f'venom_gyre_manacost cost {self.venom_gyre_manacost}')
      elif skill == 'whirling_blades':
        self.whirling_blades = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, display_name='whirling_blades', min_delay=0.3, can_extend_path=False)
        self.whirling_blades_manacost = next( (sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if 'ManaCost' in sd.keys()), 0)
        if self.whirling_blades_manacost != 0:
          self.whirling_blades_manacost = self.whirling_blades_manacost.get('ManaCost', 0)
          print(f'whirling_blades_manacost cost {self.whirling_blades_manacost}')

      elif skill == 'blood_rage':
        self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/10, display_name="blood_rage")
      elif skill == 'berserk':
        self.berserk = Skill(poe_bot=poe_bot, skill_index=skill_index, display_name='berserk')
      elif skill == 'totem':
        self.totem = Skill(poe_bot=poe_bot, skill_index=skill_index, display_name='totem')
      elif skill == "vaal_venom_gyre":
        self.vaal_venom_gyre = None
        self.vaal_venom_gyre = Skill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill)
    if not self.whirling_blades:
      self.poe_bot.raiseLongSleepException('whirling blades skill is not on the panel')
    elif not self.venom_gyre:
      self.poe_bot.raiseLongSleepException('venom gyre skill is not on the panel')
    
    if self.venom_gyre_manacost != 0:
      self.whirling_blades.mana_cost = self.whirling_blades_manacost + self.venom_gyre_manacost
      self.whirling_blades.min_mana_to_use = self.whirling_blades_manacost + self.venom_gyre_manacost
      print(f'whirling_blades_manacost final cost {self.whirling_blades.mana_cost}')


    super().__init__(poe_bot)
  def useBuffs(self):
    poe_bot = self.poe_bot
    if self.blood_rage is not None:
      if 'blood_rage' not in poe_bot.game_data.player.buffs and poe_bot.game_data.player.life.health.getPercentage() > 0.7:
        if random.randint(0,3) == 0:
          return False
        return self.blood_rage.use()
      # if 'player_aura_cold_damage' not in poe_bot.game_data.player.buffs:
        # self.hatred_blessing.use()
  def useFlasks(self):
    self.auto_flasks.useFlasks()
  def usualRoutine(self, mover:Mover = None):
    poe_bot = self.poe_bot
    used_flasks = self.auto_flasks.useFlasks()
    search_angle = 90
    search_angle_half = search_angle/2
    attack_delay_seconds = 2
    min_whirling_blade_casts = 4
    # if we are moving
    if mover is not None:
      if used_flasks != True: self.useBuffs()
      if time.time() > self.venom_gyre_last_hold_time + attack_delay_seconds or self.whirling_blades_casts_after_vg > min_whirling_blade_casts:
        # check enemies in ROI
        nearby_enemies = list(filter(lambda e: e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
        if nearby_enemies:
          if self.vaal_venom_gyre: self.vaal_venom_gyre.use(wait_for_execution=False)
          print(f'nearby_enemies: {nearby_enemies}')
          p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
          p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
          nearby_enemies = list(filter(lambda e: getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < search_angle_half, nearby_enemies))
          enemy_in_sector = nearby_enemies
          if enemy_in_sector:
            print(f'holding vg')
            list(map(lambda e:e.calculateValueForAttack(15), nearby_enemies))
            nearby_enemies.sort(key=lambda e: e.attack_value, reverse=True)
            most_valuable_entity = nearby_enemies[0]
            grid_position_x, grid_position_y = most_valuable_entity.grid_position.x, most_valuable_entity.grid_position.y
            screen_pos_x, screen_pos_y = poe_bot.getPositionOfThePointOnTheScreen(y = grid_position_y, x = grid_position_x)
            screen_pos_x, screen_pos_y = poe_bot.convertPosXY(x=screen_pos_x, y = screen_pos_y)
            start_sleep_time = time.time()
            self.venom_gyre.press()
            poe_bot.bot_controls.mouse.setPosSmooth(screen_pos_x, screen_pos_y, wait_till_executed=False)
            sleep_time = random.randint(40,60)/100
            for i in range(100):
              current_time = time.time()
              if current_time > start_sleep_time + sleep_time:
                break
              valuable_entity = next( (e for e in poe_bot.game_data.entities.attackable_entities if e.id == most_valuable_entity.id), None)
              if valuable_entity is None:
                if not current_time+0.1 > start_sleep_time + sleep_time:
                  time.sleep(0.1)
                break
              else:
                grid_position_x, grid_position_y = valuable_entity.grid_position.x, valuable_entity.grid_position.y
              screen_pos_x, screen_pos_y = poe_bot.getPositionOfThePointOnTheScreen(y = grid_position_y, x = grid_position_x)
              screen_pos_x, screen_pos_y = poe_bot.convertPosXY(x=screen_pos_x, y = screen_pos_y)
              poe_bot.bot_controls.mouse.setPosSmooth(screen_pos_x, screen_pos_y, wait_till_executed=False)
              poe_bot.refreshInstanceData()
            self.venom_gyre.release()
            self.venom_gyre_last_hold_time = time.time()
            print(f'releasing vg')
            self.whirling_blades_casts_after_vg = 0
            return True
      # use movement skill
      if mover.distance_to_target > 50:
        if self.whirling_blades.use(mover.nearest_passable_point[0], mover.nearest_passable_point[1], wait_for_execution=False) is True:
          self.whirling_blades_casts_after_vg += 1
          return True
    else: # if we are staying and waiting for smth
      self.staticDefence()
    return False
  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = random.randint(200,300)/10, *args, **kwargs):
    print(f'#VenomGyreBuild.killUsual {entity}')
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls

    entity_to_kill_id = entity.id

    min_distance = 45 # distance which is ok to start attacking
    min_hold_duration = max_kill_time_sec
    last_whirling_blades_use_time = time.time()
    whirling_blades_delay = 0.4

    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print('cannot find desired entity to kill')
      return True
    print(f'entity_to_kill {entity_to_kill}')
    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual')


    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    if entity_to_kill.isInLineOfSight() is False:
      print('entity_to_kill.isInLineOfSight() is False')
      return False

    used_flasks = self.auto_flasks.useFlasks()
    start_time = time.time()
    poe_bot.last_action_time = 0
    res = True 
    self.venom_gyre.press()
    entity_to_kill.hover(wait_till_executed=False)
    last_whirling_blades_use_time = time.time()
    while True:
      poe_bot.refreshInstanceData()
      used_flasks = self.auto_flasks.useFlasks()
      if used_flasks != True: self.useBuffs()
      if self.vaal_venom_gyre: self.vaal_venom_gyre.use(wait_for_execution=False)
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print('cannot find desired entity to kill')
        break
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break
      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        res = False
        break
      current_time = time.time()

      entity_to_kill.hover(wait_till_executed=False)
      if current_time > last_whirling_blades_use_time + whirling_blades_delay:
        self.whirling_blades.tap()
        last_whirling_blades_use_time = time.time()
        # self.whirling_blades.use(updated_entity=entity_to_kill)
      
      if current_time  > start_time + min_hold_duration:
        print(f'exceed time min_hold_duration {min_hold_duration}')
        break
    self.venom_gyre.release()
    return res
  def prepareToFight(self, entity: Entity):
    print(f'vg.preparetofight call {time.time()}')
    poe_bot = self.poe_bot
    bot_controls = self.poe_bot.bot_controls
    self.venom_gyre.press()
    entity.hover(wait_till_executed=False)
    start_hold_time = time.time()
    min_hold_duration = random.randint(40,60)/100
    while True:
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      entity.hover(update_screen_pos=True, wait_till_executed=False)
      if time.time() > start_hold_time + min_hold_duration:
        break
    self.venom_gyre.release()
class CastOnStunPf(Build):
  '''
  CastOnStunPf
  '''
  poe_bot: PoeBot
  def __init__(self,poe_bot: PoeBot) -> None:
    self.brand_last_use_time = 0

    self.poe_bot = poe_bot


    self.blood_rage = None # "blood_rage"
    self.town_portal = None # 'town_portal'
    self.movement_skill = None # "new_new_shield_charge"
    self.plague_bearer = None # "corrosive_shroud"
    # self.swapWeaponsIfNeeded()
    skills_data = poe_bot.backend.getSkillBar()
    skills_on_panel = skills_data['i_n']
    #TODO
    for skill_index in range(len(skills_data['i_n'])):
      skill = skills_data['i_n'][skill_index]
      if skill == '':
        continue
      print(skill, skill_index)
      if skill == 'blood_rage':
        self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/10, display_name="blood_rage")
      elif skill == 'town_portal':
        self.town_portal = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1,5)/100, display_name="town_portal", min_mana_to_use=0)
      elif skill == "new_new_shield_charge" or skill == "blade_flurry":
        self.movement_skill = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill, min_delay=random.randint(30,50)/100)
      elif skill == 'corrosive_shroud':
        self.plague_bearer = PlagueBearer(poe_bot=poe_bot, skill_index=skill_index, display_name=skill)
      
      else:
        pass
    super().__init__(poe_bot)
    self.auto_flasks = AutoFlasks(poe_bot=poe_bot, pathfinder=True)

  def useBuffs(self):
    poe_bot = self.poe_bot
    if self.blood_rage is not None:
      if 'blood_rage' not in poe_bot.game_data.player.buffs:
        if self.blood_rage.use() is True:
          return True
    return False

  def usualRoutine(self, mover:Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()
    # if we are moving
    if mover is not None:
      self.useBuffs()
      nearby_enemies = list(filter(lambda e: e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      print(f'nearby_enemies: {nearby_enemies}')
      really_close_enemies = list(filter(lambda e: e.distance_to_player < 20,nearby_enemies))
      min_delay = 3
      if len(really_close_enemies) != 0:
        min_delay = 2
        if self.plague_bearer:
          print(f'can turn plague bearer')
          self.plague_bearer.turnOn()
      # use movement skill
      if self.movement_skill and mover.distance_to_target > 50:
        if self.movement_skill.use(mover.grid_pos_to_step_x, mover.grid_pos_to_step_y, wait_for_execution=False) is True:
          return True
    
    # if we are staying and waiting for smth
    else:
      self.staticDefence()

    return False
  
  def prepareToFight(self, entity: Entity):
    return True
  
  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = random.randint(200,300)/10, *args, **kwargs):
    print(f'#build.killUsual {entity}')
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    mover = self.mover

    entity_to_kill_id = entity.id
    debuff_use_time = 0

    self.auto_flasks.useFlasks()
    
    min_distance = 40 # distance which is ok to start attacking
    keep_distance = 15 # if our distance is smth like this, kite

    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print('cannot find desired entity to kill')
      return True

    print(f'entity_to_kill {entity_to_kill}')
    
    if entity_to_kill.life.health.current < 0:
      print('entity is dead')
      return True

    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual')
    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    
    if entity_to_kill.isInLineOfSight() is False:
      print('entity_to_kill.isInLineOfSight() is False')
      return False


    start_time = time.time()
    poe_bot.last_action_time = 0
    kite_distance = random.randint(18,22)
    res = True
    reversed_run = random.choice([True, False])
    while True:
      skill_used = False
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print('cannot find desired entity to kill')
        break
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break
      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        break
      current_time = time.time()
      if self.useBuffs() is True:
        skill_used = True

      print('kiting')
      point = self.poe_bot.game_data.terrain.pointToRunAround(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, kite_distance+random.randint(-1,1), check_if_passable=True, reversed=reversed_run)
      mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
      if current_time  > start_time + max_kill_time_sec:
        print('exceed time')
        break
    return res
  

class HitBasedDeadeye(Build):
  '''
  HitBasedDeadeye
  '''
  poe_bot: PoeBot
  def __init__(self,poe_bot: PoeBot) -> None:
    self.brand_last_use_time = 0
    self.poe_bot = poe_bot
    self.attacking_skill = None
    self.ballista_skill = None
    self.blood_rage = None
    self.movement_skill = None
    self.debuff = None
    self.auras = []
    skills_data = poe_bot.backend.getSkillBar()
    for skill_index in range(len(skills_data['i_n'])):
      skill = skills_data['i_n'][skill_index]

      if skill == '':
        continue
      print(skill, skill_index)
      if skill == 'blood_rage':
        self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/10, display_name="blood_rage")
      elif skill == 'lightning_arrow' or skill == "elemental_hit_alt_x":
        self.attacking_skill = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1,5)/100, display_name=skill, min_mana_to_use=0)
      elif skill == "shrapnel_ballista_totem":
        self.ballista_skill = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(15,18)/10, display_name=skill, min_mana_to_use=0)
      elif skill == "quick_dodge" or skill == "flame_dash":
        self.movement_skill = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill, min_delay=random.randint(30,50)/100)
      elif skill == 'despair':
        self.debuff = AreaSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill)
    self.attacking_skill.overriden_cast_time = 0.5
    super().__init__(poe_bot)
    self.auto_flasks = AutoFlasks(poe_bot=poe_bot)
  def useBuffs(self):
    poe_bot = self.poe_bot
    if self.blood_rage is not None:
      if 'blood_rage' not in poe_bot.game_data.player.buffs and poe_bot.game_data.player.life.health.current / poe_bot.game_data.player.life.health.total > 0.7:
        if self.blood_rage.use() is True:
          return True

    return False
  def useFlasks(self):
    self.auto_flasks.useFlasks()
  def usualRoutine(self, mover:Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()
    # if we are moving
    if mover is not None:
      self.useBuffs()
      search_angle_half = 45
      hold_duration = random.randint(7,14)/10
      min_hold_duration = random.randint(15,25)/100
      nearby_enemies = list(filter(lambda e: e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      print(f'nearby_enemies: {nearby_enemies}')
      entities_to_hold_skill_on:list[Entity] = []
      if nearby_enemies:
        for iiii in range(1):
          time_now = time.time()
          nearby_visible_enemies = list(filter(lambda e: e.isInLineOfSight(), nearby_enemies))
          if not nearby_visible_enemies:
            break
          # didnt attack for a long time
          if self.attacking_skill.last_use_time + random.randint(20,30)/10 < time_now:
            print(f'didnt attack for a long time')
            entities_to_hold_skill_on = sorted(nearby_visible_enemies, key=lambda e: e.distance_to_player)
            min_hold_duration = 0.1
            break
          # if surrounded
          really_close_enemies = list(filter(lambda e: e.distance_to_player < 20, nearby_visible_enemies))
          if len(really_close_enemies) > 5:
            print(f'surrounded')
            entities_to_hold_skill_on = really_close_enemies
            break


          # on the way
          if self.attacking_skill.last_use_time + random.randint(10,15)/10 < time_now:
            p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
            p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
            enemies_in_sector = list(filter(lambda e: getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < search_angle_half, nearby_visible_enemies))
            if enemies_in_sector:
              print(f'on the way')
              min_hold_duration = 0.1
              entities_to_hold_skill_on = enemies_in_sector
          break
      if entities_to_hold_skill_on:
        entities_to_hold_skill_on_ids = list(map(lambda e: e.id, entities_to_hold_skill_on))
        hold_start_time = time.time()
        self.attacking_skill.last_use_time = hold_start_time
        self.attacking_skill.press()
        while time.time() - hold_duration < hold_start_time:
          poe_bot.refreshInstanceData()
          self.useFlasks()
          entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id in entities_to_hold_skill_on_ids), None)
          if entity_to_kill:
            entity_to_kill.hover()
          else:
            if not time.time() + 0.1 > hold_start_time + min_hold_duration:
              time.sleep(0.1)
            break
        self.attacking_skill.release()        
        return True
      # use movement skill
      if self.movement_skill and mover.distance_to_target > 50:
        if self.movement_skill.use(mover.grid_pos_to_step_x, mover.grid_pos_to_step_y, wait_for_execution=False) is True:
          return True
    # if we are staying and waiting for smth
    else:
      self.staticDefence()
    return False
  def prepareToFight(self, entity: Entity):
    print(f'frenzyfrostblink.preparetofight call {time.time()}')
    for i in range(random.randint(2,3)):
      self.poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      updated_entity = next( (e for e in self.poe_bot.game_data.entities.all_entities if e.id == entity.id), None)
      if updated_entity is None:
        break

      if self.ballista_skill:
        self.ballista_skill.use(updated_entity=updated_entity)
    return True
  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = random.randint(200,300)/10, *args, **kwargs):
    print(f'#build.killUsual {entity}')
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    mover = self.mover
    self.attacking_skill.last_use_time = 0


    entity_to_kill_id = entity.id
    self.useFlasks()
    min_distance = 40 # distance which is ok to start attacking
    keep_distance = 15 # if our distance is smth like this, kite

    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print('cannot find desired entity to kill')
      return True

    print(f'entity_to_kill {entity_to_kill}')
    
    if entity_to_kill.life.health.current < 0:
      print('entity is dead')
      return True

    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual')
    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    
    if entity_to_kill.isInLineOfSight() is False:
      print('entity_to_kill.isInLineOfSight() is False')
      return False
    start_time = time.time()
    pos_x, pos_y = entity_to_kill.location_on_screen.x, entity_to_kill.location_on_screen.y
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y) 
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    if self.ballista_skill: 
      self.ballista_skill.use(updated_entity=entity_to_kill)
      self.ballista_skill.last_use_time = time.time()
    poe_bot.last_action_time = 0
    kite_distance = random.randint(18,22)
    res = True
    reversed_run = random.choice([True, False])
    while True:
      skill_used = False
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print('cannot find desired entity to kill')
        break
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break
      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        break
      current_time = time.time()
      self.useBuffs()
      skill_use_delay = random.randint(18,20)/10
      print(f'skill_use_delay {skill_use_delay}')
      if self.ballista_skill and skill_used is False and self.ballista_skill.last_use_time + skill_use_delay < time.time():
        self.ballista_skill.use(updated_entity=entity_to_kill)
        skill_used = True
      if skill_used is False and self.attacking_skill.last_use_time + skill_use_delay < time.time():
        entity_to_kill.hover()
        hold_duration = random.randint(100,140)/100
        hold_start_time = time.time()
        self.attacking_skill.last_use_time = hold_start_time
        self.attacking_skill.press()
        while time.time() - hold_duration < hold_start_time:
          poe_bot.refreshInstanceData()
          self.auto_flasks.useFlasks()
          entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
          if entity_to_kill:
            entity_to_kill.hover()
          else:
            break
        self.attacking_skill.release()        
        skill_used = True
        continue
      if not entity_to_kill:
        break
      print('kiting')
      point = self.poe_bot.game_data.terrain.pointToRunAround(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, kite_distance+random.randint(-1,1), check_if_passable=True, reversed=reversed_run)
      mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
      if current_time  > start_time + max_kill_time_sec:
        print('exceed time')
        break
    return res
class CfKineticBlastChampion(Build):
  # https://www.youtube.com/watch?app=desktop&v=kh7fTPLn5gA
  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.kinetic_blast = None # "kinetic_blast"
    self.reap = None # "reap" # if description {SkillIsTriggered: 1} -> can be selfcasted
    self.vaal_reap = None # "reap" # if description {SkillIsTriggered: 1} -> can be selfcasted
    self.corrupting_fever = None # "corrupting_fever" description {LifeCost: 921}  # buff name "blood_surge" 
    self.corrupting_fever_life_cost:int = None
    self.corrupting_fever
    self.blood_rage = None # "blood_rage"
    self.movement_skill = None # "new_new_shield_charge"
    self.instant_movement_skill = None # "flame_dash"
    self.attacking_skill = None

    for skill_index in range(len(self.poe_bot.game_data.skills.internal_names)):
      skill_name = self.poe_bot.game_data.skills.internal_names[skill_index]
      if skill_name == '': continue
      print(skill_name, skill_index)
      if skill_name == 'blood_rage':
        self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/10, display_name=skill_name)
      elif skill_name == "corrupting_fever":
        self.corrupting_fever = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=0.4, display_name=skill_name)
        self.corrupting_fever_life_cost = next( (sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if 'LifeCost' in sd.keys()))['LifeCost']
        print(f'corrupting fever cost {self.corrupting_fever_life_cost}')
      elif skill_name == "reap":
        triggerable = next( (sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if 'SkillIsTriggered' in sd.keys()), None)
        if not triggerable:
          self.reap = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1,5)/100, display_name=skill_name, min_mana_to_use=0)
      elif skill_name == "kinetic_blast":
        self.kinetic_blast = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1,5)/100, display_name=skill_name, min_mana_to_use=0)
      elif skill_name == "new_new_shield_charge":
        self.movement_skill = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill_name, min_delay=random.randint(30,50)/100)
    
    if self.reap:
      print('will use reap as main dmg skill')
      self.attacking_skill = self.reap
    else:
      print('kinetic blast as main dmg skill')
      self.attacking_skill = self.kinetic_blast

    super().__init__(poe_bot)
  def useBuffs(self):
    poe_bot = self.poe_bot
    if self.blood_rage is not None:
      if 'blood_rage' not in poe_bot.game_data.player.buffs and poe_bot.game_data.player.life.health.current / poe_bot.game_data.player.life.health.total > 0.7:
        self.blood_rage.use()
        return True
    if "blood_surge" not in poe_bot.game_data.player.buffs: # 
      self.corrupting_fever.use()
      return True
    if "adrenaline" not in poe_bot.game_data.player.buffs and (poe_bot.game_data.player.life.health.current - self.corrupting_fever_life_cost) / poe_bot.game_data.player.life.health.total > 0.10:
      self.corrupting_fever.use()
      return True
    return False
  def usualRoutine(self, mover:Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()
    # if we are moving
    if mover is not None:
      self.useBuffs()

      search_angle_half = 45

      hold_duration = random.randint(7,14)/10
      min_hold_duration = random.randint(15,25)/100
      
      nearby_enemies = list(filter(lambda e: e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      print(f'nearby_enemies: {nearby_enemies}')
      
      entities_to_hold_skill_on:list[Entity] = []
      if nearby_enemies:
        for iiii in range(1):
          time_now = time.time()
          nearby_visible_enemies = list(filter(lambda e: e.isInLineOfSight(), nearby_enemies))
          if not nearby_visible_enemies:
            break
        
          # didnt attack for a long time
          if self.attacking_skill.last_use_time + random.randint(20,30)/10 < time_now:
            print(f'didnt attack for a long time')
            entities_to_hold_skill_on = sorted(nearby_visible_enemies, key=lambda e: e.distance_to_player)
            min_hold_duration = 0.1
            break

          # if surrounded
          really_close_enemies = list(filter(lambda e: e.distance_to_player < 20, nearby_visible_enemies))
          if len(really_close_enemies) > 5:
            print(f'surrounded')
            entities_to_hold_skill_on = really_close_enemies
            break


          # on the way
          if self.attacking_skill.last_use_time + random.randint(10,15)/10 < time_now:
            p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
            p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
            enemies_in_sector = list(filter(lambda e: getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < search_angle_half, nearby_visible_enemies))
            if enemies_in_sector:
              print(f'on the way')
              min_hold_duration = 0.1
              entities_to_hold_skill_on = enemies_in_sector
          break
      if entities_to_hold_skill_on:
        entities_to_hold_skill_on_ids = list(map(lambda e: e.id, entities_to_hold_skill_on))
        hold_start_time = time.time()
        self.attacking_skill.last_use_time = hold_start_time
        self.attacking_skill.press()
        while time.time() - hold_duration < hold_start_time:
          poe_bot.refreshInstanceData()
          self.auto_flasks.useFlasks()
          entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id in entities_to_hold_skill_on_ids), None)
          if entity_to_kill:
            entity_to_kill.hover()
          else:
            if not time.time() + 0.1 > hold_start_time + min_hold_duration:
              time.sleep(0.1)
            break
        self.attacking_skill.release()        
        return True
      # use movement skill
      if self.movement_skill and mover.distance_to_target > 50:
        instant_movement_used = False
        if self.instant_movement_skill:
          instant_movement_used = self.instant_movement_skill.use(mover.grid_pos_to_step_x, mover.grid_pos_to_step_y, wait_for_execution=False)
          if instant_movement_used:
            return True
        if self.movement_skill.use(mover.grid_pos_to_step_x, mover.grid_pos_to_step_y, wait_for_execution=False) is True:
          return True
    # if we are staying and waiting for smth
    else:
      self.staticDefence()
    return False
  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = random.randint(200,300)/10, *args, **kwargs):
    print(f'#build.killUsual {entity}')
    poe_bot = self.poe_bot
    mover = self.mover
    self.attacking_skill.last_use_time = 0
    entity_to_kill_id = entity.id
    self.auto_flasks.useFlasks()
    
    min_distance = 40 # distance which is ok to start attacking
    keep_distance = 15 # if our distance is smth like this, kite

    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print('cannot find desired entity to kill')
      return True
    print(f'entity_to_kill {entity_to_kill}')
    if entity_to_kill.life.health.current < 0:
      print('entity is dead')
      return True
    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual')
    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    if entity_to_kill.isInLineOfSight() is False:
      print('entity_to_kill.isInLineOfSight() is False')
      return False


    start_time = time.time()
    entity_to_kill.hover()
    poe_bot.last_action_time = 0
    kite_distance = random.randint(18,22)
    res = True
    reversed_run = random.choice([True, False])
    while True:
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print('cannot find desired entity to kill')
        break
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break
      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        break
      current_time = time.time()
      self.useBuffs()
      # dd_use_delay = random.randint(40,50)/100 + int(not self.desecrate is None) * 0.5
      skill_use_delay = random.randint(18,20)/10
      print(f'skill_use_delay {skill_use_delay}')
      if self.attacking_skill.last_use_time + skill_use_delay < time.time():
        hold_duration = random.randint(100,140)/100
        entity_to_kill.hover()
        hold_start_time = time.time()
        self.attacking_skill.last_use_time = hold_start_time
        self.attacking_skill.press()
        while time.time() - hold_duration < hold_start_time:
          poe_bot.refreshInstanceData()
          self.auto_flasks.useFlasks()
          entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
          if entity_to_kill:
            entity_to_kill.hover()
          else:
            break
        self.attacking_skill.release()        
        continue
      if not entity_to_kill:
        break
      print('kiting')
      point = self.poe_bot.game_data.terrain.pointToRunAround(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, kite_distance+random.randint(-1,1), check_if_passable=True, reversed=reversed_run)
      instant_movement_used = False
      if self.instant_movement_skill:
        instant_movement_used = self.instant_movement_skill.use(point[0], point[1], wait_for_execution=False)
      if instant_movement_used:
        print(f'used instant movement skill, continuing to attack')
        self.attacking_skill.last_use_time = 0
      else:
        mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
      if current_time  > start_time + max_kill_time_sec:
        print('exceed time')
        break
    return res
class EaBallistasEle(Build):
  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.ballista_totem = None # "explosive_arrow_weapon" # "Metadata/Monsters/Totems/ShotgunTotem@lvl" - path
    self.ballista_totem_max_count = None
    self.ballista_totem_duration_secs = None
    self.arcanist_brand = None # "arcanist_brand"
    self.blood_rage = None
    self.frenzy = None # frenzy
    self.have_frenzy = False
    self.movement_skill = None # "flame_dash"
    self.vaal_molten_shell = None
    for skill_index in range(len(self.poe_bot.game_data.skills.internal_names)):
      skill_name = self.poe_bot.game_data.skills.internal_names[skill_index]
      if skill_name == '': continue
      print(skill_name, skill_index)
      if skill_name == 'blood_rage':
        self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/10, display_name=skill_name)
      elif skill_name == "arcanist_brand":
        self.arcanist_brand_duration = next( (sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if 'SkillEffectDuration' in sd.keys()))['SkillEffectDuration']
        self.arcanist_brand = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=self.arcanist_brand_duration*0.75, display_name=skill_name)
        print(f'{skill_name} duration {self.arcanist_brand_duration}')
      elif skill_name == "frenzy":
        self.have_frenzy = True
        triggerable = next( (sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if 'SkillIsTriggered' in sd.keys()), None)
        if not triggerable:
          self.frenzy = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1,5)/100, display_name=skill_name, min_mana_to_use=0)
          print('frenzy is selfcast')
        else:
          print(f'frenzy is triggerable')
      elif skill_name == "explosive_arrow":
        self.ballista_totem = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1,5)/100, display_name=skill_name, min_mana_to_use=0)
        self.ballista_totem_max_count = next( (sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if 'NumberOfTotemsAllowed' in sd.keys()))['NumberOfTotemsAllowed']
        self.ballista_totem_duration_secs = next( (sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if 'TotemDuration' in sd.keys()))['TotemDuration']/1000
        print(f'explosive arrow ballista max totem count {self.ballista_totem_max_count} duration {self.ballista_totem_duration_secs}')
      elif skill_name == "flame_dash":
        self.movement_skill = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill_name, min_delay=random.randint(30,50)/100)
    # if self.frenzy or self.have_frenzy:
    #   print(f'have frenzy, wont use blood rage')
    #   self.blood_rage = None
    super().__init__(poe_bot)
  def useBuffs(self):
    poe_bot = self.poe_bot
    if self.blood_rage is not None:
      if 'blood_rage' not in poe_bot.game_data.player.buffs and poe_bot.game_data.player.life.health.current / poe_bot.game_data.player.life.health.total > 0.7:
        if self.blood_rage.use() is True:
          return True
    if self.poe_bot.combat_module.aura_manager.activateBlessingsIfNeeded():
      return True
    return False
  def usualRoutine(self, mover:Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()
    if mover is not None:
      self.useBuffs()
      frenzy_delay = random.randint(40,70)/10
      totem_delay = random.randint(40,70)/100
      nearby_enemies_on_screen = list(filter(lambda e: e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      print(f'nearby_enemies_on_screen: {nearby_enemies_on_screen}')
      if nearby_enemies_on_screen:
        if self.ballista_totem.last_use_time + totem_delay < time.time():
          alive_totems_nearby = list(filter(lambda e: e.life.health.current != 0 and not e.is_hostile and e.distance_to_player < 50 and "Metadata/Monsters/Totems/ShotgunTotem" in e.path , self.poe_bot.game_data.entities.all_entities))
          print(f'nearby totems {alive_totems_nearby}')
          if len(alive_totems_nearby) < 2:
            self.ballista_totem.use()
            return True
        if self.frenzy and self.frenzy.last_use_time + frenzy_delay < time.time():
          nearby_visible_enemies = list(filter(lambda e: e.isInLineOfSight(), nearby_enemies_on_screen))
          if nearby_visible_enemies:
            nearby_visible_enemies = sorted(nearby_visible_enemies, key=lambda e: e.distance_to_player)
            self.frenzy.use(updated_entity=nearby_visible_enemies[0])
            return True

      if self.movement_skill and mover.distance_to_target > 50:
        if self.movement_skill.use(mover.grid_pos_to_step_x, mover.grid_pos_to_step_y, wait_for_execution=False) is True:
          return True
    else:
      self.staticDefence()
    return False
  def prepareToFight(self, entity: Entity):
    print(f'#TODO hold till spawn max amount of totems, and use debuff skill as well')
    self.poe_bot.refreshInstanceData()
    self.auto_flasks.useFlasks()
    updated_entity = next( (e for e in self.poe_bot.game_data.entities.all_entities if e.id == entity.id), None)
    # if updated_entity is None:
    #   break
    self.ballista_totem.use(updated_entity=updated_entity)
    self.useBuffs()
    return True
  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = random.randint(200,300)/10, *args, **kwargs):
    print(f'#build.killUsual {entity}')
    poe_bot = self.poe_bot
    mover = self.mover
    entity_to_kill_id = entity.id
    debuff_use_time = 0
    self.auto_flasks.useFlasks()
    min_distance = 40 # distance which is ok to start attacking
    keep_distance = 15 # if our distance is smth like this, kite
    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print('cannot find desired entity to kill')
      return True
    print(f'entity_to_kill {entity_to_kill}')
    if entity_to_kill.life.health.current < 0:
      print('entity is dead')
      return True
    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual')
    if is_strong is True and self.vaal_molten_shell:
      self.vaal_molten_shell.use()
    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    if entity_to_kill.isInLineOfSight() is False:
      print('entity_to_kill.isInLineOfSight() is False')
      return False
    start_time = time.time()
    entity_to_kill.hover()
    self.ballista_totem.use(updated_entity=entity_to_kill)
    poe_bot.last_action_time = 0
    kite_distance = random.randint(18,22)
    res = True
    reversed_run = random.choice([True, False])
    while True:
      skill_used = False
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print('cannot find desired entity to kill')
        break
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break
      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        break
      current_time = time.time()
      if self.useBuffs() is True:
        skill_used = True
      if self.arcanist_brand:
        if current_time > start_time + 2:
          if current_time > debuff_use_time + 4:
            if self.arcanist_brand.use(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y) is True:
              debuff_use_time = time.time()
              skill_used = True
      totem_use_delay = random.randint(25,40)/100
      print(f'totem_use_delay {totem_use_delay}')
      if skill_used is False and self.ballista_totem.last_use_time + totem_use_delay < time.time():
        alive_totems_nearby = list(filter(lambda e: e.life.health.current != 0 and not e.is_hostile and e.distance_to_player < 50 and "Metadata/Monsters/Totems/ShotgunTotem" in e.path , self.poe_bot.game_data.entities.all_entities))
        print(f'nearby totems {alive_totems_nearby}')
        if len(alive_totems_nearby) < self.ballista_totem_max_count:
          self.ballista_totem.use(updated_entity=entity_to_kill)
          skill_used = True
      frenzy_delay = random.randint(30,50)/10
      if self.frenzy and not skill_used and self.frenzy.last_use_time + frenzy_delay < time.time():
        self.frenzy.use(updated_entity=entity_to_kill)
        # continue
      
      print('kiting')
      point = self.poe_bot.game_data.terrain.pointToRunAround(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, kite_distance+random.randint(-1,1), check_if_passable=True, reversed=reversed_run)
      mover.move(grid_pos_x = point[0], grid_pos_y = point[1])




      if current_time  > start_time + max_kill_time_sec:
        print('exceed time')
        break
    return res
class ScourgeArrowPf(Build):
  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.ballista_totem = None # "explosive_arrow_weapon" # "Metadata/Monsters/Totems/ShotgunTotem@lvl" - path
    self.ballista_totem_max_count = None
    self.ballista_totem_duration_secs = None
    self.arcanist_brand = None # "arcanist_brand"
    self.blood_rage = None
    self.frenzy = None # frenzy
    self.have_frenzy = False
    self.movement_skill = None # "flame_dash"
    self.movement_skill_last_use_time = 0
    self.vaal_molten_shell = None
    for skill_index in range(len(self.poe_bot.game_data.skills.internal_names)):
      skill_name = self.poe_bot.game_data.skills.internal_names[skill_index]
      if skill_name == '': continue
      print(skill_name, skill_index)
      if skill_name == 'blood_rage':
        self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/10, display_name=skill_name)
      elif skill_name == "arcanist_brand":
        self.arcanist_brand_duration = next( (sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if 'SkillEffectDuration' in sd.keys()))['SkillEffectDuration']
        self.arcanist_brand = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=self.arcanist_brand_duration*0.75, display_name=skill_name)
        print(f'{skill_name} duration {self.arcanist_brand_duration}')
      elif skill_name == "frenzy":
        self.have_frenzy = True
        triggerable = next( (sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if 'SkillIsTriggered' in sd.keys()), None)
        if not triggerable:
          self.frenzy = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1,5)/100, display_name=skill_name, min_mana_to_use=0)
          print('frenzy is selfcast')
        else:
          print(f'frenzy is triggerable')
      elif skill_name == "scourge_arrow_alt_x":
        self.ballista_totem = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1,5)/100, display_name=skill_name, min_mana_to_use=0)
        self.ballista_totem_max_count = next( (sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if 'NumberOfTotemsAllowed' in sd.keys()))['NumberOfTotemsAllowed']
        self.ballista_totem_duration_secs = next( (sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if 'TotemDuration' in sd.keys()))['TotemDuration']/1000
        print(f'scourge_arrow_alt_x ballista max totem count {self.ballista_totem_max_count} duration {self.ballista_totem_duration_secs}')
      elif skill_name == "flame_dash":
        self.movement_skill = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill_name, min_delay=random.randint(30,50)/100)
    # if self.frenzy or self.have_frenzy:
    #   print(f'have frenzy, wont use blood rage')
    #   self.blood_rage = None
    super().__init__(poe_bot)
    self.ballista_totem.overriden_cast_time = 0.1
    self.auto_flasks.pathfinder = True
  def useBuffs(self):
    poe_bot = self.poe_bot
    if self.blood_rage is not None:
      if 'blood_rage' not in poe_bot.game_data.player.buffs and poe_bot.game_data.player.life.health.current / poe_bot.game_data.player.life.health.total > 0.7:
        if self.blood_rage.use() is True:
          return True
    if self.poe_bot.combat_module.aura_manager.activateBlessingsIfNeeded():
      return True
    return False
  def usualRoutine(self, mover:Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()
    if mover is not None:
      self.useBuffs()
      frenzy_delay = random.randint(40,70)/10
      totem_delay = random.randint(40,70)/100
      nearby_enemies_on_screen = list(filter(lambda e: e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      print(f'nearby_enemies_on_screen: {nearby_enemies_on_screen}')
      if nearby_enemies_on_screen:
        if self.ballista_totem.last_use_time + totem_delay < time.time():
          alive_totems_nearby = list(filter(lambda e: e.life.health.current != 0 and not e.is_hostile and e.distance_to_player < 50 and "Metadata/Monsters/Totems/ShotgunTotem" in e.path , self.poe_bot.game_data.entities.all_entities))
          print(f'nearby totems {alive_totems_nearby}')
          if len(alive_totems_nearby) < 2:
            self.ballista_totem.use()
            return True
        if self.frenzy and self.frenzy.last_use_time + frenzy_delay < time.time():
          nearby_visible_enemies = list(filter(lambda e: e.isInLineOfSight(), nearby_enemies_on_screen))
          if nearby_visible_enemies:
            nearby_visible_enemies = sorted(nearby_visible_enemies, key=lambda e: e.distance_to_player)
            self.frenzy.use(updated_entity=nearby_visible_enemies[0])
            return True

      if self.movement_skill and mover.distance_to_target > 50:
        if self.movement_skill.use(mover.grid_pos_to_step_x, mover.grid_pos_to_step_y, wait_for_execution=False) is True:
          return True
    else:
      self.staticDefence()
    return False
  def prepareToFight(self, entity: Entity):
    print(f'#TODO hold till spawn max amount of totems, and use debuff skill as well')
    self.poe_bot.refreshInstanceData()
    self.auto_flasks.useFlasks()
    updated_entity = next( (e for e in self.poe_bot.game_data.entities.all_entities if e.id == entity.id), None)
    # if updated_entity is None:
    #   break
    self.ballista_totem.use(updated_entity=updated_entity)
    self.useBuffs()
    return True
  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = random.randint(200,300)/10, *args, **kwargs):
    print(f'#build.killUsual {entity}')
    poe_bot = self.poe_bot
    mover = self.mover
    entity_to_kill_id = entity.id
    debuff_use_time = 0
    self.auto_flasks.useFlasks()
    min_distance = 40 # distance which is ok to start attacking
    keep_distance = 15 # if our distance is smth like this, kite
    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print('cannot find desired entity to kill')
      return True
    print(f'entity_to_kill {entity_to_kill}')
    if entity_to_kill.life.health.current < 0:
      print('entity is dead')
      return True
    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual')
    if is_strong is True and self.vaal_molten_shell:
      self.vaal_molten_shell.use()
    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    if entity_to_kill.isInLineOfSight() is False:
      print('entity_to_kill.isInLineOfSight() is False')
      return False
    start_time = time.time()
    entity_to_kill.hover()
    self.ballista_totem.use(updated_entity=entity_to_kill)
    poe_bot.last_action_time = 0
    kite_distance = random.randint(18,22)
    res = True
    reversed_run = random.choice([True, False])
    while True:
      skill_used = False
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print('cannot find desired entity to kill')
        break
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break
      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        break
      current_time = time.time()
      if self.useBuffs() is True:
        skill_used = True
      if self.arcanist_brand:
        if current_time > start_time + 2:
          if current_time > debuff_use_time + 4:
            if self.arcanist_brand.use(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y) is True:
              debuff_use_time = time.time()
              skill_used = True
      totem_use_delay = random.randint(25,40)/100
      print(f'totem_use_delay {totem_use_delay}')
      if skill_used is False and self.ballista_totem.last_use_time + totem_use_delay < time.time():
        alive_totems_nearby = list(filter(lambda e: e.life.health.current != 0 and not e.is_hostile and e.distance_to_player < 50 and "Metadata/Monsters/Totems/ShotgunTotem" in e.path , self.poe_bot.game_data.entities.all_entities))
        print(f'nearby totems {alive_totems_nearby}')
        if len(alive_totems_nearby) < self.ballista_totem_max_count:
          self.ballista_totem.use(updated_entity=entity_to_kill)
          skill_used = True
      frenzy_delay = random.randint(30,50)/10
      if self.frenzy and not skill_used and self.frenzy.last_use_time + frenzy_delay < time.time():
        self.frenzy.use(updated_entity=entity_to_kill)
        # continue
      
      print('kiting')
      point = self.poe_bot.game_data.terrain.pointToRunAround(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, kite_distance+random.randint(-1,1), check_if_passable=True, reversed=reversed_run)
      mover.move(grid_pos_x = point[0], grid_pos_y = point[1])




      if current_time  > start_time + max_kill_time_sec:
        print('exceed time')
        break
    return res
class HolyRelicTotemNecromancer(Build):
  # https://www.youtube.com/watch?app=desktop&v=kh7fTPLn5gA
  
  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.kinetic_blast = None # "kinetic_blast" "lancing_steel_new_alt_x"
    self.attacking_skill = None
    self.summon_holy_relic = None # summon_holy_relic_alt_x
    self.blood_rage = None # "blood_rage"
    self.movement_skill = None # "new_new_shield_charge"
    self.instant_movement_skill = None # "flame_dash"
    self.current_relics_count = 0

    for skill_index in range(len(self.poe_bot.game_data.skills.internal_names)):
      skill_name = self.poe_bot.game_data.skills.internal_names[skill_index]
      if skill_name == '': continue
      print(skill_name, skill_index)
      if skill_name == 'blood_rage':
        self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/10, display_name=skill_name)
      if skill_name == 'summon_holy_relic_alt_x':
        self.summon_holy_relic = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/10, display_name=skill_name)
        self.max_relics = next( (sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if "NumberOfRelicsAllowed" in sd.keys()))["NumberOfRelicsAllowed"]
        print(f'max relics {self.max_relics}')
      elif skill_name == "kinetic_blast" or skill_name == "lancing_steel_new_alt_x":
        self.attacking_skill = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1,5)/100, display_name=skill_name, min_mana_to_use=0)
      elif skill_name in NON_INSTANT_MOVEMENT_SKILLS:
        self.movement_skill = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill_name, min_delay=random.randint(30,50)/100)
        if skill_name == "whirling_blades":
          self.instant_movement_skill = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill_name, min_delay=random.randint(30,50)/100)

    super().__init__(poe_bot)
  def summonHolyRelicIfNeeded(self):
    relics_around = list(filter(lambda e: e.is_hostile != True and e.render_name == "Holy Relic", self.poe_bot.game_data.entities.all_entities))
    print(f'len(relics_around) {len(relics_around)}')
    if self.current_relics_count != len(relics_around):
      print(f'amount of relics has changed')
      self.current_relics_count = len(relics_around)
      return False
    if len(relics_around) < self.max_relics:
      print(f'need to use relic skill')
      self.summon_holy_relic.use()
      return True
    # relics around = "Holy Relic"
    return False
  def useBuffs(self):
    poe_bot = self.poe_bot
    if self.summonHolyRelicIfNeeded() != False:
      return True
    if self.blood_rage is not None:
      if 'blood_rage' not in poe_bot.game_data.player.buffs and poe_bot.game_data.player.life.health.current / poe_bot.game_data.player.life.health.total > 0.7:
        self.blood_rage.use()
        return True
    return False
  def usualRoutine(self, mover:Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()
    # if we are moving
    if mover is not None:
      self.useBuffs()
      search_angle_half = 45
      min_hold_duration = random.randint(15,25)/100
      
      nearby_enemies = list(filter(lambda e: e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      print(f'nearby_enemies: {nearby_enemies}')
      
      entities_to_hold_skill_on:list[Entity] = []
      if nearby_enemies:
        for iiii in range(1):
          time_now = time.time()
          nearby_visible_enemies = list(filter(lambda e: e.isInLineOfSight(), nearby_enemies))
          if not nearby_visible_enemies:
            break
          # didnt attack for a long time
          if self.attacking_skill.last_use_time + random.randint(20,30)/10 < time_now:
            print(f'didnt attack for a long time')
            entities_to_hold_skill_on = sorted(nearby_visible_enemies, key=lambda e: e.distance_to_player)
            min_hold_duration = 0.1
            break
          # if surrounded
          # really_close_enemies = list(filter(lambda e: e.distance_to_player < 20, nearby_visible_enemies))
          # if len(really_close_enemies) > 5:
          #   print(f'surrounded')
          #   entities_to_hold_skill_on = really_close_enemies
          #   break
          # on the way
          if self.attacking_skill.last_use_time + random.randint(10,15)/10 < time_now:
            p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
            p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
            enemies_in_sector = list(filter(lambda e: getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < search_angle_half, nearby_visible_enemies))
            if enemies_in_sector:
              print(f'on the way')
              min_hold_duration = 0.1
              entities_to_hold_skill_on = enemies_in_sector
          break
      if entities_to_hold_skill_on:
        entities_to_hold_skill_on_ids = list(map(lambda e: e.id, entities_to_hold_skill_on))
        hold_start_time = time.time()
        self.attacking_skill.last_use_time = hold_start_time
        self.attacking_skill.press()
        print(f'self.attacking_skill.getCastTime() {self.attacking_skill.getCastTime()}')
        #  
        hold_duration = random.randint(int(self.attacking_skill.getCastTime() * 120), int(self.attacking_skill.getCastTime() * 160))/100
        print(f'hold_duration {hold_duration}')
        while time.time() - hold_duration < hold_start_time:
          poe_bot.refreshInstanceData()
          self.auto_flasks.useFlasks()
          entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id in entities_to_hold_skill_on_ids), None)
          if entity_to_kill:
            entity_to_kill.hover()
          else:
            if not time.time() + 0.1 > hold_start_time + min_hold_duration:
              time.sleep(0.1)
            break
        self.attacking_skill.release()        
        return True
      # use movement skill
      if self.movement_skill and mover.distance_to_target > 50:
        instant_movement_used = False
        if self.instant_movement_skill:
          instant_movement_used = self.instant_movement_skill.use(mover.grid_pos_to_step_x, mover.grid_pos_to_step_y, wait_for_execution=False)
          if instant_movement_used:
            return True
        if self.movement_skill.use(mover.grid_pos_to_step_x, mover.grid_pos_to_step_y, wait_for_execution=False) is True:
          return True
    # if we are staying and waiting for smth
    else:
      self.staticDefence()
    return False
  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = random.randint(200,300)/10, *args, **kwargs):
    print(f'#build.killUsual {entity}')
    poe_bot = self.poe_bot
    mover = self.mover
    self.attacking_skill.last_use_time = 0
    entity_to_kill_id = entity.id
    self.auto_flasks.useFlasks()
    
    min_distance = 40 # distance which is ok to start attacking
    keep_distance = 15 # if our distance is smth like this, kite

    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print('cannot find desired entity to kill')
      return True
    print(f'entity_to_kill {entity_to_kill}')
    if entity_to_kill.life.health.current < 0:
      print('entity is dead')
      return True
    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual')
    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    if entity_to_kill.isInLineOfSight() is False:
      print('entity_to_kill.isInLineOfSight() is False')
      return False


    start_time = time.time()
    entity_to_kill.hover()
    self.attacking_skill.press()
    poe_bot.last_action_time = 0
    last_dodge_use_time = time.time()
    dodge_delay =  random.randint(40,60)/100
    res = True
    while True:
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print('cannot find desired entity to kill')
        break
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break
      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        break
      current_time = time.time()
      self.useBuffs()
      entity_to_kill.hover()
      if self.instant_movement_skill:
        if current_time > last_dodge_use_time + dodge_delay:
          print(f'flicker strike')
          self.instant_movement_skill.tap()
          last_dodge_use_time = time.time()
      if current_time  > start_time + max_kill_time_sec:
        print('exceed time')
        break
    self.attacking_skill.release()
    return res
class PoisonConcBouncingPf(Build):
  '''
  PoisonConcBouncingPf
  '''
  poe_bot: PoeBot
  def __init__(self,poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.attacking_skill_last_use_pos = [0,0]
    self.movement_skill_uses_after_attack = 0

    self.blood_rage = None # "blood_rage"
    self.attacking_skill = None #"poisonous_concoction_alt_x"
    self.plague_bearer = None # "corrosive_shroud"
    self.debuff = None # "despair"
    self.movement_skill = None # "new_new_shield_charge"
    self.movement_skill_last_use_time = 0
    
    self.instant_movement_skill = None 
    self.malevolance_blessing = None

    self.swapWeaponsIfNeeded()
    skills_data = poe_bot.backend.getSkillBar()

    #TODO
    for skill_index in range(len(skills_data['i_n'])):
      skill = skills_data['i_n'][skill_index]

      if skill == '':
        continue
      print(skill, skill_index)
      if skill == 'blood_rage':
        self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/10, display_name="blood_rage")
      elif skill == 'poisonous_concoction_alt_x':
        self.attacking_skill = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1,5)/100, display_name=skill, min_mana_to_use=0)
      elif skill == 'despair' or skill == "temporal_chains":
        self.debuff = AreaSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill)
      elif skill == 'plague_bearer':
        self.plague_bearer = PlagueBearer(poe_bot=poe_bot, skill_index=skill_index, display_name=skill)
      elif skill in NON_INSTANT_MOVEMENT_SKILLS:
        self.movement_skill = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill, min_delay=random.randint(30,50)/100)
      elif skill in INSTANT_MOVEMENT_SKILLS:
        self.instant_movement_skill = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill, min_delay=random.randint(26,30)/100)
    super().__init__(poe_bot)
    self.auto_flasks = AutoFlasks(poe_bot=poe_bot, pathfinder=False)
  def useBuffs(self):
    poe_bot = self.poe_bot
    if self.blood_rage is not None:
      if 'blood_rage' not in poe_bot.game_data.player.buffs:
        if self.blood_rage.use() is True:
          return True
    return False
  def useFlasks(self):
    self.auto_flasks.useFlasks()
  def usualRoutine(self, mover:Mover = None):
    poe_bot = self.poe_bot
    used_smth = False
    used_smth = self.auto_flasks.useFlasks()
    movement_skill_to_use = self.movement_skill
    min_movement_skill_uses = 3
    # if we are moving
    if mover is not None:
      if used_smth != True: 
        used_smth = self.useBuffs()
      nearby_enemies = list(filter(lambda e: e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      print(f'nearby_enemies: {nearby_enemies}')
      really_close_enemies = list(filter(lambda e: e.distance_to_player < 20,nearby_enemies))
      min_delay = 3
      if len(really_close_enemies) != 0:
        min_delay = 2
        if self.plague_bearer and used_smth != True:
          print(f'can turn plague bearer')
          used_smth = self.plague_bearer.turnOn()
        if self.instant_movement_skill:
          movement_skill_to_use = self.instant_movement_skill
      if used_smth != False:
        return False
      can_attack = False
      for i in range(1):
        if self.attacking_skill.last_use_time + min_delay < time.time():
          can_attack = True
          break
        if self.movement_skill_uses_after_attack > min_movement_skill_uses:
          can_attack = True
          break
        if dist([poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y], self.attacking_skill_last_use_pos) > 60:
          can_attack = True
          break
      if can_attack != False:
        print('can attack')
        enemy_to_attack = None
        if len(really_close_enemies) != 0:
          really_close_enemies = list(filter(lambda e: e.isInLineOfSight() is True, really_close_enemies))
          if really_close_enemies != []:
            enemy_to_attack = really_close_enemies[0]
        elif len(nearby_enemies):
          search_angle_half = 45
          nearby_enemies = sorted(nearby_enemies, key=lambda e: e.distance_to_player)
          nearby_enemies = list(filter(lambda e: e.isInLineOfSight() is True, nearby_enemies))
          p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
          p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
          nearby_enemies = list(filter(lambda e: getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < search_angle_half, nearby_enemies))
          if len(nearby_enemies) != 0:
            list(map(lambda e:e.calculateValueForAttack(15), nearby_enemies))
            nearby_enemies.sort(key=lambda e: e.attack_value, reverse=True)
            enemy_to_attack = nearby_enemies[0]
        # tap
        if enemy_to_attack is not None:
          if self.attacking_skill.use(updated_entity=enemy_to_attack) is True:
            self.attacking_skill.last_use_time = time.time()
            self.attacking_skill_last_use_pos = [poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y]
            self.movement_skill_uses_after_attack = random.randint(0, (min_movement_skill_uses-1) )
            return True
      # use movement skill
      if movement_skill_to_use and mover.distance_to_target > 50 and self.movement_skill_last_use_time + random.randint(10,20)/100 < time.time():
        if movement_skill_to_use.use(mover.grid_pos_to_step_x, mover.grid_pos_to_step_y, wait_for_execution=False) is True:
          self.movement_skill_uses_after_attack += 1
          self.movement_skill_last_use_time = time.time()
          return True
    # if we are staying and waiting for smth
    else:
      self.staticDefence()

    return False
  def prepareToFight(self, entity: Entity):
    return True
  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = random.randint(200,300)/10, *args, **kwargs):
    print(f'#PoisonConcBouncingPf.killUsual {entity}')
    poe_bot = self.poe_bot

    entity_to_kill_id = entity.id

    min_distance = 45 # distance which is ok to start attacking
    min_hold_duration = max_kill_time_sec
    whirling_blades_delay = 1.2

    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print('cannot find desired entity to kill')
      return True
    print(f'entity_to_kill {entity_to_kill}')
    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual')


    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    if entity_to_kill.isInLineOfSight() is False:
      print('entity_to_kill.isInLineOfSight() is False')
      return False

    self.auto_flasks.useFlasks()
    start_time = time.time()
    self.attacking_skill.press()
    entity_to_kill.hover(wait_till_executed=False)
    poe_bot.last_action_time = 0
    res = True 
    if self.instant_movement_skill:
      self.instant_movement_skill.last_use_time = time.time()
    debuff_use_time = 0
    while True:
      skill_used = False
      poe_bot.refreshInstanceData()
      used_smth = self.auto_flasks.useFlasks()
      if used_smth != True: 
        used_smth = self.useBuffs()
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print('cannot find desired entity to kill')
        break
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break
      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        res = False
        break
      current_time = time.time()
      entity_to_kill.hover(wait_till_executed=False)
      if self.plague_bearer and used_smth != True:
        print(f'can turn plague bearer')
        used_smth = self.plague_bearer.turnOn()
      if self.debuff and used_smth != True:
        if current_time > start_time + 2:
          if current_time > debuff_use_time + 4:
            if self.debuff.use(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y) is True:
              debuff_use_time = time.time()
              print(f'used debuff {self.debuff.display_name} at {time.time()}')
              used_smth = True
      if self.instant_movement_skill != None:
        if used_smth != True:
          if current_time > self.instant_movement_skill.last_use_time + whirling_blades_delay:
            can_use_instant_skill = self.instant_movement_skill.checkIfCanUse()
            print(f'removeme self.instant_movement_skill {self.instant_movement_skill}')
            if can_use_instant_skill != False:
              self.instant_movement_skill.tap(wait_till_executed=True)
              self.instant_movement_skill.last_use_time = time.time() + random.randint(10,30)/100
      if current_time  > start_time + min_hold_duration:
        print(f'exceed time min_hold_duration {min_hold_duration}')
        break
    self.attacking_skill.release()
    return res
class Bama(Build):
  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    bama_attacking_skill_names = [
      "mirror_arrow",
      "mirror_arrow_alt_y",
      "mirror_arrow_alt_x",
    ]
    bama_moving_skill_names = [
      "blink_arrow",
      "blink_arrow_alt_y",
      "blink_arrow_alt_x",
    ]
    bama_base_cooldown = 3


    self.has_blessing_on_bama = False
    self.attacking_skill = None # mirror arrow
    self.attacking_movement_skill = None # blink arrow
    self.movement_skill = None # flamedash frostblink, dash, whatever

    attacking_skill = next( (s for s in self.poe_bot.game_data.skills.internal_names if s in bama_attacking_skill_names), None)
    attacking_movement_skill = next( (s for s in self.poe_bot.game_data.skills.internal_names if s in bama_moving_skill_names), None)
    if attacking_skill == None and attacking_movement_skill == None:
      poe_bot.raiseLongSleepException('bama must have at least mirror arrow or blink arrow skill on panel')

    if attacking_skill:
      skill_index = self.poe_bot.game_data.skills.internal_names.index(attacking_skill)
      self.attacking_skill = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1,5)/100, display_name=attacking_skill, min_mana_to_use=0, can_use_earlier=False)
      is_blessing_activator = next( (sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if 'SupportGuardiansBlessingMinionPhysicalDamagePctOfMaximumLifeAndESTakenPerMinute' in sd.keys()), False)
      if is_blessing_activator != False:
        print(f'{attacking_skill} is blessing activator')
        self.has_blessing_on_bama = True
      cooldown_speed_percent = next( (sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if 'BaseCooldownSpeedPct' in sd.keys()), None)
      if cooldown_speed_percent != None:
        self.attacking_skill.min_delay = bama_base_cooldown / ((100 + cooldown_speed_percent['BaseCooldownSpeedPct']) /100)
      else:
        self.attacking_skill.min_delay = bama_base_cooldown
      print(f'[Bama build] attacking_movement_skill {attacking_skill} cooldown {self.attacking_skill.min_delay} blessing {(is_blessing_activator != False)}')

    if attacking_movement_skill:
      skill_index = self.poe_bot.game_data.skills.internal_names.index(attacking_movement_skill)
      self.attacking_movement_skill = MovementSkill_new(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1,5)/100, display_name=attacking_movement_skill, min_mana_to_use=0, can_use_earlier=False)
      is_blessing_activator = next( (sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if 'SupportGuardiansBlessingMinionPhysicalDamagePctOfMaximumLifeAndESTakenPerMinute' in sd.keys()), False)
      if is_blessing_activator != False:
        print(f'{attacking_movement_skill} is blessing activator')
        self.has_blessing_on_bama = True
      cooldown_speed_percent = next( (sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if 'BaseCooldownSpeedPct' in sd.keys()), None)
      if cooldown_speed_percent != None:
        self.attacking_movement_skill.min_delay = bama_base_cooldown / ((100 + cooldown_speed_percent['BaseCooldownSpeedPct']) /100)
      else:
        self.attacking_movement_skill.min_delay = bama_base_cooldown
      print(f'[Bama build] attacking_movement_skill {attacking_movement_skill} cooldown {self.attacking_movement_skill.min_delay} blessing {(is_blessing_activator != False)}')
    movement_skill = next( (s for s in self.poe_bot.game_data.skills.internal_names if s in INSTANT_MOVEMENT_SKILLS), None)
    if movement_skill:
      skill_index = self.poe_bot.game_data.skills.internal_names.index(movement_skill)
      self.movement_skill = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=movement_skill, min_delay=random.randint(5,20)/10)
    super().__init__(poe_bot)
  def useBuffs(self):
    if self.has_blessing_on_bama:
      # {"ls":[481,314],"p":"Metadata/Monsters/Clone/WitchCloneImmobileRainOfArrows@70","r":"White","i":31,"o":0,"h":0,"ia":0,"t":1,"em":0,"b":1,"gp":[418,296],"wp":[4569,3243,-169],"l":[4363,4363,0,992,992,0,1755,0,0],"rn":"Clone","et":"m"},
      # {"ls":[349,479],"p":"Metadata/Monsters/Clone/WitchCloneImmobile@66","r":"White","i":34,"o":0,"h":0,"ia":0,"t":1,"em":0,"b":1,"gp":[393,290],"wp":[4297,3178,-169],"l":[3525,3525,0,906,906,0,1420,0,0],"rn":"Clone","et":"m"},
      # {"ls":[621,197],"p":"Metadata/Monsters/Clone/WitchCloneImmobileElementalShot@10","r":"White","i":37,"o":0,"h":0,"ia":0,"t":1,"em":0,"b":1,"gp":[444,297],"wp":[4852,3254,-169],"l":[102,102,0,104,104,0,51,0,0],"rn":"Clone","et":"m"}
      if 'has_guardians_blessing_aura' in self.poe_bot.game_data.player.buffs:
        return False
      if 'has_guardians_blessing_minion' in self.poe_bot.game_data.player.buffs:
        if self.poe_bot.combat_module.aura_manager.blessing_skill != None:
          used_blessing = self.poe_bot.combat_module.aura_manager.blessing_skill.use()
          if used_blessing != False:
            return True
    return False
  def prepareToFight(self, entity: Entity):
    print(f'Bama.preparetofight call {time.time()}')
    poe_bot = self.poe_bot
    bot_controls = self.poe_bot.bot_controls
    pos_x, pos_y = entity.location_on_screen.x, entity.location_on_screen.y
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y) 
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    for i in range(random.randint(2,3)):
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      entity.updateLocationOnScreen()
      entity.hover()
      if self.attacking_skill: self.attacking_skill.tap()
      if self.attacking_movement_skill: self.attacking_movement_skill.tap()
  def usualRoutine(self, mover:Mover = None):
    poe_bot = self.poe_bot
    used_smth = self.auto_flasks.useFlasks()
    if mover is not None:
      if used_smth != True: 
        used_smth = self.useBuffs()
      if used_smth != True:
        if self.attacking_skill:
          nearby_enemies_on_screen = list(filter(lambda e: e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
          print(f'nearby_enemies_on_screen: {nearby_enemies_on_screen}')
          if nearby_enemies_on_screen:
            if self.attacking_skill.use(mover.grid_pos_to_step_x, mover.grid_pos_to_step_y, wait_for_execution=False) is True:
              return True
        if self.attacking_movement_skill and mover.distance_to_target > 50:
          can_use = True
          if self.movement_skill and time.time() - self.movement_skill.last_use_time < 0.1:
            print(f'[Bama build] cant use attacking_movement_skill cos used movement_skill recentley')
            can_use = False
          if can_use != False and self.attacking_movement_skill.use(mover.nearest_passable_point[0], mover.nearest_passable_point[1], wait_for_execution=False) is True:
            return True
        if self.movement_skill and mover.distance_to_target > 50:
          can_use = True
          if self.attacking_movement_skill.last_use_time and time.time() - self.attacking_movement_skill.last_use_time < 0.5:
            print(f'[Bama build] cant use movement_skill cos used attacking_movement_skill recentley')
            can_use = False
          if can_use != False and self.movement_skill.use(mover.nearest_passable_point[0], mover.nearest_passable_point[1], wait_for_execution=False) is True:
            return True
    else:
      self.staticDefence()
    return False
  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = random.randint(200,300)/10, *args, **kwargs):
    print(f'#Bama.killUsual {entity}')
    poe_bot = self.poe_bot
    mover = self.mover
    entity_to_kill_id = entity.id
    used_smth = False
    used_smth = self.auto_flasks.useFlasks()
    min_distance = 40 # distance which is ok to start attacking
    keep_distance = 15 # if our distance is smth like this, kite
    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print('cannot find desired entity to kill')
      return True
    print(f'entity_to_kill {entity_to_kill}')
    if entity_to_kill.life.health.current < 0:
      print('entity is dead')
      return True
    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual')
    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    if entity_to_kill.isInLineOfSight() is False:
      print('entity_to_kill.isInLineOfSight() is False')
      return False
    start_time = time.time()
    skill_to_use:Skill = None
    if self.attacking_skill:
      skill_to_use = self.attacking_skill
    else:
      skill_to_use = self.attacking_movement_skill
    entity_to_kill.hover()
    skill_to_use.use(updated_entity=entity_to_kill)
    poe_bot.last_action_time = 0
    kite_distance = random.randint(18,22)
    res = True
    reversed_run = random.choice([True, False])
    while True:
      used_smth = False
      poe_bot.refreshInstanceData()
      used_smth = self.auto_flasks.useFlasks()
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print('cannot find desired entity to kill')
        break
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break
      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        break
      current_time = time.time()
      if used_smth != True:
        used_smth = self.useBuffs() 
      # if self.arcanist_brand:
      #   if current_time > start_time + 2:
      #     if current_time > debuff_use_time + 4:
      #       if self.arcanist_brand.use(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y) is True:
      #         debuff_use_time = time.time()
      #         skill_used = True

      point = self.poe_bot.game_data.terrain.pointToRunAround(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, kite_distance+random.randint(-1,1), check_if_passable=True, reversed=reversed_run)
      if used_smth != True and self.attacking_skill:
        used_smth = self.attacking_skill.use(pos_x= point[0], pos_y = point[1], wait_for_execution=False)
      if used_smth != True and self.attacking_movement_skill:
        used_smth = self.attacking_movement_skill.use(pos_x= point[0], pos_y = point[1], wait_for_execution=False, use_as_movement_skill=False)
      if used_smth != True:
        print('kiting')
        mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
      if current_time  > start_time + max_kill_time_sec:
        print('exceed time')
        break
    return res
# generic builds
HITTER_SKILLS = [
  'molten_strike',
  'splitting_steel',
  'frost_blades',
  'lightning_strike',
  'flicker_strike',
]

#   'smite',

class GenericHitter(Build):
  # lightning strike, splitting steel, frost blates, motlen strike, smite
  '''
  venom gyre
  '''
  poe_bot: PoeBot
  def __init__(self,poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    
    self.attacking_skill = None
    self.attacking_buff = None

    self.movement_skill = None
    self.instant_movement_skill = None

    self.blood_rage = None
    main_attacking_skill = next( (s for s in self.poe_bot.game_data.skills.internal_names if s in HITTER_SKILLS), None)
    if main_attacking_skill != None:
      attacking_buff = next( (s for s in self.poe_bot.game_data.skills.internal_names if s == 'smite'), None)
      if attacking_buff:
        print(f'[GenericHitter] attacking buff {attacking_buff}')
        skill_index = self.poe_bot.game_data.skills.internal_names.index(attacking_buff)
        self.attacking_buff = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/10, display_name=attacking_buff)
    else:
      main_attacking_skill = next( (s for s in self.poe_bot.game_data.skills.internal_names if s == 'smite'), None)
    if main_attacking_skill != None:
      print(f'[GenericHitter] main attacking skill {main_attacking_skill}')
      skill_index = self.poe_bot.game_data.skills.internal_names.index(main_attacking_skill)
      self.attacking_skill = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1,5)/100, display_name=main_attacking_skill, min_mana_to_use=0)
    else:
      self.poe_bot.raiseLongSleepException(f'[GenericHitter] couldnt find main attacking skill, skills are {self.poe_bot.game_data.skills.internal_names} ')
    blood_rage = next( (s for s in self.poe_bot.game_data.skills.internal_names if s == 'smite'), None)
    if blood_rage != None:
      skill_index = self.poe_bot.game_data.skills.internal_names.index(blood_rage)
      self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/10, display_name=blood_rage)
    self.movement_skill = None # "new_new_shield_charge"
    self.instant_movement_skill = None # "flame_dash"
    for skill_index in range(len(self.poe_bot.game_data.skills.internal_names)):
      skill_name = self.poe_bot.game_data.skills.internal_names[skill_index]
      if skill_name == '': continue
      print(skill_name, skill_index)
      if skill_name == 'blood_rage':
        self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay= random.randint(30,50)/10, display_name=skill_name)
      elif skill_name in NON_INSTANT_MOVEMENT_SKILLS:
        self.movement_skill = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill_name, min_delay=random.randint(30,50)/100)
        if skill_name == "whirling_blades":
          self.instant_movement_skill = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill_name, min_delay=random.randint(30,50)/100)
    super().__init__(poe_bot)
  def useBuffs(self):
    poe_bot = self.poe_bot
    if self.blood_rage is not None:
      if 'blood_rage' not in poe_bot.game_data.player.buffs and poe_bot.game_data.player.life.health.current / poe_bot.game_data.player.life.health.total > 0.7:
        self.blood_rage.use()
        return True
    return False
  def usualRoutine(self, mover:Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()
    # if we are moving
    if mover is not None:
      self.useBuffs()
      search_angle_half = 60
      min_hold_duration = random.randint(25,55)/100
      
      nearby_enemies = list(filter(lambda e: e.isInRoi() and e.distance_to_player < 30, poe_bot.game_data.entities.attackable_entities))
      print(f'nearby_enemies: {nearby_enemies}')
      
      entities_to_hold_skill_on:list[Entity] = []
      if nearby_enemies:
        for iiii in range(1):
          time_now = time.time()
          nearby_visible_enemies = list(filter(lambda e: e.isInLineOfSight(), nearby_enemies))
          if not nearby_visible_enemies:
            break
          # didnt attack for a long time
          if self.attacking_skill.last_use_time + random.randint(20,30)/10 < time_now:
            print(f'didnt attack for a long time')
            entities_to_hold_skill_on = sorted(nearby_visible_enemies, key=lambda e: e.distance_to_player)
            min_hold_duration = 0.1
            break
          # if surrounded
          # really_close_enemies = list(filter(lambda e: e.distance_to_player < 20, nearby_visible_enemies))
          # if len(really_close_enemies) > 5:
          #   print(f'surrounded')
          #   entities_to_hold_skill_on = really_close_enemies
          #   break
          # on the way
          if self.attacking_skill.last_use_time + random.uniform(1.0, 1.5) < time_now:
            p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
            p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
            enemies_in_sector = list(filter(lambda e: getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < search_angle_half, nearby_visible_enemies))
            if enemies_in_sector:
              print(f'on the way')
              min_hold_duration = 0.1
              entities_to_hold_skill_on = enemies_in_sector
          break
      if entities_to_hold_skill_on:
        entities_to_hold_skill_on_ids = list(map(lambda e: e.id, entities_to_hold_skill_on))
        hold_start_time = time.time()
        self.attacking_skill.last_use_time = hold_start_time
        self.attacking_skill.press()
        entities_to_hold_skill_on[0].hover()
        print(f'self.attacking_skill.getCastTime() {self.attacking_skill.getCastTime()}')
        hold_duration = self.attacking_skill.getCastTime() * random.randint(25,35)/10
        # hold_duration = random.randint(int(self.attacking_skill.getCastTime() * 120), int(self.attacking_skill.getCastTime() * 160))/100
        print(f'hold_duration {hold_duration}')
        while time.time() - hold_duration < hold_start_time:
          poe_bot.refreshInstanceData()
          self.auto_flasks.useFlasks()
          entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id in entities_to_hold_skill_on_ids), None)
          if entity_to_kill:
            entity_to_kill.hover()
          else:
            if not time.time() + 0.1 > hold_start_time + min_hold_duration:
              time.sleep(0.1)
            break
        self.attacking_skill.release()        
        return True
      # use movement skill
      if self.movement_skill and mover.distance_to_target > 50:
        instant_movement_used = False
        if self.instant_movement_skill:
          instant_movement_used = self.instant_movement_skill.use(mover.grid_pos_to_step_x, mover.grid_pos_to_step_y, wait_for_execution=False)
          if instant_movement_used:
            return True
        if self.movement_skill.use(mover.grid_pos_to_step_x, mover.grid_pos_to_step_y, wait_for_execution=False) is True:
          return True
    # if we are staying and waiting for smth
    else:
      self.staticDefence()
    return False
  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = random.randint(200,300)/10, *args, **kwargs):
    print(f'#build.killUsual {entity}')
    poe_bot = self.poe_bot
    mover = self.mover
    self.attacking_skill.last_use_time = 0
    entity_to_kill_id = entity.id
    self.auto_flasks.useFlasks()
    
    min_distance = 40 # distance which is ok to start attacking
    keep_distance = 15 # if our distance is smth like this, kite

    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print('cannot find desired entity to kill')
      return True
    print(f'entity_to_kill {entity_to_kill}')
    if entity_to_kill.life.health.current < 0:
      print('entity is dead')
      return True
    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual')
    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    if entity_to_kill.isInLineOfSight() is False:
      print('entity_to_kill.isInLineOfSight() is False')
      return False


    start_time = time.time()
    entity_to_kill.hover()
    self.attacking_skill.press()
    poe_bot.last_action_time = 0
    last_dodge_use_time = time.time()
    dodge_delay =  random.randint(80,140)/100
    res = True
    while True:
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print('cannot find desired entity to kill')
        break
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break
      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        break
      current_time = time.time()
      self.useBuffs()
      entity_to_kill.hover()
      if self.instant_movement_skill:
        if self.attacking_skill.display_name != 'flicker_strike' and current_time > last_dodge_use_time + dodge_delay:
          print(f'flicker strike')
          self.instant_movement_skill.tap()
          last_dodge_use_time = time.time()
      if current_time  > start_time + max_kill_time_sec:
        print('exceed time')
        break
    self.attacking_skill.release()
    return res
  def prepareToFight(self, entity: Entity):
    print(f'vg.preparetofight call {time.time()}')
    poe_bot = self.poe_bot
    bot_controls = self.poe_bot.bot_controls
    pos_x, pos_y = entity.location_on_screen.x, entity.location_on_screen.y
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y) 
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    self.attacking_skill.press()
    start_hold_time = time.time()
    min_hold_duration = random.randint(40,60)/100
    while True:
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      pos_x, pos_y = poe_bot.getPositionOfThePointOnTheScreen(y=entity.grid_position.y, x= entity.grid_position.x)
      pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y) 
      bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      if time.time() > start_hold_time + min_hold_duration:
        break
    self.attacking_skill.release()
class GenericSummoner(Build):
  spectre_list = []
  poe_bot: PoeBot
  poe_bot: PoeBot
  def __init__(self,poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    super().__init__(poe_bot)

class FacetankBuild(Build):
  """
  spams main skill till death
  """
  pass
class HitAndRunBuild(Build):
  '''
  some spam skills
  # attacks several times and runs away
  '''
  pass
class KiteAroundBuild(Build):
  '''
  totem, minions, brands
  '''
  pass

# poe2
class DodgeRoll(SkillWithDelay):
  def __init__(self, poe_bot, skill_index=3, skill_name='', display_name="DodgeRoll", min_delay=0.1, delay_random=0.1, min_mana_to_use=0, can_use_earlier=True):
    super().__init__(poe_bot, skill_index, skill_name, display_name, min_delay, delay_random, min_mana_to_use, can_use_earlier)
    self.skill_key = "DIK_SPACE"
    self.tap_func = poe_bot.bot_controls.keyboard.pressAndRelease
    self.press_func = poe_bot.bot_controls.keyboard_pressKey
    self.release_func = poe_bot.bot_controls.keyboard_releaseKey
    self.checkIfCanUse = lambda *args, **kwargs: True
    self.getCastTime = lambda *args, **kwargs: 0.5

class InfernalistZoomancer(Build):
  '''
  '''
  poe_bot: PoeBot
  def __init__(self,poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    
    self.max_srs_count = 10

    flame_wall_internal_name = "firewall"
    flame_wall_index = flame_wall_internal_name in self.poe_bot.game_data.skills.internal_names and self.poe_bot.game_data.skills.internal_names.index(flame_wall_internal_name) 
    unearth_index = False

    self.minion_reaver_enrage = None

    self.minion_arconist_dd = None
    self.minion_reaver_enrage = None
    self.minion_sniper_gas_arrow = None

    minion_command_internal_name = "command_minion"
    for skill_index in range(len(self.poe_bot.game_data.skills.internal_names)):
      skill_name_raw = self.poe_bot.game_data.skills.internal_names[skill_index]
      if skill_name_raw != minion_command_internal_name:
        continue
      skill_base_cast_time = next( (list(sd.values())[0] for sd in poe_bot.game_data.skills.descriptions[skill_index] if 'BaseSpellCastTimeMs' in sd.keys()), None)
      if skill_base_cast_time == None:
        continue
      elif self.minion_arconist_dd == None and skill_base_cast_time == 600:
        print(f'[InfernalistZoomancer.__init__] found minion_arconist_dd_index {skill_index}')
        self.minion_arconist_dd = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(20,30)/10, display_name="minion_arconist_dd", can_use_earlier=False)
      elif self.minion_reaver_enrage == None and skill_base_cast_time == 1000:
        print(f'[InfernalistZoomancer.__init__] found minion_reaver_enrage_index {skill_index}')
        self.minion_reaver_enrage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.uniform(2.5, 3.0), display_name="minion_reaver_enrage", can_use_earlier=False)
      elif self.minion_sniper_gas_arrow == None and skill_base_cast_time == 1250:
        print(f'[InfernalistZoomancer.__init__] found minion_sniper_gas_arrow_index {skill_index}')
        self.minion_sniper_gas_arrow = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.uniform(0.05, 0.15), display_name="minion_sniper_gas_arrow", can_use_earlier=False)


    #TODO minion frenzy command
    #TODO minion gas arrow command

    dd_internal_name = "detonate_dead"
    detonate_dead_index = dd_internal_name in self.poe_bot.game_data.skills.internal_names and self.poe_bot.game_data.skills.internal_names.index(dd_internal_name) 
    offering_internal_name = "pain_offering"
    offerening_index = offering_internal_name in self.poe_bot.game_data.skills.internal_names and self.poe_bot.game_data.skills.internal_names.index(offering_internal_name) 
    flammability_internal_name = "fire_weakness"
    flammability_index = flammability_internal_name in self.poe_bot.game_data.skills.internal_names and self.poe_bot.game_data.skills.internal_names.index(flammability_internal_name) 


    self.fire_skills = []

    self.flame_wall = None
    if flame_wall_index != False:
      self.flame_wall = SkillWithDelay(poe_bot=poe_bot, skill_index=flame_wall_index, min_delay=random.randint(20,30)/10, display_name="flame_wall", can_use_earlier=False)
      self.fire_skills.append(self.flame_wall)

    self.unearth = None
    if unearth_index != False:
      self.unearth = SkillWithDelay(poe_bot=poe_bot, skill_index=unearth_index, min_delay=random.randint(20,30)/10, display_name="unearth", can_use_earlier=False)

    self.detonate_dead = None
    if detonate_dead_index != False:
      self.detonate_dead = SkillWithDelay(poe_bot=poe_bot, skill_index=detonate_dead_index, min_delay=random.uniform(3.1, 4.5), display_name="detonate_dead", can_use_earlier=False)
      self.fire_skills.append(self.detonate_dead)
    
    self.offering = None
    if offerening_index != False:
      self.offering = SkillWithDelay(poe_bot=poe_bot, skill_index=offerening_index, min_delay=random.randint(20,30)/10, display_name="offering", can_use_earlier=False)

    self.flammability = None
    if flammability_index != False:
      self.flammability = SkillWithDelay(poe_bot=poe_bot, skill_index=flammability_index, min_delay=random.randint(20,30)/10, display_name="flammability", can_use_earlier=False)

    self.dodge_roll = DodgeRoll(poe_bot=poe_bot)

    super().__init__(poe_bot)
    self.auto_flasks = AutoFlasks(poe_bot=poe_bot)
  def useBuffs(self):
    return False
  def usualRoutine(self, mover:Mover = None):
    print(f'calling usual routine')
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()

    # if we are moving
    if mover is not None:
      skill_used = False
      skill_used = self.useBuffs()
      attacking_skill_delay = 2

      nearby_enemies = list(filter(lambda e: e.distance_to_player < 50 and e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      print(f'nearby_enemies: {nearby_enemies}')
      really_close_enemies = list(filter(lambda e: e.distance_to_player < 20,nearby_enemies))
      min_delay = 3
      if len(really_close_enemies) != 0:
        min_delay = 2
        attacking_skill_delay = 0.7

      enemy_to_attack = None
      if len(really_close_enemies) != 0:
        enemy_to_attack = really_close_enemies[0]
      elif len(nearby_enemies):
        nearby_enemies = sorted(nearby_enemies, key=lambda e: e.distance_to_player)
        nearby_enemies = list(filter(lambda e: e.isInLineOfSight() is True, nearby_enemies))
        if len(nearby_enemies) != 0:
          enemy_to_attack = nearby_enemies[0]
      
      attack_skill_used = False
      if enemy_to_attack is not None:

        for _i in range(1):
          if self.flame_wall and self.flame_wall.last_use_time + attacking_skill_delay < time.time():
            alive_srs_nearby = list(filter(lambda e: not e.is_hostile and e.life.health.current != 0 and e.distance_to_player < 150 and "Metadata/Monsters/RagingSpirit/RagingSpiritPlayerSummoned" in e.path , self.poe_bot.game_data.entities.all_entities))
            if len(alive_srs_nearby) < self.max_srs_count:
              print(f'[Generic summoner] need to raise srs, current count {len(alive_srs_nearby)}')
              if self.flame_wall.use(updated_entity=enemy_to_attack, wait_for_execution=False) == True:
                attack_skill_used = True
                break
          if self.detonate_dead and self.detonate_dead.canUse():
            corpses_around = poe_bot.game_data.entities.getCorpsesArountPoint(poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y, 40)
            corpses_around = list(filter(lambda e: e.isInLineOfSight() != False, corpses_around))
            if len(corpses_around) != 0:
              corpses_around.sort(key=lambda e: e.calculateValueForAttack())
              if corpses_around[0].attack_value != 0:
                if self.detonate_dead.use(updated_entity=corpses_around[0], wait_for_execution=False) != False:
                  attack_skill_used = True
                  break
                
          if self.minion_sniper_gas_arrow and self.minion_sniper_gas_arrow.canUse():
            if self.minion_sniper_gas_arrow.use(updated_entity=enemy_to_attack, wait_for_execution=False) == True:
              attack_skill_used = True
              break
          if self.minion_reaver_enrage and self.minion_reaver_enrage.canUse():
            if self.minion_reaver_enrage.use(wait_for_execution=False) == True:
              attack_skill_used = True
              break
          if self.unearth and self.unearth.canUse():
            corpses_around = poe_bot.game_data.entities.getCorpsesArountPoint(poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y, 20)
            corpses_around = list(filter(lambda e: e.isInLineOfSight() != False, corpses_around))
            if len(corpses_around) != 0:
              corpses_around.sort(key=lambda e: e.calculateValueForAttack())
              if corpses_around[0].attack_value != 0:
                if self.unearth.use(updated_entity=corpses_around[0], wait_for_execution=False) != False:
                  attack_skill_used = True
                  break


        p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
        p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
        # cast first then move back
        if len(nearby_enemies) > 1:
          go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
          poe_bot.mover.move(*go_back_point)
          return True
        if attack_skill_used:
          return True

        #TODO add global cooldown, so itll be able to finish casting skills
        extremley_close_entities = list(filter(lambda e: e.distance_to_player < 10, really_close_enemies))
        enemies_on_way = list(filter(lambda e: e.distance_to_player < 15 and getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < 45, really_close_enemies))
        if extremley_close_entities or enemies_on_way:
          if self.dodge_roll.use() == True:
            return True

        # return True
        
      


      p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
      p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
      # go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
      
      extremley_close_entities = list(filter(lambda e: e.distance_to_player < 10, really_close_enemies))
      enemies_on_way = list(filter(lambda e: e.distance_to_player < 15 and getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < 45, really_close_enemies))
      if extremley_close_entities or enemies_on_way:
        if self.dodge_roll.use() == True:
          return True
      # # use movement skill
      # if self.movement_skill and mover.distance_to_target > 50:
      #   if self.movement_skill.use(mover.grid_pos_to_step_x, mover.grid_pos_to_step_y, wait_for_execution=False) is True:
      #     return True
    
    # if we are staying and waiting for smth
    else:
      self.staticDefence()

    return False
  def prepareToFight(self, entity: Entity):
    print(f'[InfernalistZoomancer.prepareToFight] call {time.time()}')
    for i in range(random.randint(2,3)):
      self.poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      updated_entity = next( (e for e in self.poe_bot.game_data.entities.all_entities if e.id == entity.id), None)
      if updated_entity is None:
        break

      self.flame_wall.use(updated_entity=updated_entity)
    return True
  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = random.randint(200,300)/10, *args, **kwargs):
    print(f'#build.killUsual {entity}')
    poe_bot = self.poe_bot
    mover = self.mover

    entity_to_kill_id = entity.id
    debuff_use_time = 0

    self.auto_flasks.useFlasks()
    
    min_distance = 70 # distance which is ok to start attacking
    keep_distance = 15 # if our distance is smth like this, kite

    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print('cannot find desired entity to kill')
      return True

    print(f'entity_to_kill {entity_to_kill}')
    
    if entity_to_kill.life.health.current < 0:
      print('entity is dead')
      return True

    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual')
    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    
    if entity_to_kill.isInLineOfSight() is False:
      print('entity_to_kill.isInLineOfSight() is False')
      return False


    start_time = time.time()
    entity_to_kill.hover(wait_till_executed=False)
    poe_bot.last_action_time = 0
    kite_distance = random.randint(35,45)
    res = True
    reversed_run = random.choice([True, False])



    while True:
      skill_used = False
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      if self.poe_bot.game_data.player.life.health.getPercentage() < self.auto_flasks.hp_thresh:
        pass #TODO kite?

      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print('cannot find desired entity to kill')
        break
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break

      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        break
      current_time = time.time()
      skill_used = self.useBuffs()
      skill_use_delay = random.randint(20,30)/10
      print(f'skill_use_delay {skill_use_delay}')




      if skill_used is False and self.flame_wall and self.flame_wall.last_use_time + skill_use_delay < time.time():
        alive_srs_nearby = list(filter(lambda e: not e.is_hostile and e.life.health.current != 0 and e.distance_to_player < 150 and "Metadata/Monsters/RagingSpirit/RagingSpiritPlayerSummoned" in e.path , self.poe_bot.game_data.entities.all_entities))
        if len(alive_srs_nearby) < self.max_srs_count:
          print(f'[Generic summoner] need to raise srs')
          if self.flame_wall.use(updated_entity=entity_to_kill, wait_for_execution=False) == True:
            skill_used = True
      if skill_used is False and self.detonate_dead and self.detonate_dead.canUse():
        corpses_around = poe_bot.game_data.entities.getCorpsesArountPoint(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, 40)
        corpses_around = list(filter(lambda e: e.isInLineOfSight() != False, corpses_around))
        if len(corpses_around) != 0:
          corpses_around.sort(key=lambda e: e.calculateValueForAttack())
          if corpses_around[0].attack_value != 0:
            if self.detonate_dead.use(updated_entity=corpses_around[0], wait_for_execution=False) != False:
              skill_used = True
      if skill_used is False and self.unearth and self.unearth.canUse():
        corpses_around = poe_bot.game_data.entities.getCorpsesArountPoint(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, 20)
        corpses_around = list(filter(lambda e: e.isInLineOfSight() != False, corpses_around))
        if len(corpses_around) != 0:
          corpses_around.sort(key=lambda e: e.calculateValueForAttack())
          if corpses_around[0].attack_value != 0:
            if self.unearth.use(updated_entity=corpses_around[0], wait_for_execution=False) != False:
              skill_used = True
      if skill_used is False and self.minion_reaver_enrage and self.minion_reaver_enrage.canUse():
        if self.minion_reaver_enrage.use(updated_entity=entity_to_kill, wait_for_execution=False) != False:
          skill_used = True

      if skill_used is False and self.minion_sniper_gas_arrow and self.minion_sniper_gas_arrow.canUse():
        if self.minion_sniper_gas_arrow.use(updated_entity=entity_to_kill, wait_for_execution=False) != False:
          skill_used = True
        
      


      print('kiting')
      if distance_to_entity > keep_distance:
        print('away')
        p0 = (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y)
        p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
        go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
        poe_bot.mover.move(*go_back_point)
      else:
        print('around')
        point = self.poe_bot.game_data.terrain.pointToRunAround(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, kite_distance+random.randint(-1,1), check_if_passable=True, reversed=reversed_run)
        mover.move(grid_pos_x = point[0], grid_pos_y = point[1])




      if current_time  > start_time + max_kill_time_sec:
        print('exceed time')
        break
    return res

class PathfinderPoisonConc2(Build):
  '''
  '''
  poe_bot: Poe2Bot
  def __init__(self,poe_bot: Poe2Bot) -> None:
    self.poe_bot = poe_bot

    self.last_explosion_loc = [0,1,0,1]
    self.last_explosion_locations = {
      # "use_time": [grid pos area x1 x2 y1 y2]
    }
    self.pconc_area = 15
    self.pconc_area_reset_timer_sec = 4 
    self.pconc_area_in_legs_reset_timer_sec = 2 

    self.pconc:SkillWithDelay = None
    self.curse:SkillWithDelay = None
    self.wither_totem:SkillWithDelay = None

    pconc_internal_name = "throw_flask_poison"
    curse_internal_names = ["despair"]
    wither_totem_internal_name = "dark_effigy"

    pconc_on_panel = next( (s for s in self.poe_bot.game_data.skills.internal_names if s == pconc_internal_name), None)
    if pconc_on_panel != None:
      print(pconc_on_panel)
      pconc_index = self.poe_bot.game_data.skills.internal_names.index(pconc_on_panel)
      # print(pconc_on_panel, pcon)
      self.pconc = SkillWithDelay(poe_bot=poe_bot, skill_index=pconc_index, min_delay=random.randint(1,5)/100, display_name=pconc_internal_name, min_mana_to_use=0)

    curse_on_panel = next( (s for s in self.poe_bot.game_data.skills.internal_names if s in curse_internal_names), None)
    if curse_on_panel != None:
      curse_index = self.poe_bot.game_data.skills.internal_names.index(curse_on_panel)
      self.curse = SkillWithDelay(poe_bot=poe_bot, skill_index=curse_index, min_delay= random.randint(30,50)/10, display_name=curse_on_panel)

    wither_totem_on_panel = next( (s for s in self.poe_bot.game_data.skills.internal_names if s == wither_totem_internal_name), None)
    if wither_totem_on_panel != None:
      wither_totem_index = self.poe_bot.game_data.skills.internal_names.index(wither_totem_on_panel)
      self.wither_totem = SkillWithDelay(poe_bot=poe_bot, skill_index=wither_totem_index, min_delay= random.randint(30,50)/10, display_name=wither_totem_on_panel)
    self.dodge_roll = DodgeRoll(poe_bot=poe_bot)
    super().__init__(poe_bot)
    self.auto_flasks = AutoFlasks(poe_bot=poe_bot)
    self.auto_flasks.hp_thresh = 0.75
  def useBuffs(self):
    return False
  def usualRoutine(self, mover:Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()

    # if we are moving
    if mover is not None:
      print(f'calling usual routine')

      _t = time.time()
      if self.dodge_roll.last_use_time + 0.35 > _t or self.pconc.last_use_time + (self.pconc.getCastTime() / 2) > _t:
        print(f'probably casting smth atm')
        return False

      need_dodge = False
      throw_pconc_at = None # [x,y] grid pos
      enemy_to_attack:Entity = None
      search_radius = 25
      search_angle = 90
      search_angle_half = search_angle/2

      self.useBuffs()

      # either throw pconc on enemies whose attack val > 2 and didnt throw in that zone for kinda long time
      # or if didnt use pconc for long time throw pconc
      # or if surrounded throw pconc in legs

      # if surrounded and did throw pconc in legs recently, and did use pconc recentley, and if last time dodged > 1.5 sec -> dodge forward

      # if clear is bad, remove explosion zone stuff, since it's good when does it according to cd but not explosion zones
      # self.last_explosion_locations = {}

      # reset explosion areas
      for k in list(self.last_explosion_locations.keys()):
        if k + self.pconc_area_reset_timer_sec < _t:
          print(f'removing explosion zone {k} with {self.last_explosion_locations[k]} , expired')
          del self.last_explosion_locations[k]

      last_explosion_locations = list(self.last_explosion_locations.values())


      # nearby_enemies = list(filter(lambda e: e.distance_to_player < 50 and e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      nearby_enemies = list(filter(lambda e: e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      print(f'nearby_enemies: {nearby_enemies}')
      really_close_enemies = list(filter(lambda e: e.distance_to_player < 20, nearby_enemies))
      extremley_close_entities = list(filter(lambda e: e.distance_to_player < 20, nearby_enemies))

      # surrounded
      if len(extremley_close_entities) > 2:
        print(f'surrounded')
        for _i in range(1):
          did_throw_pconc_in_legs_recently = False
          #recently for throw in legs reduced timer
          last_explosion_locations_in_legs_keys = list(filter(lambda k: k + self.pconc_area_in_legs_reset_timer_sec > _t, list(self.last_explosion_locations.keys()) ))
          last_explosion_locations_in_legs = list(map(lambda k: self.last_explosion_locations[k], last_explosion_locations_in_legs_keys))
          for zone in last_explosion_locations_in_legs:
            if self.poe_bot.game_data.player.isInZone(*zone):
              did_throw_pconc_in_legs_recently = True
              print(f'did throw pconc nearby recently')
              break
          
          #TODO add cooldown to it?
          if did_throw_pconc_in_legs_recently == False:
            # throw pconc in nearest entity or legs
            entities_in_los = list(filter(lambda e: e.isInLineOfSight(), extremley_close_entities))
            if entities_in_los:
              ent = entities_in_los[0]
              throw_pconc_at = [ent.grid_position.x, ent.grid_position.y]
            else:
              # extend line from mover and use 25% or smth close to it
              throw_pconc_at = [poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y]
            break
          # if dodged recently and not throwing pconc atm
          if self.dodge_roll.last_use_time + 1.5 < _t:
            need_dodge = True
      
      # throw pconc for clear
      if need_dodge != True and throw_pconc_at == None and len(nearby_enemies) != 0:
        print('going to clear')
        for _i in range(1):
          really_close_enemies = list(filter(lambda e: e.distance_to_player < 20, nearby_enemies))
          # internal cd for clear
          if len(really_close_enemies) != 0:
            skill_cd = 1.3
          else:
            skill_cd = 2
          if self.pconc.last_use_time + skill_cd > _t:
            print(f'internal cd for clear {skill_cd}')
            break

          # sort enemies, if visible and not in last explosion zones 
          enemies_for_clear:List[Entity] = []
          for e in nearby_enemies:
            if e.isInLineOfSight() != True:
              continue
            was_in_explosion_area = False
            for zone in last_explosion_locations:
              if e.isInZone(*zone):
                was_in_explosion_area = True
                break
            if was_in_explosion_area != True:
              enemies_for_clear.append(e)
          if len(enemies_for_clear) == 0:
            break

          really_close_enemies = list(filter(lambda e: e.distance_to_player < 20, enemies_for_clear))
          
          if really_close_enemies:
            skill_cd = 1.3
          else:
            skill_cd = 2

          # if didnt use pconc for long, throw somewhere even if theres 1 attack val
          if self.pconc.last_use_time + skill_cd * 2 > _t:
            print("didnt use pconc for long, throw somewhere even if theres 1 attack val")
            enemies_for_clear.sort(key=lambda e: e.calculateValueForAttack(), reverse=True)
            enemy_to_attack = enemies_for_clear[0]
            # if enemies_for_clear[0].attack_value > 1:
            #   enemy_to_attack = enemies_for_clear[0]
          else:
            # if someone in radius 20, throw at him, but attack value > 2
            if really_close_enemies:
              print("someone in radius 20, throw at him, but attack value > 2")
              really_close_enemies.sort(key=lambda e: e.calculateValueForAttack(), reverse=True)
              if really_close_enemies[0].attack_value > 1:
                enemy_to_attack = really_close_enemies[0]
            # else calculate val for explosion and throw, attack value > 2
            else:
              print("else calculate val for explosion and throw, attack value > 2")
              p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
              p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
              enemies_in_sector = list(filter(lambda e: getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < search_angle_half, enemies_for_clear))
              if len(enemies_in_sector) != 0:
                enemies_in_sector.sort(key=lambda e: e.calculateValueForAttack(), reverse=True)
                if enemies_in_sector[0].attack_value > 1:
                  enemy_to_attack = enemies_in_sector[0]


      # result action
      if enemy_to_attack:
        #TODO convert entity pos into grid pos
        throw_pconc_at = [enemy_to_attack.grid_position.x, enemy_to_attack.grid_position.y]
        #TODO crop line if distance is long
        if dist(poe_bot.game_data.player.grid_pos.toList(), throw_pconc_at) > 15:
          throw_pconc_at = extendLine(poe_bot.game_data.player.grid_pos.toList(), throw_pconc_at, 0.75)
          print(f'pconc throw reduced to {throw_pconc_at}')
          
      if throw_pconc_at:
        self.pconc.sleep_multiplier = 0.2
        if self.pconc.canUse() and self.pconc.use(pos_x=throw_pconc_at[0], pos_y=throw_pconc_at[1], wait_for_execution=True) == True:
          self.last_explosion_locations[_t] = [throw_pconc_at[0] - self.pconc_area, throw_pconc_at[0] + self.pconc_area, throw_pconc_at[1] - self.pconc_area, throw_pconc_at[1] + self.pconc_area]
          print(f'adding explosion zone {_t} with {self.last_explosion_locations[_t]}')
          
          return True
          attack_skill_used = True

      if need_dodge:
        self.dodge_roll.use(pos_x=mover.grid_pos_to_step_x, pos_y=mover.grid_pos_to_step_y)
        return True

      return False
    
    # if we are staying and waiting for smth
    else:
      for iii in range(100):
        print(f'combatmodule build mover is none')
      self.staticDefence()

    return False
  def prepareToFight(self, entity: Entity):
    print(f'[PathfinderPoisonConc2.prepareToFight] call {time.time()}')
    return True
  def killUsual(self, entity:Entity, is_strong = False, max_kill_time_sec = random.randint(200,300)/10, *args, **kwargs):
    print(f'#build.killUsual {entity}')
    poe_bot = self.poe_bot
    mover = self.mover

    entity_to_kill_id = entity.id
    debuff_use_time = 0

    self.auto_flasks.useFlasks()
    
    min_distance = 70 # distance which is ok to start attacking
    keep_distance = 15 # if our distance is smth like this, kite

    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print('cannot find desired entity to kill')
      return True

    print(f'entity_to_kill {entity_to_kill}')
    
    if entity_to_kill.life.health.current < 0:
      print('entity is dead')
      return True
    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
    print(f'distance_to_entity {distance_to_entity} in killUsual')
    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    if entity_to_kill.isInLineOfSight() is False:
      print('entity_to_kill.isInLineOfSight() is False')
      return False


    start_time = time.time()
    entity_to_kill.hover(wait_till_executed=False)
    poe_bot.last_action_time = 0
    kite_distance = random.randint(35,45)
    res = True
    reversed_run = random.choice([True, False])



    while True:
      skill_used = False
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      if self.poe_bot.game_data.player.life.health.getPercentage() < self.auto_flasks.hp_thresh:
        pass #TODO kite?

      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print('cannot find desired entity to kill')
        break
      print(f'entity_to_kill {entity_to_kill}')
      if entity_to_kill.life.health.current < 1:
        print('entity is dead')
        break

      distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y) ) 
      print(f'distance_to_entity {distance_to_entity} in killUsual')
      if distance_to_entity > min_distance:
        print('getting closer in killUsual ')
        break
      current_time = time.time()
      skill_used = self.useBuffs()
      skill_use_delay = random.randint(20,30)/10
      print(f'skill_use_delay {skill_use_delay}')




      if skill_used is False and self.pconc and self.pconc.canUse():
        if self.pconc.use(updated_entity=entity_to_kill, wait_for_execution=False) != False:
          skill_used = True
        
      


      print('kiting')
      if distance_to_entity > keep_distance:
        print('away')
        p0 = (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y)
        p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
        go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
        poe_bot.mover.move(*go_back_point)
      else:
        print('around')
        point = self.poe_bot.game_data.terrain.pointToRunAround(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, kite_distance+random.randint(-1,1), check_if_passable=True, reversed=reversed_run)
        mover.move(grid_pos_x = point[0], grid_pos_y = point[1])




      if current_time  > start_time + max_kill_time_sec:
        print('exceed time')
        break
    return res




COMBAT_BUILDS = {
  'ColdDotElementalist':ColdDotElementalist,
  'LightningArrowLightningWarp':LightningArrowLightningWarp,
  "DetonateDeadMapper": DetonateDeadMapper,
  "DetonateDeadSimulacrum": DetonateDeadSimulacrum,
  "VenomGyre": VenomGyreBuild,
  "FrenzyFrostblink": FrenzyFrostblink,
  "PenanceBrandPf": PenanceBrandPf,
  "CastOnStunPf": CastOnStunPf,
  "HitBasedDeadeye": HitBasedDeadeye,
  "CfKineticBlastChampion": CfKineticBlastChampion,
  "EaBallistasEle": EaBallistasEle,
  "ScourgeArrowPf": ScourgeArrowPf,
  "HolyRelicTotemNecromancer": HolyRelicTotemNecromancer,
  "PoisonConcBouncingPf": PoisonConcBouncingPf,
  "GenericHitter": GenericHitter,
  "Bama": Bama,
}
COMBAT_BUILDS_LIST = list(COMBAT_BUILDS.keys())
def getBuild(build:str):
  return COMBAT_BUILDS[build]
