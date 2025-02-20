#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import random
import sys
import time
from ast import literal_eval

import matplotlib.pyplot as plt
from utils.components import UiElement
from utils.gamehelper import Entity, Poe2Bot
from utils.temps import SimulacrumCache2
from utils.utils import createLineIteratorWithValues, getFourPoints


# In[ ]:


# readabilty
poe_bot: Poe2Bot

notebook_dev = False


# In[ ]:


default_config = {
  "REMOTE_IP": "172.17.91.193",  # z2
  "unique_id": "poe_2_test",
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
  config[key] = parsed_config.get(key, default_config[key])

print(f"config to run {config}")

REMOTE_IP = config["REMOTE_IP"]  # REMOTE_IP
UNIQUE_ID = config["unique_id"]  # unique id
force_reset_temp = config["force_reset_temp"]
print(f"running simulacrum using: REMOTE_IP: {REMOTE_IP} unique_id: {UNIQUE_ID} force_reset_temp: {force_reset_temp}")


# In[ ]:


poe_bot = Poe2Bot(unique_id=UNIQUE_ID, remote_ip=REMOTE_IP)
poe_bot.refreshAll()
# poe_bot.game_data.terrain.getCurrentlyPassableArea()
# TODO move it to poe_bot.refreshAll() refreshed_data["c_t"] ## "c_t":0 - mouse || "c_t":1 - wasd
poe_bot.mover.setMoveType("wasd")


# In[ ]:


from utils.utils import createLineIteratorWithValues


# In[ ]:


from utils.combat import BarrierInvocationInfernalist, InfernalistZoomancer

if "demon_transformation" in poe_bot.game_data.skills.internal_names:
  print("barrier build")
  poe_bot.combat_module.build = BarrierInvocationInfernalist(poe_bot)

else:
  print("minions build")
  poe_bot.combat_module.build = InfernalistZoomancer(poe_bot, can_kite=False)

min_stacks_for_wave_11_plus = 60
reset_form_before_waves = [9]
max_stacks_for_wave_11_plus = 400


# In[7]:


# default mover function
poe_bot.mover.default_continue_function = poe_bot.combat_module.build.usualRoutine


# In[ ]:


# set up loot filter
from utils.loot_filter import PickableItemLabel

ARTS_TO_PICK = [
  "Art/2DItems/Currency/CurrencyModValues.dds",  # divine https://poe2db.tw/us/Divine_Orb - icon
  "Art/2DItems/Currency/CurrencyGemQuality.dds",  # gemcutter
  "Art/2DItems/Currency/CurrencyRerollRare.dds",  # chaos
  "Art/2DItems/Currency/CurrencyAddModToRare.dds",  # exalt
  "Art/2DItems/Currency/CurrencyUpgradeToUnique.dds",  # chance
]

# # big piles of gold
# for tier in range(2,17):
#   ARTS_TO_PICK.append(f"Art/2DItems/Currency/Ruthless/CoinPileTier{tier}.dds")
# # waystones
# for tier in range(13,17):
#   ARTS_TO_PICK.append(f"Art/2DItems/Maps/EndgameMaps/EndgameMap{tier}.dds")

# "Art/2DItems/Currency/Essence/GreaterFireEssence.dds"

WHITE_BASES_TO_PICK = ["Art/2DItems/Amulets/Basetypes/StellarAmulet.dds", "Art/2DItems/Rings/Basetypes/SapphireRing.dds"]


def isItemHasPickableKey(item_label: PickableItemLabel):
  if item_label.icon_render in ARTS_TO_PICK:
    return True
  elif "Art/2DItems/Currency/Essence/" in item_label.icon_render:
    return True
  elif "Art/2DItems/Currency/DistilledEmotions" in item_label.icon_render:
    return True
  elif "Art/2DItems/Flasks/Uniques/MeltingMaelstrom" in item_label.icon_render:
    print("flaaaaaaaaask")
    return True
  elif item_label.rarity == "Normal" and item_label.icon_render in WHITE_BASES_TO_PICK:
    return True
  elif item_label.displayed_name == "Uncut Skill Gem (Level 20)" or item_label == "Uncut Spirit Gem (Level 20)":
    return True
  return False


ARTS_TO_PICK.append("Art/2DItems/Currency/CurrencyUpgradeToRare.dds")
ARTS_TO_PICK.append("Art/2DItems/Currency/CurrencyDuplicate.dds")
ARTS_TO_PICK.append("Art/2DItems/Currency/CurrencyVaal.dds")  # Mirror of Calandra
ARTS_TO_PICK.append("Art/2DItems/Currency/AnnullOrb.dds")
ARTS_TO_PICK.append("Art/2DItems/Currency/CurrencyRerollSocketNumbers02.dds")  #    Greater Jeweller's Orb
ARTS_TO_PICK.append("Art/2DItems/Currency/CurrencyRerollSocketNumbers03.dds")  #    Perfect Jeweller's Orb
ARTS_TO_PICK.append("Art/2DItems/Currency/CurrencyWeaponMagicQuality.dds")  #    Arcanist's Etcher
ARTS_TO_PICK.append("Art/2DItems/Currency/CurrencyUpgradeToUniqueShard.dds")  # Chance shard
ARTS_TO_PICK.append("Art/2DItems/Jewels/DeliriumJewel.dds")  # Megalomaniac jewel
ARTS_TO_PICK.append("Art/2DItems/Amulets/Uniques/Astramentis.dds")  # Astramentis
# ARTS_TO_PICK.append("Art/2DItems/Jewels/EmeraldJewel.dds")
# remove line below in case you want it to pick ALL items
poe_bot.loot_picker.loot_filter.special_rules = [isItemHasPickableKey]


# In[9]:


poe_bot.refreshInstanceData()
poe_bot.game_data.terrain.getCurrentlyPassableArea()


# In[ ]:


from utils.components import Posx1x2y1y2, UiElement

interesting_entities = []
interesting_entities_ids = []
AFFLICTIONATOR_PATH = "Metadata/Terrain/Gallows/Leagues/Delirium/Act1Town/Objects/DeliriumnatorAct1"


class Simulacrum2:
  def __init__(self, poe_bot: Poe2Bot):
    self.poe_bot = poe_bot
    self.cache = SimulacrumCache2(poe_bot.unique_id)
    self.scanForInterestingEntities()

  def scanForInterestingEntities(self, *args, **kwargs):
    for entity in self.poe_bot.game_data.entities.all_entities:
      if entity.id in interesting_entities_ids:
        continue
      # doors
      if "Metadata/Terrain/Gallows/Leagues/Delirium/Objects/Act1Doors/DeliriumDoorArena" in entity.path:
        print(f"found door {entity.raw}")
        interesting_entities.append(entity)
        interesting_entities_ids.append(entity.id)
    # return False
    return self.poe_bot.loot_picker.collectLoot()

  def getTargetableAfflictionator(self):
    return next((e for e in self.poe_bot.game_data.entities.all_entities if e.is_targetable is True and e.path == AFFLICTIONATOR_PATH), None)

  def clickAfflictionatorTillNotTargetable(self, afflictionator_entity: Entity):
    poe_bot = self.poe_bot
    stash = poe_bot.ui.stash
    afflictionator_is_targetable = True
    iteration_num = 0
    while afflictionator_is_targetable:
      poe_bot.refreshInstanceData()
      poe_bot.combat_module.build.useFlasks()
      stash.update()
      if stash.is_opened is True:
        poe_bot.ui.closeAll()
        continue
      iteration_num += 1

      afflictionator = next(
        (
          e
          for e in self.poe_bot.game_data.entities.all_entities
          if e.path == "Metadata/Terrain/Gallows/Leagues/Delirium/Act1Town/Objects/DeliriumnatorAct1"
        ),
        None,
      )
      if afflictionator is None or afflictionator.is_targetable is False:
        afflictionator_is_targetable = True
        break
      else:
        if iteration_num % 7 == 0:
          visible_labels_raw = poe_bot.backend.getVisibleLabels()
          print("[Simulacrum2.activateWave] getting the label of afflictionator")
          afflictionator_label_raw = next((label_raw for label_raw in visible_labels_raw if label_raw["p"] == AFFLICTIONATOR_PATH), None)
          if afflictionator_label_raw is None:
            continue
          UiElement(poe_bot, Posx1x2y1y2(*afflictionator_label_raw["sz"])).click()
          afflictionator_entity.hover(y_offset=random.randint(-10, 10), x_offset=random.randint(-5, 5), update_screen_pos=True)
        elif afflictionator.is_targeted is False:
          afflictionator.hover(y_offset=random.randint(-10, 10), x_offset=random.randint(-5, 5))
        else:
          afflictionator.click()

  def stashItemsIfFull(self, items_count=40):
    # stash items when stash is somewhere around
    poe_bot = self.poe_bot
    inventory = poe_bot.ui.inventory
    filled_slots = len(poe_bot.ui.inventory.getFilledSlots(force_update=True))
    simulacrums_in_inventory = list(filter(lambda i: i.name == "Simulacrum", inventory.items))
    filled_slots -= len(simulacrums_in_inventory)
    if filled_slots > items_count:
      stash_entity = next(
        (e for e in poe_bot.game_data.entities.all_entities if e.is_targetable is True and e.path == "Metadata/MiscellaneousObjects/Stash"), None
      )
      if stash_entity:
        poe_bot.mover.goToEntitysPoint(stash_entity, release_mouse_on_end=True)
        time.sleep(random.uniform(0.20, 0.40))
        stash_entity.hover(update_screen_pos=True)
        time.sleep(random.uniform(0.20, 0.40))
        poe_bot.refreshInstanceData()
        stash_entity = next(
          (e for e in poe_bot.game_data.entities.all_entities if e.is_targetable is True and e.path == "Metadata/MiscellaneousObjects/Stash"), None
        )
        if stash_entity and stash_entity.is_targeted is True:
          stash_entity.click()
          time.sleep(random.uniform(0.20, 0.40))
          poe_bot.ui.stash.update()
          if poe_bot.ui.stash.is_opened:
            poe_bot.ui.inventory.update()
            items_can_stash = list(filter(lambda i: i.name != "Simulacrum", inventory.items))
            poe_bot.ui.stash.placeItemsAcrossStash(items_can_stash, can_sleep=False)
            poe_bot.ui.closeAll()
      return True
    else:
      return False

  def activateWave(self):
    afflictionator_entity = self.getTargetableAfflictionator()
    if afflictionator_entity:
      while True:
        res = poe_bot.mover.goToEntitysPoint(afflictionator_entity, release_mouse_on_end=True, custom_break_function=self.scanForInterestingEntities)
        if res is None:
          break
      if self.stashItemsIfFull() is True:
        poe_bot.refreshInstanceData()
        poe_bot.mover.goToEntitysPoint(afflictionator_entity, release_mouse_on_end=True, custom_break_function=self.scanForInterestingEntities)

      if isinstance(poe_bot.combat_module.build) == BarrierInvocationInfernalist and reset_form_before_waves != [] and self.cache.wave > 1:
        demon_stacks = poe_bot.combat_module.build.getDemonFormStacks()
        print(f"going to generate {min_stacks_for_wave_11_plus} stacks")
        if demon_stacks < min_stacks_for_wave_11_plus:
          self.stashItemsIfFull(0)
          poe_bot.combat_module.build.generateStacks(min_stacks_for_wave_11_plus)

      def getNextWaveFromAfflictionatorLabel():
        visible_labels_raw = poe_bot.backend.getVisibleLabels()
        print("[Simulacrum2.activateWave] getting the label of afflictionator")
        afflictionator_label_raw = next((label_raw for label_raw in visible_labels_raw if label_raw["p"] == AFFLICTIONATOR_PATH))
        # if afflictionator_label_raw:
        next_wave_text = next((line for line in afflictionator_label_raw["texts"] if "Wave " in line and "/15" in line))
        next_wave = int(next_wave_text.split("/15")[0].split("Wave ")[1])
        return next_wave

      next_wave_num = getNextWaveFromAfflictionatorLabel()
      self.cache.wave = next_wave_num
      self.cache.save()
      if self.cache.wave > 15:
        return False
      self.clickAfflictionatorTillNotTargetable(afflictionator_entity)
      print("activated")
      return True
    else:
      print("[Simulacrum2.activateWave] couldnt find afflictionator")
      return False

  def isWaveRunning(self):
    poe_bot = self.poe_bot
    if len(poe_bot.game_data.entities.attackable_entities) != 0:
      print("true cos attackable entities")
      return True
    if len(poe_bot.backend.last_data["i"]) != 0:
      print("false bcs items are visible")
      return False
    # if self.getTargetableAfflictionator() != None:
    #   print('false, cos afflictionator is targetable')
    #   return False
    return True

  def isWaveRunning_2(self):
    poe_bot = self.poe_bot
    if len(poe_bot.game_data.entities.attackable_entities) != 0:
      print("true cos attackable entities")
      return True
    if len(poe_bot.backend.last_data["i"]) != 0:
      print("false bcs items are visible")
      return False
    if self.getTargetableAfflictionator() is not None:
      print("false, cos afflictionator is targetable")
      return False
    return True

  def doPreparations(self):
    poe_bot = self.poe_bot
    inventory = poe_bot.ui.inventory
    stash = poe_bot.ui.stash
    inventory.update()
    simulacrums_in_inventory = list(filter(lambda i: i.name == "Simulacrum", inventory.items))
    if len(simulacrums_in_inventory) == 0:
      stash.open()
      all_stash_items = stash.getAllItems()
      simulacrums_in_stash = list(filter(lambda i: i.name == "Simulacrum", all_stash_items))
      if len(simulacrums_in_stash) == 0:
        stash.updateStashTemp()
        all_stash_items = stash.getAllItems()
        simulacrums_in_stash = list(filter(lambda i: i.name == "Simulacrum", all_stash_items))
        if len(simulacrums_in_stash) == 0:
          poe_bot.raiseLongSleepException("no simulacrums found in stash")

      simulacrum_item_to_pick = simulacrums_in_stash[0]
      stash.openTabIndex(simulacrum_item_to_pick.tab_index)
      stash.update()
      simulacrum_item_to_pick = next((i for i in stash.current_tab_items if i.name == "Simulacrum"), None)
      if simulacrum_item_to_pick:
        simulacrum_item_to_pick.click(hold_ctrl=True)
        time.sleep(random.uniform(0.30, 0.50))
        inventory.update()
        simulacrums_in_inventory = list(filter(lambda i: i.name == "Simulacrum", inventory.items))
        print(f"currently have {len(simulacrums_in_inventory)} simulacrums in inventory")
      else:
        self.cache.reset()
        raise Exception("[Simulacrum.doPreparations] didnt find simulacrum, retrying")
      poe_bot.ui.closeAll()

    self.cache.stage = 1
    self.cache.save()

  def activateMap(self):
    poe_bot.ui.map_device.open()
    time.sleep(1)
    poe_bot.ui.map_device.open()

    ziggurat_map = next((m for m in poe_bot.ui.map_device.all_maps if m.name == "The Ziggurat Refuge"), None)
    while ziggurat_map is None:
      poe_bot.ui.map_device.update()
      ziggurat_map = next((m for m in poe_bot.ui.map_device.all_maps if m.name == "The Ziggurat Refuge"), None)
      time.sleep(1)

    ziggurat_map.screen_pos.toList()
    ziggurat_in_roi = poe_bot.game_window.isInRoi(*ziggurat_map.screen_pos.toList())
    _i = 0
    while ziggurat_in_roi is False:
      _i += 1
      if _i > 10:
        poe_bot.raiseLongSleepException("couldnt get ziggurat in roi while clicking on its button")
      poe_bot.ui.map_device.ziggurat_button.click()
      time.sleep(2)
      poe_bot.ui.map_device.update()
      ziggurat_map = next((m for m in poe_bot.ui.map_device.all_maps if m.name == "The Ziggurat Refuge"), None)
      if ziggurat_map is None:
        continue
      ziggurat_in_roi = poe_bot.game_window.isInRoi(*ziggurat_map.screen_pos.toList())
    realmgate_map_screen_zone = next((m for m in poe_bot.ui.map_device.special_maps if m.x2 > ziggurat_map.screen_zone.x2), None)
    if realmgate_map_screen_zone is None:
      poe_bot.raiseLongSleepException("couldnt find realmgate")

    realmgate_map = UiElement(poe_bot, realmgate_map_screen_zone)
    realmgate_map.click()
    time.sleep(1)
    poe_bot.ui.map_device.update()

    if poe_bot.ui.map_device.place_map_window_opened is False:
      poe_bot.raiseLongSleepException("cant open realmgate")

    poe_bot.ui.inventory.update()
    simulacrum_item = next((i for i in poe_bot.ui.inventory.items if i.name == "Simulacrum"), None)
    if simulacrum_item is None:
      poe_bot.ui.closeAll()
      self.cache.reset()
      raise Exception("no simulacrums in inventory during map activation")
      poe_bot.raiseLongSleepException("no simulacrums in inventory")

    simulacrum_item.click(hold_ctrl=True)

    can_activate = poe_bot.ui.map_device.checkIfActivateButtonIsActive()
    if can_activate is False:
      poe_bot.raiseLongSleepException("activate button is not active")

    poe_bot.ui.map_device.activate()

    poe_bot.helper_functions.waitForNewPortals()

    self.cache.stage = 2
    self.cache.save()

  def run(self):
    poe_bot = self.poe_bot
    in_instance = "Hideout" not in poe_bot.game_data.area_raw_name  # and not "_town_" in poe_bot.game_data.area_raw_name
    if self.cache.stage == 0:
      if in_instance is True:
        self.leaveInstance()
      # self.checkIfSessionEnded()
      self.doPreparations()
    if self.cache.stage == 1:
      self.activateMap()
    if self.cache.stage == 2:
      if in_instance is False:
        if self.cache.wave_started is False and self.cache.wave > 14:
          self.cache.reset()
          poe_bot.logger.writeLine("[Simulacrum.run] simulacrum completed")
          raise Exception("[Simulacrum.run] simulacrum is completed and in hideout, restart")
        #   if nested == False:
        #     self.run(True);return
        #   else:
        # raise Exception('[Simulacrum.run] simulacrum is completed and in hideout, restart')
        # self.doStashing()

        original_area_raw_name = poe_bot.game_data.area_raw_name
        portals = poe_bot.game_data.entities.town_portals
        if len(portals) == 0:
          self.cache.reset()
          raise Exception("[Simulacrum.run] no portals left to enter")
        poe_bot.mover.goToEntitysPoint(portals[0], min_distance=30, release_mouse_on_end=True)
        while poe_bot.game_data.invites_panel_visible is False:
          portals[0].click(update_screen_pos=True)
          time.sleep(random.uniform(0.3, 0.7))
          try:
            poe_bot.refreshInstanceData()
          except Exception as e:
            if e.__str__() in ["area is loading on partial request", "Area changed but refreshInstanceData was called before refreshAll"]:
              break
        area_changed = False
        while area_changed is not True:
          poe_bot.refreshAll()
          area_changed = poe_bot.game_data.area_raw_name != original_area_raw_name

      self.completeInstance()
      self.leaveInstance()
      poe_bot.logger.writeLine("[Simulacrum.run] simulacrum completed")
      self.cache.reset()

  def completeInstance(self):
    print(f"[Simulacrum2.completeInstance] call at {time.time()}")
    poe_bot = self.poe_bot
    simulacrum = self
    running_simulacrum = True
    self.scanForInterestingEntities()
    # can be called when enters simulacrum or when accidantly got out from it
    while running_simulacrum:
      print(f"[Simulacrum2.completeInstance] prev wave is {self.cache.wave}")
      poe_bot.refreshAll()
      # plt.imshow(poe_bot.pather.terrain_for_a_star);plt.show()
      poe_bot.game_data.terrain.getCurrentlyPassableArea(dilate_kernel_size=0)
      # plt.imshow(poe_bot.game_data.terrain.currently_passable_area);plt.show()
      poe_bot.pather.terrain_for_a_star[poe_bot.game_data.terrain.currently_passable_area != 1] = 65534

      activated_wave = self.isWaveRunning_2()
      if self.cache.wave > 14 and self.cache.wave_started is False:
        print("forced to be over mostlikely simulacrum is over")
        running_simulacrum = False
        break

      # activated_wave = self.cache.wave_started
      while activated_wave is False:
        poe_bot.refreshInstanceData()
        self.poe_bot.combat_module.build.staticDefence()
        activated_wave = simulacrum.activateWave()

      self.cache.wave_started = True
      if running_simulacrum is False:
        break
      self.cache.save()
      print(f"running simulacrum wave: {self.cache.wave}")
      # plt.imshow(poe_bot.pather.terrain_for_a_star);plt.show()
      poe_bot.refreshAll()
      # plt.imshow(poe_bot.game_data.terrain.terrain_image);plt.show()
      # plt.imshow(poe_bot.game_data.terrain.passable);plt.show()
      # shut the doors
      for interesting_entitiy in interesting_entities:
        poe_bot.game_data.terrain.passable[
          interesting_entitiy.grid_position.y - 25 : interesting_entitiy.grid_position.y + 25,
          interesting_entitiy.grid_position.x - 25 : interesting_entitiy.grid_position.x + 25,
        ] = 0
      poe_bot.game_data.terrain.getCurrentlyPassableArea(dilate_kernel_size=0)
      # plt.imshow(poe_bot.game_data.terrain.currently_passable_area);plt.show()

      arena_center = poe_bot.pather.utils.getCenterOf(poe_bot.game_data.terrain.currently_passable_area)
      print(f"arena center {arena_center}")
      points = getFourPoints(*arena_center, 70)
      run_points = []
      for point in points[1:]:
        line_vals = createLineIteratorWithValues(arena_center, point, poe_bot.game_data.terrain.currently_passable_area)
        last_point = arena_center
        # print(line_vals)
        for line_point in line_vals[10:]:
          if line_point[-1] != 1.0:
            print(line_point)
            break
          last_point = line_point
        run_points.append([int(last_point[0]), int(last_point[1])])
        # passable_point = poe_bot.game_data.terrain.checkIfPointPassable(*point)

        print(f"{point} {run_points[-1]}")
      run_points = [run_points[0], run_points[2], run_points[1], run_points[3]]
      # plt.imshow(poe_bot.game_data.terrain.currently_passable_area[arena_center[1]-75:arena_center[1]+75, arena_center[0]-75:arena_center[0]+75]);plt.show()

      wave_started_at = time.time()
      is_wave_running = True
      while is_wave_running:
        # random.shuffle(run_points) # sometimes run back from opposite point which leads to it's death
        for point in run_points:
          poe_bot.mover.goToPoint(point, release_mouse_on_end=False)
          if time.time() + 10 > wave_started_at:
            is_wave_running = simulacrum.isWaveRunning()
          if is_wave_running is False:
            break
          print(f"wave running status {is_wave_running}")

      poe_bot.refreshInstanceData()
      if isinstance(poe_bot.combat_module.build) == BarrierInvocationInfernalist and (self.cache.wave + 1) in reset_form_before_waves:
        poe_bot.combat_module.build.demon_form.use()
      poe_bot.loot_picker.collectLootWhilePresented()
      self.cache.wave_started = False
      self.cache.save()
      print("wave completed")

  def leaveInstance(self):
    poe_bot = self.poe_bot

    original_area_raw_name = poe_bot.game_data.area_raw_name
    poe_bot.refreshInstanceData()
    portals = poe_bot.game_data.entities.town_portals
    if len(portals) == 0:
      # self.cache.reset()
      raise Exception("[Mapper2.run] no portals left to enter")
    while True:
      res = poe_bot.mover.goToEntitysPoint(
        portals[0], min_distance=30, release_mouse_on_end=True, custom_break_function=poe_bot.loot_picker.collectLoot
      )
      if res is None:
        break
    while poe_bot.game_data.invites_panel_visible is False:
      portals[0].click(update_screen_pos=True)
      time.sleep(random.uniform(0.3, 0.7))
      try:
        poe_bot.refreshInstanceData()
      except Exception as e:
        if e.__str__() in ["area is loading on partial request", "Area changed but refreshInstanceData was called before refreshAll"]:
          break
    area_changed = False
    while area_changed is not True:
      poe_bot.refreshAll()
      area_changed = poe_bot.game_data.area_raw_name != original_area_raw_name


# In[11]:


simulacrum = Simulacrum2(poe_bot=poe_bot)
simulacrum.run()


# In[ ]:


raise 404


# In[ ]:


original_area_raw_name = poe_bot.game_data.area_raw_name
poe_bot.refreshInstanceData()
portals = poe_bot.game_data.entities.town_portals
if len(portals) == 0:
  # self.cache.reset()
  raise Exception("[Mapper2.run] no portals left to enter")
poe_bot.mover.goToEntitysPoint(portals[0], min_distance=30, release_mouse_on_end=True)
while poe_bot.game_data.invites_panel_visible is False:
  portals[0].click(update_screen_pos=True)
  time.sleep(random.uniform(0.3, 0.7))
  try:
    poe_bot.refreshInstanceData()
  except Exception as e:
    if e.__str__() in ["area is loading on partial request", "Area changed but refreshInstanceData was called before refreshAll"]:
      break
area_changed = False
while area_changed is not True:
  poe_bot.refreshAll()
  area_changed = poe_bot.game_data.area_raw_name != original_area_raw_name


# In[ ]:


raise 404


# In[ ]:


if isinstance(poe_bot.combat_module.build) == BarrierInvocationInfernalist:
  poe_bot.combat_module.build.generateStacks(60)


# In[ ]:


poe_bot


# In[ ]:


poe_bot.refreshInstanceData()
poe_bot.game_data.skills.total_uses[poe_bot.combat_module.build.barrier_invocation.skill_index]


# In[ ]:


def getRecoupEffectsCount():
  return len(list(filter(lambda b: b == "life_recoup", poe_bot.game_data.player.buffs)))


# In[ ]:


isinstance(poe_bot.combat_module.build) == BarrierInvocationInfernalist
while True:
  poe_bot.refreshInstanceData()
  poe_bot.combat_module.build.useFlasks()
  demon_stacks = poe_bot.combat_module.build.getDemonFormStacks()
  if demon_stacks > 60:
    poe_bot.combat_module.build.demon_form.use()
  # recoup_effects = list(filter(lambda b: b == 'life_recoup', poe_bot.game_data.player.buffs))
  print(f"stacks count: {poe_bot.combat_module.build.getDemonFormStacks()}")


# In[ ]:


"""
{"ls":[325,291],"p":"Metadata/Terrain/Gallows/Leagues/Delirium/Act1Town/Objects/DeliriumnatorAct1","r":"White","i":439,"o":0,"h":1,"ia":0,"t":1,"it":0,"em":0,"b":1,"gp":[524,810],"wp":[5716,8825,-50],"l":null,"rn":"","et":"IngameIcon"}


wave 4 change loc -> arena1
wave 6 change loc -> arena2
wave 7 change loc -> arena3
wave 9 change loc -> arena4
wave 10 change loc -> arena5
wave 11 change loc -> arena6 # same as arena0
wave 13 change loc -> arena7

"VaalStatueBossInvisBeam" - kosis spawn?

"Metadata/Monsters/LeagueDelirium/DeliriumDemonBossFinal<whatever>" - kosis
"Metadata/Monsters/LeagueDelirium/DeliriumDemonBossPhysical<whatever>" - omni

"Metadata/MiscellaneousObjects/MultiplexPortal" - portal
"Metadata/MiscellaneousObjects/Stash" - stash
"Metadata/Terrain/Gallows/Leagues/Delirium/Act1Town/Objects/DeliriumnatorAct1" - afflictionator

blockades:
Metadata/Terrain/Gallows/Leagues/Delirium/Objects/Act1Doors/DeliriumDoorArena1
Metadata/Terrain/Gallows/Leagues/Delirium/Objects/Act1Doors/DeliriumDoorArena2 
"""


"""
arenas = {
}


- get to instance
- copy currently passable area and mark it as arenas[0] = *currently passable
- find arena1 by reaching the afflictinator and (total passable - arena[0])
- arena[2] = (total passable - arena[1])
...
- arena6 supposed to be the same as arena0
- arena7 finish 15 waves, go to hideout


"""


#

#


# In[ ]:


poe_bot.refreshAll()


# In[ ]:


stash = poe_bot.ui.stash
stash.open()
stash.temp.allItems()


# In[ ]:


stash.updateStashTemp()


# In[ ]:


poe_bot.refreshAll()


# In[ ]:


plt.imshow(poe_bot.game_data.terrain.terrain_image)

