from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
  from .gamehelper import Entity, Poe2Bot, PoeBot
  from .mover import Mover

import _thread
import random
import time
from math import dist
from typing import List

import numpy as np

from .constants import AURAS_SKILLS_TO_BUFFS, CONSTANTS, DANGER_ZONE_KEYS, FLASK_NAME_TO_BUFF, SKILL_KEYS, SKILL_KEYS_WASD
from .utils import createLineIteratorWithValues, extendLine, getAngle

NON_INSTANT_MOVEMENT_SKILLS = ["shield_charge", "whirling_blades"]

INSTANT_MOVEMENT_SKILLS = ["frostblink", "flame_dash"]


class CombatModule:
  build: Build

  def __init__(self, poe_bot: PoeBot, build: str = None) -> None:
    self.poe_bot = poe_bot
    if build:
      self.build = getBuild(build)(poe_bot)
    else:
      print("build is not assigned, using any functions may throw errors")
    self.entities_to_ignore_path_keys: List[str] = []
    self.aura_manager = AuraManager(poe_bot=poe_bot)

  def assignBuild(self, build: str):
    self.build = getBuild(build)(self.poe_bot)

  def killUsualEntity(self, entity: Entity, min_hp=0, max_kill_time_sec=90, is_strong=False, step_size=random.randint(30, 35)):
    poe_bot = self.poe_bot
    mover = poe_bot.mover
    build = self.build
    print(f"#killUsualEntity {entity}")
    first_attack_time = None
    # if "/LeagueBestiary/" in entity['Path']:
    #   print(f'/LeagueBestiary/ in entity path, forcing min_hp = 1')
    #   min_hp = 1
    if entity.life.health.current == min_hp:
      print("willing to kill dead entity")
      return True

    def killEntityFunctionForMover(mover: Mover):
      nonlocal first_attack_time
      print(f"first_attack_time {first_attack_time}")
      _t = time.time()
      res = build.killUsual(entity, is_strong, max_kill_time_sec)

      if res is False:
        res = build.usualRoutine(mover)

      elif res is True and first_attack_time is None:
        first_attack_time = _t
      return res

    def entityIsDead(mover: Mover):
      _t = time.time()

      entity_to_kill = list(filter(lambda e: e.id == entity.id, poe_bot.game_data.entities.attackable_entities))
      if len(entity_to_kill) != 0:
        entity_to_kill = entity_to_kill[0]
        print(f"check first_attack_time {first_attack_time}")
        if first_attack_time is not None:
          print(f"first_attack_time + max_kill_time_sec < _t {first_attack_time} + {max_kill_time_sec} < {_t}")
          if first_attack_time + max_kill_time_sec < _t:
            print(f"killUsualEntity max_kill_time_sec {max_kill_time_sec} passed, breaking")
            return True

        if min_hp != 0:
          if entity_to_kill.life.health.current <= min_hp:
            print(f"entity_to_kill.life.health.current <= min_hp <= {min_hp}")
            return True
        return False
      else:
        print("entities_to_kill not found, looks like dead")
        return True

    res = build.killUsual(entity, is_strong, max_kill_time_sec)
    if res is True:
      return True
    # get to entity first
    if entity.distance_to_player > 100:
      print("getting closer to entity")
      mover.goToEntitysPoint(
        entity_to_go=entity,
        min_distance=100,
        custom_continue_function=build.usualRoutine,
        # custom_break_function=entityIsDead,
        step_size=step_size,
      )

    print("killing it")
    # kill it
    mover.goToEntity(
      entity_to_go=entity,
      min_distance=-1,
      custom_continue_function=killEntityFunctionForMover,
      custom_break_function=entityIsDead,
      step_size=step_size,
    )

    is_dead = entityIsDead(mover=mover)
    return is_dead

  def killTillCorpseOrDisappeared(self, entity: Entity, clear_around_radius=40, max_kill_time_sec=300, step_size=random.randint(30, 35)):
    poe_bot = self.poe_bot
    mover = self.poe_bot.mover
    build = self.build
    entity_to_kill = entity
    entity_to_kill_id = entity_to_kill.id
    if entity_to_kill.is_targetable is False or entity_to_kill.is_attackable is False:
      print("entity_to_kill is not attackable or not targetable, going to it and activating it")
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
      entity_to_kill = next((e for e in poe_bot.game_data.entities.all_entities if e.id == entity_to_kill_id), None)
      if entity_to_kill is None:
        print("entity_to_kill is None corpse disappeared:")
        return True
      last_boss_pos_x, last_boss_pos_y = entity_to_kill.grid_position.x, entity_to_kill.grid_position.y
      while True:
        entity_to_kill = next((e for e in poe_bot.game_data.entities.all_entities if e.id == entity_to_kill_id), None)
        if entity_to_kill is None:
          print("entity_to_kill is None corpse disappeared:")
          return True

        if entity_to_kill.life.health.current == 0:
          print("entity_to_kill is dead")
          return True
        if entity_to_kill.is_targetable is False or entity_to_kill.is_attackable is False:
          print("boss is not attackable or not targetable, going to it clearing around it")
          killed_someone = self.clearLocationAroundPoint(
            {"X": entity_to_kill.grid_position.x, "Y": entity_to_kill.grid_position.y}, detection_radius=clear_around_radius
          )
          if killed_someone is False:
            point = poe_bot.game_data.terrain.pointToRunAround(
              point_to_run_around_x=last_boss_pos_x,
              point_to_run_around_y=last_boss_pos_y,
              distance_to_point=15,
            )
            mover.move(grid_pos_x=point[0], grid_pos_y=point[1])
            poe_bot.refreshInstanceData()
        else:
          print("boss is attackable and targetable, going to kill it")
          self.killUsualEntity(entity_to_kill, max_kill_time_sec=30)
          last_boss_pos_x, last_boss_pos_y = entity_to_kill.grid_position.x, entity_to_kill.grid_position.y
    else:
      print("entity_to_kill is attackable and targetable, going to kill it")
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

  def clearLocationAroundPoint(self, point_to_run_around, detection_radius=20, till_no_enemies_around=False, ignore_keys=[]):
    """
    point_to_run_around
    {"X":1, "Y":1}
    """
    poe_bot = self.poe_bot
    mover = poe_bot.mover
    build = self.build
    print(f"#clearLocationAroundPoint around point {point_to_run_around} ignore_keys: {ignore_keys}")
    print(f"going to {point_to_run_around}")
    point_to_go = [point_to_run_around["X"], point_to_run_around["Y"]]
    mover.goToPoint(
      point=point_to_go, min_distance=40, release_mouse_on_end=False, custom_continue_function=build.usualRoutine, step_size=random.randint(25, 33)
    )
    poe_bot.last_action_time = 0

    def enemiesAroundPoint() -> List[Entity]:
      """
      returns entities around point
      """
      lower_x = point_to_run_around["X"] - detection_radius
      upper_x = point_to_run_around["X"] + detection_radius
      lower_y = point_to_run_around["Y"] - detection_radius
      upper_y = point_to_run_around["Y"] + detection_radius
      # enemies_around = list(filter(lambda entity:entity['IsTargetable'] is True and  entity['IsHostile'] is True and entity['GridPosition']['X'] > lower_x and entity['GridPosition']['X'] < upper_x and entity['GridPosition']['Y'] > lower_y and entity['GridPosition']['Y'] < upper_y ,  poe_bot.sorted_entities['alive_enemies']))
      enemies_around = list(
        filter(
          lambda e: e.grid_position.x > lower_x and e.grid_position.x < upper_x and e.grid_position.y > lower_y and e.grid_position.y < upper_y,
          poe_bot.game_data.entities.attackable_entities,
        )
      )
      enemies_around = list(filter(lambda e: e.isOnPassableZone(), enemies_around))
      # enemies_around = list(filter(lambda e: e.grid_position.x > lower_x and e.grid_position.x < upper_x and e.grid_position.y > lower_y and e.grid_position.y < upper_y ,  poe_bot.game_data.entities.attackable_entities))

      return enemies_around

    entities_to_kill = enemiesAroundPoint()
    if len(entities_to_kill) == 0:
      return False
    print(f"entities_to_kill around point {entities_to_kill} ")
    # in theory it may spawn essences with the same metadata but white, not rare
    killed_someone = False
    for entity in entities_to_kill:
      if any(list(map(lambda _k: _k in entity.path, ignore_keys))):
        print(f"skipping {entity.raw} cos its in ignore keys")
        continue
      killed_someone = True
      self.killUsualEntity(entity, min_hp=1, max_kill_time_sec=3)
    return killed_someone

  def clearAreaAroundPoint(self, point, detection_radius=20, till_no_enemies_around=False, ignore_keys=[]):
    point_dict = {"X": point[0], "Y": point[1]}
    return self.clearLocationAroundPoint(
      point_to_run_around=point_dict, detection_radius=detection_radius, till_no_enemies_around=till_no_enemies_around, ignore_keys=ignore_keys
    )

class AutoFlasks:
  def __init__(self, poe_bot: PoeBot, hp_thresh=0.5, mana_thresh=0.5, pathfinder=False, life_flask_recovers_es=False) -> None:
    self.poe_bot = poe_bot
    self.hp_thresh = hp_thresh
    self.mana_thresh = mana_thresh
    self.utility_flasks_delay = 1
    self.life_flasks_delay = 1
    self.mana_flasks_delay = 1
    self.flask_use_time = [0, 0, 0, 0, 0]
    self.can_use_flask_after_by_type = {
      "utility": 0,
      "mana": 0,
      "life": 0,
    }
    self.pathfinder = pathfinder
    self.life_flask_recovers_es = life_flask_recovers_es
    self.utility_flasks_use_order_reversed = random.choice([True, False])
    self.flask_delay = lambda: random.uniform(0.100, 0.200)

  def useFlask(self, flask_index, flask_type="utility"):
    time_now = time.time()
    self.can_use_flask_after_by_type[flask_type] = time_now + random.randint(100, 200) / 1000
    self.poe_bot.bot_controls.keyboard.pressAndRelease(f"DIK_{flask_index + 1}", delay=random.randint(15, 35) / 100, wait_till_executed=False)
    self.flask_use_time[flask_index] = time_now

  def useFlasks(self):
    if self.useLifeFlask() is True:
      return True
    if self.useManaFlask() is True:
      return True
    if self.useUtilityFlasks() is True:
      return True
    return False

  def useUtilityFlasks(self):
    poe_bot = self.poe_bot
    time_now = time.time()
    # to prevent it from insta flask usage
    if time_now < self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.UTILITY]:
      return False

    sorted_flasks = sorted(poe_bot.game_data.player.utility_flasks, key=lambda f: f.index, reverse=self.utility_flasks_use_order_reversed)

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
          poe_bot.logger.writeLine(f"flask bug {flask.index} {self.flask_use_time}")
        except Exception:
          poe_bot.logger.writeLine("flask bug couldnt catch")
        continue
      # check if flask buff is presented
      if flask_related_buff in poe_bot.game_data.player.buffs:
        continue
      # if avaliable on panel
      if flask.can_use is False:
        continue

      # else tap on flask
      print(f"[AutoFlasks] using utility flask {flask.name} {flask.index} at {time.time()}")
      self.useFlask(flask.index)
      # if tapped, return, so it wont look like a flask macro
      return True

    return False

  def useLifeFlask(self):
    poe_bot = self.poe_bot
    need_to_use_flask = False
    if self.life_flask_recovers_es is True:
      health_component = poe_bot.game_data.player.life.energy_shield
    else:
      health_component = poe_bot.game_data.player.life.health
    print(f"[AutoFlasks.useLifeFlask] {health_component.getPercentage()} {self.hp_thresh}")
    # life flask
    if self.pathfinder is True:
      # print(f'lifeflask pf')
      if "flask_effect_life_not_removed_when_full" not in poe_bot.game_data.player.buffs:
        print("[AutoFlasks] using lifeflask pf cos not in buffs")
        need_to_use_flask = True
      elif self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.LIFE] < time.time():
        print("[AutoFlasks] using life flask pf upfront")
        need_to_use_flask = True
      if need_to_use_flask is True:
        avaliable_life_flask = next((f for f in poe_bot.game_data.player.life_flasks if f.can_use is not False), None)
        if avaliable_life_flask is not None:
          if avaliable_life_flask.index > 5 or avaliable_life_flask.index < 0:
            return False
          print(f"[AutoFlasks] using lifeflask pf {avaliable_life_flask.name} {avaliable_life_flask.index}")
          self.useFlask(avaliable_life_flask.index, flask_type=CONSTANTS.FLASKS.FLASK_TYPES.LIFE)
          self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.LIFE] = time.time() + random.randint(270, 330) / 100
          return True
        else:
          print("[AutoFlasks] dont have any avaliable life flask for pf")
          return False
    else:
      if health_component.getPercentage() < self.hp_thresh:
        # if we already have life flask
        if (
          "flask_effect_life" not in poe_bot.game_data.player.buffs
          and "flask_effect_life_not_removed_when_full" not in poe_bot.game_data.player.buffs
        ):
          if time.time() < self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.LIFE]:
            print("[AutoFlasks] reached hp thresh but wont use life flask cos cd")
            return False
          for flask in poe_bot.game_data.player.life_flasks:
            if flask.can_use is True:
              if flask.index > 5 or flask.index < 0:
                continue
              print(f"[AutoFlasks] using life flask {flask.name} {flask.index} {type(flask.index)}")
              self.useFlask(flask.index, flask_type=CONSTANTS.FLASKS.FLASK_TYPES.LIFE)
              self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.LIFE] = time.time() + (random.randint(40, 60) / 100)
              return True
    return False

  def useManaFlask(self):
    poe_bot = self.poe_bot
    if len(poe_bot.game_data.player.mana_flasks) == 0:
      return False
    # mana flask
    if poe_bot.game_data.player.life.mana.getPercentage() < self.mana_thresh:
      # if we already have mana flask
      if (
        "flask_effect_mana" not in poe_bot.game_data.player.buffs and "flask_effect_mana_not_removed_when_full" not in poe_bot.game_data.player.buffs
      ):
        if time.time() < self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.LIFE]:
          print("[AutoFlasks] reached mana thresh but wont use life flask cos cd")
          return False
        for flask in poe_bot.game_data.player.mana_flasks:
          if flask.index > 5 or flask.index < 0:
            continue
          print(f"[AutoFlasks] using mana flask {flask.name} {flask.index}")
          self.useFlask(flask.index, flask_type=CONSTANTS.FLASKS.FLASK_TYPES.MANA)
          self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.MANA] = time.time() + (random.randint(40, 60) / 100)
          return True

    return False

