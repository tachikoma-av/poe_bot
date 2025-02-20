#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import random
import sys
import time
from ast import literal_eval
from math import dist
from typing import List

import matplotlib.pyplot as plt
from utils.combat import getBuild
from utils.constants import WAYPOINTS
from utils.controller import VMHostPuppeteer
from utils.encounters import Bossroom
from utils.gamehelper import Entity, PoeBot
from utils.loot_filter import CustomLootFilter
from utils.mover import Mover
from utils.pathing import TSP
from utils.temps import AreaTempData
from utils.utils import alwaysFalseFunction


# In[ ]:


"""
# bossroom location, if died, needs to check if transition with name of LOCATION is nearby and enter it and start usual routing
- a4 red - ok, blue - false
- a4 malachai small bosses
- a4 malachai boss fight, multi bosses, multi transitions, multi bosses again
- pre beacon area, pick flag,
- beacon area
- crab boss area + bossroom + quest , exit through dialogue with npc
- 2_7_4 - multi layerd + lab
- 1_1_9a - 
- allflame quest, walk around npc's pos instead of new entity
- Loc2_9_3, waypoint, open chest, pick storm blade, go to town, exchange for bottled storm, find some area to use bottled storm, enter transition
- Loc2_9_7 if lab done, can go to other loc
- Loc2_9_8
- Loc2_9_10_2
.....

? 2_7_11 yeena activator
? a3 start, clear location till clarissa is targetable
? a4 relogs even before banner
?- 2_6_7_2 - stairs + bossroom, refresh area after boss fight, exit through other transition
? a4 piety fight, talk to it, refreshall, enter next loc
? Loc2_9_5(QuestArea): # if basilisk killed, else goto "The Tunnel"
? class Loc2_9_6(QuestArea): # if basilisk killed, else goto "The Tunnel"




"""


# In[ ]:


time_now = 0
notebook_dev = False
# readability
poe_bot: PoeBot
bot_controls: VMHostPuppeteer
mover: Mover


# In[ ]:


default_config = {
  "REMOTE_IP": "172.19.137.191",  # z2
  "unique_id": "questbottest",
  "leveling_strategy": "ranger_vg",
  "force_reset_temp": False,
}
try:
  i = sys.argv[1]
  print(i)
  parsed_config = literal_eval(i)
  print("successfully parsed cli config")
  print(f"parsed_config: {parsed_config}")
except:
  print("cannot parse config from cli, using default\dev one")
  notebook_dev = True
  parsed_config = default_config

config = {}

for key in default_config.keys():
  try:
    config[key] = parsed_config[key]
  except:
    config[key] = default_config[key]

print(f"config to run {config}")


# In[ ]:


from utils.combat import AreaSkill, AutoFlasks, Build, MinionSkillWithDelay, MovementSkill, SkillWithDelay


class RangerLeveling(Build):
  """ """

  poe_bot: PoeBot

  def __init__(self, poe_bot: PoeBot) -> None:
    self.brand_last_use_time = 0
    self.poe_bot = poe_bot
    self.attacking_skill = None
    self.ballista_skill = None
    self.blood_rage = None
    self.movement_skill = None
    self.debuff = None
    self.auras = []
    skills_data = poe_bot.backend.getSkillBar()
    for skill_index in range(len(skills_data["i_n"])):
      skill = skills_data["i_n"][skill_index]

      if skill == "":
        continue
      print(skill, skill_index)
      if skill == "blood_rage":
        self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(30, 50) / 10, display_name="blood_rage")
      elif skill == "burning_arrow" or skill == "caustic_arrow" or skill == "shrapnel_shot" or skill == "rain_of_arrows":
        is_totem = next((sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if "NumberOfTotemsAllowed" in sd.keys()), None)
        if is_totem is not None:
          print(f"{skill} is a totem")
          self.ballista_skill = SkillWithDelay(
            poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(15, 18) / 10, display_name=skill, min_mana_to_use=0
          )
        else:
          print(f"{skill} is not a totem")
          self.attacking_skill = SkillWithDelay(
            poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1, 5) / 100, display_name=skill, min_mana_to_use=0
          )

      elif skill == "shrapnel_ballista":
        self.ballista_skill = SkillWithDelay(
          poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(15, 18) / 10, display_name=skill, min_mana_to_use=0
        )
      elif skill == "dash":
        self.movement_skill = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill, min_delay=random.randint(30, 50) / 100)
      elif skill == "despair":
        self.debuff = AreaSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill)
    self.attacking_skill.overriden_cast_time = 0.5
    super().__init__(poe_bot)
    self.auto_flasks = AutoFlasks(poe_bot=poe_bot)

  def useBuffs(self):
    poe_bot = self.poe_bot
    if self.blood_rage is not None:
      if (
        "blood_rage" not in poe_bot.game_data.player.buffs
        and poe_bot.game_data.player.life.health.current / poe_bot.game_data.player.life.health.total > 0.7
      ):
        if self.blood_rage.use() is True:
          return True

    return False

  def useFlasks(self):
    self.auto_flasks.useFlasks()

  def usualRoutine(self, mover: Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()

    # if we are moving
    if mover is not None:
      self.useBuffs()
      nearby_enemies = list(filter(lambda e: e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      print(f"nearby_enemies: {nearby_enemies}")
      really_close_enemies = list(filter(lambda e: e.distance_to_player < 20, nearby_enemies))
      min_delay = 3
      if len(really_close_enemies) != 0:
        min_delay = 2

      if self.attacking_skill.last_use_time + min_delay < time.time():
        print("can use attacking_skill")
        enemy_to_attack = None
        if len(really_close_enemies) != 0:
          enemy_to_attack = really_close_enemies[0]
        elif len(nearby_enemies):
          nearby_enemies = sorted(nearby_enemies, key=lambda e: e.distance_to_player)
          nearby_enemies = list(filter(lambda e: e.isInLineOfSight() is True, nearby_enemies))
          if len(nearby_enemies) != 0:
            enemy_to_attack = nearby_enemies[0]
        if enemy_to_attack is not None:
          if self.attacking_skill.use(updated_entity=enemy_to_attack) is True:
            return True

      elif self.ballista_skill and self.ballista_skill.last_use_time + min_delay < time.time():
        print("can use ballista skills")
        enemy_to_attack = None
        if len(really_close_enemies) != 0:
          enemy_to_attack = really_close_enemies[0]
        elif len(nearby_enemies):
          nearby_enemies = sorted(nearby_enemies, key=lambda e: e.distance_to_player)
          nearby_enemies = list(filter(lambda e: e.isInLineOfSight() is True, nearby_enemies))
          if len(nearby_enemies) != 0:
            enemy_to_attack = nearby_enemies[0]
        if enemy_to_attack is not None:
          if self.ballista_skill.use() is True:
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
    print(f"frenzyfrostblink.preparetofight call {time.time()}")
    for i in range(random.randint(2, 3)):
      self.poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      updated_entity = next((e for e in self.poe_bot.game_data.entities.all_entities if e.id == entity.id), None)
      if updated_entity is None:
        break

      self.ballista_skill.use(updated_entity=updated_entity)
    return True

  def killUsual(self, entity: Entity, is_strong=False, max_kill_time_sec=random.randint(200, 300) / 10, *args, **kwargs):
    print(f"#build.killUsual {entity}")
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    mover = self.mover

    entity_to_kill_id = entity.id
    debuff_use_time = 0

    self.useFlasks()

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
    pos_x, pos_y = entity_to_kill.location_on_screen.x, entity_to_kill.location_on_screen.y
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    if self.ballista_skill:
      self.ballista_skill.use(updated_entity=entity_to_kill)
      self.ballista_skill.last_use_time = time.time()
    poe_bot.last_action_time = 0
    kite_distance = random.randint(18, 22)
    res = True
    reversed_run = random.choice([True, False])
    while True:
      skill_used = False
      poe_bot.refreshInstanceData()
      self.useFlasks()
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
      if self.useBuffs() is True:
        skill_used = True
      if self.debuff:
        if current_time > start_time + 2:
          if current_time > debuff_use_time + 4:
            if self.debuff.use(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y) is True:
              debuff_use_time = time.time()
              skill_used = True
      # dd_use_delay = random.randint(40,50)/100 + int(not self.desecrate is None) * 0.5
      skill_use_delay = random.randint(20, 30) / 10
      print(f"skill_use_delay {skill_use_delay}")
      if self.ballista_skill and skill_used is False and self.ballista_skill.last_use_time + skill_use_delay < time.time():
        self.ballista_skill.use(updated_entity=entity_to_kill)
        skill_used = True
      if skill_used is False and self.attacking_skill.last_use_time + skill_use_delay < time.time():
        hold_duration = random.randint(9, 18) / 10
        hold_start_time = time.time()
        self.attacking_skill.last_use_time = hold_start_time
        self.attacking_skill.press()
        while time.time() - hold_duration < hold_start_time:
          poe_bot.refreshInstanceData()
          self.useFlasks()
          entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
          if entity_to_kill:
            entity_to_kill.hover()
          else:
            break
        self.attacking_skill.release()
        skill_used = True

        # continue

      if entity_to_kill is None:
        break
      print("kiting")
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

  def doPreparations(self):
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls

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

    if poe_bot.game_data.player.life.mana.current / poe_bot.game_data.player.life.mana.total > 0.2:
      print("poe_bot.game_data.player.life.mana.current / poe_bot.game_data.player.life.mana.total > 0.2, activating auras")
      bot_controls.keyboard_pressKey("DIK_LCONTROL")
      time.sleep(random.randint(10, 15) / 100)
      aura_keys = ["DIK_Q", "DIK_W", "DIK_E", "DIK_R"]
      if random.randint(1, 10) == 1:
        aura_keys.reverse()
      for key in aura_keys:
        time.sleep(random.randint(10, 15) / 100)
        bot_controls.keyboard.tap(key)
        time.sleep(random.randint(10, 15) / 100)
      time.sleep(random.randint(10, 33) / 100)
      bot_controls.keyboard_releaseKey("DIK_LCONTROL")
      time.sleep(random.randint(10, 15) / 100)


# In[ ]:


from utils.constants import SKILLS_INTERNAL_NAMES


class WitchSrsLeveling(Build):
  """ """

  poe_bot: PoeBot

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot

    self.raise_zombie = None
    self.max_amount_of_zombies = 0

    self.absolution = None
    self.flame_totem = None
    self.max_amount_of_totems = 0
    self.srs = None
    self.summon_skeletons = None
    self.max_amount_of_skeletons = 0

    self.purifying_flame = None
    self.stone_golem = None
    self.movement_skill = None
    self.instant_movement_skill = None

    raise_zombie = next((s for s in self.poe_bot.game_data.skills.internal_names if s == SKILLS_INTERNAL_NAMES.RAISE_ZOMBIE), None)
    if raise_zombie:
      skill_index = self.poe_bot.game_data.skills.internal_names.index(raise_zombie)
      self.raise_zombie = MinionSkillWithDelay(
        poe_bot=poe_bot,
        skill_index=skill_index,
        min_delay=random.randint(20, 30) / 10,
        display_name=raise_zombie,
        min_mana_to_use=0,
        can_use_earlier=False,
      )
      self.raise_zombie.minion_path_key = "Metadata/Monsters/RaisedZombies/RaisedZombieStandard"
      max_amount_of_zombies = next((sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if "NumberOfZombiesAllowed" in sd.keys()), None)
      if max_amount_of_zombies is not None:
        self.max_amount_of_zombies = max_amount_of_zombies["NumberOfZombiesAllowed"]
      print(f"[Generic summoner] raise zombie max zombies {self.max_amount_of_zombies}")
    srs = next((s for s in self.poe_bot.game_data.skills.internal_names if s == SKILLS_INTERNAL_NAMES.SUMMON_RAGING_SPIRIT), None)
    if srs:
      skill_index = self.poe_bot.game_data.skills.internal_names.index(srs)
      self.srs = MinionSkillWithDelay(
        poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(20, 30) / 10, display_name=srs, min_mana_to_use=0, can_use_earlier=False
      )
      self.srs.minion_path_key = "Metadata/Monsters/SummonedSkull/SummonedSkull"
      if True:  # srs linked to unleashed
        self.srs.overriden_cast_time = self.srs.getCastTime() * 3
        # random.randint(8,10)/10
        #
    absolution = next((s for s in self.poe_bot.game_data.skills.internal_names if s == SKILLS_INTERNAL_NAMES.ABSOLUTION), None)
    if absolution:
      skill_index = self.poe_bot.game_data.skills.internal_names.index(absolution)
      self.absolution = SkillWithDelay(
        poe_bot=poe_bot,
        skill_index=skill_index,
        min_delay=random.randint(20, 30) / 10,
        display_name=absolution,
        min_mana_to_use=0,
        can_use_earlier=False,
      )
    purifying_flame = next((s for s in self.poe_bot.game_data.skills.internal_names if s == SKILLS_INTERNAL_NAMES.PURIFYING_FLAME), None)
    if purifying_flame:
      skill_index = self.poe_bot.game_data.skills.internal_names.index(purifying_flame)
      self.purifying_flame = SkillWithDelay(
        poe_bot=poe_bot,
        skill_index=skill_index,
        min_delay=random.randint(20, 30) / 10,
        display_name=purifying_flame,
        min_mana_to_use=0,
        can_use_earlier=False,
      )
    flame_totem = next((s for s in self.poe_bot.game_data.skills.internal_names if s == SKILLS_INTERNAL_NAMES.HOLY_FLAME_TOTEM), None)
    if flame_totem:
      skill_index = self.poe_bot.game_data.skills.internal_names.index(flame_totem)
      self.flame_totem = MinionSkillWithDelay(
        poe_bot=poe_bot,
        skill_index=skill_index,
        min_delay=random.randint(20, 30) / 10,
        display_name=flame_totem,
        min_mana_to_use=0,
        can_use_earlier=False,
      )
      self.flame_totem.minion_path_key = "Metadata/Monsters/Totems/HolyFireSprayTotem"
      self.max_amount_of_totems = 1
    summon_skeletons = next((s for s in self.poe_bot.game_data.skills.internal_names if s == SKILLS_INTERNAL_NAMES.SUMMON_SKELETONS), None)
    if summon_skeletons:
      skill_index = self.poe_bot.game_data.skills.internal_names.index(summon_skeletons)
      self.summon_skeletons = MinionSkillWithDelay(
        poe_bot=poe_bot,
        skill_index=skill_index,
        min_delay=random.randint(20, 30) / 10,
        display_name=summon_skeletons,
        min_mana_to_use=0,
        can_use_earlier=False,
      )
      self.summon_skeletons.minion_path_key = "Metadata/Monsters/RaisedSkeletons/RaisedSkeletonStandard"
      max_amount_of_skeletons = next(
        (sd for sd in poe_bot.game_data.skills.descriptions[skill_index] if "NumberOfSkeletonsAllowed" in sd.keys()), None
      )
      if max_amount_of_skeletons is not None:
        self.max_amount_of_skeletons = max_amount_of_skeletons["NumberOfSkeletonsAllowed"]
      print(f"[Generic summoner] summon skeletons max count {self.max_amount_of_skeletons}")

    self.attacking_skill = None  # main spam skill
    if self.absolution:
      self.attacking_skill = self.absolution
    elif self.srs:
      self.attacking_skill = self.srs
    elif self.purifying_flame:
      self.attacking_skill = self.purifying_flame

    self.temporary_minion_skills = [self.srs, self.flame_totem, self.summon_skeletons]
    self.temporary_minion_skills = list(filter(lambda s: s is not None and s != self.attacking_skill, self.temporary_minion_skills))

    self.ballista_skill = None  # totem

    self.blood_rage = None
    self.movement_skill = None
    self.debuff = None
    self.auras = []

    for skill_index in range(len(self.poe_bot.game_data.skills.internal_names)):
      skill = self.poe_bot.game_data.skills.internal_names[skill_index]
      if skill == "":
        continue
      print(skill, skill_index)
      if skill == "frostblink" or skill == "flame_dash":
        self.movement_skill = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill, min_delay=random.randint(30, 50) / 100)
      elif skill == "despair":
        self.debuff = AreaSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill)
    super().__init__(poe_bot)
    self.auto_flasks = AutoFlasks(poe_bot=poe_bot)

  def useBuffs(self):
    poe_bot = self.poe_bot
    if self.blood_rage is not None:
      if (
        "blood_rage" not in poe_bot.game_data.player.buffs
        and poe_bot.game_data.player.life.health.current / poe_bot.game_data.player.life.health.total > 0.7
      ):
        if self.blood_rage.use() is True:
          return True
    return False

  def useSkillAsAttackingSkill(self, skill: SkillWithDelay, nearby_enemies: List[Entity], really_close_enemies: List[Entity]):
    print(f"[Generic summoner] can use {skill.display_name} as attacking skill")
    enemy_to_attack = None
    if len(really_close_enemies) != 0:
      enemy_to_attack = really_close_enemies[0]
    elif len(nearby_enemies):
      nearby_enemies = sorted(nearby_enemies, key=lambda e: e.distance_to_player)
      nearby_enemies = list(filter(lambda e: e.isInLineOfSight() is True, nearby_enemies))
      if len(nearby_enemies) != 0:
        enemy_to_attack = nearby_enemies[0]
    if enemy_to_attack is not None:
      if skill.use(updated_entity=enemy_to_attack) is True:
        return True
    return False

  def usualRoutine(self, mover: Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()

    # if we are moving
    if mover is not None:
      self.useBuffs()
      attacking_skill_delay = 2

      nearby_enemies = list(filter(lambda e: e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      print(f"nearby_enemies: {nearby_enemies}")
      really_close_enemies = list(filter(lambda e: e.distance_to_player < 20, nearby_enemies))
      min_delay = 3
      if len(really_close_enemies) != 0:
        min_delay = 2
        attacking_skill_delay = 0.7
      if self.attacking_skill and self.attacking_skill.last_use_time + attacking_skill_delay < time.time():
        if self.useSkillAsAttackingSkill(self.attacking_skill, nearby_enemies=nearby_enemies, really_close_enemies=really_close_enemies) is True:
          return True
      elif self.srs and self.srs != self.attacking_skill and self.srs.last_use_time + min_delay < time.time():
        if self.useSkillAsAttackingSkill(self.srs, nearby_enemies=nearby_enemies, really_close_enemies=really_close_enemies) is True:
          return True
      elif (
        self.summon_skeletons
        and self.summon_skeletons.last_use_time + min_delay < time.time()
        and self.summon_skeletons.getMinionsCountInRadius(50) < self.max_amount_of_skeletons
      ):
        if self.useSkillAsAttackingSkill(self.summon_skeletons, nearby_enemies=nearby_enemies, really_close_enemies=really_close_enemies) is True:
          return True
      elif (
        self.flame_totem
        and self.flame_totem.last_use_time + min_delay < time.time()
        and self.flame_totem.getMinionsCountInRadius(50) < self.max_amount_of_totems
      ):
        if self.useSkillAsAttackingSkill(self.flame_totem, nearby_enemies=nearby_enemies, really_close_enemies=really_close_enemies) is True:
          return True

      if self.raise_zombie and self.raise_zombie.canUse() is not False:
        alive_zombies_nearby = list(
          filter(
            lambda e: e.life.health.current != 0
            and not e.is_hostile
            and e.distance_to_player < 150
            and "Metadata/Monsters/RaisedZombies/RaisedZombieStandard" in e.path,
            self.poe_bot.game_data.entities.all_entities,
          )
        )
        if len(alive_zombies_nearby) < self.max_amount_of_zombies:
          print("[Generic summoner] need to raise zombie")
          corpses_around = poe_bot.game_data.entities.getCorpsesArountPoint(
            poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y, 25
          )
          corpses_around = list(filter(lambda e: e.isInLineOfSight() is not False, corpses_around))
          if len(corpses_around) != 0:
            if self.raise_zombie.use(updated_entity=corpses_around[0]) is not False:
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
    print(f"frenzyfrostblink.preparetofight call {time.time()}")
    for i in range(random.randint(2, 3)):
      self.poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      updated_entity = next((e for e in self.poe_bot.game_data.entities.all_entities if e.id == entity.id), None)
      if updated_entity is None:
        break

      self.ballista_skill.use(updated_entity=updated_entity)
    return True

  def killUsual(self, entity: Entity, is_strong=False, max_kill_time_sec=random.randint(200, 300) / 10, *args, **kwargs):
    print(f"#build.killUsual {entity}")
    poe_bot = self.poe_bot
    mover = self.mover

    entity_to_kill_id = entity.id
    debuff_use_time = 0

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
    entity_to_kill.hover(wait_till_executed=False)
    poe_bot.last_action_time = 0
    kite_distance = random.randint(18, 22)
    res = True
    reversed_run = random.choice([True, False])
    holding_attacking_skill = [False]

    def releaseHoldingAttackSkill():
      if self.attacking_skill and holding_attacking_skill[0] is not False:
        self.attacking_skill.release(wait_till_executed=False)
        holding_attacking_skill[0] = False

    def pressHoldingAttackSkill():
      if self.attacking_skill and holding_attacking_skill[0] is not True:
        self.attacking_skill.press(wait_till_executed=False)
        holding_attacking_skill[0] = True

    while True:
      skill_used = False
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      if self.poe_bot.game_data.player.life.health.getPercentage() < self.auto_flasks.hp_thresh:
        releaseHoldingAttackSkill()

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

      if skill_used is not True and self.raise_zombie and self.raise_zombie.canUse() is not False:
        alive_zombies_nearby = list(
          filter(
            lambda e: e.life.health.current != 0
            and not e.is_hostile
            and e.distance_to_player < 150
            and "Metadata/Monsters/RaisedZombies/RaisedZombieStandard" in e.path,
            self.poe_bot.game_data.entities.all_entities,
          )
        )
        if len(alive_zombies_nearby) < self.max_amount_of_zombies:
          print("[Generic summoner] need to raise zombie")
          corpses_around = poe_bot.game_data.entities.getCorpsesArountPoint(
            poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y, 25
          )
          corpses_around = list(filter(lambda e: e.isInLineOfSight() is not False, corpses_around))
          if len(corpses_around) != 0:
            if self.raise_zombie.use(updated_entity=corpses_around[0]) is not False:
              return True
      if self.debuff:
        if current_time > start_time + 2:
          if current_time > debuff_use_time + 4:
            if self.debuff.use(updated_entity=entity_to_kill) is True:
              debuff_use_time = time.time()
              skill_used = True
      # dd_use_delay = random.randint(40,50)/100 + int(not self.desecrate is None) * 0.5
      skill_use_delay = random.randint(20, 30) / 10
      print(f"skill_use_delay {skill_use_delay}")

      if skill_used is not True and self.srs and self.srs != self.attacking_skill and self.srs.last_use_time + skill_use_delay < time.time():
        releaseHoldingAttackSkill()
        self.srs.use(updated_entity=entity_to_kill)
        skill_used = True
      if (
        skill_used is not True
        and self.flame_totem
        and self.flame_totem.last_use_time + skill_use_delay < time.time()
        and self.flame_totem.getMinionsCountInRadius(distance_to_entity) != 0
      ):
        releaseHoldingAttackSkill()
        self.flame_totem.use(updated_entity=entity_to_kill)
        skill_used = True
      if (
        skill_used is not True
        and self.summon_skeletons
        and self.summon_skeletons.last_use_time + skill_use_delay < time.time()
        and self.summon_skeletons.getMinionsCountInRadius(distance_to_entity) < 0
      ):
        releaseHoldingAttackSkill()
        self.summon_skeletons.use(updated_entity=entity_to_kill)
        skill_used = True

      if holding_attacking_skill[0] is True:
        entity_to_kill.hover()
      else:
        if (
          skill_used is not True and self.attacking_skill and self.poe_bot.game_data.player.life.health.getPercentage() >= self.auto_flasks.hp_thresh
        ):
          entity_to_kill.hover()
          pressHoldingAttackSkill()

      if holding_attacking_skill[0] is not True:
        print("kiting")
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
    releaseHoldingAttackSkill()
    return res


# In[ ]:


class LocusMines(Build):
  def __init__(self, poe_bot: PoeBot) -> None:
    super().__init__(poe_bot)


class TricksterMinesLeveling(Build):
  def __init__(self, poe_bot: PoeBot) -> None:
    super().__init__(poe_bot)


# In[ ]:


A3_DIALLA_QUEST_REWARDS_DICT = {
  "str_amulet": "Art/2DItems/Amulets/Amulet3.dds",
  "dex_amulet": "Art/2DItems/Amulets/Amulet4.dds",
  "int_amulet": "Art/2DItems/Amulets/Amulet5.dds",
  "rarity_amulet": "Art/2DItems/Amulets/Amulet6.dds",
}


class LevelingStrategy:
  passive_tree_ids = []  # [123,1234,4356] ordered

  a3_dialla_quest_reward_choice_item_art = A3_DIALLA_QUEST_REWARDS_DICT["int_amulet"]

  # build
  # loot_fitler_special_settings = special_loot_filter.isItemPickable
  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot


class RangerBowVgLevelingStrategy(LevelingStrategy):
  def __init__(self, poe_bot: PoeBot) -> None:
    super().__init__(poe_bot)
    skills_data = poe_bot.backend.getSkillBar()
    skills_on_panel = skills_data["i_n"]
    quest_states = poe_bot.game_data.quest_states.getOrUpdate()
    if "venom_gyre" in skills_on_panel:
      print("build is venom gyre")
      self.build = getBuild("VenomGyre")(poe_bot=poe_bot)
      if quest_states.get("Visited7Town", False) is not False:
        links_to_collect = []
      else:
        links_to_collect = ["GGGG", "GGGB"]

      special_loot_filter = CustomLootFilter(collect_rare_keys=["Art/2DItems/Weapons/OneHandWeapons/Claws/Claw"], collect_links=links_to_collect)
      self.loot_fitler_special_settings = special_loot_filter.isItemPickable
    else:
      print("build is ranger for lvling")
      self.build = RangerLeveling(poe_bot=poe_bot)
      if quest_states.get("Visited4Town", False) is not False:
        collect_rgb = False
        links_to_collect = ["GGGG", "GGGB"]
      else:
        collect_rgb = True
        links_to_collect = ["GGG"]
      special_loot_filter = CustomLootFilter(
        collect_rare_keys=["Art/2DItems/Weapons/TwoHandWeapons/Bows"], collect_rgb=collect_rgb, collect_links=links_to_collect
      )
      self.loot_fitler_special_settings = special_loot_filter.isItemPickable


class SrsWitchLevelingStrategy(LevelingStrategy):
  def __init__(self, poe_bot) -> None:
    self.a3_dialla_quest_reward_choice_item_art = A3_DIALLA_QUEST_REWARDS_DICT["str_amulet"]
    self.build = WitchSrsLeveling(poe_bot=poe_bot)
    if poe_bot.game_data.quest_states.getOrUpdate().get("Visited3Town", False) is not False:
      collect_rgb = False
      links_to_collect = ["BBBR"]
    else:
      collect_rgb = True
      links_to_collect = ["BBR"]
    special_loot_filter = CustomLootFilter(collect_rgb=collect_rgb, collect_links=links_to_collect)
    self.loot_fitler_special_settings = special_loot_filter.isItemPickable
    super().__init__(poe_bot)


leveling_strategies_dict = {
  "ranger_vg": RangerBowVgLevelingStrategy,
  "ranger_roa": RangerBowVgLevelingStrategy,
  "witch_minions": SrsWitchLevelingStrategy,
  # "shadow_mines"
  # "shadow_hitter"
}


def getLevelingStrategy(strategy_str) -> LevelingStrategy:
  stragtegy_class = leveling_strategies_dict.get(strategy_str, None)
  print(f"[Quest] leveling strategy is {stragtegy_class}")
  if stragtegy_class is not None:
    return stragtegy_class
  else:
    poe_bot.raiseLongSleepException(f"wrong leveling strategy {strategy_str}")


# In[ ]:


REMOTE_IP = config["REMOTE_IP"]  # REMOTE_IP
UNIQUE_ID = config["unique_id"]  # unique id
LEVELING_STRATEGY = config["leveling_strategy"]  # unique id
force_reset_temp = config["force_reset_temp"]
print(f"running quest using: REMOTE_IP: {REMOTE_IP} unique_id: {UNIQUE_ID} force_reset_temp: {force_reset_temp}")


# In[ ]:


poe_bot = PoeBot(unique_id=UNIQUE_ID, remote_ip=REMOTE_IP, debug=notebook_dev)
bot_controls = poe_bot.bot_controls

stash = poe_bot.ui.stash
inventory = poe_bot.ui.inventory
trade_window = poe_bot.ui.trade_window
# map_device = poe_bot.ui.map_device
afk_temp = poe_bot.afk_temp

poe_bot.refreshAll()
poe_bot.game_data.terrain.getCurrentlyPassableArea()


# In[10]:


leveling_strategy = getLevelingStrategy(LEVELING_STRATEGY)(poe_bot=poe_bot)
# leveling_strategy = RangerBowVgLevelingStrategy(poe_bot=poe_bot)
# leveling_strategy = SrsWitchLevelingStrategy(poe_bot=poe_bot)
poe_bot.combat_module.build = leveling_strategy.build
build = poe_bot.combat_module.build
poe_bot.loot_picker.loot_filter.special_rules = [leveling_strategy.loot_fitler_special_settings]


# In[ ]:


class ExplorerModule:
  discovery_points = []

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot

  def generatePointsForDiscovery(self, furthest=False):
    tsp = TSP(poe_bot=self.poe_bot)
    tsp.generatePointsForDiscovery()
    if furthest:
      discovery_points = tsp.sortedPointsForDiscovery(poe_bot.pather.utils.getFurthestPoint(poe_bot.game_data.player.grid_pos.toList()))
    else:
      discovery_points = tsp.sortedPointsForDiscovery(poe_bot.game_data.player.grid_pos.toList())
    discovery_points = list(filter(lambda p: poe_bot.game_data.terrain.checkIfPointPassable(p[0], p[1]), discovery_points))
    print(f"len(discovery_points) {len(discovery_points)} after sorting")
    self.discovery_points = discovery_points
    return discovery_points

  def explorePointTill(self, point_to_go, custom_break_function=alwaysFalseFunction):
    # check if point needs to be explored
    # need_to_explore = needToExplore(point_to_go=point_to_go)

    # go to point to make it explored
    result = self.poe_bot.mover.goToPoint(
      point=point_to_go,
      min_distance=50,
      release_mouse_on_end=False,
      custom_break_function=custom_break_function,
      custom_continue_function=build.usualRoutine,
      step_size=random.randint(30, 35),
    )
    # then, it result is True, False or None
    print(f"mover.goToPoint result {result}")

    # if we arrived to discovery point and nothing happened
    if result is None:
      poe_bot.refreshInstanceData()
      poe_bot.last_action_time = 0

    return result

  def exploreTill(self, custom_break_function=alwaysFalseFunction, generate_discovery_points=True):
    if generate_discovery_points is True:
      self.generatePointsForDiscovery()
    while len(self.discovery_points) != 0:
      point_to_go = self.discovery_points.pop(0)
      print(f"willing to explore next point {point_to_go}")
      need_to_explore = poe_bot.helper_functions.needToExplore(point_to_go=point_to_go)

      if need_to_explore is True:
        print(f"exploring point {point_to_go}")
        res = False
        explore_iter = 0
        while res is not None:
          explore_iter += 1
          print(f"point_to_go {point_to_go}, explore_iter: {explore_iter}")
          res = self.explorePointTill(point_to_go=point_to_go, custom_break_function=custom_break_function)
        print(f"point_to_go {point_to_go} explored")
      else:
        print(f"point {point_to_go} already explored")


class ExplorerRoutineSettings:
  force_kill_rares = False
  force_kill_blue = False

  def __init__(self, config: dict) -> None:
    for key, value in config.items():
      setattr(self, key, value)


class ExplorerRoutine:
  def __init__(self, settings: ExplorerRoutineSettings) -> None:
    self.settings = settings

  def exploreRoutine(self, *args):
    if self.settings.force_kill_rares is True:
      rares_nearby = list(filter(lambda e: e.distance_to_player < 60, poe_bot.game_data.entities.attackable_entities_rares))
      for rare_mob in rares_nearby:
        updated_entity = list(filter(lambda e: e.id == rare_mob.id, poe_bot.game_data.entities.attackable_entities_rares))
        if len(updated_entity) != 0:
          updated_entity = updated_entity[0]
          poe_bot.combat_module.killUsualEntity(updated_entity)
          return True

    if self.settings.force_kill_blue is True:
      rares_nearby = list(filter(lambda e: e.distance_to_player < 60, poe_bot.game_data.entities.attackable_entities_blue))
      for blue_mob in rares_nearby:
        updated_entity = list(filter(lambda e: e.id == blue_mob.id, poe_bot.game_data.entities.attackable_entities_blue))
        if len(updated_entity) != 0:
          updated_entity = updated_entity[0]
          poe_bot.combat_module.killUsualEntity(updated_entity)
          return True

    loot_collected = poe_bot.loot_picker.collectLoot()
    if loot_collected is True:
      if len(inventory.getFilledSlots()) > 51:
        self.can_pick_drop = False
      else:
        self.can_pick_drop = True
      return loot_collected

    return False


def exploreTill(custom_break_function=alwaysFalseFunction):
  tsp = TSP(poe_bot=poe_bot)
  tsp.generatePointsForDiscovery()
  mover = poe_bot.mover
  map_complete = False
  while map_complete is False:
    poe_bot.refreshInstanceData()
    print("generating pathing points")
    discovery_points = tsp.sortedPointsForDiscovery()
    print(f"len(discovery_points) {len(discovery_points)}")
    discovery_points = list(filter(lambda p: poe_bot.helper_functions.checkIfEntityOnCurrenctlyPassableArea(p[0], p[1]), discovery_points))
    print(f"len(discovery_points) {len(discovery_points)} after sorting")
    if len(discovery_points) == 0:
      print("len(discovery_points) == 0 after points generation")
      map_complete = True
      break
    point_to_go = discovery_points.pop(0)
    while point_to_go is not None:
      # check if point needs to be explored
      # need_to_explore = needToExplore(point_to_go=point_to_go)
      need_to_explore = True

      if need_to_explore is True:
        print(f"exploring point {point_to_go}")
      else:
        print(f"surrounding around {point_to_go} discovered, skipping")
        try:
          point_to_go = discovery_points.pop(0)
        except:
          point_to_go = None
        continue

      # go to point to make it explored
      result = mover.goToPoint(
        point=point_to_go,
        min_distance=50,
        release_mouse_on_end=False,
        custom_break_function=custom_break_function,
        custom_continue_function=build.usualRoutine,
        step_size=random.randint(30, 35),
      )
      # then, it result is True, False or None
      print(f"mover.goToPoint result {result}")

      # if we arrived to discovery point and nothing happened
      if result is None:
        while True:
          if len(discovery_points) == 0:
            point_to_go = None
            map_complete = True
            print("len(discovery_points) == 0, breaking")
            break

          point_to_go = discovery_points.pop(0)
          print(f"willing to explore next point {point_to_go}")
          need_to_explore = poe_bot.helper_functions.needToExplore(point_to_go=point_to_go)

          if need_to_explore is True:
            print(f"exploring point {point_to_go}")
            break
          else:
            print(f"surrounding around {point_to_go} discovered, skipping")
            continue

      poe_bot.refreshInstanceData()
      poe_bot.last_action_time = 0


# In[ ]:


from utils.encounters import Bossroom

QUEST_KEYS = {
  "baleful_gem_quest": "a2q6",
  "hailrake_chest": "a2q4",
  "malagrios_spike": "a2q4",
}
LAB_QUEST_FLAGS = {
  "a1_prison": "NormalLabyrinthCompletedPrison",
  "a2_crypt": "NormalLabyrinthCompletedSins",
  "a2_chamber": "NormalLabyrinthCompletedCrypt",
}


class QuestArea:
  ready = True
  location_name = "unknown"
  is_town = False
  waypoint_string = "unknown"
  can_open_waypoint = False
  relog_after_waypoint_opened = False
  lab_trial_flag = None
  need_to_do_lab_trial = False
  lab_enterance_loc = None
  possible_to_enter_transitions = []
  multi_layerd_transitions_render_names = []
  blockades_paths = []
  refresh_area_on_blockade = False
  blockades_to_ignore_ids = []
  bossroom_transitions = []
  bossroom_entities_render_names = []
  bossrom_activator: str = None
  bossroom_activate_boss_in_center = False
  unique_entities_to_kill_render_names = []
  bandit_name = None
  explorer_routine: ExplorerRoutine
  explore_furthest = False

  def isNeedToDoLabTrial(self, lab_trial_flag=None):
    if lab_trial_flag is None:
      lab_trial_flag = self.lab_trial_flag
    if lab_trial_flag is not None:
      quest_flags = poe_bot.backend.getQuestFlags()
      quest_flag = quest_flags.get(lab_trial_flag, False)
      if quest_flag is False:
        self.need_to_do_lab_trial = True
        print("[quest] need to do lab in this area")
        return True
      else:
        print("[quest] doesnt need to do lab in this area")
    return False

  def isNeedToOpenWaypoint(self):
    self.can_open_waypoint = False
    return False

    if self.waypoint_string is not None:
      if self.waypoint_string == "unknown":
        print("can open waypoint here, but index is unknown")
        self.can_open_waypoint = True
        return True
      waypoints_state = poe_bot.backend.getWaypointState()
      current_area_waypoint_index = WAYPOINTS.index(self.waypoint_string)
      if waypoints_state[current_area_waypoint_index] is False:
        print("can open waypoint here")
        self.can_open_waypoint = True
        return True
    return False

  def initBossroom(self, bossroom_entity: Entity):
    return Bossroom(
      poe_bot=poe_bot,
      transition_entity=bossroom_entity,
      boss_render_names=self.bossroom_entities_render_names,
      activator_inside_bossroom_path=self.bossrom_activator,
      activate_boss_in_center=self.bossroom_activate_boss_in_center,
      clear_room_custom_break_function=self.bossroom_clear_room_custom_break_function,
    )

  def complete(self):
    explorer_module = ExplorerModule(poe_bot=poe_bot)
    discovery_points = explorer_module.generatePointsForDiscovery(furthest=self.explore_furthest)
    explorer_settings = ExplorerRoutineSettings(
      {
        "force_kill_rares": False,
        "force_kill_blue": False,
      }
    )
    explorer_routine = ExplorerRoutine(explorer_settings)
    self.explorer_routine = explorer_routine

    def findBlockade():
      return next(
        (e for e in poe_bot.game_data.entities.all_entities if e.path in self.blockades_paths and e.id not in self.blockades_to_ignore_ids), None
      )

    def exploreRoutine(*args):
      nonlocal discovery_points
      self.openWaypointIfPossible()
      self.enterTransitionIfPossible()
      # special entity to kill in area
      if self.unique_entities_to_kill_render_names != []:
        unique_entity_to_kill = next(
          (
            e
            for e in poe_bot.game_data.entities.attackable_entities
            if e.rarity == "Unique" and e.render_name in self.unique_entities_to_kill_render_names
          ),
          None,
        )
        if unique_entity_to_kill is not None:
          print("found unique_entity_to_kill")
          poe_bot.mover.goToEntitysPoint(unique_entity_to_kill, min_distance=50)
          poe_bot.combat_module.killUsualEntity(unique_entity_to_kill)
          self.funcToCallAfterKillingUniqueEntity()
          return True
      # extra quest in area
      extra_quest_result = self.extraQuestInLoc()
      if extra_quest_result is not False:
        print(f"extra_quest_result returns {extra_quest_result}")
        return extra_quest_result
      # in case it needs to do lab
      if self.lab_trial_flag is not None:
        if self.lab_enterance_loc is None:
          lab_enterance = next(
            (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Labyrinth/Objects/LabyrinthIntroDoor"), None
          )
          if lab_enterance:
            return "lab_enterance_found"
      # in case if need to do bandit quest in this area
      if self.bandit_name:
        bandit_npc = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == self.bandit_name), None)
        if bandit_npc and bandit_npc.life.health.current != 0:
          self.doBanditQuest()
          self.afterBanditQuestFunction()
          return True
      # bossfights
      if len(self.bossroom_transitions) != 0:
        bossroom_entity = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name in self.bossroom_transitions), None)
        if bossroom_entity:
          print(f"found bossroom entity {bossroom_entity.raw}")
          bossroom_encounter = self.initBossroom(bossroom_entity=bossroom_entity)
          bossroom_encounter.enterBossroom()
          self.clearBossroom(bossroom_encounter)
          bossroom_encounter.leaveBossroom()
      if len(self.multi_layerd_transitions_render_names) != 0:
        transition = next(
          (
            e
            for e in poe_bot.game_data.entities.area_transitions
            if e.id not in self.area_temp.transitions_exits_ids
            and e.render_name in self.multi_layerd_transitions_render_names
            and e.isOnPassableZone() is not False
          ),
          None,
        )
        if transition:
          print("found transition to next")
          poe_bot.mover.goToEntitysPoint(transition)
          poe_bot.mover.enterTransition(transition)
          exit_transitions = []
          look_for_exit_transition = 0
          while len(exit_transitions) == 0:
            look_for_exit_transition += 1
            if look_for_exit_transition == 20 or look_for_exit_transition == 40:
              poe_bot.backend.forceRefreshArea()
            if look_for_exit_transition > 100:
              poe_bot.on_stuck_function()
              raise Exception("look_for_exit_transition > 100:")
              # poe_bot.raiseLongSleepException('look_for_exit_transition > 100:')
              # break
            poe_bot.refreshInstanceData(reset_timer=True)
            exit_transitions = list(filter(lambda e: e.rarity == "White" and e.id != transition.id, poe_bot.game_data.entities.area_transitions))
          exit_transition = exit_transitions[0]
          print(f"found exit transition {exit_transition.raw}")
          self.area_temp.transitions_exits_ids.append(exit_transition.id)
          self.area_temp.save()
          poe_bot.game_data.terrain.getCurrentlyPassableArea()
          discovery_points = explorer_module.generatePointsForDiscovery(furthest=self.explore_furthest)
          return None
      if self.blockades_paths != []:
        blockade = findBlockade()
        if blockade is not None:
          return "blockade_found"
      er_res = explorer_routine.exploreRoutine()
      if er_res is not False:
        return er_res
      return False

    while len(discovery_points) != 0:
      point_to_go = discovery_points.pop(0)
      print(f"point_to_go {point_to_go}")
      while True:
        res = poe_bot.mover.goToPoint(
          point=point_to_go,
          min_distance=50,
          release_mouse_on_end=False,
          custom_break_function=exploreRoutine,
          custom_continue_function=build.usualRoutine,
          step_size=random.randint(30, 35),
        )
        print(f"res: {res}")
        if res is None:
          break
        elif res == "lab_enterance_found":
          lab_enterance = next(
            (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Labyrinth/Objects/LabyrinthIntroDoor"), None
          )
          if lab_enterance:
            self.lab_enterance_loc = (lab_enterance.grid_position.x, lab_enterance.grid_position.y)
            copy_of = poe_bot.game_data.terrain.passable.copy()
            copy_of_currently_passable_area = poe_bot.game_data.terrain.currently_passable_area.copy()

            # plt.imshow(copy_of);plt.show()
            # plt.imshow(copy_of_currently_passable_area);plt.show()
            # area_ = 40
            # plt.imshow(copy_of[lab_enterance.grid_position.y-area_:lab_enterance.grid_position.y+area_, lab_enterance.grid_position.x-area_:lab_enterance.grid_position.x+area_]);plt.show()
            # plt.imshow(copy_of_currently_passable_area[lab_enterance.grid_position.y-area_:lab_enterance.grid_position.y+area_, lab_enterance.grid_position.x-area_:lab_enterance.grid_position.x+area_]);plt.show()

            entrance_pos_x, entrance_pos_y = lab_enterance.grid_position.x, lab_enterance.grid_position.y
            entrance_pos_x_orig, entrance_pos_y_orig = lab_enterance.grid_position.x, lab_enterance.grid_position.y
            limit_lower = 0
            limit_upper = 0
            broken_axis = None
            while True:
              entrance_pos_x += 1
              if copy_of[entrance_pos_y_orig, entrance_pos_x] != 1:
                print("broke x")
                broken_axis = "x"
                limit_upper = entrance_pos_x
                entrance_pos_x = entrance_pos_x_orig
                while copy_of[entrance_pos_y_orig, entrance_pos_x] == 1:
                  entrance_pos_x -= 1
                limit_lower = entrance_pos_x
                break

              entrance_pos_y += 1
              if copy_of[entrance_pos_y, entrance_pos_x_orig] != 1:
                print("broke y")
                broken_axis = "y"
                limit_upper = entrance_pos_y
                entrance_pos_y = entrance_pos_y_orig
                while copy_of[entrance_pos_y, entrance_pos_x_orig] == 1:
                  entrance_pos_y -= 1
                limit_lower = entrance_pos_y
                break
            limit_lower -= 1
            limit_upper += 1
            print(f"lower upper {limit_lower, limit_upper}")
            axis_length = 5
            if broken_axis == "y":
              copy_of[limit_lower:limit_upper, entrance_pos_x_orig - axis_length : entrance_pos_x_orig + axis_length] = 0  # y1 y2 x1 x2
            else:
              copy_of[entrance_pos_y_orig - axis_length : entrance_pos_y_orig + axis_length, limit_lower:limit_upper] = 0  # y1 y2 x1 x2

            poe_bot.game_data.terrain.passable = copy_of
            poe_bot.game_data.terrain.getCurrentlyPassableArea()
            lab_area = copy_of_currently_passable_area - poe_bot.game_data.terrain.currently_passable_area
            # sort other points

            discovery_points = list(filter(lambda point: poe_bot.game_data.terrain.checkIfPointPassable(point[0], point[1]), discovery_points))
            print(f"point to go {point_to_go} {discovery_points}")
            if self.need_to_do_lab_trial is True:
              self.doLab(lab_enterance, lab_area)
              self.onLabTrialCompleteFunction()
              self.need_to_do_lab_trial = False
            if not poe_bot.game_data.terrain.checkIfPointPassable(point_to_go[0], point_to_go[1]):
              print("point to go became unpassable")
              break
        elif res == "blockade_found":
          blockade = findBlockade()
          if blockade:
            print(f"found blockade {blockade.raw}")
            if self.refresh_area_on_blockade is not False:
              poe_bot.refreshAll()
              poe_bot.game_data.terrain.getCurrentlyPassableArea()
            self.blockades_to_ignore_ids.append(blockade.id)

            copy_of = poe_bot.game_data.terrain.passable.copy()
            # plt.imshow(copy_of);plt.show()
            copy_of_currently_passable_area = poe_bot.game_data.terrain.currently_passable_area.copy()
            area_ = 15
            copy_of[
              blockade.grid_position.y - area_ : blockade.grid_position.y + area_, blockade.grid_position.x - area_ : blockade.grid_position.x + area_
            ] = 0
            poe_bot.game_data.terrain.passable = copy_of
            poe_bot.game_data.terrain.getCurrentlyPassableArea()
            lab_area = copy_of_currently_passable_area - poe_bot.game_data.terrain.currently_passable_area
            discovery_points = list(filter(lambda point: poe_bot.game_data.terrain.checkIfPointPassable(point[0], point[1]), discovery_points))
            print(f"point to go {point_to_go} {discovery_points}")
            if not poe_bot.game_data.terrain.checkIfPointPassable(point_to_go[0], point_to_go[1]):
              print("point to go became unpassable because of blockade")
              break
    raise "completed"

  def enterBossroomIfNeeded(self):
    if len(self.bossroom_transitions) != 0:
      boss_transition = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name in self.bossroom_transitions), None)
      if boss_transition:
        curr_pos_x, curr_pos_y = poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y
        entered = False
        if "grace_period" in poe_bot.game_data.player.buffs:
          poe_bot.game_data.player.buffs.remove("grace_period")
          while entered is False:
            print("nearby bossroom, but seems like just resurected")
            boss_transition.click(update_screen_pos=True)
            time.sleep(1)
            poe_bot.refreshInstanceData()
            new_curr_pos_x, new_curr_pos_y = poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y
            distance_to_enterance = dist((curr_pos_x, curr_pos_y), (new_curr_pos_x, new_curr_pos_y))
            print(f"distance {distance_to_enterance}")
            if distance_to_enterance > 100 or "grace_period" in poe_bot.game_data.player.buffs:
              print("distance_to_enterance > 100 or grace_period, seems like teleported(entered)")
              poe_bot.game_data.terrain.getCurrentlyPassableArea()
              break
        else:
          poe_bot.mover.enterTransition(boss_transition)
        bossroom_encounter = self.initBossroom(bossroom_entity=boss_transition)
        bossroom_encounter.onEnteringBossroom()
        self.clearBossroom(bossroom_encounter)
        bossroom_encounter.leaveBossroom()

  def enterMultilayerdIfNeeded(self):
    if len(self.multi_layerd_transitions_render_names) != 0:
      transition = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name in self.multi_layerd_transitions_render_names), None)
      if transition:
        curr_pos_x, curr_pos_y = poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y
        entered = False
        if "grace_period" in poe_bot.game_data.player.buffs:
          poe_bot.game_data.player.buffs.remove("grace_period")
          while entered is False:
            print("nearby bossroom, but seems like just resurected")
            transition.click(update_screen_pos=True)
            time.sleep(1)
            poe_bot.refreshInstanceData()
            new_curr_pos_x, new_curr_pos_y = poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y
            distance_to_enterance = dist((curr_pos_x, curr_pos_y), (new_curr_pos_x, new_curr_pos_y))
            print(f"distance {distance_to_enterance}")
            if distance_to_enterance > 100 or "grace_period" in poe_bot.game_data.player.buffs:
              print("distance_to_enterance > 100 or grace_period, seems like teleported(entered)")
              poe_bot.game_data.terrain.getCurrentlyPassableArea()
              break
        else:
          poe_bot.mover.enterTransition(transition)
        exit_transitions = []
        look_for_exit_transition = 0
        while len(exit_transitions) == 0:
          look_for_exit_transition += 1
          if look_for_exit_transition == 20 or look_for_exit_transition == 40:
            poe_bot.backend.forceRefreshArea()
          if look_for_exit_transition > 100:
            poe_bot.on_stuck_function()
            raise Exception("look_for_exit_transition > 100:")
            # poe_bot.raiseLongSleepException('look_for_exit_transition > 100:')
            # break
          poe_bot.refreshInstanceData(reset_timer=True)
          exit_transitions = list(filter(lambda e: e.rarity == "White" and e.id != transition.id, poe_bot.game_data.entities.area_transitions))
        exit_transition = exit_transitions[0]
        print(f"found exit transition {exit_transition.raw}")
        self.area_temp.transitions_exits_ids.append(exit_transition.id)
        self.area_temp.save()

  def clearBossroom(self, bossroom_encounter: Bossroom, just_resurrected=False):
    bossroom_encounter.clearBossroom()
    self.onBossroomCompleteFunction()
    self.bossroom_transitions.remove(bossroom_encounter.transition_entity.render_name)

  def bossroom_clear_room_custom_break_function(self, *args, **kwargs):
    return False

  def onBossroomCompleteFunction(self):
    pass

  def openWaypointIfPossible(self):
    if self.can_open_waypoint is True:
      waypoint = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Waypoint"), None)
      if waypoint is not None:
        if self.waypoint_string == "unknown":
          print("opening unknown waypoint")
          prev_waypoint_state = poe_bot.backend.getWaypointState()
          new_waypoint_state = prev_waypoint_state
          while new_waypoint_state == prev_waypoint_state:
            waypoint = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Waypoint"), None)
            poe_bot.mover.goToPoint(
              point=(waypoint.grid_position.x, waypoint.grid_position.y),
              custom_continue_function=poe_bot.combat_module.build.usualRoutine,
              release_mouse_on_end=False,
            )
            # waypoint.refresh()
            waypoint.click()
            poe_bot.refreshInstanceData()
            new_waypoint_state = poe_bot.backend.getWaypointState()

          for waypoint_state_index in range(len(new_waypoint_state)):
            new_state = new_waypoint_state[waypoint_state_index]
            prev_state = prev_waypoint_state[waypoint_state_index]
            if new_state != prev_state:
              print(f"waypoint_state_index {waypoint_state_index}, {poe_bot.game_data.area_raw_name}")
          input("opened new waypoint, input smth to continue")
        waypoints_state = poe_bot.backend.getWaypointState()
        current_area_waypoint_index = WAYPOINTS.index(self.waypoint_string)
        if waypoints_state[current_area_waypoint_index] is False:
          while waypoints_state[current_area_waypoint_index] is False:
            waypoint = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Waypoint"), None)
            poe_bot.mover.goToEntitysPoint(waypoint)
            poe_bot.combat_module.clearLocationAroundPoint({"X": waypoint.grid_position.x, "Y": waypoint.grid_position.y})
            poe_bot.refreshInstanceData()
            waypoints_state = poe_bot.backend.getWaypointState()
          for i in range(3, 4):
            poe_bot.ui.closeAll()
            time.sleep(random.randint(10, 20) / 100)
          self.can_open_waypoint = False
          self.onWaypointOpenedFunction()
          if self.relog_after_waypoint_opened is True:
            poe_bot.helper_functions.relog()
          self.can_open_waypoint = False
          return True

  def onWaypointOpenedFunction(self):
    return False

  def enterTransitionIfPossible(self):
    if len(self.possible_to_enter_transitions) != 0:
      for e in poe_bot.game_data.entities.area_transitions:
        if e.render_name in self.possible_to_enter_transitions:
          transition = e
          poe_bot.mover.goToEntitysPoint(transition)
          poe_bot.mover.enterTransition(transition, necropolis_ui=True)
          return True

  def doBanditQuest(self):
    bandit_name = self.bandit_name
    bandit = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == bandit_name), None)
    if bandit:
      print("found bandit")
      poe_bot.mover.goToPoint(
        (bandit.grid_position.x, bandit.grid_position.y),
        custom_continue_function=poe_bot.combat_module.build.usualRoutine,
        release_mouse_on_end=False,
      )
      bandit = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == bandit_name), None)
      bandit.click()
      time.sleep(random.randint(5, 7) / 10)
      data_raw = poe_bot.ui.bandit_dialogue.update()
      bandit_ui_visible = data_raw["v"] != 0
      print(f"bandit_ui_visible {bandit_ui_visible}")
      while bandit_ui_visible is False:
        print(f"while cycle bandit_ui_visible {bandit_ui_visible}")
        data_raw = poe_bot.ui.bandit_dialogue.update()
        bandit = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == bandit_name), None)
        if bandit:
          bandit.click()
          data_raw = poe_bot.ui.bandit_dialogue.update()
          bandit_ui_visible = data_raw["v"] != 0
          poe_bot.ui.closeAll()
          poe_bot.refreshInstanceData()

      kill_button_pos = (int((data_raw["k_sz"][0] + data_raw["k_sz"][1]) / 2), int((data_raw["k_sz"][2] + data_raw["k_sz"][3]) / 2))
      pos_x, pos_y = poe_bot.convertPosXY(kill_button_pos[0], kill_button_pos[1], safe=False)
      for i in range(random.randint(2, 4)):
        poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
        poe_bot.bot_controls.mouseClick(pos_x, pos_y)

      while True:
        bandit = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == bandit_name), None)
        if bandit and bandit.life.health.current != 0:
          poe_bot.combat_module.killUsualEntity(bandit)
        else:
          break

      print("bandit quest finished")
      self.bandit_name = False
      return True

  def afterBanditQuestFunction(self):
    return

  def doLab(self, lab_enterance: Entity, lab_area):
    poe_bot.mover.goToPoint(
      point=(lab_enterance.grid_position.x, lab_enterance.grid_position.y),
      release_mouse_on_end=False,
      custom_continue_function=poe_bot.combat_module.build.usualRoutine,
    )
    lab_enterance.clickTillNotTargetable()
    input("do lab for me")
    return True

  def onLabTrialCompleteFunction(self):
    self.need_to_do_lab_trial = False
    return True

  def extraQuestInLoc(self):
    return False

  def funcToCallAfterKillingUniqueEntity(self):
    return False

  def enterAfterResurrect(self):
    self.enterBossroomIfNeeded()
    self.enterMultilayerdIfNeeded()

  def updateQuestStatus(self, force_update=False):
    if force_update is not False:
      poe_bot.game_data.quest_states.update()

  def updateGoals(self, force_update=False):
    pass

  def __init__(self) -> None:
    print(f"[quest] current area {poe_bot.game_data.area_raw_name}")
    self.isNeedToOpenWaypoint()
    self.isNeedToDoLabTrial()
    self.updateQuestStatus()
    self.updateGoals()
    if self.is_town:
      pass
    else:
      self.area_temp = AreaTempData(poe_bot.unique_id)
      if poe_bot.game_data.area_hash != self.area_temp.area_hash:
        self.area_temp.reset()
        self.area_temp.area_hash = poe_bot.game_data.area_hash
        self.area_temp.save()
      # find nearest transition
      poe_bot.mover.default_continue_function = poe_bot.combat_module.build.usualRoutine
      if self.ready is False:
        input("experimental, input smth")
      if "grace_period" in poe_bot.game_data.player.buffs:
        print("[quest] seems like just resurrected")
        self.enterAfterResurrect()
        poe_bot.combat_module.aura_manager.activateAurasIfNeeded()


# a1
class Loc1_1_town(QuestArea):
  def __init__(self) -> None:
    quest_states = poe_bot.backend.getQuestStates()
    # hillock
    a1q1_state = next((quest["state"] for quest in quest_states if quest["id"] == "a1q1"))
    if a1q1_state != 0:
      print("hailrake reward, need to pick reward")
      tarkleigh_npc = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Tarkleigh"), None)
      if tarkleigh_npc:
        poe_bot.mover.goToEntity(tarkleigh_npc)
        # TODO talk till reward window appears
        # pick reward
      raise "manual stuff?"
    a1q5_state = next((quest["state"] for quest in quest_states if quest["id"] == "a1q5"))
    if a1q5_state < 5 and a1q5_state != 0:
      print("medcine chest < 5, need to pick reward")
      tarkleigh_npc = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Tarkleigh"), None)
      if tarkleigh_npc:
        poe_bot.mover.goToEntity(tarkleigh_npc)
        # TODO talk till reward window appears
        # pick reward
      raise "manual stuff?"

    a1q4_state = next((quest["state"] for quest in quest_states if quest["id"] == "a1q4"))
    if a1q4_state < 3 and a1q4_state != 0:
      print("break eggs < 3, need to pick reward twice")
      tarkleigh_npc = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Tarkleigh"), None)
      if tarkleigh_npc:
        poe_bot.mover.goToEntity(tarkleigh_npc)
        # TODO talk till reward window appears
        # pick reward
      raise "manual stuff?"

    a1q7_state = next((quest["state"] for quest in quest_states if quest["id"] == "a1q7"))
    if a1q7_state < 4 and a1q7_state != 0:
      print("dweller of the deep < 4, need to pick reward")
      tarkleigh_npc = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Tarkleigh"), None)
      if tarkleigh_npc:
        poe_bot.mover.goToEntity(tarkleigh_npc)
        # TODO talk till reward window appears
        # pick reward
      raise "manual stuff?"

    # quest_state_index a1q3, prev: 6 new: 7
    # caverns of anger

    # fairgraives quest after book is used
    # quest_state_index a1q6, prev: 3 new: 0

    # ???
    # quest_state_index a1q2, prev: 1 new: 0

    raise "get to portal, go to next area"


class Loc1_1_1(QuestArea):
  def complete(self):
    raise "smth is over"
    tutorial_blockers = list(
      filter(lambda e: e.path == "Metadata/Terrain/Act1/Area1/Objects/Tutorial_Blocker_1", poe_bot.game_data.entities.all_entities)
    )
    if len(tutorial_blockers) != 0:
      tutorial_blocker = tutorial_blockers[0]
      if tutorial_blocker.is_opened is False:
        print("tutorial blocker is visible, need to close all tutorials")

        poe_bot.refreshInstanceData()
        pos_x, pos_y = poe_bot.convertPosXY(random.randint(460, 575), random.randint(710, 725), safe=False)
        poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
        time.sleep(random.randint(10, 20) / 10)
        poe_bot.bot_controls.mouseClick(pos_x, pos_y)

    # if no weapon equipped pick something, and equip it
    poe_bot.refreshInstanceData()
    pickable_items = poe_bot.loot_picker.loot_filter.getPickableItems()
    pickable_weapon_items = list(filter(lambda i_label: "Art/2DItems/Weapons/" in i_label.icon_render, pickable_items))
    print(pickable_weapon_items)
    if len(pickable_weapon_items):
      poe_bot.loot_picker.pickupDropV6(pickable_weapon_items)
    # TODO if no spell on panel, and no gem in inventory,
    # "Metadata/NPC/Act1/WoundedExile" - Talk
    # "Metadata/Monsters/Zombies/ZombieBite - kill
    # gem pick
    poe_bot.refreshInstanceData()
    pickable_items = poe_bot.loot_picker.loot_filter.getPickableItems()
    pickable_gems = list(filter(lambda i_label: "Art/2DItems/Gems/" in i_label.icon_render, pickable_items))
    if len(pickable_gems):
      poe_bot.loot_picker.pickupDropV6(pickable_gems)

    # gem equip

    # "Metadata/Chests/TutorialSupportGemChest" - open
    # pick gem, equip

    # "Metadata/Monsters/ZombieBoss/ZombieBossHillockNormal" - kill
    # pick all

    # "Metadata/QuestObjects/SouthBeachTownEntrance" - enter

    return super().complete()