class AuraManager:
  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.aura_skills = []
    self.blessing_skill: BlessingSkill = None

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
          is_blessing = next(
            (
              sd
              for sd in self.poe_bot.game_data.skills.descriptions[skill_index]
              if "SkillIsBlessingSkill" in sd.keys() or "SupportGuardiansBlessingAuraOnlyEnabledWhileSupportMinionIsSummoned" in sd.keys()
            ),
            None,
          )
          if is_blessing:
            self.blessing_skill = BlessingSkill(poe_bot=self.poe_bot, skill_index=skill_index, skill_name=skill_name, display_name=skill_name)
            print(f"{skill_name} is blessing")
            continue
          self.aura_skills.append(skill_name)
      # self.aura_skills = list(filter(lambda skill_name: skill_name in aura_keys, self.poe_bot.game_data.skills.internal_names))
      self.aura_skills = set(self.aura_skills)
    auras_to_activate = []
    for skill in self.aura_skills:
      skill_effect = AURAS_SKILLS_TO_BUFFS[skill]
      if skill_effect in self.poe_bot.game_data.player.buffs:
        print(f"{skill} already activated")
      else:
        print(f"need to activate {skill}")
        auras_to_activate.append(skill)
    print(f"total need to activate {auras_to_activate}")
    if auras_to_activate:
      indexes_to_activate = list(map(lambda skill: self.poe_bot.game_data.skills.internal_names.index(skill), auras_to_activate))
      print(f"indexes to activate {indexes_to_activate}")
      keys_to_activate = list(map(lambda skill_index: SKILL_KEYS[skill_index], indexes_to_activate))
      print(f"keys to activate {keys_to_activate}")
      first_panel_skills = list(filter(lambda key: "DIK_" in key and "CTRL+" not in key, keys_to_activate))
      second_panel_skills = list(filter(lambda key: "CTRL+DIK_" in key, keys_to_activate))
      if second_panel_skills:
        self.poe_bot.bot_controls.keyboard_pressKey("DIK_LCONTROL")
        time.sleep(random.randint(5, 15) / 100)
        for key in second_panel_skills:
          key_str = key.split("CTRL+")[1]
          self.poe_bot.bot_controls.keyboard.tap(key_str)
          time.sleep(random.randint(10, 20) / 100)
        self.poe_bot.bot_controls.keyboard_releaseKey("DIK_LCONTROL")
        time.sleep(random.randint(20, 40) / 100)
      if first_panel_skills:
        for key in first_panel_skills:
          key_str = key
          self.poe_bot.bot_controls.keyboard.tap(key_str)
          time.sleep(random.randint(10, 20) / 100)
        time.sleep(random.randint(20, 40) / 100)
      return True
    return False

  def activateBlessingsIfNeeded(self):
    if self.blessing_skill:
      print(f"activating blessing {self.blessing_skill}")
      self.blessing_skill.use()

class CombatManager:
  def __init__(self, poe_bot: PoeBot = None) -> None:
    pass

# Skill bases
class Skill:
  def __init__(
    self,
    poe_bot: PoeBot,
    skill_index: int,
    skill_name="_deprecated",
    display_name="unnamed_skill",
    min_mana_to_use=0,
    sleep_multiplier=0.5,  # if skill will have cast time, it will sleep for some time
    mana_cost=0,
    life_cost=0,
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
      "keyboard": {
        "press": bot_controls.keyboard_pressKey,
        "release": bot_controls.keyboard_releaseKey,
        "tap": bot_controls.keyboard.pressAndRelease,
      },
      "mouse": {
        "press": bot_controls.mouse.press,
        "release": bot_controls.mouse.release,
        "tap": bot_controls.mouse.click,
      },
    }

    if self.poe_bot.mover.move_type == "wasd":
      self.skill_key_raw = SKILL_KEYS_WASD[self.skill_index]
    else:
      self.skill_key_raw = SKILL_KEYS[self.skill_index]

    self.hold_ctrl = False
    key_type = "mouse"
    if "DIK" in self.skill_key_raw:
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
    """
    updates the info about last successful usage
    """
    pass

  def tap(self, wait_till_executed=True, delay=random.randint(5, 20) / 100, update=True):
    if self.hold_ctrl is True:
      self.poe_bot.bot_controls.keyboard_pressKey("DIK_LCONTROL")
      wait_till_executed = True  # to prevent it from missclicking
    self.tap_func(button=self.skill_key, wait_till_executed=wait_till_executed, delay=delay)
    if self.hold_ctrl is True:
      self.poe_bot.bot_controls.keyboard_releaseKey("DIK_LCONTROL")
    if update is not False:
      self.update()

  def press(self, wait_till_executed=True, update=True):
    """
    for holding the button, smth like LA spam on some mob
    """
    if self.hold_ctrl is True:
      self.poe_bot.bot_controls.keyboard_pressKey("DIK_LCONTROL")
    self.press_func(button=self.skill_key)
    self.holding = True
    if update is not False:
      self.update()

  def release(self, wait_till_executed=True):
    if self.hold_ctrl is True:
      self.poe_bot.bot_controls.keyboard_releaseKey("DIK_LCONTROL")
    self.release_func(button=self.skill_key)
    self.holding = False

  def checkIfCanUse(self):
    if self.min_mana_to_use != 0 and self.poe_bot.game_data.player.life.mana.current < self.min_mana_to_use:
      print(f"[Skill] cant use skill {self.display_name} cos self.poe_bot.game_data.player.life.mana.current < self.min_mana_to_use")
      return False
    if self.poe_bot.game_data.skills.can_use_skills_indexes_raw[self.skill_index] == 0:
      print(f"[Skill] cant use skill {self.display_name} cos 0 in can_use_skills_indexes_raw")
      return False
    return True

  def use(self, grid_pos_x=0, grid_pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False):
    """
    -wait_for_execution: 1
    -force: if True, itll ignore check skill usage on panel

    """
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    print(f"[Skill {self.display_name}] using  at {time.time()}")
    if force is not True and self.checkIfCanUse() is not True:
      return False
    if updated_entity is not None or grid_pos_x != 0 or grid_pos_y != 0:  # if we need to move a mouse
      if updated_entity is not None:  # if its an entity
        screen_pos_x, screen_pos_y = updated_entity.location_on_screen.x, updated_entity.location_on_screen.y
      else:
        screen_pos_x, screen_pos_y = poe_bot.getPositionOfThePointOnTheScreen(y=grid_pos_y, x=grid_pos_x)
      screen_pos_x, screen_pos_y = poe_bot.convertPosXY(screen_pos_x, screen_pos_y)
      bot_controls.mouse.setPosSmooth(screen_pos_x, screen_pos_y, wait_till_executed=False)
    start_time = time.time()
    if wait_for_execution is True:
      if self.overriden_cast_time:
        cast_time = self.overriden_cast_time
      else:
        cast_time = self.getCastTime()
      time_to_sleep = start_time - time.time() + cast_time
      if cast_time > 0:
        self.press(wait_till_executed=wait_for_execution, update=False)
        time.sleep(time_to_sleep * self.sleep_multiplier * (random.randint(9, 11) / 10))
        self.release(wait_till_executed=wait_for_execution)
      else:
        self.tap(wait_till_executed=wait_for_execution, update=False)
    else:
      self.tap(wait_till_executed=wait_for_execution, update=False)
    self.update()
    print(f"[Skill {self.display_name}] successfully used  at {time.time()}")
    return True

  def moveThenUse(self, grid_pos_x=0, grid_pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False, use_first=False):
    # hover if needed
    # send press skill button
    # wait (shorter)
    # move
    # return True
    # send release skill button

    def use_func():
      return self.use(grid_pos_x, grid_pos_y, updated_entity, False, force)

    def move_func():
      return self.poe_bot.mover.move()

    """
    - #TODO check if it's possible to execute use func, like skill is executable and whatever
    - #TODO adjust the time, if wait_for_execution == True so itll:
      either cast skill, move, wait till skill cast time
      or move, release mouse(if mover.move_type == mouse), cast, wait till skill cast time 
    """

    queue = []
    queue.append(use_func)
    if use_first is True:
      queue.insert(-1, move_func)
    else:
      queue.insert(0, move_func)
    return True

  def getCastTime(self):
    return self.poe_bot.game_data.skills.cast_time[self.skill_index]

  def convertToPos(self, pos_x, pos_y, entity: Entity = None):
    if entity is not None:
      x, y = entity.grid_position.x, entity.grid_position.y
    else:
      x, y = pos_x, pos_y
    return x, y

class AreaSkill(Skill):
  def __init__(
    self,
    poe_bot: PoeBot,
    skill_index: int,
    skill_name="tipo chtobi potom uzat skill po ego internal name",
    display_name="AreaSkill",
    area=15,
    duration=4,
  ) -> None:
    self.last_use_location = [0, 0]  # x, y
    self.last_use_time = 0
    self.area = area
    self.duration = duration
    super().__init__(poe_bot, skill_index, skill_name, display_name)

  def update(self):
    self.last_use_location = [self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y]
    self.last_use_time = time.time()

  def use(self, pos_x=0, pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False):
    dot_duration = self.duration
    if (
      dist(
        [self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y], [self.last_use_location[0], self.last_use_location[1]]
      )
      > self.area
    ):
      self.last_use_time = 0
    if time.time() - self.last_use_time < dot_duration:
      return False
    res = super().use(pos_x, pos_y, updated_entity, wait_for_execution, force=force)
    if res is True:
      x, y = self.convertToPos(pos_x, pos_y, updated_entity)
      self.last_use_location = [x, y]
    return res

class SkillWithDelay(Skill):
  def __init__(
    self,
    poe_bot: PoeBot,
    skill_index: int,
    skill_name="",
    display_name="SkillWithDelay",
    min_delay=random.randint(30, 40) / 10,
    delay_random=0.1,
    min_mana_to_use=0,
    can_use_earlier=True,
  ) -> None:
    self.min_delay = min_delay
    self.delay_random = delay_random
    self.can_use_earlier = can_use_earlier

    self.last_use_time = 0
    self.can_be_used_after = 0

    self.internal_cooldown = random.randint(100, 125) / 100
    super().__init__(poe_bot, skill_index, skill_name, display_name, min_mana_to_use)

  def update(self):
    self.last_use_time = time.time()
    if self.can_use_earlier is not False:
      _rv = [1, 0, -1]
    else:
      _rv = [1, 0]
    self.can_be_used_after = self.last_use_time + self.min_delay + random.choice(_rv) * self.delay_random * self.min_delay
    print(f"[SkillWithDelay {self.display_name}]  can be used after {self.can_be_used_after} {self.last_use_time} {self.min_delay}")

  def canUse(self, force=False):
    if force is not True and time.time() < self.can_be_used_after:
      return False
    if force is True and time.time() - self.last_use_time < self.internal_cooldown:
      print(f"[SkillWithDelay {self.display_name}] internal cooldown on force use")
      return False
    return True

  def use(self, pos_x=0, pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False):
    if self.canUse(force) is not True:
      return False
    return super().use(pos_x, pos_y, updated_entity, wait_for_execution, False)

class MinionSkillWithDelay(SkillWithDelay):
  def __init__(
    self,
    poe_bot: PoeBot,
    skill_index: int,
    skill_name="",
    display_name="SkillWithDelay",
    min_delay=random.randint(30, 40) / 10,
    delay_random=0.1,
    min_mana_to_use=0,
    can_use_earlier=True,
    minion_path_key: str | None = None,
  ) -> None:
    super().__init__(poe_bot, skill_index, skill_name, display_name, min_delay, delay_random, min_mana_to_use, can_use_earlier)
    self.minion_path_key = minion_path_key

  def getMinionsCountInRadius(self, radius: int = 150) -> int:
    if self.minion_path_key is None:
      return 0
    else:
      return len(
        list(
          filter(
            lambda e: e.life.health.current != 0 and not e.is_hostile and e.distance_to_player < radius and self.minion_path_key in e.path,
            self.poe_bot.game_data.entities.all_entities,
          )
        )
      )

class MovementSkill(Skill):
  def __init__(
    self, poe_bot: PoeBot, skill_index: int, skill_name="", display_name="MovementSkill", min_delay=random.randint(30, 40) / 10, can_extend_path=True
  ) -> None:
    self.min_delay = min_delay
    self.last_use_time = 0
    self.jump_multi = 2
    self.min_move_distance = 20
    self.can_extend_path = can_extend_path
    super().__init__(poe_bot, skill_index, skill_name, display_name)

  def update(self):
    self.last_use_time = time.time()

  def use(self, pos_x=0, pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False, extend_path=True):
    path_without_obstacles = False
    if time.time() - self.last_use_time < self.min_delay:
      return False
    if pos_x != 0 or updated_entity is not None:
      x, y = self.convertToPos(pos_x, pos_y, updated_entity)
      distance_to_next_step = dist((self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y), (x, y))
      print(f"[Combat Movement Skill] distance_to_next_step {distance_to_next_step}")
      if distance_to_next_step < self.min_move_distance:
        return False
      path_without_obstacles = self.poe_bot.game_data.terrain.checkIfPointIsInLineOfSight(x, y)
      print(f"[Combat Movement Skill] path_without_obstacles {path_without_obstacles}")
      if path_without_obstacles is not True:
        return False
      if self.can_extend_path is not False and extend_path is not False:
        pos_x, pos_y = extendLine((self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y), (x, y), self.jump_multi)
      else:
        pos_x, pos_y = x, y
    if path_without_obstacles:
      return super().use(pos_x, pos_y, updated_entity, wait_for_execution, force)
    else:
      return False

class MovementSkill_new(SkillWithDelay):
  def __init__(
    self,
    poe_bot: PoeBot,
    skill_index: int,
    skill_name="",
    display_name="MovementSkill",
    min_delay=random.randint(30, 40) / 10,
    delay_random=0.1,
    min_mana_to_use=0,
    can_use_earlier=True,
    can_extend_path=True,
  ) -> None:
    self.jump_multi = 2
    self.min_move_distance = 20
    self.can_extend_path = can_extend_path
    super().__init__(poe_bot, skill_index, skill_name, display_name, min_delay, delay_random, min_mana_to_use, can_use_earlier)

  def use(self, pos_x=0, pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False, extend_path=True, use_as_movement_skill=True):
    if self.canUse(force) is not True:
      return False

    if use_as_movement_skill is not False:
      if pos_x != 0 or updated_entity is not None:
        x, y = self.convertToPos(pos_x, pos_y, updated_entity)
        distance_to_next_step = dist((self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y), (x, y))
        print(f"[Combat Movement Skill] distance_to_next_step {distance_to_next_step}")
        if distance_to_next_step < self.min_move_distance:
          return False
        path_without_obstacles = self.poe_bot.game_data.terrain.checkIfPointIsInLineOfSight(x, y)
        print(f"[Combat Movement Skill] path_without_obstacles {path_without_obstacles}")
        if path_without_obstacles is not True:
          return False
        if self.can_extend_path is not False and extend_path is not False:
          pos_x, pos_y = extendLine((self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y), (x, y), self.jump_multi)
        else:
          pos_x, pos_y = x, y
      if path_without_obstacles:
        return super().use(pos_x, pos_y, updated_entity, wait_for_execution, force)
      else:
        return False
    else:
      return super().use(pos_x, pos_y, updated_entity, wait_for_execution, force)