class Loc1_1_2(QuestArea):
  ready = True
  waypoint_string = "1_1_2"

  def getTransitions(self):
    quest_states = poe_bot.backend.getQuestStates()
    quest_state = next((i for i in quest_states if i["id"] == "a1q5"), None)["state"]
    if quest_state > 4:
      print("can visit The Tidal Island")
      self.possible_to_enter_transitions.append("The Tidal Island")
      self.explore_furthest = True
    else:
      # if not "The Tidal Island" in self.possible_to_enter_transitions:
      print("tidal island completed1 already, can go for mud flats")
      quest_state = next((i for i in quest_states if i["id"] == "a1q4"), None)["state"]
      if quest_state > 2:
        print("can visit the mud flats")
        self.possible_to_enter_transitions.append("The Mud Flats")

  def __init__(self) -> None:
    super().__init__()
    if self.can_open_waypoint is False:
      print("can go further to do quests")
      self.getTransitions()
    else:
      print("need to open waypoint first")

  def onWaypointOpenedFunction(self):
    self.getTransitions()
    return super().onWaypointOpenedFunction()


class Loc1_1_2a(QuestArea):
  ready = True
  unique_entities_to_kill_render_names = []

  def checkIfHaveChest(self):
    quest_flags = poe_bot.backend.getQuestFlags()
    self.have_chest = quest_flags.get("A1Q5HaveMedicineChest", False)
    if self.have_chest is not False:
      self.possible_to_enter_transitions = ["The Coast"]
    else:
      self.unique_entities_to_kill_render_names.append("Hailrake")
    return self.have_chest

  def __init__(self) -> None:
    self.checkIfHaveChest()
    if self.have_chest is not False:
      print("have chest, dont need to kill hailrake")
    else:
      print("dont have chest,need to kill hailrake")
    super().__init__()

  def extraQuestInLoc(self):
    if self.have_chest is not True:
      hailrake_entity = next(
        (
          e
          for e in poe_bot.game_data.entities.unique_entities
          if e.is_attackable is not False and e.is_targetable is not False and e.render_name == "Hailrake"
        ),
        None,
      )
      if hailrake_entity:
        poe_bot.mover.goToEntitysPoint(hailrake_entity)
        poe_bot.loot_picker.collectLootWhilePresented()
        self.checkIfHaveChest()
    return super().extraQuestInLoc()


class Loc1_1_3(QuestArea):
  can_break_eggs = True
  need_to_break_eggs_count = 3
  glyph_loc = None
  can_open_glyph = False
  internal_iter = 0

  def updateQuestStatus(self, force_update=True):
    super().updateQuestStatus(force_update=force_update)
    quest_flags = poe_bot.game_data.quest_states.get()
    glyph_placed = quest_flags.get("A1Q4PlacedGlyphs", False)
    if glyph_placed is True:
      print("no need to do anything here go further")
      self.possible_to_enter_transitions.append("The Submerged Passage")
    else:
      print("need to place glyph")
      glyph_keys = [
        "A1Q4HaveGlyph1",
        "A1Q4HaveGlyph2",
        "A1Q4HaveGlyph3",
      ]
      glyph_status = list(map(lambda key: quest_flags.get(key, False), glyph_keys))
      if False in glyph_status:
        print("need to collect glyphs")
        self.can_open_glyph = False
      else:
        print("can open door")
        self.can_open_glyph = True

  def extraQuestInLoc(self):
    self.internal_iter += 1
    if self.internal_iter % 100 == 0:
      self.updateQuestStatus()
    if self.glyph_loc is None:
      print("found glyph loc")
      glyph_wall = next(
        (e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Strange Glyph Wall" and e.is_targetable is True), None
      )
      if glyph_wall:
        self.glyph_loc = (glyph_wall.grid_position.x, glyph_wall.grid_position.y)
    if self.can_open_glyph and self.glyph_loc is not None:
      print("can place glyph and its location is known")
      print("going to glyph")
      while 1:
        res = poe_bot.mover.goToPoint(
          point=(self.glyph_loc[0], self.glyph_loc[1]),
          release_mouse_on_end=False,
          custom_continue_function=poe_bot.combat_module.build.usualRoutine,
          custom_break_function=poe_bot.loot_picker.collectLoot,
        )
        if res is None:
          break

      tranisition = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "The Submerged Passage"), None)
      if tranisition and tranisition.is_targetable is False:
        glyph_wall = next(
          (e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Strange Glyph Wall" and e.is_targetable is True), None
        )
        glyph_wall.clickTillNotTargetable()

      res = poe_bot.mover.goToPoint(
        point=(tranisition.grid_position.x, tranisition.grid_position.y),
        release_mouse_on_end=False,
        custom_continue_function=poe_bot.combat_module.build.usualRoutine,
        custom_break_function=poe_bot.loot_picker.collectLoot,
      )
      poe_bot.mover.enterTransition(transition=tranisition, necropolis_ui=True)
    rhoa_chest = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Rhoa Nest" and e.is_opened is False), None)
    if rhoa_chest:
      print("found rhoa chest")
      print("going to rhoa chest")
      poe_bot.mover.goToPoint(
        (rhoa_chest.grid_position.x, rhoa_chest.grid_position.y), min_distance=20, custom_continue_function=poe_bot.combat_module.build.usualRoutine
      )
      print("clearing to rhoa chest")
      poe_bot.combat_module.clearLocationAroundPoint(
        {
          "X": rhoa_chest.grid_position.x,
          "Y": rhoa_chest.grid_position.y,
        },
        detection_radius=40,
      )
      print("clicking rhoa chest")
      rhoa_chest.clickTillNotTargetable()
      loot_collected = True
      while loot_collected is True:
        loot_collected = poe_bot.loot_picker.collectLoot()
      print("loot collected")
      self.updateQuestStatus()
      return True

    return super().extraQuestInLoc()

  def __init__(self) -> None:
    super().__init__()
    self.updateQuestStatus()


class Loc1_1_4_1(QuestArea):
  ready = True
  waypoint_string = "1_1_4_1"
  relog_after_waypoint_opened = True

  def __init__(self) -> None:
    self.isNeedToOpenWaypoint()
    quest_states = poe_bot.backend.getQuestStates()
    quest_state = next((i for i in quest_states if i["id"] == "a1q7"), None)["state"]
    if quest_state > 4:
      print("can visit dweller")
      self.possible_to_enter_transitions.append("The Flooded Depths")
    else:
      print("no need to visit dweller")
      self.possible_to_enter_transitions.append("The Ledge")
    super().__init__()


class Loc1_1_4_0(QuestArea):  # dweller
  need_to_kill_dweller = False
  unique_entities_to_kill_render_names = ["The Dweller of the Deep"]

  def isDwellerKilled(self):
    quest_flags = poe_bot.backend.getQuestFlags()
    dweller_killed = quest_flags.get("A1Q7KilledDweller", False)
    return dweller_killed

  def extraQuestInLoc(self):
    if self.need_to_kill_dweller:
      dweller_entity = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "The Dweller of the Deep"), None)
      if dweller_entity:
        print("going to dweller")
        poe_bot.mover.goToEntitysPoint(dweller_entity, min_distance=50)
        essence_entities = list(filter(lambda e: e.path == "Metadata/MiscellaneousObjects/Monolith", poe_bot.game_data.entities.all_entities))
        if dweller_entity.is_attackable is False and len(essence_entities) == 1:
          print("dweller is not attackable and there is an essence around it")
          essence_entity = essence_entities[0]
          essence_monolith_id = essence_entity.id
          essence_opened = False
          open_essence_iteration = 0
          while essence_opened is False and len(essence_entities) != 0:
            open_essence_iteration += 1
            if open_essence_iteration > 50:
              poe_bot.helper_functions.relog()
              raise Exception("cannot open essence monolith for 50 iterations")
            essence_entities = list(filter(lambda entity: essence_monolith_id == entity.id, poe_bot.game_data.entities.all_entities))
            # if len(essences) == 0:
            #   break
            essence_monolith = essence_entities[0]
            print(f"essence_monolith {essence_monolith}")
            if essence_monolith.distance_to_player > 40:
              print("essence_monolith distance to player is too far away, getting closer")
              poe_bot.mover.goToEntity(
                entity_to_go=essence_monolith,
                custom_continue_function=build.usualRoutine,
                release_mouse_on_end=False,
                # release_mouse_on_end=True,
                step_size=random.randint(25, 33),
              )
              continue
            pos_x, pos_y = poe_bot.convertPosXY(essence_monolith.location_on_screen.x, essence_monolith.location_on_screen.y)
            print(f"opening essence on {pos_x, pos_y}")
            poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
            # time.sleep(random.randint(5,7)/100)
            poe_bot.bot_controls.mouseClick(pos_x, pos_y)
            # time.sleep(random.randint(7,10)/100)
            poe_bot.refreshInstanceData()
            poe_bot.last_action_time = 0
            essence_entities = list(filter(lambda entity: essence_monolith_id == entity.id, poe_bot.game_data.entities.all_entities))
            if len(essence_entities) == 0 or essence_entities[0].is_targetable is False:
              break
          print("essence opened")
        elif dweller_entity.is_attackable:
          print("dweller is attackable, all good")
        # else:
        #   poe_bot.raiseLongSleepException('not only monolith in dweller location, possible todo')
        while True:
          if self.need_to_kill_dweller is False:
            print("dweller killed already")
            self.possible_to_enter_transitions = ["The Submerged Passage"]
            break
          dweller_entity_to_kill = next((e for e in poe_bot.game_data.entities.unique_entities if e.render_name == "The Dweller of the Deep"), None)
          if dweller_entity_to_kill:
            if dweller_entity_to_kill.is_attackable:
              poe_bot.combat_module.killTillCorpseOrDisappeared(dweller_entity_to_kill)
              if self.isDwellerKilled() is True:
                print("dweller is dead, can finish")
                raise Exception("dweller is killed, restaring")
            else:
              print("dweller is not attackable")
              print(dweller_entity_to_kill.raw)
              if self.isDwellerKilled() is True:
                self.need_to_kill_dweller = False
                self.possible_to_enter_transitions = ["The Submerged Passage"]

          else:
            print("no dweller entity found")
          poe_bot.refreshInstanceData()
    return super().extraQuestInLoc()

  def __init__(self) -> None:
    super().__init__()
    dweller_killed = self.isDwellerKilled()
    if dweller_killed:
      print("dweller killed")
      self.possible_to_enter_transitions = ["The Submerged Passage"]
    else:
      print("dweller is not killed")
      self.need_to_kill_dweller = True


class Loc1_1_5(QuestArea):
  ready = True
  waypoint_string = "1_1_5"
  explore_furthest = True

  def __init__(self) -> None:
    self.isNeedToOpenWaypoint()
    self.possible_to_enter_transitions.append("The Climb")
    super().__init__()


class Loc1_1_6(QuestArea):
  ready = True
  waypoint_string = "1_1_6"
  explore_furthest = True

  def __init__(self) -> None:
    self.isNeedToOpenWaypoint()
    self.possible_to_enter_transitions.append("The Lower Prison")
    super().__init__()


class Loc1_1_7_1(QuestArea):  # lab
  waypoint_string = "1_1_7_1"
  lab_trial_string = "labyrinth_a1"
  lab_trial_flag = "NormalLabyrinthCompletedPrison"
  relog_after_waypoint_opened = True
  lab_enterance_loc = None

  def __init__(self) -> None:
    super().__init__()
    if self.need_to_do_lab_trial is False:
      self.possible_to_enter_transitions.append("The Upper Prison")
      print("lab finished, going to next transition")
    else:
      print("need to do lab here first")


class Loc1_1_7_2(QuestArea):  # brutus
  bossroom_transitions = ["The Warden's Quarters"]
  bossroom_entities_render_names = ["Brutus, Lord Incarcerator"]
  blockades_paths = ["Metadata/Terrain/Labyrinth/Objects/HiddenDoor_Short"]

  def clearBossroom(self, bossroom_encounter: Bossroom):
    def lookForWardensChambers(*args, **kwargs):
      chambers_transition = next((e for e in poe_bot.game_data.entities.area_transitions if e.render_name == "The Warden's Chambers"), None)
      if chambers_transition:
        poe_bot.mover.goToEntitysPoint(chambers_transition)
        poe_bot.mover.enterTransition(chambers_transition)
        time.sleep(random.randint(10, 20) / 10)
        poe_bot.game_data.terrain.getCurrentlyPassableArea()
        pos_x, pos_y = poe_bot.game_data.terrain.getFurtherstPassablePoint()
        poe_bot.mover.goToPoint((pos_x, pos_y), release_mouse_on_end=False)
        prisoners_gate_transition = next((e for e in poe_bot.game_data.entities.area_transitions if e.render_name == "Prisoner's Gate"), None)
        if prisoners_gate_transition is None:
          poe_bot.raiseLongSleepException("cannot find prisoners gate")
        poe_bot.mover.goToEntitysPoint(prisoners_gate_transition)
        poe_bot.mover.enterTransition(prisoners_gate_transition, necropolis_ui=True)
      return False

    bossroom_encounter.clear_room_custom_break_function = lookForWardensChambers
    bossroom_encounter.clearBossroom()
    inside_wardens_chambers = False
    while inside_wardens_chambers is False:
      inside_wardens_chambers = lookForWardensChambers()
      bossroom_encounter.clearBossroom()
    # return super().clearBossroom(bossroom_entity)


class Loc1_1_8(QuestArea):
  ready = True
  waypoint_string = "1_1_8"
  explore_furthest = True

  def __init__(self) -> None:
    self.isNeedToOpenWaypoint()
    self.possible_to_enter_transitions.append("The Ship Graveyard")
    super().__init__()


class Loc1_1_9(QuestArea):
  waypoint_string = "1_1_9"
  fairgraves_loc: List[int] = None
  can_do_fairgraves_quest = True

  def doFairgravesQuest(self, npc_pos_x: int, npc_pos_y: int):
    # fairgraves_npc = next( (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/NPC/Act1/Fairgraves"), None)
    # npc_pos_x, npc_pos_y = fairgraves_npc.grid_position.x, fairgraves_npc.grid_position.y
    poe_bot.mover.goToPoint(
      point=(npc_pos_x, npc_pos_y),
      release_mouse_on_end=False,
      custom_continue_function=poe_bot.combat_module.build.usualRoutine,
    )

    while True:
      fairgraves_npc = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/NPC/Act1/Fairgraves"), None)
      print(f"fairgraves_npc {fairgraves_npc.raw}")
      if fairgraves_npc is None or fairgraves_npc.is_targetable is False:
        break
      fairgraves_npc.click()
      poe_bot.refreshInstanceData()
      poe_bot.ui.closeAll()

    reversed_run = random.choice([True, False])
    while True:
      poe_bot.refreshInstanceData()
      poe_bot.combat_module.clearLocationAroundPoint({"X": npc_pos_x, "Y": npc_pos_y})
      fairgraves_skeleton = next(
        (e for e in poe_bot.game_data.entities.all_entities if "Metadata/Monsters/Skeletons/SkeletonBossFairgraves" in e.path), None
      )
      if fairgraves_skeleton:
        if fairgraves_skeleton.life.health.current == 0:
          break
        elif fairgraves_skeleton.is_attackable is True and fairgraves_skeleton.is_targetable is True:
          poe_bot.combat_module.killUsualEntity(fairgraves_skeleton)
      else:
        point = poe_bot.game_data.terrain.pointToRunAround(
          npc_pos_x, npc_pos_y, 15 + random.randint(-1, 1), check_if_passable=True, reversed=reversed_run
        )
        mover.move(grid_pos_x=point[0], grid_pos_y=point[1])
        poe_bot.combat_module.build.staticDefence()
    self.possible_to_enter_transitions.append("The Cavern of Wrath")

  def complete(self):
    explorer_settings = ExplorerRoutineSettings(
      {
        "force_kill_blue": False,
        "force_kill_rares": False,
      }
    )
    explorer_routine = ExplorerRoutine(explorer_settings)

    def exploreRoutine(*args):
      self.openWaypointIfPossible()
      self.enterTransitionIfPossible()
      if self.fairgraves_loc is None:
        fairgraves_npc = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/NPC/Act1/Fairgraves"), None)
        if fairgraves_npc is not None:
          self.fairgraves_loc = (fairgraves_npc.grid_position.x, fairgraves_npc.grid_position.y)
          if self.can_do_fairgraves_quest is True:
            self.doFairgravesQuest(fairgraves_npc.grid_position.x, fairgraves_npc.grid_position.y)
            return True
          else:
            self.fairgraves_loc = [fairgraves_npc.grid_position.x, fairgraves_npc.grid_position.y]

      er_res = explorer_routine.exploreRoutine()
      if er_res is not False:
        return er_res
      return False

    if self.fairgraves_loc is not None:
      self
    explorer_module = ExplorerModule(poe_bot=poe_bot)
    explorer_module.exploreTill(exploreRoutine)

  def __init__(self) -> None:
    # quest_states = poe_bot.backend.getQuestStates()
    # quest_state = next( (i for i in quest_states if i['id'] == "a1q6"), None)["state"]
    # if quest_state > 8:
    #   print(f'need to go to cave to pick lantern')
    #   self.can_do_fairgraves_quest = False
    #   self.possible_to_enter_transitions.append("The Ship Graveyard Cave")
    # poe_bot.ui.inventory.update()
    # self.can_do_fairgraves_quest = any(list(map(lambda item: "Art/2DItems/QuestItems/Lantern" in item.render_path, poe_bot.ui.inventory.items)))
    # print(f'can do fairgr quest {self.can_do_fairgraves_quest}')
    # if self.can_do_fairgraves_quest is False:
    #   quest_states = poe_bot.backend.getQuestStates()
    #   quest_state = next( (i for i in quest_states if i['id'] == "a1q6"), None)["state"]
    #   if quest_state > 3:
    #     self.possible_to_enter_transitions.append("The Ship Graveyard Cave")
    #   else:
    #     self.possible_to_enter_transitions.append("The Cavern of Wrath")

    poe_bot.ui.inventory.update()
    self.can_do_fairgraves_quest = any(list(map(lambda item: "Art/2DItems/QuestItems/Lantern" in item.render_path, poe_bot.ui.inventory.items)))
    if self.can_do_fairgraves_quest is False:
      print("dont have lantern in inventory")
      quest_states = poe_bot.backend.getQuestStates()
      quest_state = next((i for i in quest_states if i["id"] == "a1q6"), None)["state"]
      print(f"fairgr quest state {quest_state}")
      if quest_state > 8:
        print("need to go to cave to pick lantern")
        self.can_do_fairgraves_quest = False
        self.possible_to_enter_transitions.append("The Ship Graveyard Cave")
      else:
        print("dont have lantern, fairgr killed can go to next loc")
        self.possible_to_enter_transitions.append("The Cavern of Wrath")
    else:
      print("have lantern in inventory, gonna do quest")

    super().__init__()


class Loc1_1_9a(QuestArea):
  ready = True

  def ifHasLantern(self):
    poe_bot.ui.inventory.update()
    has_lantern = any(list(map(lambda item: "Art/2DItems/QuestItems/Lantern" in item.render_path, poe_bot.ui.inventory.items)))
    return has_lantern

  def getItemFromSlaveGirl(self):
    pass

  def complete(self):
    explorer_settings = ExplorerRoutineSettings(
      {
        "force_kill_blue": False,
        "force_kill_rares": False,
      }
    )
    explorer_routine = ExplorerRoutine(explorer_settings)

    def exploreRoutine(*args):
      slave_girl_containter = next(
        (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Chests/QuestChests/Fairgraves/AllFlameSlaveGirl"), None
      )
      if slave_girl_containter and slave_girl_containter.is_targetable is True:
        print("found slave girl container")
        print("going to slave girl container")
        poe_bot.mover.goToPoint(
          point=(slave_girl_containter.grid_position.x, slave_girl_containter.grid_position.y),
          release_mouse_on_end=False,
          custom_continue_function=poe_bot.combat_module.build.usualRoutine,
        )
        print("clearing around slave girl container")
        poe_bot.combat_module.clearLocationAroundPoint({"X": slave_girl_containter.grid_position.x, "Y": slave_girl_containter.grid_position.y})
        print("opening")
        slave_girl_containter.clickTillNotTargetable()
        print("clearing around slave girl container")
        poe_bot.combat_module.clearLocationAroundPoint({"X": slave_girl_containter.grid_position.x, "Y": slave_girl_containter.grid_position.y})
        has_lantern = False
        while has_lantern is False:
          poe_bot.refreshInstanceData()
          loot_picked = poe_bot.loot_picker.collectLoot()
          if loot_picked is False:
            poe_bot.combat_module.clearLocationAroundPoint({"X": slave_girl_containter.grid_position.x, "Y": slave_girl_containter.grid_position.y})
          has_lantern = self.ifHasLantern()

        cave_exit = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "The Ship Graveyard"), None)
        poe_bot.mover.goToEntitysPoint(cave_exit)
        poe_bot.mover.enterTransition(cave_exit, necropolis_ui=True, check_for_loading=True)

      transition = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "The Ship Graveyard Cave"), None)
      if transition:
        poe_bot.mover.goToEntity(transition)
        poe_bot.mover.enterTransition(transition, necropolis_ui=True)

      er_res = explorer_routine.exploreRoutine()
      if er_res is not False:
        return er_res
      return False

    explorer_module = ExplorerModule(poe_bot=poe_bot)
    explorer_module.exploreTill(exploreRoutine)
    return super().complete()

  def __init__(self) -> None:
    # TODO if quest is finished
    poe_bot.ui.inventory.update()
    has_lantern = any(list(map(lambda item: "Art/2DItems/QuestItems/Lantern" in item.render_path, poe_bot.ui.inventory.items)))
    if has_lantern is True:
      print("quest finished in this location, may go back")
      self.possible_to_enter_transitions.append("The Ship Graveyard")
      # poe_bot.helper_functions.relog()
    # if 1_1_9 waypoint is opened, relog, else, go back
    super().__init__()


class Loc1_1_11_1(QuestArea):
  ready = True
  waypoint_string = "1_1_11_1"
  relog_after_waypoint_opened = True

  def __init__(self) -> None:
    self.possible_to_enter_transitions.append("The Cavern of Anger")
    super().__init__()


class Loc1_1_11_2(QuestArea):  # mervil bossroom
  bossroom_transitions = ["Merveil's Lair"]
  bossroom_entities_render_names = ["Merveil, the Siren", "Merveil, the Twisted"]

  def clearBossroom(self, bossroom_encounter: Bossroom):
    def lookForWardensChambers(*args, **kwargs):
      chambers_transition = next((e for e in poe_bot.game_data.entities.area_transitions if e.render_name == "The Southern Forest"), None)
      if chambers_transition:
        poe_bot.mover.goToEntitysPoint(chambers_transition)
        poe_bot.mover.enterTransition(chambers_transition)
      return False

    bossroom_encounter.clear_room_custom_break_function = lookForWardensChambers
    bossroom_encounter.clearBossroom()
    inside_wardens_chambers = False
    while inside_wardens_chambers is False:
      inside_wardens_chambers = lookForWardensChambers()
      bossroom_encounter.clearBossroom()
    input("todo")
    # return super().clearBossroom(bossroom_entity)


# ACT 2
class A2QuestArea(QuestArea):
  # right side
  killed_beast = False
  bandit_killed_kraityn = False
  crypt_lab_finished = False
  need_to_get_golden_hand = False
  chamber_lab_finished = False

  # left side
  bandit_killed_alira = False
  weaver = False
  a1_passage_opened = False
  bandit_killed_oak = False
  opened_vaal_ruins_passage_with_spear = False

  def updateQuestStatus(self, force_update=False):
    super().updateQuestStatus(force_update=force_update)
    self.needToKillGreatWhiteBeast()
    self.needToVisitWeaver()
    self.updateGoldenHandStatus()
    self.updateBanditStatus()

  def needToKillGreatWhiteBeast(self, force_update=False):
    quest_flags = poe_bot.game_data.quest_states.get(force_update=force_update)
    self.killed_beast = quest_flags.get("A2Q10KilledBeast", False)
    return self.killed_beast

  def needToVisitWeaver(self):
    pass

  def updateBanditStatus(self):
    quest_flags = poe_bot.game_data.quest_states.get()
    delivered_amulets = quest_flags.get("A2BDeliveredAmulets", False)
    if delivered_amulets is True:
      self.bandit_killed_alira = True
      self.bandit_killed_oak = True
      self.bandit_killed_kraityn = True
      return
    # "A2BHaveIntAmulet": false, # alira
    # "A2BHaveStrAmulet": false, # oak
    # "A2BHaveDexAmulet": false, # kraityn
    # "A2BIntAlly": false,
    # "A2BDexAlly": false,
    # "A2BStrAlly": false,

  def updateGoldenHandStatus(self):
    quest_flags = poe_bot.game_data.quest_states.get()
    related_quest_flags = ["A2Q5HaveGoldenHand", "A2Q5DeliveredGoldenHand"]
    self.need_to_get_golden_hand = any(list(map(lambda f: quest_flags.get(f, False), related_quest_flags)))
    return self.need_to_get_golden_hand


class Loc1_2_town(A2QuestArea):
  def __init__(self) -> None:
    raise "get to portal, go to next area"


class Loc1_2_1(A2QuestArea):
  waypoint_string = None
  possible_to_enter_transitions = ["The Forest Encampment"]


class Loc1_2_2(A2QuestArea):
  def updateGoals(self, force_update=False):
    self.updateQuestStatus(force_update)
    if self.killed_beast is False:
      print("need to kill beast")
      self.possible_to_enter_transitions = ["The Den"]
    else:
      print("beast was killed")
      self.possible_to_enter_transitions = ["The Crossroads"]
    return super().updateGoals(force_update)


class Loc1_2_2a(A2QuestArea):
  def funcToCallAfterKillingUniqueEntity(self):
    self.updateGoals(force_update=True)
    return super().funcToCallAfterKillingUniqueEntity()

  def updateGoals(self, force_update=False):
    self.updateQuestStatus(force_update=force_update)
    if self.killed_beast is not True:
      print("need to kill beast")
      self.unique_entities_to_kill_render_names = ["The Great White Beast"]
    else:
      print("beast was killed")
      self.possible_to_enter_transitions = ["The Old Fields"]
    super().updateGoals(force_update)


class Loc1_2_3(QuestArea):  # crossroads
  waypoint_string = "1_2_3"
  need_to_kill_bandit = True
  need_to_do_crypt_lab = True
  need_to_do_chamber_lab = True
  need_to_move_towards_gem = True

  def getTransitions(self):
    quest_states = poe_bot.backend.getQuestStates()
    quest_state = next((i for i in quest_states if i["id"] == "a2q10"), None)["state"]
    self.need_to_move_towards_gem = quest_state > 2
    poe_bot.ui.inventory.update()
    self.need_kill_bandit = not any(list(map(lambda item: item.render_path == "Art/2DItems/QuestItems/TriangleKey2.dds", poe_bot.ui.inventory.items)))
    quest_flags = poe_bot.backend.getQuestFlags()
    if self.need_kill_bandit is True:
      self.possible_to_enter_transitions.append("The Broken Bridge")
    # if quest_flags["NormalLabyrinthCompletedCrypt"] is False:
    if quest_flags.get("NormalLabyrinthCompletedSins", False) is False:
      self.possible_to_enter_transitions.append("The Fellshrine Ruins")

    # if self.need_to_move_towards_gem or quest_flags["NormalLabyrinthCompletedSins"] is False:
    if self.need_to_move_towards_gem or quest_flags.get("NormalLabyrinthCompletedCrypt", False) is False:
      self.possible_to_enter_transitions.append("The Chamber of Sins Level 1")

  def onWaypointOpenedFunction(self):
    self.getTransitions()
    return super().onWaypointOpenedFunction()

  def __init__(self) -> None:
    super().__init__()
    if self.can_open_waypoint is False:
      print("no need to open waypoint")
      self.getTransitions()
      if not any([self.need_kill_bandit, self.need_to_do_chamber_lab, self.need_to_move_towards_gem, self.need_to_do_crypt_lab]):
        print("[quest] all goals in area 1_2_3 are completed, relog to get back to town")
        poe_bot.helper_functions.relog()
    else:
      print("need to open waypoint first")


class Loc1_2_4(QuestArea):
  waypoint_string = "1_2_4"

  def updateGoals(self, force_update=False):
    poe_bot.ui.inventory.update()
    self.need_kill_bandit = not any(list(map(lambda item: item.render_path == "Art/2DItems/QuestItems/TriangleKey2.dds", poe_bot.ui.inventory.items)))
    if self.need_kill_bandit is False:
      print("loc 124, but already have amulet")
      self.bandit_name = None
      self.possible_to_enter_transitions = ["The Crossroads"]
    else:
      print("didnt kill Kraityn")
      self.bandit_name = "Kraityn"
    return super().updateGoals(force_update)

  def afterBanditQuestFunction(self):
    poe_bot.loot_picker.collectLootWhilePresented()
    self.possible_to_enter_transitions = ["The Crossroads"]

  def __init__(self) -> None:
    super().__init__()


class Loc1_2_15(QuestArea):
  need_to_move_towards_lab = False
  lab_trial_flag = "NormalLabyrinthCompletedSins"

  def __init__(self) -> None:
    super().__init__()
    if self.need_to_do_lab_trial is True:
      print("need to visit lab in crypt")
      self.possible_to_enter_transitions.append("The Crypt Level 1")
    else:
      print("dont need to visit lab")
      self.possible_to_enter_transitions.append("The Crossroads")


class Loc1_2_5_1(QuestArea):
  waypoint_string = "1_2_5_1"
  lab_trial_flag = "NormalLabyrinthCompletedSins"
  need_to_get_hand = False

  def doLab(self, lab_enterance: Entity, lab_area):
    poe_bot.mover.goToEntitysPoint(lab_enterance)
    lab_enterance.clickTillNotTargetable()
    furthest_unvisited = poe_bot.pather.utils.getFurthestPoint(start=(lab_enterance.grid_position.x, lab_enterance.grid_position.y), area=lab_area)

    def lookForSwitch(*args, **kwargs):
      switch = next(
        (
          e
          for e in poe_bot.game_data.entities.all_entities
          if e.is_targetable is not False and e.path == "Metadata/Terrain/Labyrinth/Objects/Puzzle_Parts/Switch_Once"
        ),
        None,
      )
      if switch:

        def findSwitchWithLowerId(*args, **kwargs):
          another_switch = next(
            (
              e
              for e in poe_bot.game_data.entities.all_entities
              if e.is_targetable is not False and e.path == "Metadata/Terrain/Labyrinth/Objects/Puzzle_Parts/Switch_Once" and e.id < switch.id
            ),
            None,
          )
          if another_switch:
            poe_bot.mover.goToEntitysPoint(another_switch)
            poe_bot.refreshInstanceData()
            another_switch.clickTillNotTargetable()
          return False

        poe_bot.mover.goToEntitysPoint(switch, custom_break_function=findSwitchWithLowerId)
        poe_bot.refreshInstanceData()
        switch.clickTillNotTargetable()
      return False

    def lookForPlaque(*args, **kwargs):
      plaque = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/QuestObjects/Labyrinth/LabyrinthTrialPlaque"), None)
      if plaque:
        poe_bot.mover.goToEntitysPoint(plaque, custom_break_function=lookForSwitch)
        while True:
          poe_bot.refreshInstanceData()
          portal = next(
            (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Labyrinth/Objects/LabyrinthTrialReturnPortal"), None
          )
          if portal and portal.is_targetable:
            print("plaque activated")
            poe_bot.ui.closeAll()
            poe_bot.mover.goToEntitysPoint(portal)
            poe_bot.mover.enterTransition(portal, entered_distance_sign=50)
            break
          plaque.click(update_screen_pos=True)
        return True
      return False

    def labExploreFunc(*args, **kwargs):
      lookForSwitch()
      if lookForPlaque() is True:
        return True
      return False

    poe_bot.mover.goToPoint((furthest_unvisited), release_mouse_on_end=False, custom_break_function=labExploreFunc)
    print("lab finished")
    return True
    # "Metadata/Terrain/Labyrinth/Objects/Puzzle_Parts/Door_Closed" # if targetable, go to switch once
    # "Metadata/Terrain/Labyrinth/Objects/Puzzle_Parts/Switch_Once" # switch once
    # "Metadata/QuestObjects/Labyrinth/LabyrinthTrialPlaque"
    # "Metadata/Terrain/Labyrinth/Objects/LabyrinthTrialReturnPortal" - if not targetable, need to do more clicks to plate

  def __init__(self) -> None:
    super().__init__()
    quest_states = poe_bot.game_data.quest_states.getOrUpdate()
    if quest_states.get("A2Q5HaveGoldenHand", False) or quest_states.get("A2Q5DeliveredGoldenHand", False):
      pass
    else:
      print("need to get to crypt lvl 2 to get hand")
      self.need_to_get_hand = True
      self.possible_to_enter_transitions.append("The Crypt Level 2")
    if self.need_to_do_lab_trial is False and self.need_to_get_hand is not True:
      print("got hand and finished lab here, going back to fellshrine ruins")
      self.possible_to_enter_transitions.append("The Fellshrine Ruins")


class Loc1_2_5_2(QuestArea):
  need_to_get_hand = False

  def getQuestStatus(self):
    poe_bot.game_data.quest_states.update()
    quest_states = poe_bot.game_data.quest_states.quest_flags_raw
    if quest_states.get("A2Q5HaveGoldenHand", False) is True or quest_states.get("A2Q5DeliveredGoldenHand", False) is True:
      self.need_to_get_hand = False
      self.possible_to_enter_transitions = ["The Crypt Level 1"]
    else:
      self.need_to_get_hand = True

  def extraQuestInLoc(self):
    if self.need_to_get_hand is True:
      stash_entity = next(
        (e for e in poe_bot.game_data.entities.all_entities if e.is_targetable and "Metadata/Chests/QuestChests/ChurchAltar" in e.path), None
      )
      if stash_entity:
        print("going to stash with bust")
        poe_bot.mover.goToEntitysPoint(
          stash_entity,
        )
        print("clearing around stash")
        poe_bot.combat_module.clearLocationAroundPoint({"X": stash_entity.grid_position.x, "Y": stash_entity.grid_position.y})
        print("opening stash")
        stash_entity.clickTillNotTargetable()
        print("collecting loot")
        poe_bot.loot_picker.collectLootWhilePresented()
        print("updating quest status")
        self.getQuestStatus()
        self.possible_to_enter_transitions.append("The Crypt Level 1")
    return super().extraQuestInLoc()

  def __init__(self) -> None:
    super().__init__()
    self.getQuestStatus()
    if self.need_to_get_hand is True:
      print("didnt get hand yet, need to find it")
    else:
      print("got hand here, may go to town")


class Loc1_2_6_1(QuestArea):
  ready = True
  waypoint_string = "1_2_6_1"
  need_to_go_towards_gem = True
  lab_trial_flag = "NormalLabyrinthCompletedCrypt"  # dunno why its not "NormalLabyrinthCompletedSins"

  def onWaypointOpenedFunction(self):
    self.possible_to_enter_transitions = ["The Chamber of Sins Level 2"]
    return super().onWaypointOpenedFunction()

  def __init__(self) -> None:
    super().__init__()
    if self.need_to_do_lab_trial is True:
      print("can go further")
      if self.can_open_waypoint:
        print("open waypoint first")
      else:
        print("can go to lvl2")
        self.possible_to_enter_transitions = ["The Chamber of Sins Level 2"]
    else:
      print("no need to go to chamber of sins lvl2")
      self.possible_to_enter_transitions.append("The Crossroads")


class Loc1_2_6_2(QuestArea):
  can_collect_gem = False
  lab_trial_flag = "NormalLabyrinthCompletedCrypt"  # dunno why its not "NormalLabyrinthCompletedSins"
  unique_entities_to_kill_render_names = ["Fidelitas, the Mourning"]

  # Entity.render_name == "Strange Device" # Transition
  def doLab(self, lab_enterance: Entity, lab_area):
    poe_bot.mover.goToEntitysPoint(lab_enterance)
    lab_enterance.clickTillNotTargetable()
    furthest_unvisited = poe_bot.pather.utils.getFurthestPoint(start=(lab_enterance.grid_position.x, lab_enterance.grid_position.y), area=lab_area)

    def lookForPlaque(*args, **kwargs):
      plaque = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/QuestObjects/Labyrinth/LabyrinthTrialPlaque"), None)
      if plaque:
        poe_bot.mover.goToEntitysPoint(plaque)
        while True:
          poe_bot.refreshInstanceData()
          portal = next(
            (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Labyrinth/Objects/LabyrinthTrialReturnPortal"), None
          )
          if portal and portal.is_targetable:
            print("plaque activated")
            poe_bot.ui.closeAll()
            poe_bot.mover.goToEntitysPoint(portal)
            poe_bot.mover.enterTransition(portal)
            break
          plaque.click(update_screen_pos=True)
        return True
      return False

    poe_bot.mover.goToPoint((furthest_unvisited), release_mouse_on_end=False, custom_break_function=lookForPlaque)
    return True

  def funcToCallAfterKillingUniqueEntity(self):
    self.can_collect_gem = True
    return super().funcToCallAfterKillingUniqueEntity()

  def extraQuestInLoc(self):
    if self.can_collect_gem:
      strange_device = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Strange Device"), None)
      if strange_device:
        poe_bot.mover.goToEntitysPoint(strange_device)
        guardian = next(
          (e for e in poe_bot.game_data.entities.attackable_entities if e.render_name == self.unique_entities_to_kill_render_names[0]), None
        )
        if guardian:
          print("need to kill guardian first")
          poe_bot.combat_module.killTillCorpseOrDisappeared(guardian)
          return False
        strange_device.clickTillNotTargetable()
        poe_bot.loot_picker.collectLootWhilePresented()
        self.can_collect_gem = False
    return super().extraQuestInLoc()

  def __init__(self) -> None:
    super().__init__()
    if self.need_to_do_lab_trial is not True and False:
      self.possible_to_enter_transitions.append("The Crossroads")


class Loc1_2_7(QuestArea):
  ready = True
  waypoint_string = "1_2_7"
  possible_to_enter_transitions = []

  def __init__(self) -> None:
    poe_bot.ui.inventory.update()
    need_to_deal_with_bandit = not any(
      list(map(lambda item: item.render_path == "Art/2DItems/QuestItems/TriangleKey1.dds", poe_bot.ui.inventory.items))
    )
    quest_states = poe_bot.backend.getQuestStates()
    quest_state = next((i for i in quest_states if i["id"] == QUEST_KEYS["malagrios_spike"]), None)["state"]
    weaver_quest = quest_state > 5

    seal_quest = False
    quest_state = next((i for i in quest_states if i["id"] == "a2q11"), None)["state"]
    if quest_state > 0:
      quest_state = next((i for i in quest_states if i["id"] == "a1q9"), None)["state"]
      if quest_state > 3:
        print("need to finish seal quest")
        seal_quest = True
    # weaver quest
    # seal quest
    # alira bandit
    if need_to_deal_with_bandit and seal_quest and weaver_quest:
      self.possible_to_enter_transitions.append("The Western Forest")
    else:
      self.possible_to_enter_transitions.append("The Wetlands")
    super().__init__()


class Loc1_2_9(QuestArea):
  ready = True
  waypoint_string = "1_2_9"
  possible_to_enter_transitions = []
  bandit_name = "Alira"
  need_to_deal_with_bandit = False
  need_to_get_seal = False
  need_to_do_weaver_quest = False

  def complete(self):
    explorer_settings = ExplorerRoutineSettings(
      {
        "force_kill_blue": False,
        "force_kill_rares": False,
      }
    )
    explorer_routine = ExplorerRoutine(explorer_settings)

    def exploreRoutine(*args):
      self.enterTransitionIfPossible()
      self.openWaypointIfPossible()
      if self.bandit_name:
        bandit_npc = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == self.bandit_name), None)
        if bandit_npc and bandit_npc.life.health.current != 0:
          self.doBanditQuest()
          return True
      if self.need_to_get_seal is True:
        captain_npc = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Captain Arteri"), None)

        if captain_npc:
          captain_npc_pos_dict = {"X": captain_npc.grid_position.x, "Y": captain_npc.grid_position.y}
          poe_bot.mover.goToPoint(
            point=(captain_npc.grid_position.x, captain_npc.grid_position.y),
            min_distance=50,
            release_mouse_on_end=False,
            custom_continue_function=poe_bot.combat_module.build.usualRoutine,
          )
          while True:
            captain_npc = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Captain Arteri"), None)
            if captain_npc and captain_npc.life.health.current != 0:
              poe_bot.combat_module.killUsualEntity(captain_npc)
            else:
              break

          poe_bot.refreshInstanceData()
          poe_bot.combat_module.clearLocationAroundPoint(captain_npc_pos_dict)
          poe_bot.refreshInstanceData()
          while True:
            poe_bot.refreshInstanceData()
            if poe_bot.loot_picker.collectLoot() is False:
              break

          seal_object = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Thaumetic Seal"), None)
          if seal_object:
            poe_bot.mover.goToEntity(seal_object, custom_continue_function=poe_bot.combat_module.build.usualRoutine)
            seal_object.clickTillNotTargetable()
          self.need_to_get_seal = False

      er_res = explorer_routine.exploreRoutine()
      if er_res is not False:
        return er_res
      return False

    explorer_module = ExplorerModule(poe_bot=poe_bot)
    explorer_module.exploreTill(exploreRoutine)
    return super().complete()

  def __init__(self) -> None:
    poe_bot.ui.inventory.update()
    need_to_deal_with_bandit = not any(
      list(map(lambda item: item.render_path == "Art/2DItems/QuestItems/TriangleKey1.dds", poe_bot.ui.inventory.items))
    )
    if need_to_deal_with_bandit is False:
      print("doesnt need to deal with bandit")
      self.bandit_name = None
    quest_states = poe_bot.backend.getQuestStates()
    quest_state = next((i for i in quest_states if i["id"] == QUEST_KEYS["malagrios_spike"]), None)["state"]
    if quest_state > 5:
      print("need to do weaver quest")
      self.possible_to_enter_transitions.append("The Weaver's Chambers")
      self.need_to_do_weaver_quest = True
    else:
      print("doesnt need to do weaver quest")
    quest_state = next((i for i in quest_states if i["id"] == "a2q11"), None)["state"]
    if quest_state > 0:
      quest_state = next((i for i in quest_states if i["id"] == "a1q9"), None)["state"]
      if quest_state > 3:
        print("need to finish seal quest")
        self.need_to_get_seal = True

    if self.need_to_deal_with_bandit is False and self.need_to_do_weaver_quest is False and self.need_to_get_seal is False:
      print("going to riverways")
      self.possible_to_enter_transitions.append("The Riverways")
    super().__init__()


class Loc1_2_10(QuestArea):
  location_name = "The Weaver's Chambers"
  bossroom_entities_render_names = ["The Weaver"]

  def __init__(self) -> None:
    poe_bot.ui.inventory.update()
    self.need_to_kill_weaver = not any(
      list(map(lambda item: item.render_path == "Art/2DItems/QuestItems/PoisonSpear.dds", poe_bot.ui.inventory.items))
    )
    quest_states = poe_bot.backend.getQuestStates()
    quest_state = next((i for i in quest_states if i["id"] == QUEST_KEYS["malagrios_spike"]), None)["state"]
    self.need_to_kill_weaver = quest_state > 5
    if self.need_to_kill_weaver is False:
      print("doesnt need to pick malagrios spike, relog")
      self.possible_to_enter_transitions = ["The Western Forest"]
    else:
      self.bossroom_transitions = ["The Weaver's Nest"]
    super().__init__()

  def onBossroomCompleteFunction(self):
    self.possible_to_enter_transitions.append("The Western Forest")
    return super().onBossroomCompleteFunction()


class Loc1_2_12(QuestArea):
  waypoint_string = "1_2_12"
  possible_to_enter_transitions = []
  can_open_poison_roots = True
  bandit_name = "Oak"
  need_to_deal_with_bandit = False

  def complete(self):
    "Metadata/QuestObjects/Inca/PoisonTree"
    explorer_settings = ExplorerRoutineSettings(
      {
        "force_kill_blue": False,
        "force_kill_rares": False,
      }
    )
    explorer_routine = ExplorerRoutine(explorer_settings)

    def exploreRoutine(*args):
      self.openWaypointIfPossible()
      if self.need_to_deal_with_bandit is True:
        bandit_npc = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == self.bandit_name), None)
        if bandit_npc and bandit_npc.life.health.current != 0:
          self.doBanditQuest()
          return True

      if self.can_open_poison_roots:
        poison_roots = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Tree Roots" and e.is_targetable is True), None)
        if poison_roots:
          poe_bot.mover.goToEntity(poison_roots)
          poison_roots.clickTillNotTargetable()
          self.can_open_poison_roots = False

          vaal_ruins_transition = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "The Vaal Ruins"), None)
          if vaal_ruins_transition:
            poe_bot.mover.enterTransition(vaal_ruins_transition)

      er_res = explorer_routine.exploreRoutine()
      if er_res is not False:
        return er_res
      return False

    explorer_module = ExplorerModule(poe_bot=poe_bot)
    explorer_module.exploreTill(exploreRoutine)

  def __init__(self) -> None:
    poe_bot.ui.inventory.update()
    need_to_kill_weaver = any(list(map(lambda item: item.render_path == "Art/2DItems/QuestItems/PoisonSpear.dds", poe_bot.ui.inventory.items)))
    self.need_to_deal_with_bandit = not any(
      list(map(lambda item: item.render_path == "Art/2DItems/QuestItems/TriangleKey3.dds", poe_bot.ui.inventory.items))
    )

    quest_states = poe_bot.backend.getQuestStates()
    quest_state = next((i for i in quest_states if i["id"] == QUEST_KEYS["malagrios_spike"]), None)["state"]
    need_to_kill_weaver = quest_state > 5
    if need_to_kill_weaver is True:
      self.can_open_poison_roots = False
    super().__init__()


class Loc1_2_11(QuestArea):
  possible_to_enter_transitions = []

  def complete(self):
    explorer_module = ExplorerModule(poe_bot=poe_bot)
    discovery_points = explorer_module.generatePointsForDiscovery()
    explorer_settings = ExplorerRoutineSettings(
      {
        "force_kill_rares": False,
        "force_kill_blue": False,
      }
    )
    explorer_routine = ExplorerRoutine(explorer_settings)

    def exploreRoutine(*args):
      self.enterTransitionIfPossible()
      self.openWaypointIfPossible()

      lab_enterance = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Ancient Seal" and e.is_targetable is True), None)
      if lab_enterance:
        lab_enterance.clickTillNotTargetable()
        poe_bot.refreshInstanceData()
        return "ancient_seal_found"

      er_res = explorer_routine.exploreRoutine()
      if er_res is not False:
        return er_res
      return False

    while len(discovery_points) != 0:
      point_to_go = discovery_points.pop(0)
      print(f"point_to_go {point_to_go}")
      while 1:
        res = poe_bot.mover.goToPoint(
          point=point_to_go,
          min_distance=50,
          release_mouse_on_end=False,
          custom_break_function=exploreRoutine,
          custom_continue_function=build.usualRoutine,
          step_size=random.randint(30, 35),
        )
        print(f"res: {res}")
        if res is None:
          break
        elif res == "ancient_seal_f1ound":
          lab_enterance = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Ancient Seal"), None)
          if lab_enterance:
            # poe_bot.refreshAll(refresh_visited=False)
            self.lab_enterance_loc = (lab_enterance.grid_position.x, lab_enterance.grid_position.y)
            copy_of = poe_bot.game_data.terrain.passable.copy()
            # plt.imshow(copy_of);plt.show()
            copy_of_currently_passable_area = poe_bot.game_data.terrain.currently_passable_area.copy()
            area_ = 15
            copy_of[
              lab_enterance.grid_position.y - area_ : lab_enterance.grid_position.y + area_,
              lab_enterance.grid_position.x - area_ : lab_enterance.grid_position.x + area_,
            ] = 0
            poe_bot.game_data.terrain.passable = copy_of
            poe_bot.game_data.terrain.getCurrentlyPassableArea()
            copy_of_currently_passable_area - poe_bot.game_data.terrain.currently_passable_area
            discovery_points = list(filter(lambda point: poe_bot.game_data.terrain.checkIfPointPassable(point[0], point[1]), discovery_points))
            print(f"point to go {point_to_go} {discovery_points}")
            if not poe_bot.game_data.terrain.checkIfPointPassable(point_to_go[0], point_to_go[1]):
              print("poimt to go became unpassable")
              break
    raise "completed"

  def __init__(self) -> None:
    self.possible_to_enter_transitions.append("The Northern Forest")
    super().__init__()


class Loc1_2_8(QuestArea):
  waypoint_string = "1_2_8"
  possible_to_enter_transitions = []

  def __init__(self) -> None:
    self.possible_to_enter_transitions.append("The Caverns")
    super().__init__()


class Loc1_2_14_2(QuestArea):
  waypoint_string = "1_2_14_2"
  possible_to_enter_transitions = ["The Ancient Pyramid"]
  relog_after_waypoint_opened = True


class Loc1_2_14_3(QuestArea):
  multi_layerd_transitions_render_names = ["Stairs"]
  bossroom_transitions = ["Pyramid Apex"]
  bossroom_entities_render_names = ["Vaal Oversoul"]
  bossrom_activator = "Metadata/Monsters/IncaShadowBoss/IncaBossSpawner"

  def clearBossroom(self, bossroom_encounter: Bossroom):
    def lookForWardensChambers(*args, **kwargs):
      chambers_transition = next(
        (e for e in poe_bot.game_data.entities.area_transitions if e.path == "Metadata/QuestObjects/Inca/IncaPyramidTransition"), None
      )
      if chambers_transition:
        poe_bot.mover.goToEntitysPoint(chambers_transition)
        poe_bot.mover.enterTransition(chambers_transition)
      return False

    bossroom_encounter.clear_room_custom_break_function = lookForWardensChambers
    bossroom_encounter.clearBossroom()
    inside_wardens_chambers = False
    while inside_wardens_chambers is False:
      inside_wardens_chambers = lookForWardensChambers()
      bossroom_encounter.clearBossroom()
    input("todo")

  # boss render name = "Vaal Oversoul"
  # leave transition through nearby = "Metadata/QuestObjects/Inca/IncaPyramidDoor"
  #  leave using "Metadata/QuestObjects/Inca/IncaPyramidTransition"


# ACT3
class A3QuestArea(QuestArea):
  have_sewer_key = False
  used_sewer_key = False
  have_or_used_sewer_key = False

  collected_busts = False
  bust_quest_finished = False

  have_talc = False
  used_talc = False

  has_or_used_tower_key = False

  def updateQuestStatus(self, force_update=False):
    super().updateQuestStatus(force_update=force_update)
    self.updateSewerKeyStatus()
    self.updateBustQuestStatus()
    self.updateTalcStatus()
    self.hasOrUsedTowerKey()

  def updateTalcStatus(self):
    quest_flags = poe_bot.game_data.quest_states.get()
    self.have_talc = quest_flags.get("A3Q5HaveTalc", False)
    self.used_talc = quest_flags.get("A3Q5UsedTalc", False)

  def updateBustQuestStatus(self, force_update=False):
    quest_flags = poe_bot.game_data.quest_states.get(force_update=force_update)
    self.bust_quest_finished = quest_flags.get("A3Q11Congratulated", False)
    if self.bust_quest_finished is True:
      self.collected_busts = True
    else:
      bust_keys = [
        "A3Q11HaveBust1",
        "A3Q11HaveBust2",
        "A3Q11HaveBust3",
      ]
      bust_keys_statuses = list(map(lambda key: quest_flags.get(key, False), bust_keys))
      if False in bust_keys_statuses:
        self.collected_busts = False
      else:
        self.collected_busts = True

  def updateSewerKeyStatus(self):
    quest_flags = poe_bot.game_data.quest_states.get()
    self.have_sewer_key = quest_flags.get("A3Q11HaveSewerKeys", False)
    self.used_sewer_key = quest_flags.get("A3Q11UsedSewerKeys", False)
    self.have_or_used_sewer_key = any([self.have_sewer_key, self.used_sewer_key])
    return self.have_or_used_sewer_key

  def hasOrUsedTowerKey(self):
    quest_flags = poe_bot.game_data.quest_states.get()
    self.has_or_used_tower_key = any(list(map(lambda flag: quest_flags.get(flag, False), ["A3Q9HaveTowerKey", "A3Q9UsedTowerKey"])))
    return self.has_or_used_tower_key


class Loc1_3_1(QuestArea):
  waypoint_string = None

  def isGirlSaved(self):
    quest_flags = poe_bot.backend.getQuestFlags()
    self.girl_rescued = quest_flags.get("A3Q1RescuedGirl", False)
    if self.girl_rescued:
      self.possible_to_enter_transitions = ["The Sarn Encampment"]
    else:
      self.unique_entities_to_kill_render_names = ["Guard Captain"]

  def extraQuestInLoc(self):
    if self.girl_rescued is False:
      girl_entity = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Clarissa"), None)
      if girl_entity:
        poe_bot.mover.goToEntitysPoint(girl_entity)
        poe_bot.combat_module.clearAreaAroundPoint(girl_entity.grid_position.toList(), till_no_enemies_around=True, detection_radius=40)
        poe_bot.mover.goToEntitysPoint(girl_entity)
        while True:
          targetable_girl_entity = next((e for e in poe_bot.game_data.entities.npcs if e.render_name == "Clarissa"), None)
          if targetable_girl_entity:
            for i in range(random.randint(2, 4)):
              targetable_girl_entity.click(update_screen_pos=True)
              poe_bot.refreshInstanceData()
              poe_bot.ui.closeAll()
              self.isGirlSaved()
              if self.girl_rescued:
                break
            if self.girl_rescued:
              break
          killed_someone = poe_bot.combat_module.clearLocationAroundPoint(
            {"X": girl_entity.grid_position.x, "Y": girl_entity.grid_position.y}, detection_radius=45
          )
          if killed_someone is False:
            point = poe_bot.game_data.terrain.pointToRunAround(
              point_to_run_around_x=girl_entity.grid_position.x,
              point_to_run_around_y=girl_entity.grid_position.y,
              distance_to_point=30,
            )
            poe_bot.mover.move(grid_pos_x=point[0], grid_pos_y=point[1])
            poe_bot.refreshInstanceData()
    return super().extraQuestInLoc()

  def funcToCallAfterKillingUniqueEntity(self):
    self.extraQuestInLoc()
    return super().funcToCallAfterKillingUniqueEntity()

  def __init__(self) -> None:
    self.isGirlSaved()
    super().__init__()


class Loc1_3_2(A3QuestArea):
  # todo quest state
  def updateGoals(self, force_update=False):
    if self.have_or_used_sewer_key:
      print("[quest 1_3_2] can go to sewers")
      self.possible_to_enter_transitions = ["The Sewers"]
    else:
      print("[quest 1_3_2] need to go to crematorium")
      self.possible_to_enter_transitions = ["The Crematorium"]

  def extraQuestInLoc(self):
    if self.have_sewer_key:
      sewer_gate = next((e for e in poe_bot.game_data.entities.all_entities if e.is_targetable and e.render_name == "Sewer Grating"), None)
      if sewer_gate:
        print("have keys and found sewer gate")
        poe_bot.mover.goToEntitysPoint(sewer_gate, custom_continue_function=poe_bot.combat_module.build.usualRoutine, min_distance=30)
        print("clearing around the sewer gate")
        poe_bot.combat_module.clearLocationAroundPoint({"X": sewer_gate.grid_position.x, "Y": sewer_gate.grid_position.y})
        print("clicking the gate till its not targetable")
        sewer_gate.clickTillNotTargetable()
    return super().extraQuestInLoc()