class BlessingSkill(SkillWithDelay):
  def __init__(
    self,
    poe_bot: PoeBot,
    skill_index: int,
    skill_name="tipo chtobi potom uzat skill po ego internal name",
    display_name="SkillWithDelay",
    min_delay=4,
    delay_random=0.1,
    min_mana_to_use=0,
  ) -> None:
    super().__init__(poe_bot, skill_index, skill_name, display_name, min_delay, delay_random, min_mana_to_use)
    self.buff_name = AURAS_SKILLS_TO_BUFFS[display_name]

  def use(self, pos_x=0, pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False):
    if self.buff_name not in self.poe_bot.game_data.player.buffs:
      print(f"[Blessing skill] {self.buff_name} is not in buff list, forcing to cast it")
      force = True
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

# Builds
class Build:
  poe_bot: PoeBot
  chaos_immune = False
  buff_skills: List[Skill] = []
  restricted_mods: List[str] = []

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.mover = self.poe_bot.mover
    self.auto_flasks = AutoFlasks(poe_bot=poe_bot)
    # actions done during usual walking
    if getattr(self, "usualRoutine", None) is None:
      raise NotImplementedError
    # actions how does it behave during killing
    if getattr(self, "killUsual", None) is None:
      raise NotImplementedError
    # actions how does it behave during killing strong entity, suchs as simulacrum boss or whatever
    if getattr(self, "killStrong", None) is None:
      self.killStrong = self.killUsual
    # summon zombies, whatever

  def useBuffs(self):
    for buff in self.buff_skills:
      if buff.use() is True:
        return True
    return False

  def useFlasks(self):
    # smth to keep it alive, usually just enough to keep flasks,
    # but smth like cwdt needs to use flasks + tap barrier button
    self.auto_flasks.useFlasks()

  def staticDefence(self):
    poe_bot = self.poe_bot
    self.useFlasks()
    mover = self.poe_bot.mover
    detection_range = 30
    danger_zones = list(
      filter(
        lambda e: e.distance_to_player < detection_range and any(list(map(lambda key: key in e.path, DANGER_ZONE_KEYS))),
        poe_bot.game_data.entities.all_entities,
      )
    )
    if len(danger_zones) != 0:
      print(f"danger zone in range {detection_range}")
      danger_zone_str = list(map(lambda e: e.path, danger_zones))
      print(danger_zone_str)
      if self.chaos_immune is False and any(list(map(lambda s: "/LeagueArchnemesis/ToxicVolatile" in s, danger_zone_str))):
        print("dodging caustic orbs")
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
        grid_pos_x, grid_pos_y = extendLine(
          (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y),
          (nearest_caustic_orb.grid_position.x, nearest_caustic_orb.grid_position.y),
          multiplier,
        )

        poe_bot.last_action_time = 0
        mover.goToPoint(
          point=(int(grid_pos_x), int(grid_pos_y)),
          min_distance=25,
          custom_continue_function=self.usualRoutine,
          # custom_break_function=collectLootIfFound,
          release_mouse_on_end=False,
          step_size=random.randint(25, 33),
        )
        print("got behind closest")

        print("going behind center of all others")

        poe_bot.last_action_time = 0
        poe_bot.refreshInstanceData()
        poe_bot.last_action_time = 0

        caustic_orbs = list(filter(lambda e: "/LeagueArchnemesis/ToxicVolatile" in e.path, poe_bot.game_data.entities.all_entities))
        while len(caustic_orbs) != 0:
          print(f"there are still {len(caustic_orbs)} caustic orbs left, going behind them")
          if len(caustic_orbs) == 0:
            print("no caustic orbs left")
            return True

          print(f"playerpos {poe_bot.game_data.player.grid_pos.x} {poe_bot.game_data.player.grid_pos.y}")
          print(
            f"list(map(lambda e: e.grid_position.x, caustic_orbs)) {list(map(lambda e: e.grid_position.x, caustic_orbs))}  {list(map(lambda e: e.grid_position.y, caustic_orbs))}"
          )
          center_x = sum(list(map(lambda e: e.grid_position.x, caustic_orbs))) / len(caustic_orbs)
          center_y = sum(list(map(lambda e: e.grid_position.y, caustic_orbs))) / len(caustic_orbs)
          caustic_orbs_center = [center_x, center_y]
          print(f"caustic_orbs_center {caustic_orbs_center}")
          caustic_orbs_center_distance_to_player = dist(
            caustic_orbs_center, (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
          )
          need_distance = caustic_orbs_center_distance_to_player + distance_to_jump
          if need_distance < min_move_distance:
            need_distance = min_move_distance

          multiplier = need_distance / caustic_orbs_center_distance_to_player
          grid_pos_x, grid_pos_y = extendLine(
            (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (center_x, center_y), multiplier
          )

          mover.goToPoint(
            point=(int(grid_pos_x), int(grid_pos_y)),
            min_distance=25,
            custom_continue_function=self.usualRoutine,
            # custom_break_function=collectLootIfFound,
            release_mouse_on_end=False,
            step_size=random.randint(25, 33),
          )

          poe_bot.last_action_time = 0
          poe_bot.refreshInstanceData()
          poe_bot.last_action_time = 0
          caustic_orbs = list(filter(lambda e: "/LeagueArchnemesis/ToxicVolatile" in e.path, poe_bot.game_data.entities.all_entities))

        #
        pass
      elif self.chaos_immune is False and any(list(map(lambda s: "Metadata/Monsters/LeagueArchnemesis/LivingCrystal" in s, danger_zone_str))):
        print("dodging living crystals")
        living_crystals = list(
          filter(lambda e: "Metadata/Monsters/LeagueArchnemesis/LivingCrystal" in e.path and e.distance_to_player < 20, danger_zones)
        )
        if len(living_crystals) != 0:
          center_x = int(sum(list(map(lambda e: e.grid_position.x, living_crystals))) / len(living_crystals))
          center_y = int(sum(list(map(lambda e: e.grid_position.y, living_crystals))) / len(living_crystals))
          possible_points_to_dodge = []
          jump_range = 35
          print(f"living crystal center x:{center_x} y:{center_y}")
          for ix in range(-1, 2):
            for iy in range(-1, 2):
              possible_points_to_dodge.append([center_x + ix * jump_range, center_y + iy * jump_range])

          random.shuffle(possible_points_to_dodge)
          point_to_dodge = None
          for point in possible_points_to_dodge:
            is_passable = poe_bot.helper_functions.checkIfEntityOnCurrenctlyPassableArea(point[0], point[1])
            if is_passable is True:
              point_to_dodge = point
              break
          if point_to_dodge is None:
            point_to_dodge = [
              int(poe_bot.game_data.player.grid_pos.x + random.randint(-1, 1) * jump_range),
              poe_bot.game_data.player.grid_pos.y + random.randint(-1, 1) * jump_range,
            ]
          mover.goToPoint(
            point=(int(point_to_dodge[0]), int(point_to_dodge[1])),
            min_distance=25,
            custom_continue_function=self.usualRoutine,
            # custom_break_function=collectLootIfFound,
            release_mouse_on_end=False,
            step_size=random.randint(25, 33),
          )
        else:
          print("they are too far away from us")
    pass

  def pointToRunAround(self, point_to_run_around_x, point_to_run_around_y, distance_to_point=15):
    poe_bot = self.poe_bot
    our_pos = [poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y]
    # entity pos
    pos_x, pos_y = point_to_run_around_x, point_to_run_around_y

    points_around = [
      [pos_x + distance_to_point, pos_y],
      [int(pos_x + distance_to_point * 0.7), int(pos_y - distance_to_point * 0.7)],
      [pos_x, pos_y - distance_to_point],
      [int(pos_x - distance_to_point * 0.7), int(pos_y - distance_to_point * 0.7)],
      [pos_x - distance_to_point, pos_y],
      [int(pos_x - distance_to_point * 0.7), int(pos_y + distance_to_point * 0.7)],
      [pos_x, pos_y + distance_to_point],
      [int(pos_x + distance_to_point * 0.7), int(pos_y + distance_to_point * 0.7)],
      [pos_x + distance_to_point, pos_y],
    ]
    distances = list(map(lambda p: dist(our_pos, p), points_around))
    nearset_pos_index = distances.index(min(distances))
    # TODO check if next point is possible
    point = points_around[nearset_pos_index + 1]
    return point

  def prepareToFight(self, entity: Entity):
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
      portal_gem_in_skills = "town_portal" in poe_bot.backend.getSkillBar()["i_n"]
      print(f"portal_gem_in_skills {portal_gem_in_skills}")
      if portal_gem_in_skills is False:
        print("weapons swapped")
        break
      if i == 10:
        poe_bot.raiseLongSleepException("cannot swap weapon for 10 iterations")
      print("swapping weapons")

      poe_bot.bot_controls.keyboard.tap("DIK_X")
      time.sleep(random.randint(10, 20) / 10)
    return True

  def usualRoutine(self, mover: Mover = None):
    self.poe_bot.raiseLongSleepException("usualRoutine is not defined in build")

  def killUsual(self, entity: Entity, is_strong=False, max_kill_time_sec=10, *args, **kwargs):
    pass

  def doPreparations(self):
    poe_bot = self.poe_bot

    for i in range(99):
      # poe_bot.skills.update()
      portal_gem_in_skills = "town_portal" in poe_bot.backend.getSkillBar()["i_n"]
      print(f"portal_gem_in_skills {portal_gem_in_skills}")
      if portal_gem_in_skills is False:
        print("weapons swapped")
        break
      if i == 10:
        poe_bot.raiseLongSleepException("cannot swap weapon for 10 iterations")
      print("swapping weapons")

      poe_bot.bot_controls.keyboard.tap("DIK_X")
      time.sleep(random.randint(10, 20) / 10)
    poe_bot.combat_module.aura_manager.activateAurasIfNeeded()

class GenericHitter(Build):
  # lightning strike, splitting steel, frost blates, motlen strike, smite
  """
  venom gyre
  """

  poe_bot: PoeBot

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot

    self.attacking_skill = None
    self.attacking_buff = None

    self.movement_skill = None
    self.instant_movement_skill = None

    self.blood_rage = None
    main_attacking_skill = next((s for s in self.poe_bot.game_data.skills.internal_names if s in GENERIC_BUILD_ATTACKING_SKILLS), None)
    if main_attacking_skill is not None:
      attacking_buff = next((s for s in self.poe_bot.game_data.skills.internal_names if s == "smite"), None)
      if attacking_buff:
        print(f"[GenericHitter] attacking buff {attacking_buff}")
        skill_index = self.poe_bot.game_data.skills.internal_names.index(attacking_buff)
        self.attacking_buff = SkillWithDelay(
          poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(30, 50) / 10, display_name=attacking_buff
        )
    else:
      main_attacking_skill = next((s for s in self.poe_bot.game_data.skills.internal_names if s == "smite"), None)
    if main_attacking_skill is not None:
      print(f"[GenericHitter] main attacking skill {main_attacking_skill}")
      skill_index = self.poe_bot.game_data.skills.internal_names.index(main_attacking_skill)
      self.attacking_skill = SkillWithDelay(
        poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1, 5) / 100, display_name=main_attacking_skill, min_mana_to_use=0
      )
    else:
      self.poe_bot.raiseLongSleepException(
        f"[GenericHitter] couldnt find main attacking skill, skills are {self.poe_bot.game_data.skills.internal_names} "
      )
    blood_rage = next((s for s in self.poe_bot.game_data.skills.internal_names if s == "smite"), None)
    if blood_rage is not None:
      skill_index = self.poe_bot.game_data.skills.internal_names.index(blood_rage)
      self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(30, 50) / 10, display_name=blood_rage)
    self.movement_skill = None  # "new_new_shield_charge"
    self.instant_movement_skill = None  # "flame_dash"
    for skill_index in range(len(self.poe_bot.game_data.skills.internal_names)):
      skill_name = self.poe_bot.game_data.skills.internal_names[skill_index]
      if skill_name == "":
        continue
      print(skill_name, skill_index)
      if skill_name == "blood_rage":
        self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(30, 50) / 10, display_name=skill_name)
      elif skill_name in NON_INSTANT_MOVEMENT_SKILLS:
        self.movement_skill = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill_name, min_delay=random.randint(30, 50) / 100)
        if skill_name == "whirling_blades":
          self.instant_movement_skill = MovementSkill(
            poe_bot=poe_bot, skill_index=skill_index, display_name=skill_name, min_delay=random.randint(30, 50) / 100
          )
    super().__init__(poe_bot)

  def useBuffs(self):
    poe_bot = self.poe_bot
    if self.blood_rage is not None:
      if (
        "blood_rage" not in poe_bot.game_data.player.buffs
        and poe_bot.game_data.player.life.health.current / poe_bot.game_data.player.life.health.total > 0.7
      ):
        self.blood_rage.use()
        return True
    return False

  def usualRoutine(self, mover: Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()
    # if we are moving
    if mover is not None:
      self.useBuffs()
      search_angle_half = 60
      min_hold_duration = random.randint(25, 55) / 100

      nearby_enemies = list(filter(lambda e: e.isInRoi() and e.distance_to_player < 30, poe_bot.game_data.entities.attackable_entities))
      print(f"nearby_enemies: {nearby_enemies}")

      entities_to_hold_skill_on: list[Entity] = []
      if nearby_enemies:
        for iiii in range(1):
          time_now = time.time()
          nearby_visible_enemies = list(filter(lambda e: e.isInLineOfSight(), nearby_enemies))
          if not nearby_visible_enemies:
            break
          # didnt attack for a long time
          if self.attacking_skill.last_use_time + random.randint(20, 30) / 10 < time_now:
            print("didnt attack for a long time")
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
            enemies_in_sector = list(
              filter(lambda e: getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < search_angle_half, nearby_visible_enemies)
            )
            if enemies_in_sector:
              print("on the way")
              min_hold_duration = 0.1
              entities_to_hold_skill_on = enemies_in_sector
          break
      if entities_to_hold_skill_on:
        entities_to_hold_skill_on_ids = list(map(lambda e: e.id, entities_to_hold_skill_on))
        hold_start_time = time.time()
        self.attacking_skill.last_use_time = hold_start_time
        self.attacking_skill.press()
        entities_to_hold_skill_on[0].hover()
        print(f"self.attacking_skill.getCastTime() {self.attacking_skill.getCastTime()}")
        hold_duration = self.attacking_skill.getCastTime() * random.randint(25, 35) / 10
        # hold_duration = random.randint(int(self.attacking_skill.getCastTime() * 120), int(self.attacking_skill.getCastTime() * 160))/100
        print(f"hold_duration {hold_duration}")
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

  def killUsual(self, entity: Entity, is_strong=False, max_kill_time_sec=random.randint(200, 300) / 10, *args, **kwargs):
    print(f"#build.killUsual {entity}")
    poe_bot = self.poe_bot
    self.attacking_skill.last_use_time = 0
    entity_to_kill_id = entity.id
    self.auto_flasks.useFlasks()

    min_distance = 40  # distance which is ok to start attacking

    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print("cannot find desired entity to kill")
      return True
    print(f"entity_to_kill {entity_to_kill}")
    if entity_to_kill.life.health.current < 0:
      print("entity is dead")
      return True
    distance_to_entity = dist(
      (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
    )
    print(f"distance_to_entity {distance_to_entity} in killUsual")
    if distance_to_entity > min_distance:
      print("getting closer in killUsual ")
      return False
    if entity_to_kill.isInLineOfSight() is False:
      print("entity_to_kill.isInLineOfSight() is False")
      return False

    start_time = time.time()
    entity_to_kill.hover()
    self.attacking_skill.press()
    poe_bot.last_action_time = 0
    last_dodge_use_time = time.time()
    dodge_delay = random.randint(80, 140) / 100
    res = True
    while True:
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print("cannot find desired entity to kill")
        break
      print(f"entity_to_kill {entity_to_kill}")
      if entity_to_kill.life.health.current < 1:
        print("entity is dead")
        break
      distance_to_entity = dist(
        (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
      )
      print(f"distance_to_entity {distance_to_entity} in killUsual")
      if distance_to_entity > min_distance:
        print("getting closer in killUsual ")
        break
      current_time = time.time()
      self.useBuffs()
      entity_to_kill.hover()
      if self.instant_movement_skill:
        if self.attacking_skill.display_name != "flicker_strike" and current_time > last_dodge_use_time + dodge_delay:
          print("flicker strike")
          self.instant_movement_skill.tap()
          last_dodge_use_time = time.time()
      if current_time > start_time + max_kill_time_sec:
        print("exceed time")
        break
    self.attacking_skill.release()
    return res

  def prepareToFight(self, entity: Entity):
    print(f"vg.preparetofight call {time.time()}")
    poe_bot = self.poe_bot
    bot_controls = self.poe_bot.bot_controls
    pos_x, pos_y = entity.location_on_screen.x, entity.location_on_screen.y
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    self.attacking_skill.press()
    start_hold_time = time.time()
    min_hold_duration = random.randint(40, 60) / 100
    while True:
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      pos_x, pos_y = poe_bot.getPositionOfThePointOnTheScreen(y=entity.grid_position.y, x=entity.grid_position.x)
      pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
      bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      if time.time() > start_hold_time + min_hold_duration:
        break
    self.attacking_skill.release()

class GenericSummoner(Build):
  spectre_list = []
  poe_bot: PoeBot
  poe_bot: PoeBot

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    super().__init__(poe_bot)

class FacetankBuild(Build):
  """
  spams main skill till death
  """

  pass

class HitAndRunBuild(Build):
  """
  some spam skills
  # attacks several times and runs away
  """

  pass

class KiteAroundBuild(Build):
  """
  totem, minions, brands
  """

  pass

# poe2
class DodgeRoll(SkillWithDelay):
  def __init__(self, poe_bot: PoeBot):
    super().__init__(
      poe_bot=poe_bot,
      skill_index=3,
      skill_name="",
      display_name="DodgeRoll",
      min_delay=0.1,
      delay_random=0.1,
      min_mana_to_use=0,
      can_use_earlier=True,
    )
    self.skill_key = "DIK_SPACE"
    self.tap_func = poe_bot.bot_controls.keyboard.pressAndRelease
    self.press_func = poe_bot.bot_controls.keyboard_pressKey
    self.release_func = poe_bot.bot_controls.keyboard_releaseKey
    self.checkIfCanUse = lambda *args, **kwargs: True
    self.getCastTime = lambda *args, **kwargs: 0.5

class InfernalistZoomancer(Build):
  """ """

  poe_bot: PoeBot

  def __init__(self, poe_bot: PoeBot, can_kite=True) -> None:
    self.poe_bot = poe_bot
    self.can_kite = can_kite
    self.max_srs_count = 10

    flame_wall_internal_name = "firewall"
    flame_wall_index = (
      flame_wall_internal_name in self.poe_bot.game_data.skills.internal_names
      and self.poe_bot.game_data.skills.internal_names.index(flame_wall_internal_name)
    )
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
      skill_base_cast_time = next(
        (list(sd.values())[0] for sd in poe_bot.game_data.skills.descriptions[skill_index] if "BaseSpellCastTimeMs" in sd.keys()), None
      )
      if skill_base_cast_time is None:
        continue
      elif self.minion_arconist_dd is None and skill_base_cast_time == 600:
        print(f"[InfernalistZoomancer.__init__] found minion_arconist_dd_index {skill_index}")
        self.minion_arconist_dd = SkillWithDelay(
          poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(20, 30) / 10, display_name="minion_arconist_dd", can_use_earlier=False
        )
      elif self.minion_reaver_enrage is None and skill_base_cast_time == 1000:
        print(f"[InfernalistZoomancer.__init__] found minion_reaver_enrage_index {skill_index}")
        self.minion_reaver_enrage = SkillWithDelay(
          poe_bot=poe_bot, skill_index=skill_index, min_delay=random.uniform(2.5, 3.0), display_name="minion_reaver_enrage", can_use_earlier=False
        )
      elif self.minion_sniper_gas_arrow is None and skill_base_cast_time == 1250:
        print(f"[InfernalistZoomancer.__init__] found minion_sniper_gas_arrow_index {skill_index}")
        self.minion_sniper_gas_arrow = SkillWithDelay(
          poe_bot=poe_bot,
          skill_index=skill_index,
          min_delay=random.uniform(0.05, 0.15),
          display_name="minion_sniper_gas_arrow",
          can_use_earlier=False,
        )

    # TODO minion frenzy command
    # TODO minion gas arrow command

    dd_internal_name = "detonate_dead"
    detonate_dead_index = dd_internal_name in self.poe_bot.game_data.skills.internal_names and self.poe_bot.game_data.skills.internal_names.index(
      dd_internal_name
    )
    offering_internal_name = "pain_offering"
    offerening_index = offering_internal_name in self.poe_bot.game_data.skills.internal_names and self.poe_bot.game_data.skills.internal_names.index(
      offering_internal_name
    )
    flammability_internal_name = "fire_weakness"
    flammability_index = (
      flammability_internal_name in self.poe_bot.game_data.skills.internal_names
      and self.poe_bot.game_data.skills.internal_names.index(flammability_internal_name)
    )

    self.fire_skills = []

    self.flame_wall = None
    if flame_wall_index is not False:
      self.flame_wall = SkillWithDelay(
        poe_bot=poe_bot, skill_index=flame_wall_index, min_delay=random.randint(20, 30) / 10, display_name="flame_wall", can_use_earlier=False
      )
      self.fire_skills.append(self.flame_wall)

    self.unearth = None
    if unearth_index is not False:
      self.unearth = SkillWithDelay(
        poe_bot=poe_bot, skill_index=unearth_index, min_delay=random.randint(20, 30) / 10, display_name="unearth", can_use_earlier=False
      )

    self.detonate_dead = None
    if detonate_dead_index is not False:
      self.detonate_dead = SkillWithDelay(
        poe_bot=poe_bot, skill_index=detonate_dead_index, min_delay=random.uniform(3.1, 4.5), display_name="detonate_dead", can_use_earlier=False
      )
      self.fire_skills.append(self.detonate_dead)

    self.offering = None
    if offerening_index is not False:
      self.offering = SkillWithDelay(
        poe_bot=poe_bot, skill_index=offerening_index, min_delay=random.randint(20, 30) / 10, display_name="offering", can_use_earlier=False
      )

    self.flammability = None
    if flammability_index is not False:
      self.flammability = SkillWithDelay(
        poe_bot=poe_bot, skill_index=flammability_index, min_delay=random.randint(20, 30) / 10, display_name="flammability", can_use_earlier=False
      )

    self.dodge_roll = DodgeRoll(poe_bot=poe_bot)

    super().__init__(poe_bot)
    self.auto_flasks = AutoFlasks(poe_bot=poe_bot)

  def useBuffs(self):
    return False

  def usualRoutine(self, mover: Mover = None):
    print("calling usual routine")
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()

    # if we are moving
    if mover is not None:
      self.useBuffs()
      attacking_skill_delay = 2

      nearby_enemies = list(filter(lambda e: e.distance_to_player < 50 and e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      print(f"nearby_enemies: {nearby_enemies}")
      really_close_enemies = list(filter(lambda e: e.distance_to_player < 20, nearby_enemies))
      if len(really_close_enemies) != 0:
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
            alive_srs_nearby = list(
              filter(
                lambda e: not e.is_hostile
                and e.life.health.current != 0
                and e.distance_to_player < 150
                and "Metadata/Monsters/RagingSpirit/RagingSpiritPlayerSummoned" in e.path,
                self.poe_bot.game_data.entities.all_entities,
              )
            )
            if len(alive_srs_nearby) < self.max_srs_count:
              print(f"[Generic summoner] need to raise srs, current count {len(alive_srs_nearby)}")
              if self.flame_wall.use(updated_entity=enemy_to_attack, wait_for_execution=False) is True:
                attack_skill_used = True
                break
          if self.detonate_dead and self.detonate_dead.canUse():
            corpses_around = poe_bot.game_data.entities.getCorpsesArountPoint(
              poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y, 40
            )
            corpses_around = list(filter(lambda e: e.isInLineOfSight() is not False, corpses_around))
            if len(corpses_around) != 0:
              corpses_around.sort(key=lambda e: e.calculateValueForAttack())
              if corpses_around[0].attack_value != 0:
                if self.detonate_dead.use(updated_entity=corpses_around[0], wait_for_execution=False) is not False:
                  attack_skill_used = True
                  break
          if self.minion_sniper_gas_arrow and self.minion_sniper_gas_arrow.canUse():
            if self.minion_sniper_gas_arrow.use(updated_entity=enemy_to_attack, wait_for_execution=False) is True:
              attack_skill_used = True
              break
          if self.minion_reaver_enrage and self.minion_reaver_enrage.canUse():
            if self.minion_reaver_enrage.use(wait_for_execution=False) is True:
              attack_skill_used = True
              break
          if self.unearth and self.unearth.canUse():
            corpses_around = poe_bot.game_data.entities.getCorpsesArountPoint(
              poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y, 20
            )
            corpses_around = list(filter(lambda e: e.isInLineOfSight() is not False, corpses_around))
            if len(corpses_around) != 0:
              corpses_around.sort(key=lambda e: e.calculateValueForAttack())
              if corpses_around[0].attack_value != 0:
                if self.unearth.use(updated_entity=corpses_around[0], wait_for_execution=False) is not False:
                  attack_skill_used = True
                  break
          if self.offering and self.offering.canUse():
            offering_spikes = list(
              filter(lambda e: "Metadata/Monsters/OfferingSpike/PainOfferingSpike" in e.path, poe_bot.game_data.entities.all_entities)
            )
            if len(offering_spikes) == 0:
              alive_skeletons_nearby = list(
                filter(
                  lambda e: e.is_hostile is False and "Metadata/Monsters/Skeletons/PlayerSummoned/Skeleton", poe_bot.game_data.entities.all_entities
                )
              )
              if len(alive_skeletons_nearby) != 0:
                if self.offering.use(updated_entity=alive_skeletons_nearby[0], wait_for_execution=False) is not False:
                  attack_skill_used = True
                  break
        p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
        p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
        # cast first then move back
        if self.can_kite and len(nearby_enemies) > 1:
          go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
          poe_bot.mover.move(*go_back_point)
          return True
        if attack_skill_used:
          return True

        # TODO add global cooldown, so itll be able to finish casting skills
        extremley_close_entities = list(filter(lambda e: e.distance_to_player < 10, really_close_enemies))
        enemies_on_way = list(
          filter(
            lambda e: e.distance_to_player < 15 and getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < 45, really_close_enemies
          )
        )
        if extremley_close_entities or enemies_on_way:
          if self.dodge_roll.use(wait_for_execution=False) is True:
            return True

        # return True

      p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
      p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
      # go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)

      extremley_close_entities = list(filter(lambda e: e.distance_to_player < 10, really_close_enemies))
      enemies_on_way = list(
        filter(
          lambda e: e.distance_to_player < 15 and getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < 45, really_close_enemies
        )
      )
      if extremley_close_entities or enemies_on_way:
        if self.dodge_roll.use() is True:
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
    print(f"[InfernalistZoomancer.prepareToFight] call {time.time()}")
    for i in range(random.randint(2, 3)):
      self.poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      updated_entity = next((e for e in self.poe_bot.game_data.entities.all_entities if e.id == entity.id), None)
      if updated_entity is None:
        break

      self.flame_wall.use(updated_entity=updated_entity)
    return True

  def killUsual(self, entity: Entity, is_strong=False, max_kill_time_sec=random.randint(200, 300) / 10, *args, **kwargs):
    print(f"#build.killUsual {entity}")
    poe_bot = self.poe_bot
    mover = self.mover

    entity_to_kill_id = entity.id

    self.auto_flasks.useFlasks()

    min_distance = 70  # distance which is ok to start attacking
    keep_distance = 15  # if our distance is smth like this, kite

    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print("cannot find desired entity to kill")
      return True

    print(f"entity_to_kill {entity_to_kill}")

    if entity_to_kill.life.health.current < 0:
      print("entity is dead")
      return True

    distance_to_entity = dist(
      (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
    )
    print(f"distance_to_entity {distance_to_entity} in killUsual")
    if distance_to_entity > min_distance:
      print("getting closer in killUsual ")
      return False

    if entity_to_kill.isInLineOfSight() is False:
      print("entity_to_kill.isInLineOfSight() is False")
      return False

    start_time = time.time()
    entity_to_kill.hover(wait_till_executed=False)
    poe_bot.last_action_time = 0
    kite_distance = random.randint(35, 45)
    res = True
    reversed_run = random.choice([True, False])

    while True:
      skill_used = False
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      if self.poe_bot.game_data.player.life.health.getPercentage() < self.auto_flasks.hp_thresh:
        pass  # TODO kite?

      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print("cannot find desired entity to kill")
        break
      print(f"entity_to_kill {entity_to_kill}")
      if entity_to_kill.life.health.current < 1:
        print("entity is dead")
        break

      distance_to_entity = dist(
        (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
      )
      print(f"distance_to_entity {distance_to_entity} in killUsual")
      if distance_to_entity > min_distance:
        print("getting closer in killUsual ")
        break
      current_time = time.time()
      skill_used = self.useBuffs()
      skill_use_delay = random.randint(20, 30) / 10
      print(f"skill_use_delay {skill_use_delay}")

      if skill_used is False and self.flame_wall and self.flame_wall.last_use_time + skill_use_delay < time.time():
        alive_srs_nearby = list(
          filter(
            lambda e: not e.is_hostile
            and e.life.health.current != 0
            and e.distance_to_player < 150
            and "Metadata/Monsters/RagingSpirit/RagingSpiritPlayerSummoned" in e.path,
            self.poe_bot.game_data.entities.all_entities,
          )
        )
        if len(alive_srs_nearby) < self.max_srs_count:
          print("[Generic summoner] need to raise srs")
          if self.flame_wall.use(updated_entity=entity_to_kill, wait_for_execution=False) is True:
            skill_used = True
      if skill_used is False and self.detonate_dead and self.detonate_dead.canUse():
        corpses_around = poe_bot.game_data.entities.getCorpsesArountPoint(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, 40)
        corpses_around = list(filter(lambda e: e.isInLineOfSight() is not False, corpses_around))
        if len(corpses_around) != 0:
          corpses_around.sort(key=lambda e: e.calculateValueForAttack())
          if corpses_around[0].attack_value != 0:
            if self.detonate_dead.use(updated_entity=corpses_around[0], wait_for_execution=False) is not False:
              skill_used = True
      if skill_used is False and self.unearth and self.unearth.canUse():
        corpses_around = poe_bot.game_data.entities.getCorpsesArountPoint(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, 20)
        corpses_around = list(filter(lambda e: e.isInLineOfSight() is not False, corpses_around))
        if len(corpses_around) != 0:
          corpses_around.sort(key=lambda e: e.calculateValueForAttack())
          if corpses_around[0].attack_value != 0:
            if self.unearth.use(updated_entity=corpses_around[0], wait_for_execution=False) is not False:
              skill_used = True
      if skill_used is False and self.minion_reaver_enrage and self.minion_reaver_enrage.canUse():
        if self.minion_reaver_enrage.use(updated_entity=entity_to_kill, wait_for_execution=False) is not False:
          skill_used = True

      if skill_used is False and self.minion_sniper_gas_arrow and self.minion_sniper_gas_arrow.canUse():
        if self.minion_sniper_gas_arrow.use(updated_entity=entity_to_kill, wait_for_execution=False) is not False:
          skill_used = True

      print("kiting")
      if distance_to_entity > keep_distance:
        print("away")
        p0 = (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y)
        p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
        go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
        poe_bot.mover.move(*go_back_point)
      else:
        print("around")
        point = self.poe_bot.game_data.terrain.pointToRunAround(
          entity_to_kill.grid_position.x,
          entity_to_kill.grid_position.y,
          kite_distance + random.randint(-1, 1),
          check_if_passable=True,
          reversed=reversed_run,
        )
        mover.move(grid_pos_x=point[0], grid_pos_y=point[1])

      if current_time > start_time + max_kill_time_sec:
        print("exceed time")
        break
    return res

class PathfinderPoisonConc2(Build):
  """ """

  poe_bot: Poe2Bot

  def __init__(self, poe_bot: Poe2Bot) -> None:
    self.poe_bot = poe_bot

    self.last_explosion_loc = [0, 1, 0, 1]
    self.last_explosion_locations = {
      # "use_time": [grid pos area x1 x2 y1 y2]
    }
    self.pconc_area = 20
    self.pconc_area_reset_timer_sec = 4
    self.pconc_area_in_legs_reset_timer_sec = 2

    self.pconc: SkillWithDelay = None
    self.curse: SkillWithDelay = None
    self.wither_totem: SkillWithDelay = None

    pconc_internal_name = "throw_flask_poison"
    curse_internal_names = ["despair"]
    wither_totem_internal_name = "dark_effigy"

    pconc_on_panel = next((s for s in self.poe_bot.game_data.skills.internal_names if s == pconc_internal_name), None)
    if pconc_on_panel is not None:
      print(pconc_on_panel)
      pconc_index = self.poe_bot.game_data.skills.internal_names.index(pconc_on_panel)
      # print(pconc_on_panel, pcon)
      self.pconc = SkillWithDelay(
        poe_bot=poe_bot, skill_index=pconc_index, min_delay=random.randint(1, 5) / 100, display_name=pconc_internal_name, min_mana_to_use=0
      )
      self.pconc.sleep_multiplier = 0.2

    curse_on_panel = next((s for s in self.poe_bot.game_data.skills.internal_names if s in curse_internal_names), None)
    if curse_on_panel is not None:
      curse_index = self.poe_bot.game_data.skills.internal_names.index(curse_on_panel)
      self.curse = SkillWithDelay(poe_bot=poe_bot, skill_index=curse_index, min_delay=random.randint(30, 50) / 10, display_name=curse_on_panel)

    wither_totem_on_panel = next((s for s in self.poe_bot.game_data.skills.internal_names if s == wither_totem_internal_name), None)
    if wither_totem_on_panel is not None:
      wither_totem_index = self.poe_bot.game_data.skills.internal_names.index(wither_totem_on_panel)
      self.wither_totem = SkillWithDelay(
        poe_bot=poe_bot, skill_index=wither_totem_index, min_delay=random.randint(30, 50) / 10, display_name=wither_totem_on_panel
      )
    self.dodge_roll = DodgeRoll(poe_bot=poe_bot)
    super().__init__(poe_bot)
    self.auto_flasks = AutoFlasks(poe_bot=poe_bot)
    self.auto_flasks.hp_thresh = 0.75

  def useBuffs(self):
    return False

  def usualRoutine(self, mover: Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()

    # if we are moving
    if mover is not None:
      print("calling usual routine")

      _t = time.time()
      if self.dodge_roll.last_use_time + 0.35 > _t or self.pconc.last_use_time + (self.pconc.getCastTime() / 2) > _t:
        print("probably casting smth atm")
        return False

      need_dodge = False
      throw_pconc_at = None  # [x,y] grid pos
      enemy_to_attack: Entity = None
      really_close_enemies_distance = 50
      pconc_explode_area = self.pconc_area
      search_angle = 90
      search_angle_half = search_angle / 2

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
          print(f"removing explosion zone {k} with {self.last_explosion_locations[k]} , expired")
          del self.last_explosion_locations[k]

      last_explosion_locations = list(self.last_explosion_locations.values())

      # nearby_enemies = list(filter(lambda e: e.distance_to_player < 50 and e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      nearby_enemies = list(filter(lambda e: e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      print(f"nearby_enemies: {nearby_enemies}")
      really_close_enemies = list(filter(lambda e: e.distance_to_player < 20, nearby_enemies))
      extremley_close_entities = list(filter(lambda e: e.distance_to_player < 20, nearby_enemies))

      # surrounded
      if len(extremley_close_entities) > 2:
        print("surrounded")
        for _i in range(1):
          did_throw_pconc_in_legs_recently = False
          # #recently for throw in legs reduced timer
          # last_explosion_locations_in_legs_keys = list(filter(lambda k: k + self.pconc_area_in_legs_reset_timer_sec > _t, list(self.last_explosion_locations.keys()) ))
          # last_explosion_locations_in_legs = list(map(lambda k: self.last_explosion_locations[k], last_explosion_locations_in_legs_keys))
          # for zone in last_explosion_locations_in_legs:
          #   if self.poe_bot.game_data.player.isInZone(*zone):
          #     did_throw_pconc_in_legs_recently = True
          #     print(f'did throw pconc nearby recently')
          #     break

          # TODO add cooldown to it?
          if did_throw_pconc_in_legs_recently is False:
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
          if self.dodge_roll.last_use_time + 1 < _t:
            need_dodge = True

      # throw pconc for clear
      if need_dodge is not True and throw_pconc_at is None and len(nearby_enemies) != 0:
        print("going to clear")
        for _i in range(1):
          really_close_enemies = list(filter(lambda e: e.distance_to_player < really_close_enemies_distance, nearby_enemies))
          # internal cd for clear
          if len(really_close_enemies) != 0:
            pass
          else:
            pass

          # if self.pconc.last_use_time + skill_cd > _t:
          #   print(f'internal cd for clear {skill_cd}')
          #   break

          # sort enemies, if visible and not in last explosion zones
          enemies_for_clear: List[Entity] = []
          for e in nearby_enemies:
            if e.isInLineOfSight() is not True:
              continue
            was_in_explosion_area = False
            for zone in last_explosion_locations:
              if e.isInZone(*zone):
                was_in_explosion_area = True
                break
            if was_in_explosion_area is not True:
              enemies_for_clear.append(e)
          if len(enemies_for_clear) == 0:
            print("no enemies outside of the zone")
            break

          really_close_enemies = list(filter(lambda e: e.distance_to_player < really_close_enemies_distance, enemies_for_clear))

          if really_close_enemies:
            pass
          else:
            pass

          # if didnt use pconc for long, throw somewhere even if theres 1 attack val
          if True:
            # if self.pconc.last_use_time + skill_cd * 2 < _t:
            print("didnt use pconc for long, throw somewhere even if theres 1 attack val")
            enemies_for_clear.sort(key=lambda e: e.calculateValueForAttack(), reverse=True)
            enemy_to_attack = enemies_for_clear[0]
            print(f"enemy_to_attack.attack_value {enemy_to_attack.attack_value} {enemy_to_attack.raw}")
            # min 1, max 4
            attack_val_mult = min(max(enemy_to_attack.attack_value, 1), 3)
            if enemy_to_attack.attack_value > 4:
              pconc_explode_area = int(self.pconc_area * attack_val_mult)
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
              enemies_in_sector = list(
                filter(lambda e: getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < search_angle_half, enemies_for_clear)
              )
              if len(enemies_in_sector) != 0:
                enemies_in_sector.sort(key=lambda e: e.calculateValueForAttack(), reverse=True)
                if enemies_in_sector[0].attack_value > 1:
                  enemy_to_attack = enemies_in_sector[0]

      # result action
      enemy_to_attack_cropped_pos = False
      if enemy_to_attack:
        # TODO convert entity pos into grid pos
        throw_pconc_at = [enemy_to_attack.grid_position.x, enemy_to_attack.grid_position.y]
        # TODO crop line if distance is long
        if dist(poe_bot.game_data.player.grid_pos.toList(), throw_pconc_at) > 15:
          throw_pconc_at = extendLine(poe_bot.game_data.player.grid_pos.toList(), throw_pconc_at, 0.75)
          print(f"pconc throw reduced to {throw_pconc_at}")
          enemy_to_attack_cropped_pos = True

      if throw_pconc_at:
        if self.pconc.canUse() and self.pconc.use(pos_x=throw_pconc_at[0], pos_y=throw_pconc_at[1], wait_for_execution=True) is True:
          self.last_explosion_locations[_t] = [
            throw_pconc_at[0] - pconc_explode_area,
            throw_pconc_at[0] + pconc_explode_area,
            throw_pconc_at[1] - pconc_explode_area,
            throw_pconc_at[1] + pconc_explode_area,
          ]
          print(f"adding explosion zone {_t} with {self.last_explosion_locations[_t]}")
          if enemy_to_attack_cropped_pos:
            self.last_explosion_locations[_t + 0.001] = [
              enemy_to_attack.grid_position.x - pconc_explode_area,
              enemy_to_attack.grid_position.x + pconc_explode_area,
              enemy_to_attack.grid_position.y - pconc_explode_area,
              enemy_to_attack.grid_position.y + pconc_explode_area,
            ]

          # return True
          return False

      if need_dodge:
        self.dodge_roll.use(pos_x=mover.grid_pos_to_step_x, pos_y=mover.grid_pos_to_step_y)
        return False
        # return True

      return False

    # if we are staying and waiting for smth
    else:
      for iii in range(100):
        print("combatmodule build mover is none")
      self.staticDefence()

    return False

  def prepareToFight(self, entity: Entity):
    print(f"[PathfinderPoisonConc2.prepareToFight] call {time.time()}")
    return True

  def killUsual(self, entity: Entity, is_strong=False, max_kill_time_sec=random.randint(200, 300) / 10, *args, **kwargs):
    print(f"#build.killUsual {entity}")
    poe_bot = self.poe_bot
    mover = self.mover
    entity_to_kill_id = entity.id

    self.auto_flasks.useFlasks()

    keep_distance = 15  # if our distance is smth like this, kite

    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print("cannot find desired entity to kill")
      return True

    print(f"entity_to_kill {entity_to_kill}")

    if entity_to_kill.life.health.current < 0:
      print("entity is dead")
      return True
    if entity_to_kill.isInRoi() is False or entity_to_kill.isInLineOfSight() is False:
      # if distance_to_entity > min_distance:
      print("getting closer in killUsual ")
      return False

    start_time = time.time()
    entity_to_kill.hover(wait_till_executed=False)
    kite_distance = random.randint(35, 45)
    reversed_run = random.choice([True, False])
    res = True
    poe_bot.last_action_time = 0

    while True:
      skill_used = False
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      if self.poe_bot.game_data.player.life.health.getPercentage() < self.auto_flasks.hp_thresh:
        pass  # TODO kite?

      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print("cannot find desired entity to kill")
        break
      print(f"entity_to_kill {entity_to_kill}")
      if entity_to_kill.life.health.current < 1:
        print("entity is dead")
        break
      if entity_to_kill.isInRoi() is False or entity_to_kill.isInLineOfSight() is False:
        print("getting closer in killUsual ")
        break
      distance_to_entity = dist(
        (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
      )
      print(f"distance_to_entity {distance_to_entity} in killUsual")

      current_time = time.time()
      skill_used = self.useBuffs()
      skill_use_delay = random.randint(20, 30) / 10
      print(f"skill_use_delay {skill_use_delay}")

      if skill_used is False and self.pconc and self.pconc.last_use_time + (self.pconc.getCastTime() / 2) < time.time():
        if self.pconc.use(updated_entity=entity_to_kill, wait_for_execution=False) is not False:
          skill_used = True

      print("kiting")
      if distance_to_entity > keep_distance:
        print("around")
        point = self.poe_bot.game_data.terrain.pointToRunAround(
          entity_to_kill.grid_position.x,
          entity_to_kill.grid_position.y,
          kite_distance + random.randint(-1, 1),
          check_if_passable=True,
          reversed=reversed_run,
        )
        mover.move(grid_pos_x=point[0], grid_pos_y=point[1])
      else:
        print("away")
        p0 = (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y)
        p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
        go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
        poe_bot.mover.move(*go_back_point)

      if current_time > start_time + max_kill_time_sec:
        print("exceed time")
        break
    return res

GENERIC_BUILD_ATTACKING_SKILLS = [
  "spark",
  "lightning_arrow",
  "tempest_flurry",
  "storm_wave",
  "quarterstaff_combo_attack",
]

class GenericBuild2(Build):
  def __init__(self, poe_bot):
    super().__init__(poe_bot)
    self.last_action_time = 0
    self.attacking_skill: SkillWithDelay = None  # smth like la or sparks
    self.supporting_skill: SkillWithDelay = None  # smth like lightning rod or flame wall

    main_attacking_skill = next((s for s in self.poe_bot.game_data.skills.internal_names if s in GENERIC_BUILD_ATTACKING_SKILLS), None)
    if main_attacking_skill is None:
      self.poe_bot.raiseLongSleepException(f"[GenericBuild2.init] couldnt find skills from {GENERIC_BUILD_ATTACKING_SKILLS}")

    print(f"[GenericBuild2] main attacking skill {main_attacking_skill}")
    skill_index = self.poe_bot.game_data.skills.internal_names.index(main_attacking_skill)
    self.attacking_skill = SkillWithDelay(
      poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1, 5) / 100, display_name=main_attacking_skill, min_mana_to_use=0
    )
    self.dodge_roll = DodgeRoll(poe_bot=poe_bot)
    self.dodge_roll.min_delay = 0.75

  def usualRoutine(self, mover: Mover):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()

    # _t = time.time()
    # if self.dodge_roll.last_use_time + 0.35 > _t or self.pconc.last_use_time + (self.pconc.getCastTime() / 2) > _t:
    #   print(f'probably casting smth atm')
    #   return False
    self.useBuffs()
    nearby_enemies = list(filter(lambda e: e.isInRoi() and e.isInLineOfSight(), poe_bot.game_data.entities.attackable_entities))
    if len(nearby_enemies) == 0:
      return False

    nearby_enemies.sort(key=lambda e: e.distance_to_player)
    self.attacking_skill.use(updated_entity=nearby_enemies[0], wait_for_execution=False)
    return False

  def killUsual(self, entity, is_strong=False, max_kill_time_sec=10, *args, **kwargs):
    poe_bot = self.poe_bot
    entity_to_kill_id = entity.id
    self.auto_flasks.useFlasks()
    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print("[build.killUsual] cannot find desired entity to kill")
      return True
    if entity_to_kill.life.health.current == 0:
      print("[build.killUsual] entity is dead")
      return True
    if entity_to_kill.isInRoi() is False or entity_to_kill.isInLineOfSight() is False:
      print("[build.killUsual] getting closer in killUsual")
      return False

    keep_distance = 30  # if our distance is smth like this, kite
    start_time = time.time()
    kite_distance = random.randint(35, 45)
    reversed_run = random.choice([True, False])

    entity_to_kill.hover(wait_till_executed=False)
    self.attacking_skill.press(wait_till_executed=False)
    poe_bot.last_action_time = 0
    while True:
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print("[build.killUsual] cannot find desired entity to kill")
        break
      print(f"[build.killUsual] entity_to_kill {entity_to_kill}")
      if entity_to_kill.life.health.current == 0:
        print("[build.killUsual] entity is dead")
        break
      if entity_to_kill.isInRoi() is False or entity_to_kill.isInLineOfSight() is False:
        print("[build.killUsual] getting closer in killUsual ")
        break

      self.useBuffs()
      entity_to_kill.hover()

      if entity_to_kill.distance_to_player > keep_distance:
        print("[build.killUsual] kiting around")
        point = self.poe_bot.game_data.terrain.pointToRunAround(
          entity_to_kill.grid_position.x,
          entity_to_kill.grid_position.y,
          kite_distance + random.randint(-1, 1),
          check_if_passable=True,
          reversed=reversed_run,
        )
        poe_bot.mover.move(grid_pos_x=point[0], grid_pos_y=point[1])
      else:
        print("[build.killUsual] kiting away")
        p0 = (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y)
        p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
        go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
        poe_bot.mover.move(*go_back_point)

      if time.time() > start_time + max_kill_time_sec:
        print("[build.killUsual] exceed time")
        break
    self.attacking_skill.release()
    return True

class GenericBuild2Cautious(GenericBuild2):
  def usualRoutine(self, mover: Mover):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()

    can_do_action = True
    moving_back = False
    dodging = False

    _t = time.time()
    if self.dodge_roll.last_use_time + 0.35 > _t or self.attacking_skill.last_use_time + (self.attacking_skill.getCastTime() / 2) > _t:
      print("probably casting smth atm")
      can_do_action = False
    if can_do_action:
      self.useBuffs()
    nearby_enemies = list(filter(lambda e: e.isInRoi() and e.isInLineOfSight(), poe_bot.game_data.entities.attackable_entities))
    if len(nearby_enemies) == 0:
      return moving_back
    nearby_enemies.sort(key=lambda e: e.distance_to_player)
    enemies_in_radius_50 = list(filter(lambda e: e.distance_to_player < 50, nearby_enemies))
    if len(enemies_in_radius_50) > 1:
      p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
      p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
      go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
      poe_bot.mover.move(*go_back_point)
      moving_back = True
      if can_do_action and len(list(filter(lambda e: e.distance_to_player < 15, enemies_in_radius_50))) != 0:
        dodging = self.dodge_roll.use(wait_for_execution=False)
    if can_do_action and dodging is not True:
      self.attacking_skill.use(updated_entity=nearby_enemies[0], wait_for_execution=False)
    return moving_back

class LoopController:
  def __init__(self, poe_bot: Poe2Bot, build):
    self.poe_bot = poe_bot
    self.running = False

    self.build: BarrierInvocationInfernalist = build

    self.last_analyzed_timestamp = 0.0

    self.keep_thread_alive_till = 0.0
    self.hold_till = 0.0
    self.terminate_thread_after_inactivity_secs = 2.0
    self.terminate_thread_due_to_expired_data_secs = 0.33

  def start(self):
    poe_bot = self.poe_bot
    self.running = True
    print("[LoopController.start] thread starting")

    barrier_uses_history = [0 for x in range(10)]
    barrier_loop_running = False
    expected_change_history = [False for x in range(10)]
    change_result_history = [False for x in range(10)]

    def startLooping():
      pass

    while self.running:
      if time.time() > poe_bot.game_data.last_update_time + self.terminate_thread_due_to_expired_data_secs:
        # if time.time() + self.terminate_thread_due_to_expired_data_secs > poe_bot.game_data.last_update_time:
        print("[LoopController.start] terminating thread due to expired data")
        break

      if time.time() > self.keep_thread_alive_till:
        print("[LoopController] terminating thread due to inactivity")
        break

      if self.last_analyzed_timestamp == poe_bot.game_data.last_update_time:
        # nothing changed
        time.sleep(0.02)
        continue
      self.last_analyzed_timestamp = poe_bot.game_data.last_update_time

      barrier_uses_history.pop(0)
      barrier_uses = poe_bot.game_data.skills.total_uses[self.build.barrier_invocation.skill_index]
      barrier_uses_history.append(barrier_uses)

      expected_change_history.pop(0)
      expected_change_history.append(barrier_loop_running)

      change_result_history.pop(0)
      change_result_history.append(barrier_uses_history[-1] != barrier_uses_history[-2])
      # print(f'{barrier_uses_history}')
      # print(f'{expected_change_history}')
      # print(f'{change_result_history}')
      buffs = poe_bot.game_data.player.buffs
      is_ignited = "ignited" in buffs
      is_in_demon_form = "demon_form_spell_gem_buff" in buffs
      is_barrier_charged = "invocation_skill_ready" in buffs

      active_flask_effects_count = len(list(filter(lambda e: e == "flask_effect_life", poe_bot.game_data.player.buffs)))
      print(f"[BarrierInvocationInfernalist.useFlasks] flask_effects_active_count: {active_flask_effects_count}")

      pressed_smth = False
      if pressed_smth is False and is_in_demon_form is False:
        print("[BarrierInvocationInfernalist.useFlasks] need to activate demon form")
        if self.build.demon_form.canUse():
          self.build.demon_form.use()

      if (is_ignited or barrier_loop_running) and time.time() > self.build.can_use_flask_after:
        if active_flask_effects_count < 5:
          for flask in poe_bot.game_data.player.life_flasks:
            if flask.can_use is True:
              if flask.index > 5 or flask.index < 0:
                continue
              print(f"[AutoFlasks] using life flask {flask.name} {flask.index} {type(flask.index)}")
              self.poe_bot.bot_controls.keyboard.pressAndRelease(
                f"DIK_{flask.index + 1}", delay=random.randint(15, 35) / 100, wait_till_executed=False
              )
              self.build.can_use_flask_after = time.time() + random.uniform(0.40, 0.50)
              break
      else:
        self.build.auto_flasks.useFlasks()
      barrier_invocation_key = self.build.barrier_invocation.skill_key
      if self.build.stop_spamming_condition_func() is False:
        # if poe_bot.game_data.player.life.energy_shield.getPercentage() > 0.75:
        if barrier_loop_running is False and is_barrier_charged is False:
          print("barrier is not charged")
          self.build.curse.use()
        else:
          barrier_loop_running = True
          if (barrier_invocation_key in poe_bot.bot_controls.keyboard.pressed) is False:
            print(f"pressing button {barrier_invocation_key}")
            poe_bot.bot_controls.keyboard_pressKey(barrier_invocation_key, False)
            pressed_smth = True
      else:
        print(f"seems like hp is < {self.build.es_thresh_for_loop} cant do loop thing")
        if self.build.barrier_invocation.skill_key in poe_bot.bot_controls.keyboard.pressed:
          print(f"releasing button {self.build.barrier_invocation.skill_key}")
          poe_bot.bot_controls.keyboard_releaseKey(self.build.barrier_invocation.skill_key, False)
          pressed_smth = True
          barrier_loop_running = False

      if barrier_loop_running:
        if all(expected_change_history[-3:]):
          changed_in_past = any(change_result_history[-3:])
          print(f"barrier running for 3+ cycles already {changed_in_past}")
          if changed_in_past is False:
            poe_bot.bot_controls.keyboard_releaseKey(self.build.barrier_invocation.skill_key, False)
            barrier_loop_running = False

      time.sleep(0.05)

    print("[LoopController.start] thread finished")
    if self.build.barrier_invocation.skill_key in poe_bot.bot_controls.keyboard.pressed:
      print(f"releasing button {self.build.barrier_invocation.skill_key}")
      poe_bot.bot_controls.keyboard_releaseKey(self.build.barrier_invocation.skill_key, False)

    self.running = False
    self.last_analyzed_timestamp = 0

  def keepAlive(self):
    self.keep_thread_alive_till = time.time() + self.terminate_thread_after_inactivity_secs

  def keepLoopingFor(self, t=5.0):
    self.keepAlive()
    self.hold_till = time.time() + t
    if self.running is False:
      _thread.start_new_thread(self.start, ())

  def forceStopHolding(self):
    self.keepAlive()
    self.hold_till = 0.0

class ButtonHolder:
  def __init__(self, poe_bot: Poe2Bot, button: str, max_hold_duration=10.0, custom_break_function=lambda: False):
    self.poe_bot = poe_bot
    self.thread_finished = [False]
    self.can_hold_till = [0]
    self.custom_break_function = custom_break_function

    self.button = button
    self.press_func = poe_bot.bot_controls.keyboard_pressKey
    self.release_func = poe_bot.bot_controls.keyboard_releaseKey

    self.max_hold_duration = max_hold_duration

    self.keep_thread_till = 0.0
    self.terminate_thread_after_inactivity_secs = 2.0

    self.running = False

  def start(self):
    self.running = True
    poe_bot = self.poe_bot
    print(f"[ButtonHolder.start] started at {time.time()}")
    while self.thread_finished[0] is not True:
      if time.time() < self.can_hold_till[0]:
        if (self.button in poe_bot.bot_controls.keyboard.pressed) is False:
          print(f"pressing button {self.button}")
          self.press_func(self.button, False)
      else:
        if self.button in poe_bot.bot_controls.keyboard.pressed:
          print(f"releasing button {self.button}")
          self.release_func(self.button, False)

      if time.time() > self.keep_thread_till:
        print("terminating thread due to inactivity")
        break

      if self.custom_break_function() is True:
        print("breaking because of condition")
        break
      time.sleep(0.02)
    if self.button in poe_bot.bot_controls.keyboard.pressed:
      print(f"releasing button {self.button}")
      self.release_func(self.button, False)
    print(f"[ButtonHolder.start] finished at {time.time()}")
    self.running = False

  def keepAlive(self):
    self.keep_thread_till = time.time() + self.terminate_thread_after_inactivity_secs

  def forceStopPress(self):
    self.keepAlive()
    self.can_hold_till[0] = 0
    print("releasing")

  def holdFor(self, t: float):
    self.keepAlive()
    self.can_hold_till[0] = time.time() + t
    print(f"will hold till {self.can_hold_till[0]}")
    if self.running is not True:
      _thread.start_new_thread(self.start, ())

class BarrierInvocationInfernalist(Build):
  def __init__(self, poe_bot):
    super().__init__(poe_bot)
    self.auto_flasks.life_flask_recovers_es = True
    self.auto_flasks.hp_thresh = 0.75
    self.can_use_flask_after = 0.0
    self.barrier_charged_at = 0.0
    self.es_thresh_for_loop = 0.5
    self.stop_spamming_condition_func = lambda: poe_bot.game_data.player.life.energy_shield.getPercentage() < self.es_thresh_for_loop

    self.barrier_invocation: SkillWithDelay
    self.curse: SkillWithDelay
    self.demon_form: SkillWithDelay

    demon_form = next((s for s in poe_bot.game_data.skills.internal_names if s == "demon_transformation"), None)
    if demon_form:
      print("found demon form")
      skill_index = poe_bot.game_data.skills.internal_names.index("demon_transformation")
      self.demon_form = SkillWithDelay(poe_bot, skill_index)
      self.demon_form.overriden_cast_time = 0.1
    else:
      raise Exception("demon form not found")
    curse = next((s for s in poe_bot.game_data.skills.internal_names if s == "cold_weakness"), None)
    if curse:
      print("found curse")
      skill_index = poe_bot.game_data.skills.internal_names.index("cold_weakness")
      self.curse = SkillWithDelay(poe_bot, skill_index, min_delay=0.1)
    else:
      raise Exception("cwdt activator not found")

    barrier_button = next((s for s in poe_bot.game_data.skills.internal_names if s == "barrier_invocation"), None)
    for i in range(3, 8):
      if self.poe_bot.game_data.skills.internal_names[i] == "barrier_invocation":
        barrier_button = SKILL_KEYS_WASD[i]
        print(f"barrier button is {barrier_button}")
        break
    if barrier_button is None:
      poe_bot.raiseLongSleepException("barrier set to mouse, couldnt find barrier on keyboard qwert, press it on qwert")

    if barrier_button:
      print("found barrier_invocation")
      skill_index = poe_bot.game_data.skills.internal_names.index("barrier_invocation")
      self.barrier_invocation = SkillWithDelay(poe_bot, skill_index, min_delay=0.1)
    else:
      raise Exception("cwdt trigger not found")

    self.cwdt_loop = LoopController(poe_bot, self)

    self.dodge = DodgeRoll(self.poe_bot)

  def generateStacks(self, stacks_count=60):
    poe_bot = self.poe_bot
    demon_stacks = poe_bot.combat_module.build.getDemonFormStacks()
    while demon_stacks < stacks_count:
      poe_bot.refreshInstanceData()
      demon_stacks = self.getDemonFormStacks()
      print(f"[generateDemonFormStacks] generating stacks, {demon_stacks}/{stacks_count} ")
      is_barrier_charged = "invocation_skill_ready" in poe_bot.game_data.player.buffs

      if demon_stacks < 5 or is_barrier_charged is False:
        self.useFlasks()
      else:
        if poe_bot.game_data.player.life.energy_shield.getPercentage() < 0.65:
          self.auto_flasks.useFlasks()
        else:
          self.barrier_invocation.use()
        time.sleep(0.75)

  def getDemonFormStacks(self):
    poe_bot = self.poe_bot
    return len(list(filter(lambda b: b == "demon_form_buff", poe_bot.game_data.player.buffs)))

  def isInDemonForm(self):
    return "demon_form_spell_gem_buff" in self.poe_bot.game_data.player.buffs

  def useFlasks(self):
    self.cwdt_loop.keepLoopingFor()

  def usualRoutine(self, mover: Mover):
    poe_bot = self.poe_bot
    self.useFlasks()
    self.useBuffs()
    nearby_enemies = list(filter(lambda e: e.isInRoi() and e.isInLineOfSight(), poe_bot.game_data.entities.attackable_entities))
    pos_x_to_go, pos_y_to_go = mover.nearest_passable_point[0], mover.nearest_passable_point[1]
    if len(nearby_enemies) != 0:
      list(map(lambda e: e.calculateValueForAttack(), nearby_enemies))
      nearby_enemies.sort(key=lambda e: e.attack_value, reverse=True)
      # nearby_enemies.sort(key=lambda e: e.distance_to_player)
      nearby_enemies[0].hover(wait_till_executed=False)
    else:
      # move mouse towards direction
      screen_pos_x, screen_pos_y = poe_bot.getPositionOfThePointOnTheScreen(pos_y_to_go, pos_x_to_go)
      screen_pos_x, screen_pos_y = poe_bot.game_window.convertPosXY(screen_pos_x, screen_pos_y)
      poe_bot.bot_controls.mouse.setPosSmooth(screen_pos_x, screen_pos_y, False)
    if self.isInDemonForm() is True and mover.distance_to_target > 50:
      # distance to next step on screen
      distance_to_next_step = dist((poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (pos_x_to_go, pos_y_to_go))
      print(f"distance_to_next_step {distance_to_next_step}")
      if distance_to_next_step > 20:
        path_values = createLineIteratorWithValues(
          (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (pos_x_to_go, pos_y_to_go), poe_bot.game_data.terrain.passable
        )
        path_without_obstacles = np.all(path_values[:, 2] > 0)
        print(f"path_without_obstacles {path_without_obstacles}")
        if path_without_obstacles:
          mover.move(pos_x_to_go, pos_y_to_go)
          if self.dodge.use(wait_for_execution=False):
            return True
          return True

    return False

  def killUsual(self, entity, is_strong=False, max_kill_time_sec=10, *args, **kwargs):
    poe_bot = self.poe_bot
    entity_to_kill_id = entity.id
    self.useFlasks()
    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print("[build.killUsual] cannot find desired entity to kill")
      return True
    if entity_to_kill.life.health.current == 0:
      print("[build.killUsual] entity is dead")
      return True
    if entity_to_kill.isInRoi() is False or entity_to_kill.isInLineOfSight() is False:
      print("[build.killUsual] getting closer in killUsual")
      return False

    keep_distance = 30  # if our distance is smth like this, kite
    start_time = time.time()
    kite_distance = random.randint(35, 45)
    reversed_run = random.choice([True, False])

    entity_to_kill.hover(wait_till_executed=False)
    poe_bot.last_action_time = 0
    while True:
      poe_bot.refreshInstanceData()
      self.useFlasks()
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print("[build.killUsual] cannot find desired entity to kill")
        break
      print(f"[build.killUsual] entity_to_kill {entity_to_kill}")
      if entity_to_kill.life.health.current == 0:
        print("[build.killUsual] entity is dead")
        break
      if entity_to_kill.isInRoi() is False or entity_to_kill.isInLineOfSight() is False:
        print("[build.killUsual] getting closer in killUsual ")
        break
      self.useBuffs()
      entity_to_kill.hover()
      if entity_to_kill.distance_to_player > keep_distance:
        print("[build.killUsual] kiting around")
        point = self.poe_bot.game_data.terrain.pointToRunAround(
          entity_to_kill.grid_position.x,
          entity_to_kill.grid_position.y,
          kite_distance + random.randint(-1, 1),
          check_if_passable=True,
          reversed=reversed_run,
        )
        poe_bot.mover.move(grid_pos_x=point[0], grid_pos_y=point[1])
        if self.isInDemonForm() is True:
          self.dodge.use(wait_for_execution=False)
      else:
        print("[build.killUsual] kiting away")
        p0 = (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y)
        p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
        go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
        poe_bot.mover.move(*go_back_point)

      if time.time() > start_time + max_kill_time_sec:
        print("[build.killUsual] exceed time")
        break
    return True

class TemporalisBlinker(Build):
  def __init__(self, poe_bot):
    super().__init__(poe_bot)
    self.dodge = DodgeRoll(self.poe_bot)

class TempestFlurryBuild(Build):
  def __init__(self, poe_bot):
    super().__init__(poe_bot)
    self.tempest_flurry_travel_distance = 20  # adjust it
    # find tempest flurry
    # only one on keyboard
    flurry_button = None
    print("looking for tempest flurry button on keyboard")
    for i in range(3, 8):
      if self.poe_bot.game_data.skills.internal_names[i] == "tempest_flurry":
        flurry_button = SKILL_KEYS_WASD[i]
        print(f"flurry button is {flurry_button}")
        break
    if flurry_button is None:
      poe_bot.raiseLongSleepException("set to wasd, press it on qwert")
    self.tempest_flurry_button_holder: ButtonHolder = ButtonHolder(self.poe_bot, flurry_button, max_hold_duration=0.33)
    text = "###README### \nButtonHolder class has an issue, it basically sends the hold action to the machine, but not checks if it's registered in poe. if in somehow your poe window will lag and wont register the hold action, itll think that its holding it, there was an issue when i was testing cwdt. i was managed to deal with it by checking the history of poe_bot.game_data.skills.total_uses[self.build.barrier_invocation.skill_index], so if the value isnt changed for several cycles, it means that the button isnt holding"
    for z in range(10):
      print(text)
    # override mover.stopMoving, so itll release tempest flurry as well
    tempset_flurry_button_holder = self.tempest_flurry_button_holder

    def customStopMoving(self):
      q = [lambda: self.__class__.stopMoving(self), lambda: tempset_flurry_button_holder.forceStopPress()]
      random.shuffle(q)
      while len(q) != 0:
        action = q.pop()
        action()

    self.poe_bot.mover.stopMoving = customStopMoving.__get__(self.poe_bot.mover)

  def usualRoutine(self, mover: Mover):
    poe_bot = self.poe_bot
    self.useFlasks()
    hold_flurry = False
    nearby_enemy = next((e for e in poe_bot.game_data.entities.attackable_entities if e.isInRoi() and e.isInLineOfSight()), None)
    while True:
      if nearby_enemy:
        hold_flurry = True
        break
      if mover.distance_to_target > self.tempest_flurry_travel_distance:
        hold_flurry = True
        break
      break
    while True:
      if hold_flurry:
        pos_x_to_go, pos_y_to_go = mover.nearest_passable_point[0], mover.nearest_passable_point[1]
        # if no enemies around, make a check if it's direct
        if nearby_enemy is not None:
          path_values = createLineIteratorWithValues(
            (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (pos_x_to_go, pos_y_to_go), poe_bot.game_data.terrain.passable
          )
          path_without_obstacles = np.all(path_values[:, 2] > 0)
          if not path_without_obstacles:
            break

        screen_pos_x, screen_pos_y = poe_bot.getPositionOfThePointOnTheScreen(pos_y_to_go, pos_x_to_go)
        screen_pos_x, screen_pos_y = poe_bot.game_window.convertPosXY(screen_pos_x, screen_pos_y)
        poe_bot.bot_controls.mouse.setPosSmooth(screen_pos_x, screen_pos_y, False)
        self.tempest_flurry_button_holder.holdFor(0.33)
        return True
      break

    return False

  def killUsual(self, entity, is_strong=False, max_kill_time_sec=10, *args, **kwargs):
    poe_bot = self.poe_bot
    entity_to_kill_id = entity.id
    self.useFlasks()
    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print("[build.killUsual] cannot find desired entity to kill")
      return True
    if entity_to_kill.life.health.current == 0:
      print("[build.killUsual] entity is dead")
      return True
    if entity_to_kill.isInRoi() is False or entity_to_kill.isInLineOfSight() is False:
      print("[build.killUsual] getting closer in killUsual")
      return False
    start_time = time.time()
    entity_to_kill.hover(wait_till_executed=False)
    poe_bot.last_action_time = 0
    while True:
      poe_bot.refreshInstanceData()
      self.useFlasks()
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print("[build.killUsual] cannot find desired entity to kill")
        break
      print(f"[build.killUsual] entity_to_kill {entity_to_kill}")
      if entity_to_kill.life.health.current == 0:
        print("[build.killUsual] entity is dead")
        break
      if entity_to_kill.isInRoi() is False or entity_to_kill.isInLineOfSight() is False:
        print("[build.killUsual] getting closer in killUsual ")
        break
      entity_to_kill.hover()
      self.tempest_flurry_button_holder.holdFor(0.33)
      if time.time() > start_time + max_kill_time_sec:
        print("[build.killUsual] exceed time")
        break
    return True

class InfernalistMinion(Build):
  """ """

  poe_bot: PoeBot

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot

    # raging spririts count
    self.max_srs_count = 7

    self.minion_arconist_dd = None
    self.minion_reaver_enrage = None
    self.minion_sniper_gas_arrow = None

    minion_command_internal_name = "command_minion"
    for skill_index in range(len(self.poe_bot.game_data.skills.internal_names)):
      skill_name_raw = self.poe_bot.game_data.skills.internal_names[skill_index]
      if skill_name_raw != minion_command_internal_name:
        continue
      skill_base_cast_time = next(
        (list(sd.values())[0] for sd in poe_bot.game_data.skills.descriptions[skill_index] if "BaseSpellCastTimeMs" in sd.keys()),
        None,
      )
      if skill_base_cast_time is None:
        continue
      elif self.minion_arconist_dd is None and skill_base_cast_time == 600:
        print(f"[InfernalistMinion.__init__] found minion_arconist_dd_index {skill_index}")
        self.minion_arconist_dd = SkillWithDelay(
          poe_bot=poe_bot,
          skill_index=skill_index,
          min_delay=random.uniform(3.0, 4.0),
          display_name="minion_arconist_dd",
          can_use_earlier=False,
        )
      elif self.minion_reaver_enrage is None and skill_base_cast_time == 1000:
        print(f"[InfernalistMinion.__init__] found minion_reaver_enrage_index {skill_index}")
        self.minion_reaver_enrage = SkillWithDelay(
          poe_bot=poe_bot,
          skill_index=skill_index,
          min_delay=random.uniform(3.0, 4.0),
          display_name="minion_reaver_enrage",
          can_use_earlier=False,
        )
      elif self.minion_sniper_gas_arrow is None and skill_base_cast_time == 1250:
        print(f"[InfernalistMinion.__init__] found minion_sniper_gas_arrow_index {skill_index}")
        self.minion_sniper_gas_arrow = SkillWithDelay(
          poe_bot=poe_bot,
          skill_index=skill_index,
          min_delay=random.uniform(2.5, 3.0),
          display_name="minion_sniper_gas_arrow",
          can_use_earlier=False,
        )

    unearth_internal_name = "bone_cone"
    unearth_index = unearth_internal_name in self.poe_bot.game_data.skills.internal_names and self.poe_bot.game_data.skills.internal_names.index(
      unearth_internal_name
    )
    print(f"unearth_index {unearth_index}")
    self.unearth = None
    if unearth_index is not False:
      self.unearth = SkillWithDelay(
        poe_bot=poe_bot,
        skill_index=unearth_index,
        min_delay=random.uniform(0.1, 0.2),
        display_name="unearth",
        can_use_earlier=True,
      )

    detonate_dead_internal_name = "detonate_dead"
    detonate_dead_index = (
      detonate_dead_internal_name in self.poe_bot.game_data.skills.internal_names
      and self.poe_bot.game_data.skills.internal_names.index(detonate_dead_internal_name)
    )
    print(f"detonate_dead_index {detonate_dead_index}")
    self.detonate_dead = None
    if detonate_dead_index is not False:
      self.detonate_dead = SkillWithDelay(
        poe_bot=poe_bot,
        skill_index=detonate_dead_index,
        min_delay=random.uniform(0.5, 1.5),
        display_name="detonate_dead",
        can_use_earlier=False,
      )

    offering_internal_name = "pain_offering"
    offerening_index = offering_internal_name in self.poe_bot.game_data.skills.internal_names and self.poe_bot.game_data.skills.internal_names.index(
      offering_internal_name
    )
    print(f"offerening_index {offerening_index}")
    self.offering = None
    if offerening_index is not False:
      self.offering = SkillWithDelay(
        poe_bot=poe_bot,
        skill_index=offerening_index,
        min_delay=random.uniform(6.0, 8.0),
        display_name="offering",
        can_use_earlier=False,
      )

    flammability_internal_name = "fire_weakness"
    flammability_index = (
      flammability_internal_name in self.poe_bot.game_data.skills.internal_names
      and self.poe_bot.game_data.skills.internal_names.index(flammability_internal_name)
    )
    print(f"flammability_index {flammability_index}")
    self.flammability = None
    if flammability_index is not False:
      self.flammability = SkillWithDelay(
        poe_bot=poe_bot,
        skill_index=flammability_index,
        min_delay=random.uniform(2.0, 3.0),
        display_name="flammability",
        can_use_earlier=False,
      )

    flame_wall_internal_name = "firewall"
    flame_wall_index = (
      flame_wall_internal_name in self.poe_bot.game_data.skills.internal_names
      and self.poe_bot.game_data.skills.internal_names.index(flame_wall_internal_name)
    )
    print(f"flame_wall_index {flame_wall_index}")
    self.flame_wall = None
    if flame_wall_index is not False:
      self.flame_wall = SkillWithDelay(
        poe_bot=poe_bot,
        skill_index=flame_wall_index,
        min_delay=random.uniform(0.5, 1),
        display_name="flame_wall",
        can_use_earlier=False,
      )

    self.dodge_roll = DodgeRoll(poe_bot=poe_bot)

    super().__init__(poe_bot)
    self.auto_flasks = AutoFlasks(poe_bot=poe_bot)

  def useBuffs(self):
    return False

  def usualRoutine(self, mover: Mover = None):
    poe_bot = self.poe_bot
    self.useFlasks()

    # if we are moving
    if mover is not None:
      entity_to_explode: Entity = None
      entity_to_unearth: Entity = None
      search_radius = 25
      search_angle = 40

      attacking_skill_delay = random.uniform(0.35, 0.5)

      self.last_explosion_loc = [0, 1, 0, 1]
      self.last_explosion_time = 0

      self.useBuffs()

      corpses = poe_bot.game_data.entities.getCorpsesArountPoint(poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y, 40)
      if corpses:
        if self.last_explosion_time + 1 < time.time():
          self.last_explosion_loc = [0, 1, 0, 1]

        list(map(lambda e: e.calculateValueForAttack(search_radius), corpses))
        corpses = list(filter(lambda e: e.attack_value > 4, corpses))
        corpses = list(filter(lambda e: not e.isInZone(*self.last_explosion_loc), corpses))

        if corpses:
          corpses.sort(key=lambda e: e.attack_value, reverse=True)
          entity_to_explode = corpses[0]
          print(f"found valuable corpse to explode {entity_to_explode.raw}")

      if entity_to_explode and self.detonate_dead.canUse() and self.detonate_dead.last_use_time + attacking_skill_delay < time.time():
        self.detonate_dead.use(updated_entity=entity_to_explode)
        self.last_explosion_time = time.time()
        self.last_explosion_loc = [
          entity_to_explode.grid_position.x - 20,
          entity_to_explode.grid_position.x + 20,
          entity_to_explode.grid_position.y - 20,
          entity_to_explode.grid_position.y + 20,
        ]
        return True

      corpses = poe_bot.game_data.entities.getCorpsesArountPoint(poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y, 35)
      if corpses:
        p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
        p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
        corpses = list(
          filter(
            lambda e: getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < search_angle,
            corpses,
          )
        )
        list(map(lambda e: e.calculateValueForAttack(search_radius), corpses))

        if len(corpses) > 5:
          corpses.sort(key=lambda e: e.attack_value > 1, reverse=True)
          entity_to_unearth = corpses[0]
          print(f"found valuable corpse to unearth {entity_to_unearth.raw}")

      if entity_to_unearth and self.unearth.canUse() and self.unearth.last_use_time + attacking_skill_delay + 1 < time.time():
        self.unearth.use(updated_entity=entity_to_unearth)
        return True

      nearby_enemies = list(
        filter(
          lambda e: e.distance_to_player < 90 and e.isInRoi() and e.is_hostile,
          poe_bot.game_data.entities.attackable_entities,
        )
      )
      print(f"nearby_enemies: {nearby_enemies}")
      really_close_enemies = list(filter(lambda e: e.distance_to_player < 45, nearby_enemies))

      enemy_to_attack = None
      if len(really_close_enemies) != 0:
        enemy_to_attack = really_close_enemies[0]
      elif len(nearby_enemies):
        nearby_enemies = sorted(nearby_enemies, key=lambda e: e.distance_to_player)
        # nearby_enemies = list(filter(lambda e: e.isInLineOfSight() is True, nearby_enemies))
        if len(nearby_enemies) != 0:
          enemy_to_attack = nearby_enemies[0]

      if enemy_to_attack is not None:
        if self.flame_wall and self.flame_wall.canUse() and self.flame_wall.last_use_time + attacking_skill_delay < time.time():
          alive_srs_nearby = list(
            filter(
              lambda e: not e.is_hostile
              and e.life.health.current != 0
              and e.distance_to_player < 150
              and "Metadata/Monsters/RagingSpirit/RagingSpiritPlayerSummoned" in e.path,
              self.poe_bot.game_data.entities.all_entities,
            )
          )
          if len(alive_srs_nearby) < self.max_srs_count:
            self.flame_wall.use(updated_entity=enemy_to_attack, wait_for_execution=False)

        if self.flammability and self.flammability.canUse() and self.flammability.last_use_time + attacking_skill_delay < time.time():
          self.flammability.use(updated_entity=enemy_to_attack, wait_for_execution=False)

        if (
          self.minion_sniper_gas_arrow
          and self.minion_sniper_gas_arrow.canUse()
          and self.minion_sniper_gas_arrow.last_use_time + attacking_skill_delay < time.time()
        ):
          self.minion_sniper_gas_arrow.use(updated_entity=enemy_to_attack, wait_for_execution=False)

        # Get nearby allies
        nearby_allies = [
          e
          for e in poe_bot.game_data.entities.all_entities
          if not e.is_hostile and e.distance_to_player < 60 and e.grid_position and e.life.health.current != 0
        ]
        if nearby_allies:
          try:
            middle_x = sum(e.grid_position.x for e in nearby_allies) / len(nearby_allies)
            middle_y = sum(e.grid_position.y for e in nearby_allies) / len(nearby_allies)
            mover.move(middle_x, middle_y)
          except Exception:
            pass

      p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
      p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)

      # if len(really_close_enemies) > 1:
      #  go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
      #  poe_bot.mover.move(*go_back_point)
      #  return True

      extremley_close_entities = list(filter(lambda e: e.distance_to_player < 15, nearby_enemies))
      enemies_on_way = list(
        filter(
          lambda e: e.distance_to_player < 45 and getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < 35,
          nearby_enemies,
        )
      )

      if extremley_close_entities:
        go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
        mover.move(*go_back_point)
        self.dodge_roll.use(wait_for_execution=False)
        return True
      elif enemies_on_way:
        nearby_allies = [
          e
          for e in poe_bot.game_data.entities.all_entities
          if not e.is_hostile and e.distance_to_player < 60 and e.grid_position and e.life.health.current != 0
        ]
        if nearby_allies:
          try:
            middle_x = sum(e.grid_position.x for e in nearby_allies) / len(nearby_allies)
            middle_y = sum(e.grid_position.y for e in nearby_allies) / len(nearby_allies)
            mover.move(middle_x, middle_y)
            return True
          except Exception:
            pass

      # elif really_close_enemies or enemies_on_way and enemies_on_way[0].distance_to_player < 35:
      #  go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
      #  mover.move(*go_back_point)
      #  return True
      elif enemy_to_attack is not None:
        # point = self.poe_bot.game_data.terrain.pointToRunAround(enemy_to_attack.grid_position.x, enemy_to_attack.grid_position.y, 40, reversed=random.choice([True, False]))
        # mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
        return True

  def prepareToFight(self, entity: Entity):
    print(f"[InfernalistMinion.prepareToFight] call {time.time()}")
    self.poe_bot.refreshInstanceData()
    self.useFlasks()
    return True

  def useFlasks(self):
    self.auto_flasks.useFlasks()

  def killUsual(
    self,
    entity: Entity,
    is_strong=False,
    max_kill_time_sec=random.randint(200, 300) / 10,
    *args,
    **kwargs,
  ):
    print(f"#build.killUsual {entity}")
    poe_bot = self.poe_bot
    mover = self.mover

    entity_to_kill_id = entity.id

    self.useFlasks()

    min_distance = 35  # distance which is ok to start attacking
    keep_distance = 55  # if our distance is smth like this, kite
    critical_distance = 15
    distance_range = 5

    start_time = time.time()
    poe_bot.last_action_time = 0

    entity_to_kill = next(
      (e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id),
      None,
    )
    if not entity_to_kill:
      print("cannot find desired entity to kill")
      return True

    print(f"entity_to_kill {entity_to_kill}")

    if entity_to_kill.life.health.current < 0:
      print("entity is dead")
      return True

    distance_to_entity = dist(
      (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y),
      (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y),
    )
    print(f"distance_to_entity {distance_to_entity} in killUsual")
    if distance_to_entity > min_distance:
      print("getting closer in killUsual ")
      return False

    if entity_to_kill.isInLineOfSight() is False:
      print("entity_to_kill.isInLineOfSight() is False")
      return False

    entity_to_kill.hover(wait_till_executed=False)

    while True:
      skill_used = False
      poe_bot.refreshInstanceData()
      self.useFlasks()
      if self.poe_bot.game_data.player.life.health.getPercentage() < self.auto_flasks.hp_thresh:
        pass  # TODO kite?

      entity_to_kill = next(
        (e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id),
        None,
      )
      if not entity_to_kill:
        print("cannot find desired entity to kill")
        break

      distance_to_entity = dist(
        (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y),
        (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y),
      )
      print(f"distance_to_entity {distance_to_entity} in killUsual")
      if distance_to_entity > min_distance:
        print("getting closer in killUsual ")
        break
      current_time = time.time()

      # TODO: some logic how and when to use skills, currently -> if ememy then use skill

      if skill_used is False and self.flame_wall and self.flame_wall.canUse():
        alive_srs_nearby = list(
          filter(
            lambda e: not e.is_hostile
            and e.life.health.current != 0
            and e.distance_to_player < 150
            and "Metadata/Monsters/RagingSpirit/RagingSpiritPlayerSummoned" in e.path,
            self.poe_bot.game_data.entities.all_entities,
          )
        )
        if len(alive_srs_nearby) < self.max_srs_count:
          print(f"[Generic summoner] need to raise srs, current count {len(alive_srs_nearby)}")
          if self.flame_wall.use(updated_entity=entity_to_kill, wait_for_execution=False) is True:
            skill_used = True

      if skill_used is False and self.offering and self.offering.canUse():
        minions_around = list(
          filter(
            lambda e: e.is_hostile is False and e.distance_to_player < 35,
            poe_bot.game_data.entities.all_entities,
          )
        )
        if len(minions_around) != 0:
          if self.offering.use(updated_entity=minions_around[0], wait_for_execution=False) is True:
            skill_used = True

      if skill_used is False and self.flammability and self.flammability.canUse():
        if self.flammability.use(updated_entity=entity_to_kill, wait_for_execution=False) is True:
          skill_used = True

      if skill_used is False and self.minion_reaver_enrage and self.minion_reaver_enrage.canUse():
        if self.minion_reaver_enrage.use(updated_entity=entity_to_kill, wait_for_execution=False) is True:
          skill_used = True

      if skill_used is False and self.minion_sniper_gas_arrow and self.minion_sniper_gas_arrow.canUse():
        if self.minion_sniper_gas_arrow.use(updated_entity=entity_to_kill, wait_for_execution=False) is True:
          skill_used = True

      if skill_used is False and self.minion_arconist_dd and self.minion_arconist_dd.canUse():
        if self.minion_arconist_dd.use(updated_entity=entity_to_kill, wait_for_execution=False) is True:
          skill_used = True

      p0 = (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y)
      p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)

      if distance_to_entity < critical_distance:
        # distance_to_entity is below the critical distance
        go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
        mover.move(*go_back_point)
        self.dodge_roll.use(wait_for_execution=False)

      if distance_to_entity < keep_distance - distance_range:
        # distance_to_entity is below the range
        go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
        mover.move(*go_back_point)

      # Calculate middlepoint of nearby allies and move there
      nearby_allies = [
        e
        for e in poe_bot.game_data.entities.all_entities
        if not e.is_hostile and e.distance_to_player < 60 and e.grid_position and e.life.health.current != 0
      ]
      if nearby_allies:
        try:
          middle_x = sum(e.grid_position.x for e in nearby_allies) / len(nearby_allies)
          middle_y = sum(e.grid_position.y for e in nearby_allies) / len(nearby_allies)
          mover.move(middle_x, middle_y)
        except Exception:
          pass

      # elif distance_to_entity > keep_distance + distance_range:
      # distance_to_entity is above the range
      # mover.goToPoint(p1)
      # mover.goToEntity(entity_to_kill, keep_distance)
      # point = self.poe_bot.game_data.terrain.pointToRunAround(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, distance_range, check_if_passable=True, reversed=random.choice([True, False]))
      # mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
      # else:
      # distance_to_entity is within the range
      # mover.goToPoint(p1)
      # break
      # mover.goToEntity(entity_to_kill, keep_distance)

      # point = self.poe_bot.game_data.terrain.pointToRunAround(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, kite_distance+random.randint(-3,3), check_if_passable=True, reversed=reversed_run)
      # mover.move(grid_pos_x = point[0], grid_pos_y = point[1])

      if current_time > start_time + max_kill_time_sec:
        print("exceed time")
        break

    return True

COMBAT_BUILDS = {
  "barrier_invocation_infernalist": BarrierInvocationInfernalist,
  "temporalis_blinker": TemporalisBlinker,
  "tempest_flurry": TempestFlurryBuild,
  "infernalist_minion": InfernalistMinion,
}
COMBAT_BUILDS_LIST = list(COMBAT_BUILDS.keys())


def getBuild(build: str):
  return COMBAT_BUILDS[build]