class Loc1_3_3_1(A3QuestArea):  # TODO quest
  lab_trial_flag = "NormalLabyrinthCompletedCrematorium"
  waypoint_string = "1_3_3_1"
  unique_entities_to_kill_render_names = ["Piety"]
  can_collect_gem = True

  def updateGoals(self, force_update=False):
    super().updateGoals()
    if self.have_or_used_sewer_key:
      print("[quest 1_3_2] can go to sewers")
      self.possible_to_enter_transitions = ["The Sewers"]
    else:
      print("[quest 1_3_2] need to go to crematorium")
      self.possible_to_enter_transitions = ["The Crematorium"]

  def extraQuestInLoc(self):
    if self.can_collect_gem:
      strange_device = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Chests/QuestChests/Tolman/TolmanChair"), None)
      if strange_device:
        poe_bot.mover.goToEntitysPoint(strange_device)
        guardian = next(
          (e for e in poe_bot.game_data.entities.attackable_entities if e.render_name == self.unique_entities_to_kill_render_names[0]), None
        )
        if guardian:
          print("need to kill guardian first")
          poe_bot.combat_module.killTillCorpseOrDisappeared(guardian)
          return False
        strange_device.clickTillNotTargetable()
        poe_bot.loot_picker.collectLootWhilePresented()
        self.can_collect_gem = False
    return super().extraQuestInLoc()

  def doLab(self, lab_enterance: Entity, lab_area):
    poe_bot.mover.goToEntitysPoint(lab_enterance)
    lab_enterance.clickTillNotTargetable()
    furthest_unvisited = poe_bot.pather.utils.getFurthestPoint(start=(lab_enterance.grid_position.x, lab_enterance.grid_position.y), area=lab_area)

    def lookForSwitch(*args, **kwargs):
      switch = next(
        (
          e
          for e in poe_bot.game_data.entities.all_entities
          if e.is_targetable is not False and e.path == "Metadata/Terrain/Labyrinth/Objects/Puzzle_Parts/Switch_Once"
        ),
        None,
      )
      if switch:

        def findSwitchWithHigherId(*args, **kwargs):
          another_switch = next(
            (
              e
              for e in poe_bot.game_data.entities.all_entities
              if e.is_targetable is not False and e.path == "Metadata/Terrain/Labyrinth/Objects/Puzzle_Parts/Switch_Once" and e.id > switch.id
            ),
            None,
          )
          if another_switch:
            poe_bot.mover.goToEntitysPoint(another_switch)
            poe_bot.refreshInstanceData()
            another_switch.clickTillNotTargetable()
          return False

        poe_bot.mover.goToEntitysPoint(switch, custom_break_function=findSwitchWithHigherId)
        poe_bot.refreshInstanceData()
        switch.clickTillNotTargetable()
      return False

    def lookForPlaque(*args, **kwargs):
      plaque = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/QuestObjects/Labyrinth/LabyrinthTrialPlaque"), None)
      if plaque:
        poe_bot.mover.goToEntitysPoint(plaque, custom_break_function=lookForSwitch)
        while True:
          poe_bot.refreshInstanceData()
          portal = next(
            (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Labyrinth/Objects/LabyrinthTrialReturnPortal"), None
          )
          if portal and portal.is_targetable:
            print("plaque activated")
            poe_bot.ui.closeAll()
            poe_bot.mover.goToEntitysPoint(portal)
            poe_bot.mover.enterTransition(portal, entered_distance_sign=50)
            break
          plaque.click(update_screen_pos=True)
        return True
      return False

    def labExploreFunc(*args, **kwargs):
      lookForSwitch()
      if lookForPlaque() is True:
        return True
      return False

    poe_bot.mover.goToPoint((furthest_unvisited), release_mouse_on_end=False, custom_break_function=labExploreFunc)
    print("lab finished")
    return True


class Loc1_3_10_1(A3QuestArea):
  waypoint_string = "1_3_10_1"
  possible_to_enter_transitions = []

  def updateGoals(self, force_update=False):
    if force_update:
      self.updateQuestStatus(force_update=force_update)
    if self.have_talc or self.used_talc:
      self.possible_to_enter_transitions.append("The Ebony Barracks")
    else:
      self.blockades_paths = ["Metadata/QuestObjects/Sewers/BioWall"]
      if self.bust_quest_finished:
        self.possible_to_enter_transitions.append("The Marketplace")

  def extraQuestInLoc(self):
    if self.collected_busts is not True:
      stash_entity = next(
        (e for e in poe_bot.game_data.entities.all_entities if e.is_targetable and "Metadata/Chests/QuestChests/Victario/Stash" in e.path), None
      )
      if stash_entity:
        print("going to stash with bust")
        poe_bot.mover.goToEntitysPoint(
          stash_entity,
        )
        print("clearing around stash")
        poe_bot.combat_module.clearLocationAroundPoint({"X": stash_entity.grid_position.x, "Y": stash_entity.grid_position.y})
        print("opening stash")
        stash_entity.clickTillNotTargetable()
        print("collecting loot")
        poe_bot.loot_picker.collectLootWhilePresented()
        print("updating quest status")
        self.updateGoals(force_update=True)
    if self.have_talc:
      activator = next(
        (e for e in poe_bot.game_data.entities.all_entities if e.is_targetable and "Metadata/QuestObjects/Sewers/BioWall" in e.path), None
      )
      if activator:
        print("going to activator")
        poe_bot.mover.goToEntitysPoint(
          activator,
        )
        print("clearing around activator")
        poe_bot.combat_module.clearLocationAroundPoint({"X": activator.grid_position.x, "Y": activator.grid_position.y})
        print("opening activator")
        activator.clickTillNotTargetable()
    return super().extraQuestInLoc()


class Loc1_3_5(A3QuestArea):
  waypoint_string = "1_3_5"

  def updateGoals(self, force_update=False):
    if force_update:
      poe_bot.game_data.quest_states.update()
    quest_flags = poe_bot.game_data.quest_states.get()
    if quest_flags.get("NormalLabyrinthCompletedHedgeMaze", False) is not False:
      print("lab in NormalLabyrinthCompletedHedgeMaze finished")
      self.possible_to_enter_transitions.append("The Battlefront")
    else:
      print("lab in NormalLabyrinthCompletedHedgeMaze not finished")
      self.possible_to_enter_transitions.append("The Catacombs")


class Loc1_3_6(A3QuestArea):
  lab_trial_flag = "NormalLabyrinthCompletedHedgeMaze"
  possible_to_enter_transitions = []

  def updateGoals(self, force_update=False):
    if self.need_to_do_lab_trial is True:
      print("[quest] need to complete NormalLabyrinthCompletedHedgeMaze")
    else:
      print("[quest] doesnt need to complete NormalLabyrinthCompletedHedgeMaze")
      self.possible_to_enter_transitions.append("The Marketplace")

  def doLab(self, lab_enterance: Entity, lab_area):
    poe_bot.mover.goToEntitysPoint(lab_enterance)
    lab_enterance.clickTillNotTargetable()
    furthest_unvisited = poe_bot.pather.utils.getFurthestPoint(start=(lab_enterance.grid_position.x, lab_enterance.grid_position.y), area=lab_area)

    def lookForSwitch(*args, **kwargs):
      switch = next(
        (
          e
          for e in poe_bot.game_data.entities.all_entities
          if e.is_targetable is not False and e.path == "Metadata/Terrain/Labyrinth/Objects/Puzzle_Parts/Switch_Once"
        ),
        None,
      )
      if switch:
        poe_bot.mover.goToEntitysPoint(switch)
        poe_bot.refreshInstanceData()
        switch.clickTillNotTargetable()
      return False

    def lookForPlaque(*args, **kwargs):
      plaque = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/QuestObjects/Labyrinth/LabyrinthTrialPlaque"), None)
      if plaque:
        poe_bot.mover.goToEntitysPoint(plaque, custom_break_function=lookForSwitch)
        while True:
          poe_bot.refreshInstanceData()
          portal = next(
            (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Labyrinth/Objects/LabyrinthTrialReturnPortal"), None
          )
          if portal and portal.is_targetable:
            print("plaque activated")
            poe_bot.ui.closeAll()
            poe_bot.mover.goToEntitysPoint(portal)
            poe_bot.mover.enterTransition(portal)
            break
          plaque.click(update_screen_pos=True)
        return True
      return False

    def labExploreFunc(*args, **kwargs):
      lookForSwitch()
      if lookForPlaque() is True:
        return True
      return False

    poe_bot.mover.goToPoint((furthest_unvisited), release_mouse_on_end=False, custom_break_function=labExploreFunc)
    print("lab finished")
    return True

  def onLabTrialCompleteFunction(self):
    self.possible_to_enter_transitions.append("The Marketplace")
    return super().onLabTrialCompleteFunction()


class Loc1_3_7(QuestArea):
  waypoint_string = "1_3_7"
  possible_to_enter_transitions = []

  def ifOpenedContainer(self):
    quest_flags = poe_bot.backend.getQuestFlags()
    self.have_ribon_spool = quest_flags.get("A3Q4HaveRibbonSpool", False)
    self.have_sulphite = quest_flags.get("A3Q5HaveSulphite", False)

  def extraQuestInLoc(self):
    slave_girl_containter = next(
      (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Chests/QuestChests/Dialla/RibbonSpoolChest"), None
    )
    if slave_girl_containter and slave_girl_containter.is_targetable is True:
      print("found container")
      print("going container")
      poe_bot.mover.goToPoint(
        point=(slave_girl_containter.grid_position.x, slave_girl_containter.grid_position.y),
        release_mouse_on_end=False,
        custom_continue_function=poe_bot.combat_module.build.usualRoutine,
      )
      print("clearing around  container")
      poe_bot.combat_module.clearLocationAroundPoint({"X": slave_girl_containter.grid_position.x, "Y": slave_girl_containter.grid_position.y})
      print("opening")
      slave_girl_containter.clickTillNotTargetable()
      print("clearing container")
      poe_bot.combat_module.clearLocationAroundPoint({"X": slave_girl_containter.grid_position.x, "Y": slave_girl_containter.grid_position.y})
      poe_bot.loot_picker.collectLootWhilePresented()
      self.have_ribon_spool = True
      self.possible_to_enter_transitions = ["The Docks"]

    return super().extraQuestInLoc()

  def __init__(self) -> None:
    super().__init__()
    self.ifOpenedContainer()
    if self.can_open_waypoint is True:
      print("looking for a waypoint")
    else:
      if self.have_ribon_spool:
        print("dont need to get the spool")
        if self.have_sulphite:
          print("have sulhite and spool, goto solaris")
          self.possible_to_enter_transitions = ["The Solaris Temple Level 1"]
        else:
          print("need to pick sulphite")
          self.possible_to_enter_transitions = ["The Docks"]


class Loc1_3_9(QuestArea):
  waypoint_string = "1_3_9"
  possible_to_enter_transitions = []

  def ifOpenedContainer(self):
    quest_flags = poe_bot.backend.getQuestFlags()
    self.have_ribon_spool = quest_flags.get("A3Q4HaveRibbonSpool", False)
    self.have_sulphite = quest_flags.get("A3Q5HaveSulphite", False)

  def extraQuestInLoc(self):
    slave_girl_containter = next(
      (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Chests/QuestChests/Dialla/SulphiteChest"), None
    )
    if slave_girl_containter and slave_girl_containter.is_targetable is True:
      print("found container")
      print("going container")
      poe_bot.mover.goToPoint(
        point=(slave_girl_containter.grid_position.x, slave_girl_containter.grid_position.y),
        release_mouse_on_end=False,
        custom_continue_function=poe_bot.combat_module.build.usualRoutine,
      )
      print("clearing around  container")
      poe_bot.combat_module.clearLocationAroundPoint({"X": slave_girl_containter.grid_position.x, "Y": slave_girl_containter.grid_position.y})
      print("opening")
      slave_girl_containter.clickTillNotTargetable()
      print("clearing container")
      poe_bot.combat_module.clearLocationAroundPoint({"X": slave_girl_containter.grid_position.x, "Y": slave_girl_containter.grid_position.y})
      poe_bot.loot_picker.collectLootWhilePresented()
      print("have sulphite, can go back to battlefront")
      self.possible_to_enter_transitions = ["The Battlefront"]
      return True
    return False

  def __init__(self) -> None:
    super().__init__()
    self.ifOpenedContainer()
    if self.have_sulphite:
      print("have sulphite, can go back to battlefront")
      self.possible_to_enter_transitions = ["The Battlefront"]


class Loc1_3_8_1(QuestArea):
  waypoint_string = "1_3_8_1"
  possible_to_enter_transitions = []

  def __init__(self) -> None:
    self.possible_to_enter_transitions.append("The Solaris Temple Level 2")
    super().__init__()


class Loc1_3_8_2(QuestArea):  # Solaris lvl1 #TODO talk to dialla, take quest item
  waypoint_string = "1_3_8_2"
  possible_to_enter_transitions = []

  def extraQuestInLoc(self):
    dialla_entity = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Lady Dialla"), None)
    if dialla_entity:
      poe_bot.mover.goToEntitysPoint(dialla_entity)

      poe_bot.raiseLongSleepException("talk to dialla, goto other loc")
    return super().extraQuestInLoc()


class Loc1_3_13(A3QuestArea):
  ready = True
  waypoint_string = "1_3_13"
  possible_to_enter_transitions = []

  def __init__(self) -> None:
    self.updateQuestStatus()
    super().__init__()
    if self.can_open_waypoint is True:
      print("looking for a waypoint")
    else:
      if self.has_or_used_tower_key:
        print("got tower key")
        self.possible_to_enter_transitions.append("The Imperial Gardens")
      else:
        print("dont have tower key")
        self.possible_to_enter_transitions.append("The Lunaris Temple Level 1")

  def onWaypointOpenedFunction(self):
    self.possible_to_enter_transitions.append("The Lunaris Temple Level 1")
    return super().onWaypointOpenedFunction()


class Loc1_3_14_1(QuestArea):
  waypoint_string = "1_3_14_1"
  explore_furthest = True

  def onWaypointOpenedFunction(self):
    self.possible_to_enter_transitions.append("The Lunaris Temple Level 2")
    return super().onWaypointOpenedFunction()

  def __init__(self) -> None:
    super().__init__()
    if self.can_open_waypoint is False:
      self.possible_to_enter_transitions.append("The Lunaris Temple Level 2")


class Loc1_3_14_2(A3QuestArea):
  bossroom_transitions = ["Portal"]
  bossroom_entities_render_names = ["Piety"]
  explore_furthest = True

  def clearBossroom(self, bossroom_encounter: Bossroom):
    while True:
      bossroom_encounter.clearBossroom()
      self.updateQuestStatus(force_update=True)
      if self.has_or_used_tower_key is True:
        break
    self.onBossroomCompleteFunction()
    self.bossroom_transitions.remove(bossroom_encounter.transition_entity.render_name)

  def updateTransitions(self):
    if self.has_or_used_tower_key:
      print("got tower key")
      self.possible_to_enter_transitions.append("The Lunaris Temple Level 1")
    else:
      print("dont have tower key")
      self.bossroom_transitions = ["Portal"]

  def __init__(self) -> None:
    self.updateQuestStatus()
    self.updateTransitions()
    super().__init__()


class Loc1_3_15(QuestArea):
  waypoint_string = "1_3_15"
  lab_trial_flag = "NormalLabyrinthCompletedCatacombs"
  used_keys = False

  def doLab(self, lab_enterance: Entity, lab_area):
    poe_bot.mover.goToEntitysPoint(lab_enterance)
    lab_enterance.clickTillNotTargetable()
    furthest_unvisited = poe_bot.pather.utils.getFurthestPoint(start=(lab_enterance.grid_position.x, lab_enterance.grid_position.y), area=lab_area)

    def lookForPlaque(*args, **kwargs):
      plaque = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/QuestObjects/Labyrinth/LabyrinthTrialPlaque"), None)
      if plaque:
        poe_bot.mover.goToEntitysPoint(plaque)
        while True:
          poe_bot.refreshInstanceData()
          portal = next(
            (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Labyrinth/Objects/LabyrinthTrialReturnPortal"), None
          )
          if portal and portal.is_targetable:
            print("plaque activated")
            poe_bot.ui.closeAll()
            poe_bot.mover.goToEntitysPoint(portal)
            poe_bot.mover.enterTransition(portal)
            break
          plaque.click(update_screen_pos=True)
        return True
      return False

    poe_bot.mover.goToPoint((furthest_unvisited), release_mouse_on_end=False, custom_break_function=lookForPlaque)
    print("lab finished")
    return True

  def onLabTrialCompleteFunction(self):
    return super().onLabTrialCompleteFunction()

  def extraQuestInLoc(self):
    if self.need_to_do_lab_trial is False and self.used_keys is False:
      locked_door = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Locked Door"), False)
      if locked_door:
        poe_bot.mover.goToEntitysPoint(locked_door)
        locked_door.clickTillNotTargetable()
        poe_bot.refreshInstanceData()
        self.used_keys = True
        self.possible_to_enter_transitions.append("The Sceptre of God")
        return True
    return super().extraQuestInLoc()

  def __init__(self) -> None:
    super().__init__()
    if self.need_to_do_lab_trial is False:
      self.possible_to_enter_transitions.append("The Sceptre of God")


class Loc1_3_18_1(QuestArea):
  multi_layerd_transitions_render_names = ["Stairs"]  # , "Stairs"
  waypoint_string = "1_3_18_1"
  possible_to_enter_transitions = ["The Upper Sceptre of God"]


class Loc1_3_18_2(QuestArea):  # TODO scion quest #TODO bossroom entities names
  multi_layerd_transitions_render_names = ["Stairs"]  # , "Stairs"
  bossroom_transitions = ["Tower Rooftop"]
  bossroom_entities_render_names = [
    "Compulsor Octavia Sparkfist",
    "Imperator Stantinus Bitterblade",
    "Draconarius Wilhelm Flamebrand",
    "Orcus the Reaver",
    "Alal the Terrifying",
    "Kali the Crazed",
    "Dominus, High Templar",
    "Dominus, Ascendant",
  ]
  scion_freed = False

  def clearBossroom(self, bossroom_encounter: Bossroom):
    def lookForWardensChambers(*args, **kwargs):
      chambers_transition = next(
        (e for e in poe_bot.game_data.entities.area_transitions if e.path == "Metadata/MiscellaneousObjects/AreaTransitionMapMarker"), None
      )
      if chambers_transition:
        poe_bot.mover.goToEntitysPoint(chambers_transition)
        poe_bot.mover.enterTransition(chambers_transition)
      return False

    bossroom_encounter.clear_room_custom_break_function = lookForWardensChambers
    bossroom_encounter.clearBossroom()
    inside_wardens_chambers = False
    while inside_wardens_chambers is False:
      inside_wardens_chambers = lookForWardensChambers()
      bossroom_encounter.clearBossroom()
    input("todo")

  def updateQuestStatus(self, force_update=True):
    super().updateQuestStatus(force_update=force_update)
    self.scion_freed = poe_bot.game_data.quest_states.quest_flags_raw.get("ScionUnlocked", False)

  def extraQuestInLoc(self):
    if self.scion_freed is not True:
      steel_cage = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/NPC/Act3/ScionCage"), None)
      if steel_cage:
        poe_bot.mover.goToEntitysPoint(steel_cage)
        poe_bot.combat_module.clearAreaAroundPoint((steel_cage.grid_position.x, steel_cage.grid_position.y))
        steel_cage.clickTillNotTargetable()
        while self.scion_freed is not True:
          poe_bot.refreshInstanceData()
          scion = next(
            (e for e in poe_bot.game_data.entities.all_entities if e.is_targetable is not False and e.path == "Metadata/NPC/Act3/Scion"), None
          )
          if scion:
            scion.click()
            poe_bot.ui.closeAll()
          else:
            poe_bot.combat_module.clearAreaAroundPoint((steel_cage.grid_position.x, steel_cage.grid_position.y))
          self.updateQuestStatus()
    return super().extraQuestInLoc()

  def __init__(self) -> None:
    # check if need to do scion quest
    self.updateQuestStatus()
    super().__init__()


# act 4
class A4QuestArea(QuestArea):
  have_banner = False
  used_banner = False
  have_or_used_banner = False

  need_to_free_dashret = False

  have_daresso_gem = False
  used_daresso_gem = False
  have_or_used_daresso_gem = False

  have_kaom_gem = False
  used_kaom_gem = False
  have_or_used_kaom_gem = False

  # 'A4Q5HaveOrgan1' # lungs doedre
  have_doedre_item = False
  used_doedre_item = False
  have_or_used_doedre_item = False
  # 'A4Q5HaveOrgan2' # heart maligaro
  have_maligaro_item = False
  used_maligaro_item = False
  have_or_used_maligaro_item = False
  # 'A4Q5HaveOrgan3' # entrails shavronne
  have_shavronne_item = False
  used_shavronne_item = False
  have_or_used_shavronne_item = False

  def updateQuestStatus(self, force_update=False):
    super().updateQuestStatus(force_update)
    self.updateBannerStatus()
    self.updateDeshretStatus()
    self.updateDaressoStatus()
    self.updateKaomStatus()
    self.updateHarvestQuestStatus()

  def updateBannerStatus(self):
    quest_flags = poe_bot.game_data.quest_states.get()
    self.have_banner = quest_flags.get("A4Q2HaveBanner", False)
    self.used_banner = quest_flags.get("A4Q2UsedBanner", False)
    self.have_or_used_banner = any([self.have_banner, self.used_banner])
    return self.have_or_used_banner

  def updateDeshretStatus(self):
    quest_flags = poe_bot.game_data.quest_states.get()
    deshret_keys = ["A4Q6DeshretFreed", "A4Q6UsedRewardBook", "A4Q6QuestRewardSeen"]
    deshret_keys_statuses = list(map(lambda key: quest_flags.get(key, False), deshret_keys))
    self.need_to_free_dashret = True not in deshret_keys_statuses

  def updateKaomStatus(self):
    quest_flags = poe_bot.game_data.quest_states.getOrUpdate()
    self.have_kaom_gem = quest_flags.get("A4Q3HaveGem", False)
    self.used_kaom_gem = quest_flags.get("A4Q3DeliveredGem", False)
    self.have_or_used_kaom_gem = any([self.have_kaom_gem, self.used_kaom_gem])
    return self.have_or_used_kaom_gem

  def updateDaressoStatus(self):
    quest_flags = poe_bot.game_data.quest_states.getOrUpdate()
    self.have_daresso_gem = quest_flags.get("A4Q4HaveGem", False)
    self.used_daresso_gem = quest_flags.get("A4Q4DeliveredGem", False)
    self.have_or_used_daresso_gem = any([self.have_daresso_gem, self.used_daresso_gem])
    return self.have_or_used_daresso_gem

  def updateHarvestQuestStatus(self):
    quest_flags = poe_bot.game_data.quest_states.getOrUpdate()
    self.harvest_quest_completed = quest_flags.get("A4Q5QuestComplete", False)
    if self.harvest_quest_completed is True:
      self.have_or_used_doedre_item, self.have_or_used_maligaro_item, self.have_or_used_shavronne_item = True
      return True
    # 'A4Q5HaveOrgan1' # lungs doedre
    self.have_doedre_item = quest_flags.get("A4Q5HaveOrgan1", False)
    self.used_doedre_item = quest_flags.get("A4Q5DeliveredOrgan1", False)
    self.have_or_used_doedre_item = any([self.have_doedre_item, self.used_doedre_item])
    # 'A4Q5HaveOrgan2' # heart maligaro
    self.have_maligaro_item = quest_flags.get("A4Q5HaveOrgan2", False)
    self.used_maligaro_item = quest_flags.get("A4Q5DeliveredOrgan2", False)
    self.have_or_used_maligaro_item = any([self.have_maligaro_item, self.used_maligaro_item])
    # 'A4Q5HaveOrgan3' # entrails shavronne
    self.have_shavronne_item = quest_flags.get("A4Q5HaveOrgan3", False)
    self.used_shavronne_item = quest_flags.get("A4Q5DeliveredOrgan3", False)
    self.have_or_used_shavronne_item = any([self.have_shavronne_item, self.used_shavronne_item])


class Loc1_4_1(QuestArea):
  ready = True
  possible_to_enter_transitions = []
  waypoint_string = None
  explore_furthest = True

  def __init__(self) -> None:
    self.possible_to_enter_transitions.append("Highgate")
    super().__init__()


class Loc1_4_town(QuestArea):
  def __init__(self) -> None:
    super().__init__()


class Loc1_4_2(A4QuestArea):
  unique_entities_to_kill_render_names = ["Voll, Emperor of Purity"]

  def funcToCallAfterKillingUniqueEntity(self):
    poe_bot.loot_picker.collectLootWhilePresented()
    self.updateQuestStatus(force_update=True)
    self.updateGoals()
    return super().funcToCallAfterKillingUniqueEntity()

  def updateGoals(self, force_update=False):
    if self.have_or_used_banner is True:
      self.possible_to_enter_transitions = ["Highgate"]
    return super().updateGoals(force_update)


class Loc1_4_3_1(QuestArea):
  possible_to_enter_transitions = ["The Mines Level 2"]


class Loc1_4_3_2(A4QuestArea):  # mines lvl 2
  def extraQuestInLoc(self):
    if self.need_to_free_dashret:
      spirit_entity = next((e for e in poe_bot.game_data.entities.all_entities if e.is_targetable and e.render_name == "Deshret's Spirit"), None)
      if spirit_entity:
        print("found spirit entity, going to it")
        poe_bot.mover.goToEntitysPoint(spirit_entity)
        print("clicking spirit entity")
        spirit_entity.clickTillNotTargetable()
        print("now can go to next loc")
        self.need_to_free_dashret = False
        self.updateGoals()
    return super().extraQuestInLoc()

  def updateGoals(self, force_update=False):
    if self.need_to_free_dashret is False:
      self.possible_to_enter_transitions = ["The Crystal Veins"]
    return super().updateGoals(force_update)


class Loc1_4_3_3(A4QuestArea):  # crystal veins
  waypoint_string = "1_4_3_3"

  def extraQuestInLoc(self):
    if self.have_daresso_gem and self.have_kaom_gem:
      dialla_npc = next((e for e in poe_bot.game_data.entities.npcs if e.path == "Metadata/NPC/Act4/DiallaRapture"), None)
      if dialla_npc:
        poe_bot.mover.goToEntitysPoint(dialla_npc, release_mouse_on_end=True)
        while True:
          poe_bot.refreshInstanceData()
          rapture_transition = next(
            (e for e in poe_bot.game_data.entities.area_transitions if e.path == "Metadata/QuestObjects/Act4/RaptureTransition"), None
          )
          if rapture_transition:
            # or A4Q1RaptureActivated or A4Q1DiallaOnTransformed quest_flag
            poe_bot.mover.goToEntitysPoint(rapture_transition)
            break
          dialla_npc.click(update_screen_pos=True)
          time.sleep(random.randint(5, 7) / 10)
          poe_bot.ui.closeAll()
    return super().extraQuestInLoc()

  def updateGoals(self, force_update=False):
    if self.have_or_used_kaom_gem is False:
      self.possible_to_enter_transitions.append("Kaom's Dream")
    elif self.have_or_used_daresso_gem is False:
      self.possible_to_enter_transitions.append("Daresso's Dream")
    else:
      self.possible_to_enter_transitions.append("The Belly of the Beast Level 1")
    return super().updateGoals(force_update)


class Loc1_4_4_1(QuestArea):
  possible_to_enter_transitions = ["Kaom's Stronghold"]
  explore_furthest = True


class Loc1_4_4_3(A4QuestArea):  # TODO supposed to relog on killing kaom
  waypoint_string = "1_4_4_3"
  bossroom_transitions = ["Caldera of The King"]
  bossroom_entities_render_names = ["King Kaom"]
  explore_furthest = True


class Loc1_4_6_1(QuestArea):
  possible_to_enter_transitions = ["The Belly of the Beast Level 2"]


class Loc1_4_6_2(QuestArea):  # TODO after boss fight supposed to Piety->blocker->door+open->crafting recipe->transition
  bossroom_transitions = ["The Bowels of the Beast"]
  bossroom_entities_render_names = ["Piety, the Abomination"]
  location_name = "The Belly of the Beast Level 2"
  """
  belly of the beast level 2
  """

  def clearBossroom(self, bossroom_encounter: Bossroom):
    def lookForWardensChambers(*args, **kwargs):
      chambers_transition = next((e for e in poe_bot.game_data.entities.npcs if e.path == "Metadata/NPC/Act4/PietyBelly"), None)
      if chambers_transition:
        poe_bot.mover.goToEntitysPoint(chambers_transition)
        while True:
          blocker = next(
            (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Mountain/Belly/Objects/BellyHarvestBlocker"), None
          )
          if blocker and blocker.is_opened is not False:
            break
          chambers_transition.click(update_screen_pos=True)
          poe_bot.refreshInstanceData()
          poe_bot.ui.closeAll()
        poe_bot.mover.goToEntitysPoint(blocker)
        blocker.clickTillNotTargetable()
        harvest_transition = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "The Harvest"), None)
        if harvest_transition:
          poe_bot.mover.goToEntitysPoint(harvest_transition)
          poe_bot.mover.enterTransition(harvest_transition)
          poe_bot.raiseLongSleepException("supposed to be done")
        else:
          poe_bot.raiseLongSleepException("couldnt find next transition")
      return False

    bossroom_encounter.clear_room_custom_break_function = lookForWardensChambers
    inside_wardens_chambers = False
    while inside_wardens_chambers is False:
      inside_wardens_chambers = lookForWardensChambers()
      bossroom_encounter.clearBossroom()


class Loc1_4_6_3(A4QuestArea):  # TODO test logic
  bossroom_transitions = ["Maligaro's Arena", "Shavronne's Arena", "Doedre's Arena"]
  bossroom_entities_render_names = ["Maligaro, The Inquisitor", "Shavronne of Umbra", "Doedre Darktongue"]

  def updateGoals(self, force_update=False):
    self.bossroom_transitions = []
    self.bossroom_entities_render_names = []
    if self.have_or_used_maligaro_item is not True:
      self.bossroom_transitions.append("Maligaro's Arena")
      self.bossroom_entities_render_names.append("Maligaro, The Inquisitor")
    if self.have_or_used_shavronne_item is not True:
      self.bossroom_transitions.append("Shavronne's Arena")
      self.bossroom_entities_render_names.append("Shavronne of Umbra")
    if self.have_or_used_doedre_item is not True:
      self.bossroom_transitions.append("Doedre's Arena")
      self.bossroom_entities_render_names.append("Doedre Darktongue")

    return super().updateGoals(force_update)

  def extraQuestInLoc(self):
    if self.have_or_used_doedre_item is True and self.have_or_used_maligaro_item is True and self.have_or_used_shavronne_item is True:
      piety_npc = next((e for e in poe_bot.game_data.entities.npcs if e.path == "Metadata/NPC/Act4/PietyHarvest"), None)
      if piety_npc:
        poe_bot.mover.goToEntitysPoint(piety_npc)
        while self.harvest_quest_completed is not True:
          poe_bot.refreshInstanceData()
          piety_npc.click(update_screen_pos=True)
          time.sleep(random.randint(5, 7) / 10)
          poe_bot.ui.closeAll()
          self.updateQuestStatus(force_update=True)
        core_mouth = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/QuestObjects/Act4/CoreMouth"), None)
        if core_mouth:
          poe_bot.mover.goToEntitysPoint(core_mouth)
          core_mouth.clickTillNotTargetable()

        "Metadata/QuestObjects/Act4/CoreTransition"
        next((e for e in poe_bot.game_data.entities.area_transitions if e.render_name == "The Black Core"), None)
        next((e for e in poe_bot.game_data.entities.area_transitions if e.render_name == "The Black Heart"), None)
        next((e for e in poe_bot.game_data.entities.attackable_entities if e.render_name == "Heart of the Beast"), None)
        next((e for e in poe_bot.game_data.entities.area_transitions if e.path == "Metadata/QuestObjects/Act4/MalachaiDeathPortal"), None)

    return super().extraQuestInLoc()

  def onBossroomCompleteFunction(self):
    self.updateQuestStatus(force_update=True)
    self.updateGoals()
    return super().onBossroomCompleteFunction()


class Loc1_4_7(QuestArea):
  explore_furthest = True

  def extraQuestInLoc(self):
    activator = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Act4/Area7/Objects/PortalDeviceLever"), None)
    if activator:
      print("found activator")
      print("going activator")
      poe_bot.mover.goToPoint(
        point=(activator.grid_position.x, activator.grid_position.y),
        release_mouse_on_end=False,
        custom_continue_function=poe_bot.combat_module.build.usualRoutine,
      )
      print("clearing around activator")
      poe_bot.combat_module.clearLocationAroundPoint({"X": activator.grid_position.x, "Y": activator.grid_position.y})
      print("opening")
      activator = next(
        (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Act4/Area7/Objects/PortalDeviceLever"), None
      )
      if activator.is_targetable is True:
        activator.clickTillNotTargetable()
      poe_bot.refreshInstanceData()
      transition_device_path_key = "Metadata/Terrain/Act4/Area7/Objects/PortalDeviceTransition"
      transition_device = next((e for e in poe_bot.game_data.entities.all_entities if e.path == transition_device_path_key), None)
      poe_bot.mover.enterTransition(transition_device)
      return True
    return False


# a5
class A5QuestArea(QuestArea):
  pass


class Loc1_5_1(QuestArea):
  waypoint_string = None
  unique_entities_to_kill_render_names = ["Overseer Krow"]

  def funcToCallAfterKillingUniqueEntity(self):
    ladder_key = "Metadata/Terrain/Act5/Area1/Objects/ProximitySpearLadderOnce"
    poe_bot.refreshInstanceData()
    ladder = next((e for e in poe_bot.game_data.entities.all_entities if e.path == ladder_key), None)
    if ladder:
      print("going to ladder")
      poe_bot.mover.goToPoint(
        (ladder.grid_position.x, ladder.grid_position.y),
        custom_continue_function=poe_bot.combat_module.build.usualRoutine,
        release_mouse_on_end=False,
      )
      while True:
        ladder.updateLocationOnScreen()
        ladder.click()
        time.sleep(random.randint(20, 40) / 100)
        poe_bot.refreshInstanceData()
        transition = next((e for e in poe_bot.game_data.entities.area_transitions), None)
        if transition:
          poe_bot.mover.enterTransition(transition)
          break

    else:
      poe_bot.raiseLongSleepException("cannot find ladder after killing overseer")


class Loc1_5_2(QuestArea):
  unique_entities_to_kill_render_names = ["Justicar Casticus"]

  def __init__(self) -> None:
    super().__init__()
    quest_flags = poe_bot.backend.getQuestFlags()
    self.have_miasmeter = quest_flags.get("A5Q3HaveItem", False)
    if self.have_miasmeter:
      print("can go to oriath square")
      self.possible_to_enter_transitions = ["Oriath Square"]
    else:
      print("need to get miasmeter")

  def extraQuestInLoc(self):
    if self.have_miasmeter is False:
      supply_box = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Experimental Supplies"), None)
      if supply_box:
        poe_bot.mover.goToEntitysPoint(supply_box)
        supply_box.clickTillNotTargetable()
        self.possible_to_enter_transitions = ["Oriath Square"]
        self.have_miasmeter = True
    else:
      security_door = next(
        (
          e
          for e in poe_bot.game_data.entities.all_entities
          if e.is_targetable and e.path == "Metadata/Terrain/Act5/Area2/Objects/SlavePenSecurityDoor"
        ),
        None,
      )
      if security_door:
        poe_bot.mover.goToEntitysPoint(security_door)
        security_door.clickTillNotTargetable()
    return super().extraQuestInLoc()


class Loc1_5_3(QuestArea):
  waypoint_string = "1_5_3"
  courts_door_path_key = "Metadata/QuestObjects/Act5/TemplarCourtsDoor"
  possible_to_enter_transitions = ["The Templar Courts"]
  opened_door = False

  def extraQuestInLoc(self):
    if self.opened_door is False:
      courts_door = next((e for e in poe_bot.game_data.entities.all_entities if e.is_targetable and self.courts_door_path_key in e.path), None)
      if courts_door:
        print("going to courts door")
        poe_bot.mover.goToPoint(
          (courts_door.grid_position.x, courts_door.grid_position.y),
          custom_continue_function=poe_bot.combat_module.build.usualRoutine,
          release_mouse_on_end=False,
        )
        courts_door.clickTillNotTargetable()
        self.opened_door = True
    return False


class Loc1_5_4(QuestArea):
  waypoint_string = "1_5_4"
  possible_to_enter_transitions = ["The Chamber of Innocence"]


class Loc1_5_5(QuestArea):
  waypoint_string = "1_5_5"
  bossroom_entities_render_names = ["High Templar Avarius", "Innocence, God-Emperor of Eternity"]

  def __init__(self) -> None:
    quest_flags = poe_bot.backend.getQuestFlags()
    innocence_killed = quest_flags.get("A5Q4KilledBoss", False)
    if innocence_killed:
      print('innocence is killed, can go to ["The Torched Courts"')
      self.possible_to_enter_transitions.append("The Torched Courts")
    else:
      print("innocence is not killed killed, going to kill innocence")
      self.bossroom_transitions.append("Sanctum of Innocence")
    super().__init__()


class Loc1_5_4b(QuestArea):
  ready = True
  possible_to_enter_transitions = ["The Ruined Square"]


class Loc1_5_3b(QuestArea):
  ready = True
  waypoint_string = "1_5_3b"

  def __init__(self) -> None:
    quest_flags = poe_bot.backend.getQuestFlags()
    have_banner = quest_flags.get("A5Q6HaveItem", False)
    if have_banner is False:
      print("need to pick banner")
      self.possible_to_enter_transitions.append("The Ossuary")
    # if didnt do quest

    chest_quest_keys = [
      "A5Q7HaveItem1",
      "A5Q7HaveItem2",
      "A5Q7HaveItem3",
    ]

    need_to_collect_relics = True
    quest_flags = poe_bot.backend.getQuestFlags()
    delivered_relics = quest_flags.get("A5Q7DeliveredItems", False)
    if delivered_relics is True:
      print("already delivered relics")
      need_to_collect_relics = False
    relics_status = list(map(lambda key: quest_flags.get(key, False), chest_quest_keys))
    if False in relics_status:
      print("need to collect relics")
    else:
      print("already have all relics")
      need_to_collect_relics = False

    if need_to_collect_relics is True:
      self.possible_to_enter_transitions.append("The Reliquary")

    if have_banner is True and need_to_collect_relics is False:
      print("got banner and collected relics, can go to kitava")
      self.possible_to_enter_transitions.append("The Cathedral Rooftop")
    super().__init__()


class Loc1_5_6(QuestArea):
  blockades_paths = ["Metadata/Terrain/Act5/Area6/Objects/Ossuary_HiddenDoor"]
  refresh_area_on_blockade = True

  def extraQuestInLoc(self):
    stash_entity = next(
      (e for e in poe_bot.game_data.entities.all_entities if e.is_targetable and "Metadata/Chests/QuestChests/Ossuary/PurityBox" in e.path), None
    )
    if stash_entity:
      print("going to stash with bust")
      poe_bot.mover.goToEntitysPoint(
        stash_entity,
      )
      print("clearing around stash")
      poe_bot.combat_module.clearLocationAroundPoint({"X": stash_entity.grid_position.x, "Y": stash_entity.grid_position.y})
      print("opening stash")
      stash_entity.clickTillNotTargetable()
      print("collecting loot")
      poe_bot.loot_picker.collectLootWhilePresented()
      print("updating quest status")
      self.getQuestStatus()
    return super().extraQuestInLoc()

  def getQuestStatus(self):
    quest_flags = poe_bot.game_data.quest_states.getOrUpdate()
    if quest_flags.get("A5Q6HaveItem", False) is not False:
      self.possible_to_enter_transitions = ["The Ruined Square"]

  def __init__(self) -> None:
    self.getQuestStatus()
    super().__init__()


class Loc1_5_7(QuestArea):
  ready = True
  waypoint_string = None  # "1_5_7"
  chest_key = "Metadata/Chests/QuestChests/Reliquary/RelicCase"
  blockades_paths = ["Metadata/Terrain/Act5/Area7/Objects/VaultDoor"]

  def extraQuestInLoc(self):
    chest = next((e for e in poe_bot.game_data.entities.all_entities if e.is_targetable is not False and self.chest_key in e.path), None)
    print("found targetable chest")
    if chest:
      poe_bot.mover.goToPoint(
        (chest.grid_position.x, chest.grid_position.y), custom_continue_function=poe_bot.combat_module.build.usualRoutine, release_mouse_on_end=False
      )

      print("going to open chest")
      chest = next((e for e in poe_bot.game_data.entities.all_entities if e.is_targetable is not False and self.chest_key in e.path), None)
      chest.clickTillNotTargetable()
      poe_bot.loot_picker.collectLoot()
      return True
    # {"ls":[469,356],"p":"Metadata/Chests/QuestChests/Reliquary/RelicCase2","r":"White","i":1028,"o":0,"h":1,"ia":0,"t":1,"em":0,"b":1,"gp":[305,345],"l":null,"a":"Metadata/Chests/QuestChests/Reliquary/KaomChestQuest02.ao","rn":"Karui Relic Case","et":"c"}
    # {"ls":[469,356],"p":"Metadata/Chests/QuestChests/Reliquary/RelicCase1","r":"White","i":1028,"o":0,"h":1,"ia":0,"t":1,"em":0,"b":1,"gp":[305,345],"l":null,"a":"Metadata/Chests/QuestChests/Reliquary/KaomChestQuest02.ao","rn":"Karui Relic Case","et":"c"}
    # {"ls":[469,356],"p":"Metadata/Chests/QuestChests/Reliquary/RelicCase3","r":"White","i":1028,"o":0,"h":1,"ia":0,"t":1,"em":0,"b":1,"gp":[305,345],"l":null,"a":"Metadata/Chests/QuestChests/Reliquary/KaomChestQuest02.ao","rn":"Karui Relic Case","et":"c"}
    #
    #
    return False

  def __init__(self) -> None:
    super().__init__()
    chest_quest_keys = [
      "A5Q7HaveItem1",
      "A5Q7HaveItem2",
      "A5Q7HaveItem3",
    ]
    need_to_collect_relics = True
    quest_flags = poe_bot.backend.getQuestFlags()
    delivered_relics = quest_flags.get("A5Q7DeliveredItems", False)
    if delivered_relics is True:
      print("already delivered relics")
      need_to_collect_relics = False
    relics_status = list(map(lambda key: quest_flags.get(key, False), chest_quest_keys))
    if False in relics_status:
      print("need to collect relics")
    else:
      print("already have all relics")
      need_to_collect_relics = False

    if need_to_collect_relics is False:
      self.possible_to_enter_transitions = ["The Ruined Square"]


class Loc1_5_8(QuestArea):  # cathedral rooftop kitava
  ready = True
  bossroom_transitions = ["Cathedral Apex"]
  bossrom_activator = "Metadata/Terrain/Act5/Area8/Objects/ArenaSocket"
  bossroom_entities_render_names = ["Kitava, the Insatiable"]
  explore_furthest = True


# a6
class A6QuestArea(QuestArea):
  pass


class Loc1_6_town(QuestArea):
  def __init__(self) -> None:
    super().__init__()
    poe_bot.game_data.quest_states.getOrUpdate()
    ["A6Q4AreaCleared"]
    # if


class Loc2_6_1(QuestArea):
  def __init__(self) -> None:
    quest_flags = poe_bot.game_data.quest_states.getOrUpdate()
    cleared_loc = quest_flags.get("A6Q4AreaCleared", False)
    if cleared_loc is not False:
      self.possible_to_enter_transitions.append("Lioneye's Watch")
    super().__init__()


class Loc2_6_2(QuestArea):
  possible_to_enter_transitions = ["The Mud Flats"]
  waypoint_string = "2_6_2"


class Loc2_6_4(QuestArea):
  ready = True
  have_key = False

  def ifHaveKaruiFortressKey(self):
    quest_flags = poe_bot.backend.getQuestFlags()
    self.have_key = quest_flags.get("A6Q3HaveItem", False)
    return self.have_key

  def extraQuestInLoc(self):
    if self.have_key:
      fortress_entrance = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "The Karui Fortress"), None)
      if fortress_entrance:
        poe_bot.mover.goToEntitysPoint(fortress_entrance)
        poe_bot.mover.enterTransition(fortress_entrance)
    else:
      voll_boss = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "The Dishonoured Queen"), None)
      if voll_boss:
        print("found voll boss")
        poe_bot.mover.goToPoint(
          point=(voll_boss.grid_position.x, voll_boss.grid_position.y),
          release_mouse_on_end=False,
          custom_continue_function=poe_bot.combat_module.build.usualRoutine,
          min_distance=50,
        )
        poe_bot.combat_module.killTillCorpseOrDisappeared(voll_boss)
        poe_bot.combat_module.clearLocationAroundPoint({"X": voll_boss.grid_position.x, "Y": voll_boss.grid_position.y})
        while self.have_key is False:
          poe_bot.refreshInstanceData()
          self.ifHaveKaruiFortressKey()
          poe_bot.loot_picker.collectLoot()
          poe_bot.combat_module.clearLocationAroundPoint({"X": voll_boss.grid_position.x, "Y": voll_boss.grid_position.y})
        print("finished")
        return True
    return False

  def __init__(self) -> None:
    super().__init__()
    self.ifHaveKaruiFortressKey()
    if self.have_key:
      print("gonna go fortress")
    else:
      print("kill queen and goto fortress")


class Loc2_6_5(QuestArea):  # TODO complicated boss with totems
  bossroom_entities_render_names = ["Tukohama, Karui God of War"]

  def clearBossroom(self, bossroom_encounter: Bossroom, just_resurrected=False):
    input("kill boss, has totems on stage, relog")
    return super().clearBossroom(bossroom_encounter, just_resurrected)

  def __init__(self) -> None:
    super().__init__()
    quest_flags = poe_bot.backend.getQuestFlags()
    boss_killed = quest_flags.get("A6Q3KilledBoss", False)
    if boss_killed is False:
      print("need to kill boss here")
      self.bossroom_transitions.append("Tukohama's Keep")
    else:
      print("can go further")
      self.possible_to_enter_transitions.append("The Ridge")


class Loc2_6_6(QuestArea):
  ready = True
  waypoint_string = "2_6_6"
  possible_to_enter_transitions = ["The Lower Prison"]


class Loc2_6_7_1(QuestArea):
  ready = True
  waypoint_string = "2_6_7_1"
  lab_trial_flag = "CruelLabyrinthCompletedPrison"

  def __init__(self) -> None:
    super().__init__()
    if self.need_to_do_lab_trial:
      print("going to look for lab here")
    else:
      print("lab is done here, going to tower")
      self.possible_to_enter_transitions.append("Shavronne's Tower")


class Loc2_6_7_2(QuestArea):
  ready = True
  multi_layerd_transitions_render_names = ["Stairs"]
  bossroom_transitions = ["Prison Rooftop"]
  bossroom_entities_render_names = ["Reassembled Brutus", "Shavronne the Returned"]
  bossroom_activate_boss_in_center = True

  def __init__(self) -> None:
    super().__init__()

  def clearBossroom(self, bossroom_encounter: Bossroom):
    def lookForWardensChambers(*args, **kwargs):
      chambers_transition = next((e for e in poe_bot.game_data.entities.area_transitions if e.render_name == "The Warden's Chambers"), None)
      if chambers_transition:
        poe_bot.mover.goToEntitysPoint(chambers_transition)
        poe_bot.mover.enterTransition(chambers_transition)
        time.sleep(random.randint(10, 20) / 10)
        poe_bot.game_data.terrain.getCurrentlyPassableArea()
        pos_x, pos_y = poe_bot.game_data.terrain.getFurtherstPassablePoint()

        def lookForPrisonersTransition(*args, **kwargs):
          prisoners_gate_transition = next((e for e in poe_bot.game_data.entities.area_transitions if e.render_name == "Prisoner's Gate"), None)
          if prisoners_gate_transition:
            poe_bot.mover.goToEntitysPoint(prisoners_gate_transition)
            poe_bot.mover.enterTransition(prisoners_gate_transition, necropolis_ui=True)
          return False

        poe_bot.mover.goToPoint((pos_x, pos_y), release_mouse_on_end=False, custom_break_function=lookForPrisonersTransition)
        poe_bot.raiseLongSleepException("cannot find prisoners gate")
      return False

    bossroom_encounter.clear_room_custom_break_function = lookForWardensChambers
    bossroom_encounter.clearBossroom()
    inside_wardens_chambers = False
    while inside_wardens_chambers is False:
      inside_wardens_chambers = lookForWardensChambers()
      bossroom_encounter.clearBossroom()


class Loc2_6_8(QuestArea):  # TODO complicated boss with multi layerd transitions
  ready = True
  waypoint_string = None

  def __init__(self) -> None:
    quest_flags = poe_bot.backend.getQuestFlags()
    killed_boss = quest_flags.get("A6Q7KilledBoss", False)
    if killed_boss is True:
      print("boss in valley of the fire drinker killed")
      self.possible_to_enter_transitions.append("The Western Forest")
    else:
      print("need to kill fire drinker first")
      self.bossroom_transitions.append("Valley of the Fire Drinker")
    super().__init__()

  def clearBossroom(self, bossroom_encounter: Bossroom, just_resurrected=False):
    input('kill boss, transitions in bossroom "smth smth" "Valley of the Soul Drinker", relog')
    return super().clearBossroom(bossroom_encounter, just_resurrected)


class Loc2_6_9(QuestArea):
  waypoint_string = "2_6_9"
  ready = True
  possible_to_enter_transitions = ["The Riverways"]


class Loc2_6_10(QuestArea):
  waypoint_string = "2_6_10"

  def getTransitionsAndBossrooms(self):
    quest_flags = poe_bot.backend.getQuestFlags()
    killed_puppet = quest_flags.get("A6Q6KilledBoss", False)
    if killed_puppet is False:
      print("puppet in wetlands wasnt killed")
      self.possible_to_enter_transitions.append("The Wetlands")  # puppet
    else:
      print("puppet in wetlands was killed going to southern forest")
      self.possible_to_enter_transitions.append("The Southern Forest")  # main quest

  def __init__(self) -> None:
    super().__init__()
    if self.can_open_waypoint is True:
      print("need to open waypoint first")
    else:
      self.getTransitionsAndBossrooms()

  def onWaypointOpenedFunction(self):
    self.getTransitionsAndBossrooms()


class Loc2_6_11(QuestArea):
  bossroom_entities_render_names = ["Ryslatha's Nest", "Ryslatha, the Puppet Mistress"]

  def getTransitionsAndBossrooms(self):
    quest_flags = poe_bot.backend.getQuestFlags()
    killed_puppet = quest_flags.get("A6Q6KilledBoss", False)
    if killed_puppet is False:
      print("puppet in wetlands wasnt killed")
      self.bossroom_transitions.append("The Spawning Ground")
    else:
      print("puppet in wetlands was killed going back toriverways")
      self.possible_to_enter_transitions.append("The Riverways")  # main quest

  def onBossroomCompleteFunction(self):
    self.possible_to_enter_transitions.append("The Riverways")  # main quest
    return super().onBossroomCompleteFunction()

  def __init__(self) -> None:
    self.getTransitionsAndBossrooms()
    super().__init__()


class Loc2_6_12(QuestArea):
  ready = True
  waypoint_string = "2_6_12"

  def __init__(self) -> None:
    self.possible_to_enter_transitions.append("The Cavern of Anger")  # main quest
    super().__init__()


class Loc2_6_13(QuestArea):  # multi layerd "Passage" + pick flag
  have_flag = False

  def extraQuestInLoc(self):
    if self.have_flag is not True:
      visible_chest = next(
        (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Chests/QuestChests/BlackFlagChest" and e.is_targetable is True),
        None,
      )
      if visible_chest:
        poe_bot.mover.goToEntity(visible_chest)
        visible_chest.clickTillNotTargetable()
        time.sleep(1)
        poe_bot.loot_picker.collectLootWhilePresented()
        self.getQuestStatus()
    return super().extraQuestInLoc()

  def getQuestStatus(self):
    poe_bot.game_data.quest_states.update()
    quest_flags = poe_bot.game_data.quest_states.getOrUpdate()
    self.have_flag = quest_flags.get("A6Q1HaveFlag", False)
    if self.have_flag is not False:
      self.multi_layerd_transitions_render_names.append("Passage")
      self.possible_to_enter_transitions.append("The Beacon")  # main quest

  def __init__(self) -> None:
    self.getQuestStatus()
    super().__init__()


class Loc2_6_14(QuestArea):  # beacon quest "Metadata/QuestObjects/Act6/BeaconPayload"
  waypoint_string = "2_6_14"
  payloads_to_ignore_ids = []
  refueled_beacon = False

  # bossroom_transitions = ["The Brine King's Throne"]
  def extraQuestInLoc(self):
    beacon_payload = next(
      (
        e
        for e in poe_bot.game_data.entities.all_entities
        if e.path == "Metadata/QuestObjects/Act6/BeaconPayload" and e.id not in self.payloads_to_ignore_ids
      ),
      None,
    )
    if beacon_payload:
      print(f"found payload {beacon_payload.raw}")
      print("going to it")
      poe_bot.mover.goToEntitysPoint(beacon_payload, min_distance=60)
      fuel_tank = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/QuestObjects/Act6/BeaconFuelTank"), None)
      if (
        fuel_tank is None
        or dist((fuel_tank.grid_position.x, fuel_tank.grid_position.y), (beacon_payload.grid_position.x, beacon_payload.grid_position.y)) > 30
      ):
        print("following beacon")
        poe_bot.mover.goToEntitysPoint(beacon_payload, min_distance=20)
        while True:
          killed_someone = poe_bot.combat_module.clearLocationAroundPoint(
            {"X": beacon_payload.grid_position.x, "Y": beacon_payload.grid_position.y},
            # ignore_keys=self.current_map.entities_to_ignore_in_bossroom_path_keys
          )
          if killed_someone is False:
            point = poe_bot.game_data.terrain.pointToRunAround(
              point_to_run_around_x=beacon_payload.grid_position.x,
              point_to_run_around_y=beacon_payload.grid_position.y,
              distance_to_point=10,
            )
            poe_bot.mover.move(grid_pos_x=point[0], grid_pos_y=point[1])
          poe_bot.refreshInstanceData(reset_timer=killed_someone)
          updated_beacon_payload = next((e for e in poe_bot.game_data.entities.all_entities if e.id == beacon_payload.id), None)
          if updated_beacon_payload is not None:
            beacon_payload = updated_beacon_payload
          else:
            pass
          if fuel_tank:
            distance_to_fuel_tank = dist(
              (fuel_tank.grid_position.x, fuel_tank.grid_position.y), (beacon_payload.grid_position.x, beacon_payload.grid_position.y)
            )
            print(f"distance to fuel tank {distance_to_fuel_tank}")
            if distance_to_fuel_tank < 25:
              self.payloads_to_ignore_ids.append(beacon_payload.id)
              break
          else:
            fuel_tank = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/QuestObjects/Act6/BeaconFuelTank"), None)
      else:
        print("ignoring this payload since its close to fuel tank")
        self.payloads_to_ignore_ids.append(beacon_payload.id)
      if len(self.payloads_to_ignore_ids) == 2 or self.refueled_beacon is not False:
        activator = next(
          (
            e
            for e in poe_bot.game_data.entities.all_entities
            if e.is_targetable is not False
            and e.path in ["Metadata/QuestObjects/Act6/BlackCrest_BeaconLever", "Metadata/QuestObjects/Act6/BlackCrest_BeaconInteract"]
          ),
          None,
        )
        if activator:
          poe_bot.mover.goToEntitysPoint(activator)
          activator.clickTillNotTargetable()
    weylam = next(
      (e for e in poe_bot.game_data.labels_on_ground_entities if e.is_targetable is not False and e.path == "Metadata/NPC/Act6/WeylamBeacon"), None
    )
    if weylam:
      poe_bot.mover.goToEntitysPoint(weylam, release_mouse_on_end=True)
      weylam.openDialogue()
      next((ch for ch in poe_bot.ui.npc_dialogue.choices if ch.text == "Sail to the Brine King's Reef")).click()

    return super().extraQuestInLoc()


class Loc2_6_15(QuestArea):  # the brine kings reef
  waypoint_string = "2_6_15"
  bossroom_transitions = ["The Brine King's Throne"]
  bossroom_entities_render_names = ["Tsoagoth, The Brine King"]
  bossroom_activate_boss_in_center = True

  def clearBossroom(self, bossroom_encounter: Bossroom):
    def lookForWardensChambers(*args, **kwargs):
      chambers_transition = next(
        (e for e in poe_bot.game_data.labels_on_ground_entities if e.is_targetable is True and e.path == "Metadata/NPC/Act6/WeylamReef2"), None
      )
      if chambers_transition:
        poe_bot.mover.goToEntitysPoint(chambers_transition, release_mouse_on_end=True)
        chambers_transition.openDialogue()
        next((ch for ch in poe_bot.ui.npc_dialogue.choices if ch.text == "Sail to the Bridge Encampment")).click()
      return False

    bossroom_encounter.clear_room_custom_break_function = lookForWardensChambers
    inside_wardens_chambers = False
    while inside_wardens_chambers is False:
      bossroom_encounter.clearBossroom()
      inside_wardens_chambers = lookForWardensChambers()


# a7
class A7QuestArea(QuestArea):
  have_map = False
  fireflies_collected = False
  gruthkul_killed = False

  def updateQuestStatus(self, force_update=False):
    super().updateQuestStatus(force_update)
    self.updateMapStatus()
    self.updateFireFlyQuest()
    self.updateGruthkulStatus()
    self.updateCryptSilkQuestStatus()

  def updateMapStatus(self):
    quest_flags = poe_bot.game_data.quest_states.getOrUpdate()
    self.have_map = quest_flags.get("A7Q2HaveItem", False)

  def updateCryptSilkQuestStatus(self):
    quest_flags = poe_bot.game_data.quest_states.getOrUpdate()
    # kill malagrio, take poison
    self.have_black_venom = quest_flags.get("A7Q3HaveItem", False)
    # deliver poison
    self.delivered_black_venom = quest_flags.get("A7Q3DeliveredItem", False)
    # take key
    self.chamber2_key_taken = quest_flags.get("A7Q1HaveKey", False)
    # use key
    self.chamber2_key_used = quest_flags.get("A7Q1UsedKey", False)

  def updateFireFlyQuest(self):
    quest_flags = poe_bot.game_data.quest_states.getOrUpdate()
    firefly_keys = [
      "A7Q7HaveItem1",
      "A7Q7HaveItem2",
      "A7Q7HaveItem3",
      "A7Q7HaveItem4",
      "A7Q7HaveItem5",
      "A7Q7HaveItem6",
      "A7Q7HaveItem7",
    ]
    firefly_statuses = list(map(lambda key: quest_flags.get(key, False), firefly_keys))
    self.fireflies_collected = False not in firefly_statuses

  def updateGruthkulStatus(self):
    quest_flags = poe_bot.game_data.quest_states.getOrUpdate()
    self.gruthkul_killed = quest_flags.get("A7Q9KilledBoss", False)


class Loc2_7_1(QuestArea):  # ridge
  possible_to_enter_transitions = ["The Crossroads"]


class Loc2_7_2(A7QuestArea):  # crossroads
  waypoint_string = "2_7_2"

  def updateGoals(self, force_update=False):
    super().updateGoals(force_update)
    if self.can_open_waypoint is True:
      print("open waypoint first")
    else:
      print("can go further")
      if self.have_map is False:
        print("need to get map firts")
        self.possible_to_enter_transitions = ["The Fellshrine Ruins"]
      else:
        print("open the map")
        self.possible_to_enter_transitions = ["The Chamber of Sins Level 1"]

  def onWaypointOpenedFunction(self):
    self.updateGoals()


class Loc2_7_3(QuestArea):  # The Fellshrine Ruins
  possible_to_enter_transitions = ["The Crypt"]


class Loc2_7_4(A7QuestArea):  # The crypt
  lab_trial_flag = "CruelLabyrinthCompletedSins"
  waypoint_string = "2_7_4"
  have_map = False

  def updateGoals(self, force_update=False):
    super().updateGoals(force_update)
    if self.need_to_do_lab_trial is False:
      self.multi_layerd_transitions_render_names.append("Stairs")
      if self.have_map is True:
        poe_bot.helper_functions.relog()

  def doLab(self, lab_enterance: Entity, lab_area):
    poe_bot.mover.goToEntitysPoint(lab_enterance)
    lab_enterance.clickTillNotTargetable()
    furthest_unvisited = poe_bot.pather.utils.getFurthestPoint(start=(lab_enterance.grid_position.x, lab_enterance.grid_position.y), area=lab_area)

    def lookForSwitch(*args, **kwargs):
      switch = next(
        (
          e
          for e in poe_bot.game_data.entities.all_entities
          if e.is_targetable is not False and e.path == "Metadata/Terrain/Labyrinth/Objects/Puzzle_Parts/Switch_Once"
        ),
        None,
      )
      if switch:

        def findSwitchWithLowerId(*args, **kwargs):
          another_switch = next(
            (
              e
              for e in poe_bot.game_data.entities.all_entities
              if e.is_targetable is not False and e.path == "Metadata/Terrain/Labyrinth/Objects/Puzzle_Parts/Switch_Once" and e.id < switch.id
            ),
            None,
          )
          if another_switch:
            poe_bot.mover.goToEntitysPoint(another_switch)
            poe_bot.refreshInstanceData()
            another_switch.clickTillNotTargetable()
          return False

        poe_bot.mover.goToEntitysPoint(switch, custom_break_function=findSwitchWithLowerId)
        poe_bot.refreshInstanceData()
        switch.clickTillNotTargetable()
      return False

    def lookForPlaque(*args, **kwargs):
      plaque = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/QuestObjects/Labyrinth/LabyrinthTrialPlaque"), None)
      if plaque:
        poe_bot.mover.goToEntitysPoint(plaque, custom_break_function=lookForSwitch)
        while True:
          poe_bot.refreshInstanceData()
          portal = next(
            (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Labyrinth/Objects/LabyrinthTrialReturnPortal"), None
          )
          if portal and portal.is_targetable:
            print("plaque activated")
            poe_bot.ui.closeAll()
            poe_bot.mover.goToEntitysPoint(portal)
            poe_bot.mover.enterTransition(portal, entered_distance_sign=50)
            break
          plaque.click(update_screen_pos=True)
        return True
      return False

    def labExploreFunc(*args, **kwargs):
      lookForSwitch()
      if lookForPlaque() is True:
        return True
      return False

    poe_bot.mover.goToPoint((furthest_unvisited), release_mouse_on_end=False, custom_break_function=labExploreFunc)
    print("lab finished")
    return True

  def onLabTrialCompleteFunction(self):
    self.multi_layerd_transitions_render_names.append("Stairs")
    return super().onLabTrialCompleteFunction()

  def extraQuestInLoc(self):
    if self.need_to_do_lab_trial is False:
      sarcophagus = next(
        (
          e
          for e in poe_bot.game_data.entities.all_entities
          if e.is_targetable and e.path == "Metadata/Chests/Sarcophagi/sarcophagus_door" and e.is_targetable is not False
        ),
        None,
      )
      if sarcophagus:
        poe_bot.mover.goToEntitysPoint(sarcophagus)
        sarcophagus.clickTillNotTargetable()
        return True
    malagrio_chest = next(
      (
        e
        for e in poe_bot.game_data.entities.all_entities
        if e.is_targetable and e.path == "Metadata/Chests/QuestChests/MaligaroMapChest" and e.is_targetable is not False
      ),
      None,
    )
    if malagrio_chest:
      poe_bot.mover.goToEntitysPoint(malagrio_chest)
      malagrio_chest.clickTillNotTargetable()
      poe_bot.combat_module.clearAreaAroundPoint((malagrio_chest.grid_position.x, malagrio_chest.grid_position.y))
      poe_bot.loot_picker.collectLootWhilePresented()
      self.updateQuestStatus(force_update=True)
      if self.have_map is not False:
        poe_bot.helper_functions.relog()

    return super().extraQuestInLoc()


class Loc2_7_5_1(QuestArea):  # Chamber of sins lvl1 #TODO extra quest
  waypoint_string = "2_7_5_1"

  def __init__(self) -> None:
    super().__init__()
    if self.can_open_waypoint is True:
      print("need to open waypoint first")
    else:
      # check if
      pass


class Loc2_7_5_map(A7QuestArea):
  pass


class Loc2_7_5_2(QuestArea):  # Chamber of sins lvl2 #TODO lab trial doors are unpassable
  lab_trial_flag = "CruelLabyrinthCompletedCrypt"

  def doLab(self, lab_enterance: Entity, lab_area):
    # "Metadata/Terrain/Labyrinth/Objects/Puzzle_Parts/Door_Closed"
    poe_bot.mover.goToEntitysPoint(lab_enterance)
    lab_enterance.clickTillNotTargetable()
    furthest_unvisited = poe_bot.pather.utils.getFurthestPoint(start=(lab_enterance.grid_position.x, lab_enterance.grid_position.y), area=lab_area)

    def lookForPlaque(*args, **kwargs):
      plaque = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/QuestObjects/Labyrinth/LabyrinthTrialPlaque"), None)
      if plaque:
        poe_bot.mover.goToEntitysPoint(plaque)
        while True:
          poe_bot.refreshInstanceData()
          portal = next(
            (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Labyrinth/Objects/LabyrinthTrialReturnPortal"), None
          )
          if portal and portal.is_targetable:
            print("plaque activated")
            poe_bot.ui.closeAll()
            poe_bot.mover.goToEntitysPoint(portal)
            poe_bot.mover.enterTransition(portal)
            break
          plaque.click(update_screen_pos=True)
        return True
      return False

    poe_bot.mover.goToPoint((furthest_unvisited), release_mouse_on_end=False, custom_break_function=lookForPlaque)
    return True

  def extraQuestInLoc(self):
    if self.need_to_do_lab_trial is False:
      door = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Secret Passage"), None)
      if door:
        poe_bot.mover.goToEntitysPoint(door)
        door.clickTillNotTargetable()
        transition = next((e for e in poe_bot.game_data.entities.area_transitions if e.render_name == "The Den"), None)
        if transition:
          poe_bot.mover.enterTransition(transition)
    return False


class Loc2_7_6(QuestArea):  # "The Den"
  waypoint_string = "2_7_6"
  possible_to_enter_transitions = ["The Ashen Fields"]


class Loc2_7_7(QuestArea):
  waypoint_string = "2_7_7"
  bossroom_transitions = ["The Fortress Encampment"]
  bossroom_entities_render_names = ["Greust, Lord of the Forest", "Enthralled Dire Wolf"]

  def clearBossroom(self, bossroom_encounter: Bossroom):
    def lookForTransition(*args, **kwargs):
      area_transition = next((e for e in poe_bot.game_data.entities.area_transitions if e.render_name == "The Northern Forest"), None)
      if area_transition:
        poe_bot.mover.goToEntitysPoint(area_transition)
        poe_bot.mover.enterTransition(area_transition)
      return False

    bossroom_encounter.clear_room_custom_break_function = lookForTransition
    inside_wardens_chambers = False
    while inside_wardens_chambers is False:
      inside_wardens_chambers = lookForTransition()
      bossroom_encounter.clearBossroom()


class Loc2_7_8(A7QuestArea):  # "The Northern Forest"
  waypoint_string = None

  def updateGoals(self, force_update=False):
    super().updateGoals(force_update)
    if self.fireflies_collected is True and self.gruthkul_killed is True:
      print("[Loc2_7_8] collected fireflies and gruthkul killed, may go to causeway")
      self.possible_to_enter_transitions = ["The Causeway"]
    else:
      print(
        f"[Loc2_7_8] collected fireflies status {self.fireflies_collected} and gruthkul_killed status {self.gruthkul_killed}, need to visit dread thicket"
      )
      self.possible_to_enter_transitions = ["The Dread Thicket"]


class Loc2_7_9(QuestArea):
  ready = True
  location_name = "The Dread Thicket"
  firefly_container_key = "Metadata/Chests/QuestChests/Fireflies/FireflyChest"
  need_to_collect_fireflies = False
  bossroom_entities_render_names = ["Gruthkul, Mother of Despair"]

  def __init__(self) -> None:
    need_to_do_location = False
    self.checkFireflyStatus()
    if self.need_to_collect_fireflies is False:
      print("no need to collect fireflies here")
    else:
      print("need to collect fireflies here")
      need_to_do_location = True
    quest_flags = poe_bot.backend.getQuestFlags()
    killed_boss = quest_flags.get("A7Q9KilledBoss", False)
    if killed_boss is False:
      need_to_do_location = True
      self.bossroom_transitions.append("Den of Despair")
    if need_to_do_location is False:
      self.possible_to_enter_transitions.append("The Northern Forest")
    super().__init__()

  def checkFireflyStatus(self):
    quest_flags = poe_bot.backend.getQuestFlags()
    firefly_keys = [
      "A7Q7HaveItem1",
      "A7Q7HaveItem2",
      "A7Q7HaveItem3",
      "A7Q7HaveItem4",
      "A7Q7HaveItem5",
      "A7Q7HaveItem6",
      "A7Q7HaveItem7",
    ]
    firefly_statuses = list(map(lambda key: quest_flags.get(key, False), firefly_keys))
    if False in firefly_statuses:
      self.need_to_collect_fireflies = True
    else:
      self.need_to_collect_fireflies = False

  def extraQuestInLoc(self):
    firefly_containter = next((e for e in poe_bot.game_data.entities.all_entities if e.is_targetable and self.firefly_container_key in e.path), None)
    if firefly_containter:
      print("found firefly container")
      poe_bot.mover.goToPoint(
        (firefly_containter.grid_position.x, firefly_containter.grid_position.y),
        release_mouse_on_end=False,
        custom_continue_function=poe_bot.combat_module.build.usualRoutine,
      )
      firefly_containter.clickTillNotTargetable()
      loot_collected = True
      while loot_collected is True:
        loot_collected = poe_bot.loot_picker.collectLoot()
        poe_bot.refreshInstanceData()
      self.checkFireflyStatus()
    return False


class Loc2_7_10(QuestArea):  # "The Causeway" #TODO sometimes doesnt collect loot from lockbox
  ready = True
  waypoint_string = "2_7_10"
  anchor_keys = ["Kishara's Lockbox", "The Vaal City"]

  def extraQuestInLoc(self):
    box_or_transition = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name in self.anchor_keys), None)
    if box_or_transition:
      poe_bot.mover.goToEntitysPoint(box_or_transition)
      kishara_box = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Kishara's Lockbox"))
      poe_bot.mover.goToEntitysPoint(kishara_box)
      kishara_box.clickTillNotTargetable()
      poe_bot.refreshInstanceData()
      poe_bot.loot_picker.collectLootWhilePresented()
      poe_bot.refreshInstanceData()
      transition = next((e for e in poe_bot.game_data.entities.area_transitions if e.render_name == "The Vaal City"))
      while True:
        res = poe_bot.mover.goToPoint(
          (transition.grid_position.x, transition.grid_position.y),
          release_mouse_on_end=False,
          custom_continue_function=poe_bot.combat_module.build.usualRoutine,
          custom_break_function=poe_bot.loot_picker.collectLoot(),
        )
        if res is None:
          break
      poe_bot.mover.enterTransition(transition, necropolis_ui=True)
    return False


class Loc2_7_11(QuestArea):  # "The Vaal City" #TODO not sure if it completes the quest properly
  waypoint_string = "2_7_11"
  possible_to_enter_transitions = ["The Temple of Decay Level 1"]
  anchor_keys = ["The Temple of Decay Level 1", "Yeena"]

  def extraQuestInLoc(self):
    if self.can_open_waypoint is False:
      anchor = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name in self.anchor_keys), None)
      if anchor:
        print("found anchor to temple of decay lvl1 ")
        poe_bot.mover.goToEntitysPoint(anchor)
        yeena_npc = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Yeena"), None)
        poe_bot.combat_module.clearAreaAroundPoint(yeena_npc.grid_position.toList())
        poe_bot.mover.goToEntitysPoint(yeena_npc)
        yeena_targetable = yeena_npc.is_targetable
        print(f"yeena {yeena_npc.raw}")
        while yeena_targetable is not False:
          poe_bot.refreshInstanceData()
          yeena_npc.click(update_screen_pos=True)
          poe_bot.ui.closeAll()
          print("clicked on yeena yeena")
          yeena_npc = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Yeena"), None)
          if yeena_npc and yeena_npc.is_targetable is False:
            print("yeena became untargetable")
            break
        next_transition = next((e for e in poe_bot.game_data.entities.area_transitions if e.render_name == "The Temple of Decay Level 1"), None)
        if next_transition:
          print("found next transition")
          poe_bot.mover.goToEntitysPoint(next_transition)
          poe_bot.mover.enterTransition(next_transition)
    return False


class Loc2_7_12_1(QuestArea):
  multi_layerd_transitions_render_names = ["Stairs"]
  possible_to_enter_transitions = ["The Temple of Decay Level 2"]


class Loc2_7_12_2(
  QuestArea
):  # "The Temple of Decay Level 2" #TODO boss in bossroom is out of passable, need to update terrain on entrance and on boss kill
  multi_layerd_transitions_render_names = ["Stairs"]
  bossroom_transitions = ["Arakaali's Web"]


# a8
class A8QuestArea(QuestArea):
  killed_gemlings = False

  def updateQuestStatus(self, force_update=False):
    super().updateQuestStatus(force_update)
    self.updateGemlingsStatus()

  def updateGemlingsStatus(self):
    quest_flags = poe_bot.game_data.quest_states.getOrUpdate()
    self.killed_gemlings = quest_flags.get("A8Q7KilledBoss", False)


class Loc2_8_1(QuestArea):
  possible_to_enter_transitions = ["The Sarn Encampment"]
  multi_layerd_transitions_render_names = ["Stairs"]
  waypoint_string = None


class Loc2_8_2_1(QuestArea):
  possible_to_enter_transitions = ["Doedre's Cesspool"]


class Loc2_8_2_2(QuestArea):
  bossroom_transitions = ["The Cauldron"]

  # bossrom_activator = "Valve"
  # bossroom_entities_render_names = []
  # after boss fight go to "Sewer Outlet"
  def extraQuestInLoc(self):
    grate_entity = next((e for e in poe_bot.game_data.entities.all_entities if e.is_targetable is True and e.render_name == "Loose Grate"), None)
    if grate_entity:
      poe_bot.mover.goToEntitysPoint(grate_entity)
      grate_entity.clickTillNotTargetable()
    return super().extraQuestInLoc()


class Loc2_8_8(QuestArea):
  need_ankh = False
  have_ankh = False
  A8Q6KilledBoss = False
  need_to_get_ankh = False
  need_get_to_resurrection_site = False

  def clearBossroom(self, bossroom_encounter: Bossroom):
    def activateClarissaIfExists(*args, **kwargs):
      clarissa_npc = next(
        (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/NPC/Act8/ClarissaQuay" and e.is_targetable is True), None
      )
      if clarissa_npc:
        poe_bot.mover.goToEntitysPoint(clarissa_npc)
        clarissa_npc.clickTillNotTargetable()
      return False

    activateClarissaIfExists()
    bossroom_encounter.clear_room_custom_break_function = activateClarissaIfExists
    while True:
      quest_flags = poe_bot.backend.getQuestFlags()
      self.A8Q6KilledBoss = quest_flags.get("A8Q6KilledBoss", False)
      if self.A8Q6KilledBoss is True:
        break
      bossroom_encounter.clearBossroom()
    self.onBossroomCompleteFunction()
    self.bossroom_transitions.remove(bossroom_encounter.transition_entity.render_name)

  def getQuestStatus(self):
    quest_flags = poe_bot.backend.getQuestFlags()
    self.have_ankh = quest_flags.get("A8Q6HaveItem", False)
    self.delivered_ankh = quest_flags.get("A8Q6DeliveredItem", False)
    self.A8Q6KilledBoss = quest_flags.get("A8Q6KilledBoss", False)
    if self.A8Q6KilledBoss is True:
      print("resurection site quest is complete")
      self.possible_to_enter_transitions.append("The Grain Gate")
    else:
      print("need to do resurection site quest")
      if self.have_ankh is False and self.delivered_ankh is False:
        print("need to get ankh first")
        self.need_to_get_ankh = True
      else:
        print("need to go to resurection site")
        self.bossroom_transitions.append("Resurrection Site")

  def __init__(self) -> None:
    self.getQuestStatus()
    super().__init__()

  def extraQuestInLoc(self):
    if self.need_to_get_ankh is True:
      cascet = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Sealed Casket"), None)
      if cascet:
        print("found cascet, going to it")
        poe_bot.mover.goToEntitysPoint(cascet)
        poe_bot.combat_module.clearLocationAroundPoint({"X": cascet.grid_position.x, "Y": cascet.grid_position.y})
        cascet.clickTillNotTargetable()
        poe_bot.loot_picker.collectLootWhilePresented()
        self.need_to_get_ankh = False
        self.bossroom_transitions = ["Resurrection Site"]
    return super().extraQuestInLoc()


class Loc2_8_9(A8QuestArea):
  waypoint_string = "2_8_9"

  def updateGoals(self, force_update=False):
    super().updateGoals(force_update)
    if self.killed_gemlings is True:
      self.possible_to_enter_transitions = ["The Imperial Fields"]

  def extraQuestInLoc(self):
    if self.killed_gemlings is False:
      gemling_guy = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Gemling Legionnaire"), None)
      if gemling_guy:
        print("going to gemling guy")
        poe_bot.mover.goToEntitysPoint(gemling_guy)
        print("killing gemling guy")
        poe_bot.combat_module.killTillCorpseOrDisappeared(gemling_guy)
        print("gemling guy killed")
        gemling_guys = list(filter(lambda e: e.render_name == "Gemling Legionnaire", poe_bot.game_data.entities.attackable_entities))
        for guy in gemling_guys:
          poe_bot.combat_module.killUsualEntity(guy)
        poe_bot.refreshInstanceData()
        self.updateQuestStatus(force_update=True)
        self.updateGoals()
    return super().extraQuestInLoc()


class Loc2_8_10(QuestArea):  # 'The Imperial Fields'
  waypoint_string = "2_8_10"
  possible_to_enter_transitions = ["The Solaris Temple Level 1"]


class Loc2_8_12_1(QuestArea):  # "The Solaris Temple Level 1"
  waypoint_string = "2_8_12_1"
  possible_to_enter_transitions = ["The Solaris Temple Level 2"]


class Loc2_8_12_2(QuestArea):  # "The Solaris Temple Level 2" #TODO doesnt pick solaris stone
  ready = True
  bossroom_transitions = ["Portal"]
  bossroom_entities_render_names = ["Dawn, Harbinger of Solaris"]

  def onBossroomCompleteFunction(self):
    poe_bot.ui.inventory.update()
    solaris_orb = next((i for i in poe_bot.ui.inventory.items if i.render_path == "Art/2DItems/QuestItems/SolarisStone.dds"), None)
    if solaris_orb is None:
      poe_bot.raiseLongSleepException("didnt pick solaris orb on completion bossroom")
    else:
      poe_bot.helper_functions.relog()
    return super().onBossroomCompleteFunction()


class Loc2_8_3(QuestArea):
  ready = True
  possible_to_enter_transitions = ["The Bath House"]
  explore_furthest = True


class Loc2_8_5(QuestArea):  # TODO lab complete order is unknown
  waypoint_string = "2_8_5"
  lab_trial_flag = "MercilessLabyrinthCompletedBathHouse"

  def getTransitions(self):
    quest_flags = poe_bot.backend.getQuestFlags()
    killed_boss = quest_flags.get("A8Q4KilledBoss", False)
    if killed_boss is False:
      print("killed boss in gardens")
      self.possible_to_enter_transitions = ["The High Gardens"]
    else:
      if self.need_to_do_lab_trial is False:
        print("no need to do lab here, can go to The Lunaris Concourse")
        self.possible_to_enter_transitions = ["The Lunaris Concourse"]
      else:
        print("need to do lab")

  def doLab(self, lab_enterance: Entity, lab_area):
    poe_bot.mover.goToEntitysPoint(lab_enterance)
    lab_enterance.clickTillNotTargetable()
    furthest_unvisited = poe_bot.pather.utils.getFurthestPoint(start=(lab_enterance.grid_position.x, lab_enterance.grid_position.y), area=lab_area)

    def lookForSwitch(*args, **kwargs):
      switch = next(
        (
          e
          for e in poe_bot.game_data.entities.all_entities
          if e.is_targetable is not False and e.path == "Metadata/Terrain/Labyrinth/Objects/Puzzle_Parts/Switch_Once"
        ),
        None,
      )
      if switch:

        def findSwitchWithLowerId(*args, **kwargs):
          another_switch = next(
            (
              e
              for e in poe_bot.game_data.entities.all_entities
              if e.is_targetable is not False and e.path == "Metadata/Terrain/Labyrinth/Objects/Puzzle_Parts/Switch_Once" and e.id < switch.id
            ),
            None,
          )
          if another_switch:
            poe_bot.mover.goToEntitysPoint(another_switch)
            poe_bot.refreshInstanceData()
            another_switch.clickTillNotTargetable()
          return False

        poe_bot.mover.goToEntitysPoint(switch, custom_break_function=findSwitchWithLowerId)
        poe_bot.refreshInstanceData()
        switch.clickTillNotTargetable()
      return False

    def lookForPlaque(*args, **kwargs):
      plaque = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/QuestObjects/Labyrinth/LabyrinthTrialPlaque"), None)
      if plaque:
        poe_bot.mover.goToEntitysPoint(plaque, custom_break_function=lookForSwitch)
        while True:
          poe_bot.refreshInstanceData()
          portal = next(
            (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Labyrinth/Objects/LabyrinthTrialReturnPortal"), None
          )
          if portal and portal.is_targetable:
            print("plaque activated")
            poe_bot.ui.closeAll()
            poe_bot.mover.goToEntitysPoint(portal)
            poe_bot.mover.enterTransition(portal, entered_distance_sign=50)
            break
          plaque.click(update_screen_pos=True)
        return True
      return False

    def labExploreFunc(*args, **kwargs):
      lookForSwitch()
      if lookForPlaque() is True:
        return True
      return False

    poe_bot.mover.goToPoint((furthest_unvisited), release_mouse_on_end=False, custom_break_function=labExploreFunc)
    print("lab finished")
    return True

  def __init__(self) -> None:
    self.getTransitions()
    super().__init__()


class Loc2_8_4(QuestArea):
  explore_furthest = True
  bossroom_entities_render_names = ["Yugul, Reflection of Terror", "Reflection of Terror"]

  def getTransitions(self):
    quest_flags = poe_bot.backend.getQuestFlags()
    killed_boss = quest_flags.get("A8Q4KilledBoss", False)
    if killed_boss is False:
      print("kill boss in gardens")
      self.bossroom_transitions = ["The Pools of Terror"]
    else:
      print("no need to do lab here, can go to The Lunaris Concourse through bath house")
      self.possible_to_enter_transitions = ["The Bath House"]

  def __init__(self) -> None:
    self.getTransitions()
    super().__init__()


class Loc2_8_6(QuestArea):
  ready = True
  waypoint_string = "2_8_6"

  def __init__(self) -> None:
    super().__init__()
    if self.can_open_waypoint is True:
      print("need to open waypoint first")
    else:
      print("waypoint opened going to temple")
      self.possible_to_enter_transitions.append("The Lunaris Temple Level 1")

  def onWaypointOpenedFunction(self):
    self.possible_to_enter_transitions.append("The Lunaris Temple Level 1")
    return super().onWaypointOpenedFunction()


class Loc2_8_7_1_(QuestArea):
  ready = True
  waypoint_string = "2_8_7_1_"
  possible_to_enter_transitions = ["The Lunaris Temple Level 2"]


class Loc2_8_7_2(QuestArea):  # TODO doesnt pick solaris stone
  ready = True
  bossroom_transitions = ["Portal"]
  bossroom_entities_render_names = ["Dusk, Harbinger of Lunaris"]
  explore_furthest = True

  def onBossroomCompleteFunction(self):
    poe_bot.ui.inventory.update()
    solaris_orb = next((i for i in poe_bot.ui.inventory.items if i.render_path == "Art/2DItems/QuestItems/LunarisStone.dds"), None)
    if solaris_orb is None:
      poe_bot.raiseLongSleepException("didnt pick solaris orb on completion bossroom")
    else:
      poe_bot.helper_functions.relog()


# TODO bridge harbour -> fight
# a9
class A9QuestArea(QuestArea):
  dealt_with_basilisk = False

  def updateQuestStatus(self, force_update=False):
    super().updateQuestStatus(force_update=force_update)
    self.updateBasiliskQuest()

  def updateBasiliskQuest(self):
    quest_flags = poe_bot.game_data.quest_states.getOrUpdate()
    have_basilisk_item = quest_flags.get("A9Q1HaveItem2", False)
    if have_basilisk_item is True:
      self.dealt_with_basilisk = True
    else:
      self.dealt_with_basilisk = False
    return self.dealt_with_basilisk


class Loc2_9_1(QuestArea):
  waypoint_string = None
  possible_to_enter_transitions = ["Highgate"]


class Loc2_9_2(QuestArea):
  multi_layerd_transitions_render_names = ["Supply Hoist"]
  possible_to_enter_transitions = ["The Vastiri Desert"]


class Loc2_9_3(QuestArea):  # The Vastiri Desert, #TODO storm blade quest
  waypoint_string = "2_9_3"

  def extraQuestInLoc(self):
    # "Metadata/QuestObjects/Act9/MummyEventChest"

    return super().extraQuestInLoc()

  def __init__(self) -> None:
    killed_archanid = True
    if killed_archanid is True:
      self.possible_to_enter_transitions.append("The Foothills")
    super().__init__()


class Loc2_9_5(A9QuestArea):  # if basilisk killed, else goto "The Tunnel"
  waypoint_string = "2_9_5"

  def updateGoals(self, force_update=False):
    super().updateGoals(force_update)
    if self.can_open_waypoint is False:
      if self.dealt_with_basilisk is not False:
        self.possible_to_enter_transitions = ["The Tunnel"]
      else:
        self.possible_to_enter_transitions = ["The Boiling Lake"]

  def onWaypointOpenedFunction(self):
    self.updateQuestStatus(force_update=True)
    self.updateGoals()
    return super().onWaypointOpenedFunction()


class Loc2_9_6(A9QuestArea):
  unique_entities_to_kill_render_names = ["The Basilisk"]

  def funcToCallAfterKillingUniqueEntity(self):
    self.possible_to_enter_transitions.append("The Foothills")
    return super().funcToCallAfterKillingUniqueEntity()

  def updateGoals(self, force_update=False):
    super().updateGoals(force_update)
    if self.dealt_with_basilisk is True:
      self.possible_to_enter_transitions.append("The Foothills")


class Loc2_9_7(QuestArea):  # "The Tunnel" #TODO lab
  ready = False
  lab_trial_flag = "MercilessLabyrinthCompletedTunnel"

  def getTransitions(self):
    if self.need_to_do_lab_trial is False:
      self.possible_to_enter_transitions = ["The Quarry"]

  def onLabTrialCompleteFunction(self):
    self.possible_to_enter_transitions = ["The Quarry"]

  def __init__(self) -> None:
    self.getTransitions()
    super().__init__()


class Loc2_9_8(A9QuestArea):  # "The Quarry", #TODO refinery quest logic, panteon boss logic, deliver items logic
  ready = True

  # waypoint_string = None
  def updateGoals(self, force_update=False):
    super().updateGoals(force_update)
    quest_flags = poe_bot.game_data.quest_states.getOrUpdate()
    have_golem_item = quest_flags.get("A9Q1HaveItem1", False)
    if self.can_open_waypoint is False:
      killed_panteon_boss = False
      if have_golem_item is False:
        self.possible_to_enter_transitions.append("The Refinery")
      if killed_panteon_boss is False:
        pass
        # self.bossroom_transitions.append('')
    return


class Loc2_9_10_1(QuestArea):
  ready = True
  possible_to_enter_transitions = ["The Rotting Core"]


class Loc2_9_10_2(QuestArea):
  ready = True
  bossroom_transitions = ["asd"]


# a10
class A10QuestArea(QuestArea):
  vilenta_killed = False

  def updateQuestStatus(self, force_update=False):
    super().updateQuestStatus(force_update)
    self.updateControlBlockBossStatus()

  def updateControlBlockBossStatus(self):
    quest_flags = poe_bot.game_data.quest_states.getOrUpdate()
    self.vilenta_killed = quest_flags.get("A10Q6KilledBoss", False)


class Loc2_10_1(QuestArea):  # #TODO bannon quest
  possible_to_enter_transitions = ["The Ravaged Square"]


class Loc2_10_2(QuestArea):  # The Ravaged Square #TODO get quest status for avarius, bannom tansformation
  waypoint_string = "2_10_2"
  possible_to_enter_transitions = ["The Torched Courts"]

  def __init__(self) -> None:
    super().__init__()
    quest_flags = poe_bot.backend.getQuestFlags()
    control_blocks_done = quest_flags.get("A10Q6KilledBoss", False)
    if control_blocks_done is False:
      self.possible_to_enter_transitions.append("The Control Blocks")
    lab_done = quest_flags.get("MercilessLabyrinthCompletedOssuary", False)
    if lab_done is False:
      self.possible_to_enter_transitions.append("The Ossuary")
    if control_blocks_done and lab_done:
      bannon_transformed = quest_flags.get("A10Q2BannonTransformed", False)
      if bannon_transformed:
        # A10Q3OpenedGate
        input("can go to kitava")


class Loc2_10_3(QuestArea):  # "The Torched Courts"
  possible_to_enter_transitions = ["The Desecrated Chambers"]


class Loc2_10_4(QuestArea):  # The Desecrated Chambers #TODO relog on boss kill, or just go back to square
  waypoint_string = "2_10_4"
  bossroom_transitions = ["Sanctum of Innocence"]
  bossroom_entities_render_names = ["Avarius, Reassembled"]


class Loc2_10_5(QuestArea):  # ridge
  possible_to_enter_transitions = ["The Feeding Trough"]


class Loc2_10_6(QuestArea):  # "The Feeding Trough", #TODO kitava fight
  ready = False


class Loc2_10_7(A10QuestArea):  # control blocks
  waypoint_string = "2_10_7"
  location_name = "The Control Blocks"

  def updateGoals(self, force_update=False):
    super().updateGoals(force_update)
    if self.vilenta_killed is True:
      self.possible_to_enter_transitions = ["The Ravaged Square"]
    else:
      self.bossroom_transitions = ["Arena"]
      self.bossroom_entities_render_names = ["Vilenta"]


class Loc2_10_9(QuestArea):  # the ossuary
  multi_layerd_transitions_render_names = ["The Bone Pits"]
  lab_trial_flag = "MercilessLabyrinthCompletedOssuary"

  def updateGoals(self, force_update=False):
    super().updateGoals(force_update)
    if self.need_to_do_lab_trial is False:
      poe_bot.helper_functions.relog()
      self.possible_to_enter_transitions = ["The Ravaged Square"]

  def doLab(self, lab_enterance: Entity, lab_area):
    poe_bot.mover.goToEntitysPoint(lab_enterance)
    lab_enterance.clickTillNotTargetable()
    furthest_unvisited = poe_bot.pather.utils.getFurthestPoint(start=(lab_enterance.grid_position.x, lab_enterance.grid_position.y), area=lab_area)

    def lookForSwitch(*args, **kwargs):
      switch = next(
        (
          e
          for e in poe_bot.game_data.entities.all_entities
          if e.is_targetable is not False and e.path == "Metadata/Terrain/Labyrinth/Objects/Puzzle_Parts/Switch_Once"
        ),
        None,
      )
      if switch:
        poe_bot.mover.goToEntitysPoint(switch)
        poe_bot.refreshInstanceData()
        switch.clickTillNotTargetable()
      return False

    def lookForPlaque(*args, **kwargs):
      plaque = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/QuestObjects/Labyrinth/LabyrinthTrialPlaque"), None)
      if plaque:
        poe_bot.mover.goToEntitysPoint(plaque, custom_break_function=lookForSwitch)
        while True:
          poe_bot.refreshInstanceData()
          portal = next(
            (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Labyrinth/Objects/LabyrinthTrialReturnPortal"), None
          )
          if portal and portal.is_targetable:
            print("plaque activated")
            poe_bot.ui.closeAll()
            poe_bot.mover.goToEntitysPoint(portal)
            poe_bot.helper_functions.relog()
            poe_bot.mover.enterTransition(portal)
            break
          plaque.click(update_screen_pos=True)
        return True
      return False

    def labExploreFunc(*args, **kwargs):
      lookForSwitch()
      if lookForPlaque() is True:
        return True
      return False

    poe_bot.mover.goToPoint((furthest_unvisited), release_mouse_on_end=False, custom_break_function=labExploreFunc)
    print("lab finished")
    self.onLabTrialCompleteFunction()
    return True

  def onLabTrialCompleteFunction(self):
    poe_bot.helper_functions.relog()
    return super().onLabTrialCompleteFunction()


QUEST_AREAS_BY_KEYS_DICT = {
  # a1
  "1_1_1": Loc1_1_1,
  "1_1_2": Loc1_1_2,
  "1_1_2a": Loc1_1_2a,  # essence
  "1_1_3": Loc1_1_3,
  "1_1_4_1": Loc1_1_4_1,
  "1_1_4_0": Loc1_1_4_0,
  "1_1_5": Loc1_1_5,
  "1_1_6": Loc1_1_6,
  "1_1_7_1": Loc1_1_7_1,  # lower prison  #TODO lab
  "1_1_7_2": Loc1_1_7_2,  # TODO boss fight brutus fight
  "1_1_8": Loc1_1_8,
  "1_1_9": Loc1_1_9,  # TODO fairgraves quest is broken?
  "1_1_9a": Loc1_1_9a,
  "1_1_11_1": Loc1_1_11_1,
  "1_1_11_2": Loc1_1_11_2,  # the cavern of anger #TODO boss fight
  # a2
  "1_2_1": Loc1_2_1,
  "1_2_2": Loc1_2_2,
  "1_2_2a": Loc1_2_2a,  # beast transition or killing is broken
  "1_2_3": Loc1_2_3,  # crossroads
  "1_2_4": Loc1_2_4,  # loc with kraytlin bandit
  "1_2_15": Loc1_2_15,
  "1_2_5_1": Loc1_2_5_1,  # crypt lvl 1 # TODO lab
  "1_2_5_2": Loc1_2_5_2,  # crypt lvl 2 # go back if hand taken
  "1_2_6_1": Loc1_2_6_1,
  "1_2_6_2": Loc1_2_6_2,  # chamber of sins lvl 2 # TODO lab
  "1_2_7": Loc1_2_7,
  "1_2_9": Loc1_2_9,  # western forest
  "1_2_10": Loc1_2_10,  # weaver's chamber #TODO boss fight
  "1_2_12": Loc1_2_12,  # the wetlands #TODO bandit quest
  "1_2_11": Loc1_2_11,  # vaal ruins
  "1_2_8": Loc1_2_8,  # Northern forest
  "1_2_14_2": Loc1_2_14_2,  # the caverns
  "1_2_14_3": Loc1_2_14_3,  # vaal temple, multi layerd + boss fight
  # a3
  "1_3_1": Loc1_3_1,  # girl saved, kill guard, talk to girl, go to town
  "1_3_2": Loc1_3_2,  # the slums
  "1_3_3_1": Loc1_3_3_1,  # the slums
  "1_3_10_1": Loc1_3_10_1,  # the sewers
  "1_3_5": Loc1_3_5,  # the marketplace
  "1_3_6": Loc1_3_6,  # the catacombs
  "1_3_7": Loc1_3_7,  # the battlefront
  "1_3_9": Loc1_3_9,  # the docks
  "1_3_8_1": Loc1_3_8_1,  # the solaris lvl1
  "1_3_8_2": Loc1_3_8_2,  # the solaris lvl2
  "1_3_13": Loc1_3_13,  # the ebony barracks
  "1_3_14_1": Loc1_3_14_1,  # lunaris 1
  "1_3_14_2": Loc1_3_14_2,  # lunaris 2
  "1_3_15": Loc1_3_15,  # lunaris 2
  "1_3_18_1": Loc1_3_18_1,  # sceptre of god
  "1_3_18_2": Loc1_3_18_2,  # upper sceptre of the god
  # a4
  "1_4_1": Loc1_4_1,  # aqueduct
  "1_4_2": Loc1_4_2,  # dried lake
  "1_4_3_1": Loc1_4_3_1,  # mines lvl 1
  "1_4_3_2": Loc1_4_3_2,  # mines lvl 2
  "1_4_3_3": Loc1_4_3_3,  # crystal veins
  "1_4_4_1": Loc1_4_4_1,  # kaom's dream
  "1_4_4_3": Loc1_4_4_3,  # kaom's stronghold
  "1_4_7": Loc1_4_7,  # lunaris 2
  "1_4_6_1": Loc1_4_6_1,  # belly of the beast 1
  "1_4_6_2": Loc1_4_6_2,  # belly of the beast 2
  # a5
  "1_5_1": Loc1_5_1,
  "1_5_2": Loc1_5_2,
  "1_5_3": Loc1_5_3,
  "1_5_4": Loc1_5_4,
  "1_5_5": Loc1_5_5,
  "1_5_6": Loc1_5_6,
  "1_5_4b": Loc1_5_4b,
  "1_5_3b": Loc1_5_3b,
  "1_5_7": Loc1_5_7,
  "1_5_8": Loc1_5_8,
  # a6
  "2_6_2": Loc2_6_2,
  "2_6_4": Loc2_6_4,
  "2_6_5": Loc2_6_5,
  "2_6_6": Loc2_6_6,
  "2_6_7_1": Loc2_6_7_1,
  "2_6_7_2": Loc2_6_7_2,  # multi layerd + tower bossroom
  "2_6_8": Loc2_6_8,
  "2_6_9": Loc2_6_9,
  "2_6_10": Loc2_6_10,
  "2_6_11": Loc2_6_11,  # bossfight puppet
  "2_6_12": Loc2_6_12,
  "2_6_13": Loc2_6_13,
  "2_6_14": Loc2_6_14,  # beacon, follow the lantern quest, activate beacon, goto the boat guy
  "2_6_15": Loc2_6_15,
  # a7
  "2_7_1": Loc2_7_1,
  "2_7_2": Loc2_7_2,
  "2_7_3": Loc2_7_3,
  "2_7_4": Loc2_7_4,  # multi layered, layer 1, do lab, layer 2, pcik map
  "2_7_5_1": Loc2_7_5_1,
  "2_7_5_2": Loc2_7_5_2,
  "2_7_6": Loc2_7_6,
  "2_7_7": Loc2_7_7,
  "2_7_8": Loc2_7_8,
  "2_7_9": Loc2_7_9,
  "2_7_10": Loc2_7_10,
  "2_7_11": Loc2_7_11,
  "2_7_12_1": Loc2_7_12_1,
  "2_7_12_2": Loc2_7_12_2,
  # a8
  "2_8_2_1": Loc2_8_2_1,
  # "2_8_2_2": Loc2_8_2_2,
  "2_8_1": Loc2_8_1,
  "2_8_10": Loc2_8_10,
  "2_8_12_1": Loc2_8_12_1,
  "2_8_12_2": Loc2_8_12_2,
  "2_8_3": Loc2_8_3,
  "2_8_5": Loc2_8_5,  # bath house
  "2_8_4": Loc2_8_4,
  "2_8_6": Loc2_8_6,
  "2_8_7_1_": Loc2_8_7_1_,
  "2_8_7_2": Loc2_8_7_2,
  "2_8_8": Loc2_8_8,
  "2_8_9": Loc2_8_9,
  # a9
  "2_9_1": Loc2_9_1,
  "2_9_2": Loc2_9_2,
  "2_9_3": Loc2_9_3,
  "2_9_5": Loc2_9_5,
  "2_9_6": Loc2_9_6,
  "2_9_10_1": Loc2_9_10_1,
  "2_10_1": Loc2_10_1,
  "2_10_2": Loc2_10_2,
  "2_10_3": Loc2_10_3,
  "2_10_4": Loc2_10_4,
  "2_10_5": Loc2_10_5,
  "2_10_7": Loc2_10_7,
  "2_10_9": Loc2_10_9,
  # a10
  # bannon
  # ravaged square, waypoing
  # ossunari, lab
  # cathedral, kill innocence
  # control blocks
  # ravaged square check if control blocks, lab, banner
  # goto kitava
  # kill kitava boss
}


def getQuestArea(area_raw_name: str) -> QuestArea:
  area_class = QUEST_AREAS_BY_KEYS_DICT.get(area_raw_name, None)
  print(f"current area raw name {area_raw_name}")
  if area_class is None:
    raise Exception(f"{area_raw_name} current area isn't supported")
  else:
    area_object = area_class()
    return area_object


# In[ ]:


poe_bot.refreshInstanceData()
current_quest_area = getQuestArea(poe_bot.game_data.area_raw_name)
current_quest_area.complete()


# In[ ]:


raise Exception("Script ended, restart")


# In[ ]:


next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Trial of Ascendancy"), None)


# In[ ]:


current_quest_area.need_to_do_lab_trial


# In[ ]:


poe_bot.refreshAll()
poe_bot.game_data.terrain.getCurrentlyPassableArea()
poe_bot.game_data.player.buffs


# In[ ]:


fairgraves_npc = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/NPC/Act1/Fairgraves"), None)
npc_pos_x, npc_pos_y = fairgraves_npc.grid_position.x, fairgraves_npc.grid_position.y
poe_bot.mover.goToPoint(
  point=(npc_pos_x, npc_pos_y),
  release_mouse_on_end=False,
  custom_continue_function=poe_bot.combat_module.build.usualRoutine,
)

while True:
  fairgraves_npc = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/NPC/Act1/Fairgraves"), None)
  if fairgraves_npc is None:
    break
  print(f"fairgraves_npc {fairgraves_npc.raw}")
  fairgraves_npc.click()
  poe_bot.refreshInstanceData()
  poe_bot.ui.closeAll()


while True:
  poe_bot.refreshInstanceData()
  poe_bot.combat_module.clearLocationAroundPoint({"X": npc_pos_x, "Y": npc_pos_y})

  fairgraves_skeleton = next(
    (
      e
      for e in poe_bot.game_data.entities.all_entities
      if e.animated_property_metadata == "Metadata/Monsters/Skeletons/Skeleton/SkeletonFairGraves.ao"
    ),
    None,
  )
  if fairgraves_skeleton:
    if fairgraves_skeleton.life.health.current == 0:
      break
    elif fairgraves_skeleton.is_attackable is True:
      poe_bot.combat_module.killUsualEntity(fairgraves_skeleton)


# In[ ]:


boss_transition = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "The Warden's Quarters"), None)
curr_pos_x, curr_pos_y = poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y
if boss_transition:
  entered = False
  if "grace_period" in poe_bot.game_data.player.buffs:
    while entered is False:
      print("nearby bossroom, but seems like just resurected")
      boss_transition.click()
      time.sleep(1)
      poe_bot.refreshInstanceData()
      new_curr_pos_x, new_curr_pos_y = poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y
      distance_to_enterance = dist((curr_pos_x, curr_pos_y), (new_curr_pos_x, new_curr_pos_y))
      print(f"distance {distance_to_enterance}")
      if distance_to_enterance > 100:
        print("")
        poe_bot.game_data.terrain.getCurrentlyPassableArea()
        break


# In[ ]:


poe_bot.ui.inventory.update()
list(map(lambda i: i.raw, poe_bot.ui.inventory.items))
any(list(map(lambda item: "Metadata/Items/QuestItems/TowerKey" == item.render_path, poe_bot.ui.inventory.items)))


# In[ ]:


list(map(lambda item: item.render_path, poe_bot.ui.inventory.items))


# In[ ]:





# In[ ]:


current_quest_area.can_open_poison_roots


# In[ ]:


quest_states = poe_bot.backend.getQuestStates()
quest_state = next((i for i in quest_states if i["id"] == "a1q6"), None)["state"]
quest_state


# In[ ]:


current_quest_area = getQuestArea(poe_bot.game_data.area_raw_name)


# In[ ]:


current_quest_area.isNeedToDoLabTrial()


# In[ ]:


poe_bot.refreshAll()
poe_bot.game_data.terrain.getCurrentlyPassableArea()
print(poe_bot.game_data.area_raw_name)
poe_bot.refreshInstanceData()
pickable_items = poe_bot.loot_picker.loot_filter.getPickableItems()
plt.imshow(poe_bot.game_data.terrain.currently_passable_area)
pickable_items


# In[ ]:


quest_flags = poe_bot.backend.getQuestFlags()
quest_flags["NormalLabyrinthCompletedSins"]


# In[ ]:


quest_flags["NormalLabyrinthCompletedSins"]


# In[ ]:


next((e for e in poe_bot.game_data.entities.area_transitions if e.render_name == "The Weaver's Nest"), None)


# In[ ]:


poe_bot.ui.inventory.update()
need_kill_bandit = not any(list(map(lambda item: item.render_path == "Art/2DItems/QuestItems/TriangleKey2.dds", poe_bot.ui.inventory.items)))


# In[ ]:


poe_bot.ui.bandit_dialogue.update()


# In[ ]:


poe_bot.refreshInstanceData()


# In[ ]:


quest_states = poe_bot.backend.getQuestStates()
quest_state = next((i for i in quest_states if i["id"] == "a2q11"), None)["state"]
quest_state


# In[ ]:


bandit_name = "Alira"
bandit = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == bandit_name), None)
if bandit:
  data_raw = poe_bot.ui.bandit_dialogue.update()
  bandit_ui_visible = data_raw["v"] != 0
  while bandit_ui_visible is False:
    data_raw = poe_bot.ui.bandit_dialogue.update()
    bandit = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == bandit_name), None)
    if bandit:
      bandit.click()
      data_raw = poe_bot.ui.bandit_dialogue.update()
      bandit_ui_visible = data_raw["v"] != 0
      poe_bot.ui.closeAll()
      poe_bot.refreshInstanceData()

  kill_button_pos = (int((data_raw["k_sz"][0] + data_raw["k_sz"][1]) / 2), int((data_raw["k_sz"][2] + data_raw["k_sz"][3]) / 2))
  pos_x, pos_y = poe_bot.convertPosXY(kill_button_pos[0], kill_button_pos[1], safe=False)
  for i in range(random.randint(2, 4)):
    poe_bot.bot_controls.mouseClick(pos_x, pos_y)

  while True:
    bandit = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == bandit_name), None)
    if bandit and bandit.life.health.current != 0:
      poe_bot.combat_module.killUsualEntity(bandit)
    else:
      break


# In[ ]:


fairgraves_npc = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/NPC/Act1/Fairgraves"), None)
npc_pos_x, npc_pos_y = fairgraves_npc.grid_position.x, fairgraves_npc.grid_position.y
poe_bot.mover.goToPoint(
  point=(npc_pos_x, npc_pos_y),
  release_mouse_on_end=False,
  custom_continue_function=poe_bot.combat_module.build.usualRoutine,
)

while True:
  fairgraves_npc = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/NPC/Act1/Fairgraves"), None)
  if fairgraves_npc is None:
    break
  fairgraves_npc.click()
  poe_bot.refreshInstanceData()
  poe_bot.ui.closeAll()


while True:
  poe_bot.refreshInstanceData()
  poe_bot.combat_module.clearLocationAroundPoint({"X": npc_pos_x, "Y": npc_pos_y})

  fairgraves_skeleton = next(
    (
      e
      for e in poe_bot.game_data.entities.all_entities
      if e.animated_property_metadata == "Metadata/Monsters/Skeletons/Skeleton/SkeletonFairGraves.ao"
    ),
    None,
  )
  if fairgraves_skeleton:
    if fairgraves_skeleton.life.health.current == 0:
      break
    elif fairgraves_skeleton.is_attackable is True:
      poe_bot.combat_module.killUsualEntity(fairgraves_skeleton)


# In[ ]:


quest_states = poe_bot.backend.getQuestStates()
quest_state = next((i for i in quest_states if i["id"] == "a1q5"), None)["state"]
if quest_state < 5:
  print(quest_state)


# In[ ]:


plt.imshow(poe_bot.game_data.terrain.terrain_image)
plt.show()

plt.imshow(poe_bot.game_data.terrain.currently_passable_area)
plt.show()


# In[ ]:


plt.imshow(poe_bot.game_data.terrain.passable)
plt.show()


# In[ ]:


poe_bot.ui.inventory.update()
any(list(map(lambda item: item.render_path == "Art/2DItems/QuestItems/PoisonSpear.dds", poe_bot.ui.inventory.items)))
for item in poe_bot.ui.inventory.items:
  print(item.raw)


# In[ ]:


poe_bot.refreshInstanceData()


# In[ ]:


discovery_points = list(filter(lambda point: poe_bot.game_data.terrain.checkIfPointPassable(point[0], point[1]), discovery_points))


# In[ ]:


game_img = poe_bot.getImage()
print("game_img")
plt.imshow(game_img)
plt.show()


# In[ ]:


raise 404


# In[ ]:





# In[ ]:


raise 404


# In[ ]:


class A1PrisonLabTrial:
  def complete(self):
    "Metadata/Terrain/Labyrinth/Objects/Puzzle_Parts/Switch_Once"
    "Metadata/Terrain/Labyrinth/Objects/Puzzle_Parts/Door_Closed"
    "Metadata/QuestObjects/Labyrinth/LabyrinthTrialPlaque"
    "Metadata/Terrain/Labyrinth/Objects/LabyrinthTrialReturnPortal"
    pass


class A2Cryptlevel1LabTrial:
  def complete(self):
    "Metadata/Terrain/Labyrinth/Objects/Puzzle_Parts/Switch_Once"
    "Metadata/Terrain/Labyrinth/Objects/Puzzle_Parts/Door_Closed"
    "Metadata/QuestObjects/Labyrinth/LabyrinthTrialPlaque"
    "Metadata/Terrain/Labyrinth/Objects/LabyrinthTrialReturnPortal"
    pass


# In[ ]:


class Loc(QuestArea):
  def complete(self):
    return super().complete()


# In[ ]:


poe_bot.loot_picker.loot_filter.special_rules[0]


# In[ ]:


poe_bot.loot_picker.loot_filter.special_rules


# In[ ]:


from inspect import signature

sig = signature(poe_bot.loot_picker.loot_filter.special_rules[0])
str(sig)


# In[ ]:


poe_bot.refreshAll()


# In[ ]:


from utils.pathing import TSP

tsp = TSP(poe_bot=poe_bot)
tsp.generatePointsForDiscovery()
mover = poe_bot.mover
map_complete = False
while map_complete is False:
  poe_bot.refreshInstanceData()
  print("generating pathing points")
  discovery_points = tsp.sortedPointsForDiscovery()
  print(f"len(discovery_points) {len(discovery_points)}")
  discovery_points = list(filter(lambda p: poe_bot.helper_functions.checkIfEntityOnCurrenctlyPassableArea(p[0], p[1]), discovery_points))
  print(f"len(discovery_points) {len(discovery_points)} after sorting")
  if len(discovery_points) == 0:
    print("len(discovery_points) == 0 after points generation")
    map_complete = True
    break
  point_to_go = discovery_points.pop(0)
  while point_to_go is not None:
    # check if point needs to be explored
    # need_to_explore = needToExplore(point_to_go=point_to_go)
    need_to_explore = True

    if need_to_explore is True:
      print(f"exploring point {point_to_go}")
    else:
      print(f"surrounding around {point_to_go} discovered, skipping")
      try:
        point_to_go = discovery_points.pop(0)
      except:
        point_to_go = None
      continue

    # go to point to make it explored
    result = mover.goToPoint(
      point=point_to_go,
      min_distance=50,
      release_mouse_on_end=False,
      # custom_break_function=mapper.exploreRoutine,
      custom_continue_function=build.usualRoutine,
      step_size=random.randint(30, 35),
    )
    # then, it result is True, False or None
    print(f"mover.goToPoint result {result}")

    # if we arrived to discovery point and nothing happened
    if result is None:
      while True:
        if len(discovery_points) == 0:
          point_to_go = None
          map_complete = True
          print("len(discovery_points) == 0, breaking")
          break

        point_to_go = discovery_points.pop(0)
        print(f"willing to explore next point {point_to_go}")
        need_to_explore = poe_bot.helper_functions.needToExplore(point_to_go=point_to_go)

        if need_to_explore is True:
          print(f"exploring point {point_to_go}")
          break
        else:
          print(f"surrounding around {point_to_go} discovered, skipping")
          continue

    poe_bot.refreshInstanceData()
    poe_bot.last_action_time = 0
  # if possible_transition to explore, go to it, run discovery again


# In[ ]:


prev_waypoint_state = poe_bot.backend.getWaypointState()


# In[ ]:


new_waypoint_state = poe_bot.backend.getWaypointState()
for waypoint_state_index in range(len(new_waypoint_state)):
  new_state = new_waypoint_state[waypoint_state_index]
  prev_state = prev_waypoint_state[waypoint_state_index]
  if new_state != prev_state:
    print(f"waypoint_state_index {waypoint_state_index}, {poe_bot.game_data.area_raw_name}")


# In[ ]:


# fairgraives quest after book is used
# quest_state_index a1q6, prev: 3 new: 0

# ???
# quest_state_index a1q2, prev: 1 new: 0

# A2
# baleful gem quest greust
# quest_state_index a2q6, prev: 4 new: 0
# silk baleful gem?
# quest_state_index a2q11, prev: 8 new: 4

# beast quest?


# In[ ]:


prev_quest_states = poe_bot.backend.getQuestStates()


# In[ ]:


new_quest_state = poe_bot.backend.getQuestStates()
for quest_state_index in range(len(new_quest_state)):
  quest_id = new_quest_state[quest_state_index]["id"]
  new_state = new_quest_state[quest_state_index]["state"]
  prev_state = prev_quest_states[quest_state_index]["state"]
  if new_state != prev_state:
    print(f"quest_state_index {quest_id}, prev: {prev_state} new: {new_state}")


# In[ ]:


new_quest_state = poe_bot.backend.getQuestStates()
for quest_state_index in range(len(new_quest_state)):
  quest_id = new_quest_state[quest_state_index]["id"]
  new_state = new_quest_state[quest_state_index]["state"]
  prev_state = prev_quest_states[quest_state_index]["state"]
  if new_state != prev_state:
    print(f"quest_state_index {quest_id}, prev: {prev_state} new: {new_state}")


# In[ ]:


game_img = poe_bot.getImage()
print("game_img")
plt.imshow(game_img)
plt.show()


# In[ ]:


import random

SESSION_24h_6h_sleep = []  # [3.4, 6]
total_play_time = 16
total_sleep_time = 8
for c in range(1):
  play_time = random.randint(25, 43) / 10  # 3.4
  sleep_time = random.randint(50, 70) / 10
  total_play_time -= play_time
  total_sleep_time -= sleep_time
  SESSION_24h_6h_sleep.append(play_time)
  SESSION_24h_6h_sleep.append(sleep_time)
for c in range(4):
  play_time = random.randint(25, 43) / 10  # 3.4
  sleep_time = random.randint(20, 100) / 100  # 0.6
  total_play_time -= play_time
  total_sleep_time -= sleep_time
  SESSION_24h_6h_sleep.append(play_time)
  SESSION_24h_6h_sleep.append(sleep_time)


if total_play_time < 0:
  exceed_amount_total = total_play_time
  exceed_amount_per_session = exceed_amount_total / 5
  play_time_indexes = range(0, len(SESSION_24h_6h_sleep), 2)
  for play_time_index in play_time_indexes:
    SESSION_24h_6h_sleep[play_time_index] += exceed_amount_per_session
    SESSION_24h_6h_sleep[play_time_index] = round(SESSION_24h_6h_sleep[play_time_index], 2)
if total_sleep_time < 0:
  exceed_amount_total = total_sleep_time
  exceed_amount_per_session = exceed_amount_total / 5
  sleep_time_indexes = range(1, len(SESSION_24h_6h_sleep) + 1, 2)
  for sleep_time_index in sleep_time_indexes:
    SESSION_24h_6h_sleep[sleep_time_index] += exceed_amount_per_session
    SESSION_24h_6h_sleep[sleep_time_index] = round(SESSION_24h_6h_sleep[sleep_time_index], 2)

SESSION_24h_6h_sleep


# In[ ]:


poe_bot.refreshInstanceData()
lab_enterance = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Trial of Ascendancy"), None)
if lab_enterance:
  copy_of = poe_bot.game_data.terrain.passable.copy()
  # plt.imshow(copy_of);plt.show()
  copy_of_currently_passable_area = poe_bot.game_data.terrain.currently_passable_area.copy()
  area_ = 15
  copy_of[
    lab_enterance.grid_position.y - area_ : lab_enterance.grid_position.y + area_,
    lab_enterance.grid_position.x - area_ : lab_enterance.grid_position.x + area_,
  ] = 0
  poe_bot.game_data.terrain.passable = copy_of
  poe_bot.game_data.terrain.getCurrentlyPassableArea()
  lab_area = copy_of_currently_passable_area - poe_bot.game_data.terrain.currently_passable_area
  plt.imshow(lab_area)


# In[ ]:


poe_bot.refreshAll()
poe_bot.game_data.terrain.getCurrentlyPassableArea()


# In[ ]:


poe_bot.ui.inventory.update()


# In[ ]:


lab_enterance = next((e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Act5/Area6/Objects/Ossuary_HiddenDoor"), None)


# In[ ]:


lab_enterance = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Trial of Ascendancy"), None)


# In[ ]:


lab_enterance


# In[80]:


poe_bot.refreshInstanceData()


# In[ ]:


poe_bot.refreshInstanceData()
if lab_enterance:
  copy_of = poe_bot.game_data.terrain.passable.copy()
  copy_of_currently_passable_area = poe_bot.game_data.terrain.currently_passable_area.copy()

  # plt.imshow(copy_of);plt.show()
  # plt.imshow(copy_of_currently_passable_area);plt.show()
  # area_ = 40
  # plt.imshow(copy_of[lab_enterance.grid_position.y-area_:lab_enterance.grid_position.y+area_, lab_enterance.grid_position.x-area_:lab_enterance.grid_position.x+area_]);plt.show()
  # plt.imshow(copy_of_currently_passable_area[lab_enterance.grid_position.y-area_:lab_enterance.grid_position.y+area_, lab_enterance.grid_position.x-area_:lab_enterance.grid_position.x+area_]);plt.show()

  entrance_pos_x, entrance_pos_y = lab_enterance.grid_position.x, lab_enterance.grid_position.y
  entrance_pos_x_orig, entrance_pos_y_orig = lab_enterance.grid_position.x, lab_enterance.grid_position.y
  limit_lower = 0
  limit_upper = 0
  broken_axis = None
  while True:
    entrance_pos_x += 1
    if copy_of[entrance_pos_y_orig, entrance_pos_x] != 1:
      print("broke x")
      broken_axis = "x"
      limit_upper = entrance_pos_x
      entrance_pos_x = entrance_pos_x_orig
      while copy_of[entrance_pos_y_orig, entrance_pos_x] == 1:
        entrance_pos_x -= 1
      limit_lower = entrance_pos_x
      break

    entrance_pos_y += 1
    if copy_of[entrance_pos_y, entrance_pos_x_orig] != 1:
      print("broke y")
      broken_axis = "y"
      limit_upper = entrance_pos_y
      entrance_pos_y = entrance_pos_y_orig
      while copy_of[entrance_pos_y, entrance_pos_x_orig] == 1:
        entrance_pos_y -= 1
      limit_lower = entrance_pos_y
      break
  limit_lower -= 1
  limit_upper += 1
  print(f"lower upper {limit_lower, limit_upper}")
  axis_length = 5
  if broken_axis == "y":
    copy_of[limit_lower:limit_upper, entrance_pos_x_orig - axis_length : entrance_pos_x_orig + axis_length] = 0  # y1 y2 x1 x2
  else:
    copy_of[entrance_pos_y_orig - axis_length : entrance_pos_y_orig + axis_length, limit_lower:limit_upper] = 0  # y1 y2 x1 x2

  poe_bot.game_data.terrain.passable = copy_of
  poe_bot.game_data.terrain.getCurrentlyPassableArea()
  lab_area = copy_of_currently_passable_area - poe_bot.game_data.terrain.currently_passable_area

area_ = 5
copy_of[
  lab_enterance.grid_position.y - area_ : lab_enterance.grid_position.y + area_,
  lab_enterance.grid_position.x - area_ : lab_enterance.grid_position.x + area_,
]


# In[ ]:


area_ = 10
print(
  poe_bot.game_data.terrain.passable[
    lab_enterance.grid_position.y - area_ : lab_enterance.grid_position.y + area_,
    lab_enterance.grid_position.x - area_ : lab_enterance.grid_position.x + area_,
  ]
)


# In[ ]:


print(
  copy_of[
    lab_enterance.grid_position.y - area_ : lab_enterance.grid_position.y + area_,
    lab_enterance.grid_position.x - area_ : lab_enterance.grid_position.x + area_,
  ]
)


# In[ ]:


print(
  poe_bot.game_data.terrain.currently_passable_area[
    lab_enterance.grid_position.y - area_ : lab_enterance.grid_position.y + area_,
    lab_enterance.grid_position.x - area_ : lab_enterance.grid_position.x + area_,
  ]
)


# In[ ]:


plt.imshow(poe_bot.game_data.terrain.passable)


# In[ ]:


plt.imshow(poe_bot.game_data.terrain.currently_passable_area)


# In[ ]:


poe_bot.ui.inventory.update()


# In[ ]:


poe_bot.refreshAll()
plt.imshow(poe_bot.game_data.terrain.passable)
plt.show()


# In[ ]:


poe_bot.refreshInstanceData()
grid_pos_to_go_y, grid_pos_to_go_x = (1, 1200)
path = poe_bot.pather.generatePath(
  (int(poe_bot.game_data.player.grid_pos.y), int(poe_bot.game_data.player.grid_pos.x)), (grid_pos_to_go_y, grid_pos_to_go_x)
)


# In[ ]:


import numpy as np

empty_arr = np.zeros_like(poe_bot.game_data.terrain.passable)
for point in path:
  empty_arr[point[0], point[1]] = 1
plt.imshow(poe_bot.game_data.terrain.passable)
plt.show()
plt.imshow(empty_arr)
plt.show()


# In[ ]:


poe_bot.refreshInstanceData()
step_size = 35
point = poe_bot.pather.cropPath(
  path,
  int(step_size * 1.7),
  step_size,
  current_pos_x=int(poe_bot.game_data.player.grid_pos.x),
  current_pos_y=int(poe_bot.game_data.player.grid_pos.y),
  max_path_length=int(step_size * 1.5),
)
if point != []:
  area = 25
  pos_x = point[0][1]
  pos_y = point[0][0]
  passable_copy = poe_bot.game_data.terrain.passable.copy()
  point_area = 3
  passable_copy[pos_y - point_area : pos_y + point_area, pos_x - point_area : pos_x + point_area] = 0
  plt.imshow(passable_copy[pos_y - area : pos_y + area, pos_x - area : pos_x + area])
  plt.show()
  plt.imshow(poe_bot.game_data.terrain.passable[pos_y - area : pos_y + area, pos_x - area : pos_x + area])
  plt.show()


# In[ ]:


poe_bot.convertPosXY(575, 900)


# In[ ]:


poe_bot.helper_functions.relog()


# In[ ]:


for i in range(10):
  poe_bot.bot_controls.mouse.setPosSmooth(100, 100, False)
  print(time.time())


# In[ ]:


action = "action=mouseSetCursorPosSmooth&x=100&y=100&mtm=-1&msm=1&wtr=1&"
len(action.split("wtr=1&")) != 1


# In[ ]:


poe_bot.bot_controls.getScreen()


# In[ ]:


plt.imshow(poe_bot.game_data.terrain.terrain_image)


# In[19]:


poe_bot.bot_controls.disconnect()


# In[ ]:


poe_bot.refreshAll()
plt.imshow(poe_bot.game_data.terrain.terrain_image)


# In[14]:


action_msg = "action=getFullScreen"


# In[ ]:


action_msg = "action=getFullScreen"
data = poe_bot.bot_controls.sendCommand(command=action_msg, wait_till_recieved=False, recv_buffer_size=5308581 * 2)


# In[ ]:


poe_bot.bot_controls.s.send(action_msg.encode())


# In[ ]:


data = poe_bot.bot_controls.s.recv(53085581 * 2)
len(data)


# In[ ]:


len(data)


# In[ ]:


import pickle

img = pickle.loads(data)


# In[10]:


inventory.update()
items_to_click = inventory.items


# In[ ]:


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


def getItemVal(item):
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
for item in items:
  print(item.raw)


# In[ ]:


dialla_entity = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Lady Dialla"), None)
dialla_entity.click(update_screen_pos=True)


# In[13]:


from utils.ui import Item


# In[ ]:


poe_bot.ui.npc_dialogue.update()


# In[ ]:


refreshed_data = poe_bot.backend.getNpcDialogueUi()
print(refreshed_data)


# In[ ]:


item = Item(poe_bot=poe_bot, item_raw=refreshed_data["rw"][0])

items = list(map(lambda i_raw: Item(poe_bot=poe_bot, item_raw=i_raw), refreshed_data["rw"]))


# In[ ]:


items[0].render_path


# In[ ]:


item.getScreenPos()
item.click(hold_ctrl=True)


# In[ ]:





# In[ ]:


dialla_entity.click(update_screen_pos=True)


# In[11]:


poe_bot.bot_controls.disconnect()


# In[ ]:


weylam = next(
  (e for e in poe_bot.game_data.entities.all_entities if e.is_targetable is not False and e.path == "Metadata/NPC/Act6/WeylamBeacon"), None
)


# In[ ]:


# poe_bot.mover.goToEntitysPoint(weylam, release_mouse_on_end=True)
# while True:
#   weylam.click(update_screen_pos=True)
#   poe_bot.refreshInstanceData()
#   time.sleep(random.randint(4,7)/10)
#   poe_bot.ui.npc_dialogue.update()
#   if poe_bot.ui.npc_dialogue.visible == True:
#     break
poe_bot.ui.npc_dialogue.update()
while poe_bot.ui.npc_dialogue.visible is False or poe_bot.ui.npc_dialogue.text is not None:
  weylam.click(update_screen_pos=True)
  poe_bot.refreshInstanceData()
  time.sleep(random.randint(3, 6) / 10)
  poe_bot.ui.npc_dialogue.update()
  if poe_bot.ui.npc_dialogue.visible is True and poe_bot.ui.npc_dialogue.text is not None:
    poe_bot.ui.closeAll()
    time.sleep(random.randint(2, 4) / 10)


# In[22]:


next((ch for ch in poe_bot.ui.npc_dialogue.choices if ch.text == "Sail to the Brine King's Reef")).click()


# In[ ]:


poe_bot.ui.npc_dialogue is False


# In[21]:


poe_bot.ui.npc_dialogue.visible
poe_bot.ui.npc_dialogue.raw

