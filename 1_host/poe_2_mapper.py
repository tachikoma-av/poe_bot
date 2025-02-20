#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import random
import sys
import time
from ast import literal_eval
from math import dist
from typing import List, Type

from utils.gamehelper import Entity, Poe2Bot


# In[ ]:


# readabilty
poe_bot: Poe2Bot

notebook_dev = False


# In[ ]:


from utils.components import PoeBotComponent
from utils.constants import ESSENCES_KEYWORD
from utils.encounters import BreachEncounter, DeliriumEncounter, EssenceEncounter, RitualEncounter
from utils.temps import MapperCache2
from utils.ui import InventoryItem, Item, StashItem


# open portal and enter it
def openPortal():
  poe_bot.bot_controls.releaseAll()

  time.sleep(random.randint(40, 80) / 100)
  pos_x, pos_y = random.randint(709, 711), random.randint(694, 696)
  pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y, safe=False)
  poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
  time.sleep(random.randint(40, 80) / 100)
  poe_bot.bot_controls.mouse.click()
  time.sleep(random.randint(30, 60) / 100)


MAPS_TO_IGNORE = [
  "MapCrypt_NoBoss",  # activators
  "MapCrypt",  # activators
  "MapAugury_NoBoss",  # activators
  "MapAugury",  # activators
  "MapFortress",  # TODO class MapForptress boss activators
  "MapLostTowers",  # class MapLostTowers multi layerd location
  "MapBluff",  # tower
  "MapMesa",  # tower
  "MapSwampTower",  # multi layerd
  "MapSwampTower_NoBoss",  # multi layerd
]

OILS_BY_TIERS = ["Distilled Ire", "Distilled Guilt", "Distilled Greed"]


class MapperSettings:
  #
  atlas_explorer = False  # prefer to run higher tier maps over lower tier
  boss_rush = False
  alch_chisel = False  # will use alch + chisel if it's possible
  alch_chisel_force = False  # TODO will use alch or scour alch chisel if possible
  # TODO above will be deprecated moslikely

  session_duration = "24h"

  default_discovery_percent = 0.93  # % for which itll explore the area
  discovery_percent = default_discovery_percent  # % for which itll explore the area

  prefered_tier: str = "5+"
  min_map_tier = 1
  max_map_tier = 8
  prefer_high_tier = True

  # TODO keep consumables same as maps.ipynb
  keep_consumables = []
  keep_waystones_in_inventory = 5

  low_priority_maps = []
  high_priority_maps = []

  waystone_upgrade_to_rare = True
  waystone_upgrade_to_rare_force = True  # TODO identify + alch|| identify + aug + regal
  waystone_vaal = False  ##TODO if map is rare, not corrupted and identified vaal it

  anoint_maps = False
  anoint_maps_force = False
  anoint_max_tier = 2

  max_map_run_time = 600

  complete_tower_maps = True

  force_kill_blue = True
  force_kill_rares = True

  force_deli = False
  force_breaches = False

  do_essences = True

  do_rituals = True
  do_rituals_buyout_function = lambda *agrs, **kwargs: True

  def __init__(self, config: dict) -> None:
    for key, value in config.items():
      setattr(self, key, value)
    print(str(self))

  def assignConsumables(self):
    if self.waystone_upgrade_to_rare:
      self.keep_consumables.append({"Orb of Alchemy": 10})
    if self.waystone_upgrade_to_rare_force:
      self.keep_consumables.append({"Orb of Augmentation": 10})
      self.keep_consumables.append({"Regal Orb": 10})
    if self.waystone_vaal:
      self.keep_consumables.append({"Vaal Orb": 10})

  def __str__(self):
    return f"[MapperSettings]: {str(vars(self))}"


class Mapper2(PoeBotComponent):
  can_pick_drop: bool = None
  keep_consumables: List[dict] = []

  def __init__(self, poe_bot: Poe2Bot, settings: MapperSettings):
    super().__init__(poe_bot)
    self.settings = settings
    self.assignConsumables()
    self.cache = MapperCache2(unique_id=poe_bot.unique_id)
    self.current_map: MapArea

  def assignConsumables(self):
    if self.settings.waystone_upgrade_to_rare:
      self.keep_consumables.append({"Orb of Alchemy": 10})
    if self.settings.waystone_upgrade_to_rare_force:
      self.keep_consumables.append({"Orb of Augmentation": 10})
      self.keep_consumables.append({"Regal Orb": 10})
    if self.settings.waystone_vaal:
      self.keep_consumables.append({"Vaal Orb": 10})

  # TODO write logic
  def sortWaystones(self, items: List[Item]):
    if self.settings.waystone_upgrade_to_rare or self.settings.waystone_upgrade_to_rare_force:
      items.sort(key=lambda i: i.rarity == "Normal", reverse=True)
      items.sort(key=lambda i: i.rarity == "Rare", reverse=True)
    if self.settings.anoint_maps or self.settings.anoint_maps_force:
      items.sort(key=lambda i: len(i.getDeliriumMods()) != 0, reverse=True)
    items.sort(key=lambda i: i.map_tier, reverse=self.settings.prefer_high_tier)

  def filterWaystonesCanRun(self, items: List[Item], sorted=False):
    waystones_can_run = list(
      filter(lambda i: i.map_tier and i.map_tier >= self.settings.min_map_tier and i.map_tier <= self.settings.max_map_tier, items)
    )
    if sorted:
      self.sortWaystones(waystones_can_run)
    return waystones_can_run

  def getWaystonesCanUse(self, priority="inventory", source="all"):
    inventory = self.poe_bot.ui.inventory
    stash = self.poe_bot.ui.stash
    all_maps: List[Item] = []
    maps_we_can_run_in_inventory: List[InventoryItem] = []
    maps_we_can_run_in_stash: List[StashItem] = []
    if source != "stash":
      inventory.update()
      maps_we_can_run_in_inventory = self.filterWaystonesCanRun(inventory.items)
    if source != "inventory":
      all_stash_items = stash.getAllItems()
      maps_we_can_run_in_stash = self.filterWaystonesCanRun(all_stash_items)

    if priority == "inventory":
      all_maps.extend(maps_we_can_run_in_inventory)
      all_maps.extend(maps_we_can_run_in_stash)
    else:
      all_maps.extend(maps_we_can_run_in_stash)
      all_maps.extend(maps_we_can_run_in_inventory)

    self.sortWaystones(all_maps)
    return all_maps

  def doPreparations(self):
    """
    basically just
    - sell items if needed and
    - pick consumables if needed #call self.doStashing
    - stash items if needed #call self.doStashing
    - modify waystones
    """
    print(f"[Mapper.doPreparations] call at {time.time()}")
    inventory = self.poe_bot.ui.inventory
    inventory.update()
    need_to_manage_stash = False
    while True:
      # if stash temp is empty
      all_stash_items = poe_bot.ui.stash.getAllItems()
      if len(all_stash_items) == 0:
        print("[Mapper.doPreparations] need_to_manage_stash because empty cache")
        need_to_manage_stash = True
        break
      # if has better map in stash
      waystones_can_use = self.getWaystonesCanUse()
      need_to_manage_stash_waystone_reason = None
      if len(waystones_can_use) == 0:
        need_to_manage_stash_waystone_reason = "no waystones in inventory"
      if waystones_can_use[0].source == "stash":
        need_to_manage_stash_waystone_reason = "best waystone is in stash"
      if need_to_manage_stash_waystone_reason is not None:
        print(f"[Mapper.doPreparations] need_to_manage_stash because {need_to_manage_stash_waystone_reason}")
        need_to_manage_stash = True
        break

      # if lack of consumables or willing to modify maps

      break
    print(f"[Mapper.doPreparations] need_to_manage_stash {need_to_manage_stash}")
    if need_to_manage_stash is True:
      self.manageStashAndInventory(pick_consumables=True)

    maps_in_inventory = self.getWaystonesCanUse(source="inventory")
    # if the best map to run needs to be modified, pick consumables and modify all at once
    need_to_modify_maps = False
    while True:
      if self.settings.anoint_maps and len(maps_in_inventory[0].getDeliriumMods()) == 0:
        need_to_modify_maps = True
        break
      if (self.settings.waystone_upgrade_to_rare or self.settings.waystone_upgrade_to_rare_force) and maps_in_inventory[0].rarity != "Rare":
        need_to_modify_maps = True
        break
      break

    if need_to_modify_maps:
      if need_to_manage_stash is False:
        self.manageStashAndInventory(pick_consumables=True)

      def identifyMaps():
        poe_bot.ui.inventory.update()
        unidentified_items = list(filter(lambda m: m.map_tier and m.identified is False, poe_bot.ui.inventory.items))
        if len(unidentified_items) != 0:
          while True:
            poe_bot.refreshInstanceData()
            poe_bot.ui.inventory.update()
            unidentified_items = list(filter(lambda m: m.map_tier and m.identified is False, poe_bot.ui.inventory.items))
            if len(unidentified_items) == 0:
              break
            doryani_entity = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Doryani"))
            doryani_entity.click(hold_ctrl=True)
            time.sleep(random.uniform(0.30, 0.60))
          poe_bot.ui.npc_dialogue.update()
          if poe_bot.ui.npc_dialogue.visible is True:
            poe_bot.ui.closeAll()

      identifyMaps()
      inventory.open()
      maps_in_inventory = self.getWaystonesCanUse(source="inventory")
      # alch logic
      if self.settings.waystone_upgrade_to_rare or self.settings.waystone_upgrade_to_rare_force:
        maps_can_alch = list(filter(lambda m: m.corrupted is False and m.rarity == "Normal", maps_in_inventory))
        alchemy_orb_stacks = list(filter(lambda i: i.name == "Orb of Alchemy", inventory.items))
        alchemy_orb_count = sum(list(map(lambda i: i.items_in_stack, alchemy_orb_stacks)))
        maps_can_alch = maps_can_alch[:alchemy_orb_count]

        if alchemy_orb_count != 0 and len(maps_can_alch) != 0:
          alchemy_orb_stacks[0].click(button="right")
          time.sleep(random.uniform(0.20, 0.40))
          poe_bot.ui.clickMultipleItems(maps_can_alch, hold_ctrl=False, hold_shift=True)
        # aug logic
        maps_can_aug_regal = list(filter(lambda m: m.corrupted is False and m.identified is True and m.rarity == "Magic", maps_in_inventory))
        maps_can_aug = []
        maps_can_regal = []

        for map_item in maps_can_aug_regal:
          map_mods = len(map_item.item_mods_raw) - len(map_item.getDeliriumMods())
          if map_mods == 1:
            maps_can_aug.append(map_item)
          else:
            maps_can_regal.append(map_item)

        aug_stacks = list(filter(lambda i: i.name == "Orb of Augmentation", inventory.items))
        aug_count = sum(list(map(lambda i: i.items_in_stack, aug_stacks)))
        maps_can_aug = maps_can_aug[:aug_count]
        maps_can_regal.extend(maps_can_aug)

        if aug_count != 0 and len(maps_can_aug) != 0:
          aug_stacks[0].click(button="right")
          time.sleep(random.uniform(0.20, 0.40))
          poe_bot.ui.clickMultipleItems(maps_can_aug, hold_ctrl=False, hold_shift=True)
          time.sleep(random.uniform(0.20, 0.40))

        # regal logic
        regal_stacks = list(filter(lambda i: i.name == "Regal Orb", inventory.items))
        regal_count = sum(list(map(lambda i: i.items_in_stack, regal_stacks)))
        maps_can_regal = maps_can_regal[:regal_count]

        if regal_count != 0 and len(maps_can_regal) != 0:
          regal_stacks[0].click(button="right")
          time.sleep(random.uniform(0.20, 0.40))
          poe_bot.ui.clickMultipleItems(maps_can_regal, hold_ctrl=False, hold_shift=True)
          time.sleep(random.uniform(0.20, 0.40))
      # anoint logic
      if self.settings.anoint_maps:
        maps_can_be_anointed = list(filter(lambda m: m.corrupted is False and len(m.getDeliriumMods()) < 3, maps_in_inventory))
        for m in maps_can_be_anointed:
          print(m.raw)
        oils_can_use = self.getUsableOilsFromItems(inventory.items)
        oil_items = []
        for oil in oils_can_use:
          for i in range(oil.items_in_stack):
            oil_items.append(oil)

        while len(maps_can_be_anointed) != 0:
          map_item = maps_can_be_anointed.pop(0)
          map_deli_mods = map_item.getDeliriumMods()
          availiable_mods = 3 - len(map_deli_mods)
          if len(oil_items) < availiable_mods:
            break
          anoint_with = []
          for _i in range(availiable_mods):
            anoint_with.append(oil_items.pop(0))
          poe_bot.ui.anoint_ui.anointItem(map_item, anoint_with)
      self.poe_bot.ui.closeAll()
    self.cache.stage = 1
    self.cache.save()

  # TODO add some sorting for maps rather than this: map_obj = random.choice(possible_to_run_maps)
  def getUsableOilsFromItems(self, items: List[Item]):
    # TODO sort oils by tier
    OILS_TYPES_CAN_USE = OILS_BY_TIERS[: self.settings.anoint_max_tier]
    oils_can_use = list(filter(lambda i: i.name in OILS_TYPES_CAN_USE, items))
    oils_can_use.sort(key=lambda i: OILS_BY_TIERS.index(i.name))
    return oils_can_use

  def activateMap(self):
    """
    open map devic
    activate map
    """
    poe_bot: Poe2Bot = self.poe_bot
    poe_bot.ui.inventory.update()
    maps_in_inventory = self.getWaystonesCanUse(source="inventory")
    if len(maps_in_inventory) == 0:
      self.cache.reset()
      raise Exception("[Mapper.activateMap] len(maps_in_inventory) == 0 in activateMap")
    # open map device
    poe_bot.ui.map_device.open()
    # move to map, open dropdown
    poe_bot.ui.map_device.update()
    possible_to_run_maps = list(
      filter(
        lambda m:
        # m.is_boss == False and # some bosses have unique logic?
        # m.is_tower == False and# cant run tower maps yet
        m.is_hideout is False  # hideouts ignored
        and m.is_trader is False  # manual trade
        and
        # m.is_ritual == False and# save rituals for tests
        (m.name_raw in MAPS_TO_IGNORE) is False,
        poe_bot.ui.map_device.avaliable_maps,
      )
    )
    if len(possible_to_run_maps) == 0:
      poe_bot.raiseLongSleepException("dont have any maps to run visible")
    print("[Mapper.activateMap] #TODO sort maps by some criteria")

    possible_to_run_maps.sort(key=lambda m: dist(m.screen_pos.toList(), (poe_bot.game_window.center_point)))
    possible_to_run_maps.sort(key=lambda m: m.name in self.settings.low_priority_maps)
    possible_to_run_maps.sort(key=lambda m: m.name in self.settings.high_priority_maps, reverse=True)
    # for m in possible_to_run_maps: print(m.raw)

    map_obj = possible_to_run_maps[0]
    print(f"[Mapper.activateMap] going to run map {map_obj.raw}")
    poe_bot.ui.map_device.moveScreenTo(map_obj)
    time.sleep(random.uniform(0.15, 0.35))
    poe_bot.ui.map_device.update()
    updated_map_obj = next((m for m in poe_bot.ui.map_device.avaliable_maps if m.id == map_obj.id))
    updated_map_obj.click()
    time.sleep(random.uniform(0.15, 0.35))
    poe_bot.ui.map_device.update()

    if poe_bot.ui.map_device.place_map_window_opened is not True:
      print("[Mapper.activateMap] dropdown didnt open, clicking on nearby element and clicking back again")
      # TODO filter by if its in roi
      another_map_objects = list(filter(lambda m: m.id != map_obj.id, poe_bot.ui.map_device.avaliable_maps))
      nearest_map_objects = sorted(another_map_objects, key=lambda m: dist(map_obj.screen_zone.getCenter(), m.screen_zone.getCenter()))
      nearest_map_objects[0].click()
      time.sleep(random.uniform(0.15, 0.35))
      poe_bot.ui.map_device.update()
      map_obj = next((m for m in poe_bot.ui.map_device.avaliable_maps if m.id == map_obj.id))
      map_obj.click()
      time.sleep(random.uniform(0.15, 0.35))
      poe_bot.ui.map_device.update()

      # pos_x, pos_y = poe_bot.game_window.convertPosXY(100, 100)
      # poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      # time.sleep(random.uniform(0.15, 0.35))
      # poe_bot.ui.map_device.update()
      # updated_map_obj = next( (m for m in poe_bot.ui.map_device.avaliable_maps if m.id == map_obj.id))
      # updated_map_obj.click()
      # time.sleep(random.uniform(0.15, 0.35))
      # poe_bot.ui.map_device.update()
      if poe_bot.ui.map_device.place_map_window_opened is False:
        print("[Mapper.activateMap] seems like map device bug")
        raise Exception("[Mapper.activateMap] cant open dropdown for map device #TODO click on other map element in roi and try again?")
        poe_bot.raiseLongSleepException("[Mapper.activateMap] cant open dropdown for map device #?")
    poe_bot.ui.map_device.update()

    print("[Mapper.activateMap] dropdown opened")
    if len(poe_bot.ui.map_device.place_map_window_items) != 0:
      poe_bot.raiseLongSleepException("[Mapper.activateMap] len(poe_bot.ui.map_device.place_map_window_items) != 0 #TODO remove all, test below")
      poe_bot.ui.clickMultipleItems(poe_bot.ui.map_device.place_map_window_items)
    maps_in_inventory = self.getWaystonesCanUse(source="inventory")
    map_to_run = maps_in_inventory[0]
    print(f"[Mapper.activateMap] going to run map: {map_to_run.raw}")

    print(f"[Mapper.activateMap] placing map {map_to_run.raw}")
    map_to_run.click(hold_ctrl=True)
    time.sleep(random.uniform(0.4, 1.2))

    poe_bot.ui.map_device.update()
    poe_bot.ui.map_device.checkIfActivateButtonIsActive()
    poe_bot.ui.map_device.activate()
    poe_bot.helper_functions.waitForNewPortals()

    self.cache.stage = 2
    self.cache.save()

  def manageStashAndInventory(self, pick_consumables=False):
    poe_bot = self.poe_bot
    stash = poe_bot.ui.stash
    inventory = poe_bot.ui.inventory
    all_stash_items = stash.getAllItems()
    if len(all_stash_items) == 0:
      stash.updateStashTemp()

    if pick_consumables:
      stash_tab_indexes: List[int] = []
      consumables_to_pick = []
      oils_to_pick_count = 0
      maps_to_pick_count = random.randint(max([1, int(self.settings.keep_waystones_in_inventory * 0.6)]), self.settings.keep_waystones_in_inventory)

      all_waystones = self.getWaystonesCanUse()
      if len(all_waystones) == 0:
        print("[Mapper.manageStashAndInventory] no waystones in stash.cache or inventory, rechecking stash")
        stash.updateStashTemp()
        all_waystones = self.getWaystonesCanUse()
        if len(all_waystones) == 0:
          poe_bot.raiseLongSleepException("[Mapper.manageStashAndInventory] no waystones found in stash and inventory after updating")
      if all_waystones[0].source == "stash":
        print("[Mapper.manageStashAndInventory] best waystone is in stash")
        list(map(lambda i: stash_tab_indexes.append(i.tab_index), self.getWaystonesCanUse(source="stash")))

      all_stash_items = stash.getAllItems()

      for key in self.keep_consumables:
        consumable: str = list(key.keys())[0]
        min_amount = key[consumable]
        consumable_in_inventory = list(filter(lambda i: i.name == consumable, inventory.items))
        amount_in_inventory = sum(list(map(lambda i: i.items_in_stack, consumable_in_inventory)))
        need_to_pick = min_amount - amount_in_inventory
        if need_to_pick > 0:
          consumables_to_pick.append({consumable: need_to_pick})
          similar_items_in_stash = list(filter(lambda i: i.name == consumable, all_stash_items))
          if len(similar_items_in_stash) != 0:
            key_stash_tabs = list(map(lambda i: i.tab_index, similar_items_in_stash))
            stash_tab_indexes.extend(key_stash_tabs)

      oils_count_to_keep_in_invnentory = self.settings.keep_waystones_in_inventory * 3
      oils_in_inventory = self.getUsableOilsFromItems(inventory.items)
      current_oil_count = sum(list(map(lambda i: i.items_in_stack, oils_in_inventory)))
      oils_to_pick_count = oils_count_to_keep_in_invnentory - current_oil_count
      if oils_to_pick_count > 0:
        oils_in_stash = self.getUsableOilsFromItems(all_stash_items)
        list(map(lambda i: stash_tab_indexes.append(i.tab_index), oils_in_stash))

      stash_tab_indexes = list(set(stash_tab_indexes))
      if len(stash_tab_indexes) != 0:
        stash.open()
        print(f"[Mapper.manageStashAndInventory] going to check stash tab indexes {stash_tab_indexes}")
        random.shuffle(stash_tab_indexes)
        try:
          stash_tab_indexes.pop(stash_tab_indexes.index(stash.current_tab_index))
        except Exception:
          print(f"[Mapper.manageStashAndInventory] tab with index {stash.current_tab_index} is not in list, but we ll still check it")
        stash_tab_indexes.insert(0, stash.current_tab_index)

        for stash_tab_index in stash_tab_indexes:
          print(f"[Mapper.manageStashAndInventory] getting items from stash tab {stash_tab_index}")
          items_to_pick: List[StashItem] = []
          stash.openTabIndex(stash_tab_index)
          # check if have better maps maps_to_pick_count
          if maps_to_pick_count > 0:
            all_maps = []
            maps_we_can_run_in_inventory = self.filterWaystonesCanRun(inventory.items)
            maps_we_can_run_in_stash = self.filterWaystonesCanRun(stash.current_tab_items)
            all_maps.extend(maps_we_can_run_in_stash)
            all_maps.extend(maps_we_can_run_in_inventory)
            self.sortWaystones(all_maps)
            for map_item in all_maps[: self.settings.keep_waystones_in_inventory]:
              if map_item.source == "stash":
                # TODO added 1 map, supposed to stash 1
                print(f"[Mapper.manageStashAndInventory] going to pick map {map_item.raw}")
                items_to_pick.append(map_item)
                maps_to_pick_count -= 1
              if maps_to_pick_count <= 0:
                break
          # check if have oils_to_pick_count
          if oils_to_pick_count > 0:
            usable_oils_in_tab = self.getUsableOilsFromItems(stash.current_tab_items)
            for oil_item in usable_oils_in_tab:
              print(f"[Mapper.manageStashAndInventory] going to pick oil {oil_item.raw}")
              items_to_pick.append(oil_item)
              oils_to_pick_count -= oil_item.items_in_stack
              if oils_to_pick_count <= 0:
                break
          # check if have consumables_to_pick
          if len(consumables_to_pick) != 0:
            indexes_to_remove = []
            for key_index in range(len(consumables_to_pick)):
              key = consumables_to_pick[key_index]
              consumable: str = list(key.keys())[0]
              need_to_pick = consumables_to_pick[key_index][consumable]
              consumables_in_current_tab = list(filter(lambda i: i.name == consumable, stash.current_tab_items))
              consumables_in_current_tab.sort(key=lambda i: i.items_in_stack)
              for consumable_item in consumables_in_current_tab:
                items_to_pick.append(consumable_item)
                consumables_to_pick[key_index][consumable] -= consumable_item.items_in_stack
                if consumables_to_pick[key_index][consumable] <= 0:
                  indexes_to_remove.append(key_index)
                  break

            for key_index in indexes_to_remove[::-1]:
              consumables_to_pick.pop(key_index)
          self.stashUselessItems()
          self.poe_bot.ui.clickMultipleItems(items_to_pick, random_sleep=False)
        self.poe_bot.ui.closeAll()
      # checks if all ok
      waystones_in_inventory = self.getWaystonesCanUse(source="inventory")
      if len(waystones_in_inventory) == 0:
        poe_bot.raiseLongSleepException("[Mapper.manageStashAndInventory] dont have waystones after managing stash")
      # check if best map is anointed or we have consumables to make it rare
      if self.settings.anoint_maps_force:
        oils_in_inventory = []
        if waystones_in_inventory[0].getDeliriumMods() == 0 and len(oils_in_inventory) == 0:
          poe_bot.raiseLongSleepException(
            "[Mapper.manageStashAndInventory] settings.anoint_maps_force and best map isnt delirious and dont have oils to make it delirious"
          )

      # check if best map is rare or we have consumables to make it rare
      if self.settings.waystone_upgrade_to_rare_force:
        pass
    else:
      # free inventory if needed
      if self.stashUselessItems() is True:
        poe_bot.ui.closeAll()
        time.sleep(random.uniform(0.3, 1.4))

  def stashUselessItems(self, consumables_multiplier=2):
    inventory = self.poe_bot.ui.inventory
    poe_bot.ui.inventory.update()
    empty_slots = poe_bot.ui.inventory.getEmptySlots()
    if len(empty_slots) < 40:
      poe_bot.ui.stash.open()
      items_to_keep = []
      poe_bot.ui.inventory.update()

      # waystones
      waystones_to_keep = self.getWaystonesCanUse(source="inventory")
      self.sortWaystones(waystones_to_keep)
      items_to_keep.extend(waystones_to_keep[: self.settings.keep_waystones_in_inventory - 1])

      # usual consumables
      for consumable in self.keep_consumables:
        name: str = list(consumable.keys())[0]
        amount: int = consumable[name] * consumables_multiplier
        consumables_in_inventory = list(filter(lambda i: i.name == name, poe_bot.ui.inventory.items))
        if len(consumables_in_inventory) == 0:
          continue
        consumables_in_inventory.sort(key=lambda i: i.items_in_stack, reverse=False)
        current_amount = 0
        while len(consumables_in_inventory) != 0:
          if current_amount > amount:
            break
          consumable_to_keep = consumables_in_inventory.pop(0)
          consumable_to_keep_count = consumable_to_keep.items_in_stack
          current_amount += consumable_to_keep_count
          items_to_keep.append(consumable_to_keep)

      # oils
      oils_count_to_keep_in_invnentory = self.settings.keep_waystones_in_inventory * 3 * consumables_multiplier
      oils_in_inventory = self.getUsableOilsFromItems(inventory.items)
      oils_in_inventory_count = 0
      for oil_item in oils_in_inventory:
        items_to_keep.append(oil_item)
        oils_in_inventory_count += oil_item.items_in_stack
        if oils_in_inventory_count >= oils_count_to_keep_in_invnentory:
          break
      items_can_stash = list(filter(lambda i: i not in items_to_keep, poe_bot.ui.inventory.items))
      poe_bot.ui.clickMultipleItems(items_can_stash)
      return True
    return False

  def isMapCompleted(self):
    poe_bot = self.poe_bot
    poe_bot.game_data.map_info.update()
    if poe_bot.game_data.map_info.map_completed is not True:
      print(f"[Mapper.isMapCompleted] poe_bot.game_data.map_info.map_completed {poe_bot.game_data.map_info.map_completed}")
      return False
    if self.settings.do_rituals is True:
      poe_bot.ui.ritual_ui.update()
      if poe_bot.ui.ritual_ui.ritual_button is not None:
        rituals_left = poe_bot.ui.ritual_ui.progress_total - poe_bot.ui.ritual_ui.progress_current
        if rituals_left != 0:
          print(
            f"[Mapper.isMapCompleted] ritual progress {poe_bot.ui.ritual_ui.progress_total}/{poe_bot.ui.ritual_ui.progress_current} rituals left {rituals_left}"
          )
          return False
    return True

  def run(self, nested=False):
    poe_bot = self.poe_bot
    in_instance = "Hideout" not in poe_bot.game_data.area_raw_name  # and not "_town_" in poe_bot.game_data.area_raw_name
    print(f"[Mapper2.run] current instance: {poe_bot.game_data.area_raw_name} in_instance {in_instance}")
    if self.cache.stage == 0:
      # self.checkIfSessionEnded()
      self.doPreparations()
    if self.cache.stage == 1:
      self.activateMap()
    if self.cache.stage == 2:
      # #TODO part below is somewhere here
      # time.sleep(random.uniform(0.8, 1.6))
      # poe_bot.helper_functions.waitForNewPortals()
      # poe_bot.refreshInstanceData()
      # original_area_raw_name = poe_bot.game_data.area_raw_name
      # poe_bot.helper_functions.getToPortal(check_for_map_device=False, refresh_area=True)
      # area_changed = False
      # while area_changed != True:
      #   poe_bot.refreshAll()
      #   area_changed = poe_bot.game_data.area_raw_name != original_area_raw_name

      # self.poe_bot.combat_module.build.doPreparations()
      if in_instance is False:
        if self.cache.map_completed is True:
          self.cache.reset()
          poe_bot.logger.writeLine("map completed")
          if nested is False:
            self.run(True)
            return
          else:
            raise Exception("[Mapper2.run] map is completed and in hideout, restart")
        self.manageStashAndInventory()

        original_area_raw_name = poe_bot.game_data.area_raw_name
        portals = poe_bot.game_data.entities.town_portals
        if len(portals) == 0:
          self.cache.reset()
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

    # TODO move to if self.cache.stage == 2
    self.current_map = getMapArea(poe_bot.game_data.area_raw_name)(poe_bot=poe_bot, mapper=self)
    self.current_map.complete()
    self.onMapFinishedFunction()

  def exploreRoutine(self, *args, **kwargs):
    poe_bot = self.poe_bot
    mapper = self
    settings = mapper.settings
    current_area = self.current_map

    # if it runs map for more than
    if current_area.started_running_map_at + settings.max_map_run_time < time.time():
      poe_bot.logger.writeLine(
        f"[MapArea.exploreRoutine] started at {current_area.started_running_map_at}, limit {settings.max_map_run_time}, time now {time.time()}, stuck"
      )
      poe_bot.on_stuck_function()
    # activate mirror if find it
    if settings.force_deli is not False and mapper.cache.delirium_mirror_activated is False:
      delirium_mirror = next(
        (
          e
          for e in poe_bot.game_data.entities.all_entities
          if e.path == "Metadata/Terrain/Gallows/Leagues/Delirium/Objects/DeliriumInitiator" and e.is_opened is not True and e.isOnPassableZone()
        ),
        None,
      )
      if delirium_mirror:
        DeliriumEncounter(delirium_mirror).doEncounter()
        mapper.cache.delirium_mirror_activated = True
        mapper.cache.save()
        return True

    # TODO, supposed to step on those shard packs to open them
    # Metadata/Monsters/LeagueDelirium/DoodadDaemons/DoodadDaemonShardPack<smth> or 1 only is metadata key for those things
    if settings.force_deli:
      pass

    # TODO custom break function to check if there are any other activators which are closer on our way
    if current_area.activators_on_map:
      activators_on_map = list(
        filter(lambda e: e.is_targetable is not False and e.path in current_area.activators_on_map, poe_bot.game_data.entities.all_entities)
      )
      if len(activators_on_map) != 0:
        activator_on_map = activators_on_map[0]
        poe_bot.mover.goToEntitysPoint(activator_on_map)
        activator_on_map.clickTillNotTargetable()
        return True
    if settings.force_kill_rares is not False:
      mob_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities_rares if e.isOnPassableZone()), None)
      if mob_to_kill:
        res = True
        while res is not None:
          res = poe_bot.mover.goToEntitysPoint(mob_to_kill, custom_break_function=poe_bot.loot_picker.collectLoot)
          mob_to_kill = next(
            (e for e in poe_bot.game_data.entities.attackable_entities_rares if e.id == mob_to_kill.id and e.isOnPassableZone()), None
          )
          if mob_to_kill is None:
            break
        if mob_to_kill is not None:
          poe_bot.combat_module.killUsualEntity(mob_to_kill)
        return True
    if settings.force_kill_blue is not False:
      mob_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities_blue if e.isOnPassableZone()), None)
      if mob_to_kill:
        poe_bot.combat_module.killUsualEntity(mob_to_kill)
        return True
    if settings.do_essences is not False:
      if len(poe_bot.game_data.entities.essence_monsters) != 0:
        print("got essenced mobs, killing them")
        for entity in poe_bot.game_data.entities.essence_monsters:
          poe_bot.combat_module.killUsualEntity(entity=entity)
        return True
      essence = next(
        (e for e in poe_bot.game_data.entities.all_entities if e.is_targetable is True and ESSENCES_KEYWORD in e.path and e.isOnPassableZone()), None
      )
      if essence:
        essence_encounter = EssenceEncounter(poe_bot, essence)
        essence_encounter.doEncounter()
        poe_bot.loot_picker.collectLoot()
        return True
    if settings.force_breaches is not False:
      breach_entity = next(
        (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/MiscellaneousObjects/Breach/BreachObject"), None
      )
      if breach_entity:
        BreachEncounter(poe_bot, breach_entity).doEncounter()
        return True
    if settings.do_rituals is not False:
      ritual_entity = next(
        (
          e
          for e in poe_bot.game_data.entities.all_entities
          if e.path == "Metadata/Terrain/Leagues/Ritual/RitualRuneInteractable" and e.id not in mapper.cache.ritual_ignore_ids
        ),
        None,
      )
      if ritual_entity:
        poe_bot.mover.goToEntitysPoint(ritual_entity, min_distance=100)
        poe_bot.game_data.minimap_icons.update()
        corresponding_icon = next((i for i in poe_bot.game_data.minimap_icons.icons if i.id == ritual_entity.id), None)
        if not corresponding_icon:
          poe_bot.mover.goToEntitysPoint(ritual_entity, min_distance=50)
        poe_bot.game_data.minimap_icons.update()
        corresponding_icon = next((i for i in poe_bot.game_data.minimap_icons.icons if i.id == ritual_entity.id), None)
        if not corresponding_icon:
          print("ritual minimap icon is not in hud, ignoring")
          mapper.cache.ritual_ignore_ids.append(ritual_entity.id)
          mapper.cache.save()
          return True
        if corresponding_icon.name == "RitualRuneFinished":
          print("according to minimap icon data, ritual is finished")
          mapper.cache.ritual_ignore_ids.append(ritual_entity.id)
          mapper.cache.save()
          return True
        RitualEncounter(poe_bot, ritual_entity).doEncounter()
        mapper.cache.ritual_ignore_ids.append(ritual_entity.id)
        mapper.cache.save()
        return True
    # TODO map bossrooms
    # kill map bosses if theyre presented on maps
    # if self.ignore_bossroom is None:
    #   self.setIgnoreBossroom()
    # if self.ignore_bossroom is False and self.current_map.ignore_bossroom is False:
    #   if self.current_map.bossroom_activator:
    #     bossroom_activator = next( (e for e in poe_bot.game_data.entities.all_entities if e.is_targetable is True and e.path == self.current_map.bossroom_activator), None)
    #     if bossroom_activator:
    #       bossroom_activator.clickTillNotTargetable()
    #       return True
    #   bossrooms = self.seekForBossrooms()
    #   if len(bossrooms) != 0:
    #     bossroom = bossrooms[0]
    #     self.clearBossroom(bossroom=bossrooms[0])
    #     self.temp.cleared_bossrooms.append(bossroom.id)
    #     self.temp.save()
    #     return True

    # TODO sometimes boss spawn can be outside of passable area, or activators for boss
    map_boss = next(
      (
        e
        for e in self.poe_bot.game_data.entities.unique_entities
        if e.render_name not in ["Volatile Core"] and e.life.health.current != 0 and e.is_hostile is not False and e.isOnPassableZone()
      ),
      None,
    )
    # if current_area.boss_render_names:
    #   map_boss = next( (e for e in self.poe_bot.game_data.entities.unique_entities if e.life.health.current != 0 and e.render_name in current_area.boss_render_names and e.isOnPassableZone()), None)
    if map_boss:
      current_area.killMapBoss(map_boss)
      mapper.cache.map_boss_killed = True
      mapper.cache.save()
      # TODO is it used?
      mapper.cache.map_boss_killed = True
      mapper.cache.killed_map_bosses_render_names.append(map_boss.render_name)
      return True
    if mapper.can_pick_drop is None:
      if len(poe_bot.ui.inventory.getFilledSlots()) > 51:
        mapper.can_pick_drop = False
      else:
        mapper.can_pick_drop = True
    if mapper.can_pick_drop is not False:
      loot_collected = poe_bot.loot_picker.collectLoot()
      if loot_collected is True:
        if len(poe_bot.ui.inventory.getFilledSlots()) > 51:
          mapper.can_pick_drop = False
        else:
          mapper.can_pick_drop = True
        return True

    # TODO passable transitions
    # TODO check if area is on a currently passable area or somewhere around
    # area_transitions = list(filter(lambda e: e.rarity == 'White' and e.render_name != 'Arena' and e.id not in mapper.temp.visited_transitions_ids and e.id not in unvisited_transitions_ids, poe_bot.game_data.entities.area_transitions))
    # unvisited_transitions_ids = list(map(lambda e: e['i'], mapper.cache.unvisited_transitions))
    # area_transitions = list(filter(lambda e:
    #   e.rarity == 'White'
    #   and e.is_targetable == True
    #   and e.render_name != ''
    #   and e.render_name != "Twisted Burrow" # affliction enterance
    #   and e.path != "Metadata/Terrain/Leagues/Azmeri/WoodsEntranceTransition" # affliction enterance
    #   and e.path != "Metadata/MiscellaneousObjects/PortalToggleableNew" # affliction enterance
    #   and e.path != "Metadata/MiscellaneousObjects/PortalToggleable" # affliction enterance
    #   and e.render_name != self.arena_render_name
    #   and e.render_name not in self.transitions_to_ignore_render_names
    #   # and (len(self.current_map.transitions_to_ignore_render_names) != 0 and e.render_name not in self.current_map.transitions_to_ignore_render_names)
    #   and e.render_name != 'Syndicate Laboratory' # betrayal Laboratory
    #   and "Metadata/Terrain/Leagues/Incursion/Objects/IncursionPortal" not in e.path # alva
    #   and 'Metadata/QuestObjects/Labyrinth/LabyrinthTrialPortal' not in e.path # lab trial
    #   and e.id not in mapper.cache.visited_transitions_ids
    #   and e.id not in unvisited_transitions_ids
    #   and e.id not in mapper.cache.currently_ignore_transitions_id
    #   and e.render_name != "Starfall Crater",
    # poe_bot.game_data.entities.area_transitions))
    # if len(area_transitions) != 0:
    #   new_transition_found = False
    #   for area_transition in area_transitions:
    #     object_reachable = poe_bot.game_data.terrain.checkIfPointPassable(area_transition.grid_position.x, area_transition.grid_position.y)
    #     if object_reachable is False:
    #       mapper.cache.currently_ignore_transitions_id.append(area_transition.id)
    #     else:
    #       print(f'found new transition {str(area_transition)}')
    #       mapper.cache.unvisited_transitions.append(area_transition.raw)
    #       new_transition_found = True
    #   if new_transition_found is True:
    #     return True
    #   return True
    return False

  # TODO open portal with first attempt?
  def onMapFinishedFunction(self):
    poe_bot = self.poe_bot
    if hasattr(poe_bot.game_data.terrain, "currently_passable_area") is False:
      poe_bot.game_data.terrain.getCurrentlyPassableArea()
    self.cache.map_streak += 1
    self.cache.map_completed = True
    self.cache.save()
    print(f"[Mapper] onMapFinishedFunction call at {time.time()}")
    print("#TODO self.deactivateDeliriumMirror()")
    """
    poe_bot.ui.delirium_ui.update()
    if poe_bot.ui.delirium_ui.disable_button != None:
      poe_bot.ui.delirium_ui.disable_button.click()
    """
    map_finish_time = time.time()
    time_now = time.time()
    rev = bool(random.randint(0, 1))
    while time_now < map_finish_time + 1:
      poe_bot.refreshInstanceData()
      point_to_run_around = [self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y]
      # make sure it wont activate the tower
      if self.settings.complete_tower_maps is False:
        tower_activator_entity = next(
          (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/MiscellaneousObjects/Endgame/TowerCompletion"), None
        )
        if tower_activator_entity:
          point_to_run_around = poe_bot.game_data.terrain.pointToRunAround(
            point_to_run_around_x=tower_activator_entity.grid_position.x,
            point_to_run_around_y=tower_activator_entity.grid_position.y,
            distance_to_point=75,
            reversed=rev,
          )
      killed_someone = poe_bot.combat_module.clearLocationAroundPoint({"X": point_to_run_around[0], "Y": point_to_run_around[1]}, detection_radius=50)
      res = self.exploreRoutine()
      if killed_someone is False and res is False:
        point = poe_bot.game_data.terrain.pointToRunAround(
          point_to_run_around_x=point_to_run_around[0], point_to_run_around_y=point_to_run_around[1], distance_to_point=15, reversed=rev
        )
        poe_bot.mover.move(grid_pos_x=point[0], grid_pos_y=point[1])
        poe_bot.refreshInstanceData()
      time_now = time.time()

      # find point which is far away from
      # {"ls":[241,312],"p":"Metadata/MiscellaneousObjects/Endgame/TowerCompletion","i":11,"t":1,"b":1,"gp":[553,4020],"wp":[6031,43716,-613],"rn":"Precursor Beacon","et":"IngameIcon"}

    # check if we did 3 of 3 or 4of4 rituals, if true, defer\whatever items
    self.settings.do_rituals_buyout_function()

    poe_bot.refreshInstanceData()
    # TODO poe1
    # print(f'[Mapper.onMapFinishedFunction] leveling gems at {time.time()}')
    # for i in range(random.randint(3,5)):
    #   res = poe_bot.helper_functions.lvlUpGem()
    #   if res != 1:
    #     break
    i = 0
    random_click_iter = 0
    can_click_portal_after = time.time()
    while True:
      while True:
        poe_bot.refreshInstanceData()
        res = poe_bot.loot_picker.collectLoot()
        if res is False:
          break
      if poe_bot.game_data.invites_panel_visible is not False:
        print("[Mapper.onMapFinishedFunction] already loading")
      else:
        i += 1
        random_click_iter += 1
        if random_click_iter > 15:
          print("[Mapper] cannot get to portal, clicking random point around the player")
          poe_bot.ui.closeAll()
          # points = getFourPoints(x = poe_bot.game_data.player.grid_pos.x, y = poe_bot.game_data.player.grid_pos.y, radius = random.randint(7,13))
          # point = random.choice(points)
          point = poe_bot.game_data.terrain.pointToRunAround(
            poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y, distance_to_point=random.randint(15, 25), check_if_passable=True
          )
          pos_x, pos_y = poe_bot.getPositionOfThePointOnTheScreen(y=point[1], x=point[0])
          pos_x, pos_y = poe_bot.convertPosXY(x=pos_x, y=pos_y)
          poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
          poe_bot.bot_controls.mouse.click()
          random_click_iter = random.randint(0, 3)
        if i > 200:
          poe_bot.raiseLongSleepException("portal bug")
        nearby_portals = list(filter(lambda e: e.distance_to_player < 50, poe_bot.game_data.entities.town_portals))
        if len(nearby_portals) == 0:
          # TODO poe_bot.helper_functions.openPortal()
          openPortal()
          nearby_portals = list(filter(lambda e: e.distance_to_player < 50, poe_bot.game_data.entities.town_portals))

        if len(nearby_portals) != 0 and time.time() > can_click_portal_after:
          print("[Mapper.onMapFinishedFunction] clicking on portal")
          poe_bot.refreshInstanceData()
          nearby_portals = list(filter(lambda e: e.distance_to_player < 50, poe_bot.game_data.entities.town_portals))
          nearby_portals.sort(key=lambda e: e.distance_to_player)
          nearest_portal = nearby_portals[0]
          nearest_portal.click()
          can_click_portal_after = time.time() + random.randint(5, 15) / 10
          print(f"[Mapper.onMapFinishedFunction] can_click_portal_after {can_click_portal_after}")
      poe_bot.combat_module.clearLocationAroundPoint(
        {"X": self.poe_bot.game_data.player.grid_pos.x, "Y": self.poe_bot.game_data.player.grid_pos.y}, detection_radius=50
      )
      self.exploreRoutine()


class MapArea(PoeBotComponent):
  boss_render_names: List[str] = []
  activators_on_map: List[str] = []
  entities_to_ignore_in_bossroom_path_keys: List[str] = []
  boss_clear_around_radius: int = 50

  def __init__(self, poe_bot, mapper: Mapper2):
    super().__init__(poe_bot)
    self.mapper = mapper

  # TODO rewrite some breaks to return, merge %of discovery with mapper.isMapCompleted
  def complete(self):
    mapper = self.mapper
    poe_bot = self.poe_bot

    self.started_running_map_at = time.time()

    tsp = poe_bot.pather.tsp

    poe_bot.refreshInstanceData()
    while mapper.cache.map_completed is False:
      print("generating pathing points")
      tsp.generatePointsForDiscovery()
      # if mapper.settings.boss_rush is True:
      #   discovery_points = tsp.sortedPointsForDiscovery(poe_bot.pather.utils.getFurthestPoint(poe_bot.game_data.player.grid_pos.toList()))
      # else:
      discovery_points = tsp.sortedPointsForDiscovery()
      print(f"len(discovery_points) {len(discovery_points)}")
      discovery_points = list(filter(lambda p: poe_bot.game_data.terrain.checkIfPointPassable(p[0], p[1]), discovery_points))
      print(f"len(discovery_points) {len(discovery_points)} after sorting")
      if len(discovery_points) == 0:
        print("len(discovery_points) == 0 after points generation")
        mapper.cache.map_completed = True
        break
      point_to_go = discovery_points.pop(0)
      while point_to_go is not None and mapper.cache.map_completed is False:
        # check if point needs to be explored
        need_to_explore = poe_bot.game_data.terrain.isPointVisited(point_to_go[0], point_to_go[1])
        # TODO rewrite block below
        if need_to_explore is True:
          print(f"exploring point {point_to_go}")
        else:
          print(f"surrounding around {point_to_go} discovered, skipping")
          try:
            point_to_go = discovery_points.pop(0)
          except:
            point_to_go = None
          continue
        print(f"point_to_go {point_to_go}")
        # endblock

        # go to point to make it explored
        result = poe_bot.mover.goToPoint(
          point=point_to_go,
          min_distance=50,
          release_mouse_on_end=False,
          custom_break_function=self.mapper.exploreRoutine,
          step_size=random.randint(30, 35),
        )
        # then, it result is True, False or None
        print(f"[MapArea.complete] mover.goToPoint result {result}")

        if self.mapper.isMapCompleted() is True:
          mapper.cache.map_completed = True
          break

        # if mapper.settings.boss_rush is True and mapper.cache.map_boss_killed is True:
        #   print(f'[MapArea.complete] killed map boss on boss rush')
        #   mapper.cache.map_completed = True
        #   break

        # TODO below is block for multi layerd maps
        # check if we have transitions (excluding bossrooms, vaal, #TODO hideout, betrayal,)
        # if len(mapper.temp.unvisited_transitions):
        #   need_to_go_to_next_transition = can_go_to_another_transition
        #   if mapper.boss_rush is True:
        #     need_to_go_to_next_transition = True
        #   else:
        #     print(f'mapper.temp.unvisited_transitions {mapper.temp.unvisited_transitions}')
        #     passable_area_discovered_percent = poe_bot.game_data.terrain.getPassableAreaDiscoveredForPercent(total=False)
        #     print(f'passable_area_discovered_percent {passable_area_discovered_percent}')
        #     # check if current area visited percent > 75%:
        #     if passable_area_discovered_percent > 0.75:
        #       need_to_go_to_next_transition = True

        #   if need_to_go_to_next_transition is True:
        #     # check if unvisited transitions == 1: otherwise raise error
        #     raw_transition_entity = mapper.temp.unvisited_transitions.pop(0)
        #     # mapper.temp.save()
        #     transition_entity = Entity(poe_bot, raw_transition_entity)
        #     while True:
        #       res = mover.goToPoint(
        #         point=[transition_entity.grid_position.x, transition_entity.grid_position.y],
        #         min_distance=30,
        #         release_mouse_on_end=False,
        #         custom_continue_function=build.usualRoutine,
        #         custom_break_function=poe_bot.loot_picker.collectLoot,
        #         step_size=random.randint(25,33)
        #       )
        #       if res is None:
        #         break
        #     mover.enterTransition(transition_entity)
        #     poe_bot.refreshInstanceData()
        #     exit_transitions = []
        #     look_for_exit_transition = 0
        #     while len(exit_transitions) == 0:
        #       look_for_exit_transition += 1
        #       if look_for_exit_transition == 20 or look_for_exit_transition == 40:
        #         poe_bot.backend.forceRefreshArea()
        #       if look_for_exit_transition > 100:
        #         poe_bot.on_stuck_function()
        #         raise Exception('look_for_exit_transition > 100:')
        #         # poe_bot.raiseLongSleepException('look_for_exit_transition > 100:')
        #         # break
        #       poe_bot.refreshInstanceData(reset_timer=True)
        #       exit_transitions = list(filter(lambda e: e.rarity == 'White' and e.id != transition_entity.id, poe_bot.game_data.entities.area_transitions))

        #     exit_transition = exit_transitions[0]
        #     mapper.temp.visited_transitions_ids.append(exit_transition.id)
        #     mapper.temp.visited_transitions_ids.append(transition_entity.id)
        #     mapper.temp.transition_chain.append(transition_entity.raw)
        #     mapper.temp.save()
        #     can_go_to_another_transition = False
        #     break
        # ENDBLOCK

        # TODO useful?
        # if map was discovered
        if (
          mapper.settings.boss_rush is False
          and (mapper.settings.atlas_explorer is False or mapper.cache.map_boss_killed is True)
          and poe_bot.game_data.terrain.getPassableAreaDiscoveredForPercent(total=True) >= mapper.settings.discovery_percent
        ):
          if mapper.cache.unvisited_transitions != []:
            print("willing to finish the map, but got another transition to visit")
            continue
          print(f"discovered for more than {int(mapper.settings.discovery_percent * 100)} percents, breaking")
          mapper.cache.map_completed = True
          break

        # if we arrived to discovery point and nothing happened
        if result is None:
          while True:
            if len(discovery_points) == 0:
              if mapper.settings.boss_rush is True or mapper.settings.discovery_percent > mapper.settings.default_discovery_percent:
                print("mapper.boss_rush is True or custom_discovery_percent and len(discovery_points) == 0")
                print("generating new points")
                point_to_go = None
                break
              else:
                point_to_go = None
                mapper.cache.map_completed = True
                print("len(discovery_points) == 0, breaking")
                break

            point_to_go = discovery_points.pop(0)
            print(f"willing to explore next point {point_to_go}")
            need_to_explore = poe_bot.game_data.terrain.isPointVisited(point_to_go[0], point_to_go[1])

            if need_to_explore is True:
              print(f"exploring point {point_to_go}")
              break
            else:
              print(f"surrounding around {point_to_go} discovered, skipping")
              continue

        poe_bot.refreshInstanceData()
        poe_bot.last_action_time = 0

    # main loop from quest.py and maps.py

  # TODO check for quest.py for better samples
  def killMapBoss(self, entity: Entity):
    start_time = time.time()
    print(f"[MapArea.killmapboss] {start_time} {entity.raw}")
    boss_entity = entity
    boss_entity_id = boss_entity.id
    if boss_entity.is_targetable is False or boss_entity.is_attackable is False:
      print("boss is not attackable or not targetable, going to it and activating it")
      while True:
        # if self.activator_inside_bossroom is not None and self.activated_activator_in_bossroom is False:
        #   activator:Entity = next((e for e in poe_bot.game_data.entities.all_entities if e.path == self.current_map.activator_inside_bossroom), None)
        #   if activator:
        #     if activator.is_targetable is True:
        #       self.activate(activator)
        #     self.activated_activator_in_bossroom = True
        res = poe_bot.mover.goToEntitysPoint(
          boss_entity,
          min_distance=15,
          # custom_break_function=poe_bot.loot_picker.collectLoot,
          release_mouse_on_end=False,
          step_size=random.randint(25, 33),
          # TODO poe1
          # possible_transition = self.current_map.possible_transition_on_a_way_to_boss
        )
        if res is None:
          break
      last_boss_pos_x, last_boss_pos_y = boss_entity.grid_position.x, boss_entity.grid_position.y

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
        if boss_entity.is_targetable is False or boss_entity.is_attackable is False:
          print(f"boss is not attackable or not targetable, going to it clearing around it {boss_entity.raw}")
          killed_someone = poe_bot.combat_module.clearLocationAroundPoint(
            {"X": boss_entity.grid_position.x, "Y": boss_entity.grid_position.y},
            detection_radius=self.boss_clear_around_radius,
            ignore_keys=self.entities_to_ignore_in_bossroom_path_keys,
          )
          if killed_someone is False:
            point = poe_bot.game_data.terrain.pointToRunAround(
              point_to_run_around_x=last_boss_pos_x,
              point_to_run_around_y=last_boss_pos_y,
              distance_to_point=15,
            )
            poe_bot.mover.move(grid_pos_x=point[0], grid_pos_y=point[1])
          poe_bot.refreshInstanceData(reset_timer=killed_someone)
        else:
          print("boss is attackable and targetable, going to kill it")
          poe_bot.combat_module.killUsualEntity(boss_entity, max_kill_time_sec=30)
          last_boss_pos_x, last_boss_pos_y = boss_entity.grid_position.x, boss_entity.grid_position.y
    else:
      print("boss is attackable and targetable, going to kill it")
      poe_bot.combat_module.killUsualEntity(boss_entity)


# add custom logic or whatever thing
class MapBackwash(MapArea):
  boss_render_names = ["Yaota, the Loathsome"]


class MapDecay(MapArea):
  boss_render_names = ["The Fungus Behemoth"]


class MapBloomingField(MapArea):
  boss_render_names = ["The Black Crow"]


class MapFortress(MapArea):
  boss_render_names = ["Pirasha, the Forgotten Prisoner"]
  # "Metadata/Terrain/Gallows/Act2/2_2/Objects/BossChainAnchor_1"
  # "Metadata/Terrain/Gallows/Act2/2_2/Objects/BossChainAnchor_2"
  # "Metadata/Terrain/Gallows/Act2/2_2/Objects/BossChainAnchor_3"
  boss_activators_paths = ["Metadata/Terrain/Gallows/Act2/2_2/Objects/BossChainAnchor"]
  # or list(map(lambda i: f"Metadata/Terrain/Gallows/Act2/2_2/Objects/BossChainAnchor_{i}"), [1,2,3])


class MapLostTowers(MapArea):
  # init, change strategy to boss rush
  pass


MAP_AREAS_BY_KEYS_DICT = {
  "MapLostTowers": MapLostTowers,
  "MapDecay": MapDecay,
  "MapBloomingField": MapBloomingField,
}


def getMapArea(current_area_string: str) -> Type[MapArea]:
  return MAP_AREAS_BY_KEYS_DICT.get(current_area_string, MapArea)


# settings
prefer_high_tier = True
alch_map_if_possible = True


# In[ ]:


default_config = {
  "REMOTE_IP": "172.27.109.227sd",  # z2
  "unique_id": "poe_2_test",
  "build": "EaBallistasEle",
  "max_lvl": 101,
  "chromatics_recipe": True,
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
MAX_LVL = config.get("max_lvl")
CHROMATICS_RECIPE = config["chromatics_recipe"]
BUILD_NAME = config["build"]  # build_name
force_reset_temp = config["force_reset_temp"]
print(
  f"running aqueduct using: REMOTE_IP: {REMOTE_IP} unique_id: {UNIQUE_ID} max_lvl: {MAX_LVL} chromatics_recipe: {CHROMATICS_RECIPE} force_reset_temp: {force_reset_temp}"
)


# In[ ]:


poe_bot = Poe2Bot(unique_id=UNIQUE_ID, remote_ip=REMOTE_IP)
poe_bot.refreshAll()
# poe_bot.game_data.terrain.getCurrentlyPassableArea()
# TODO move it to poe_bot.refreshAll() refreshed_data["c_t"] ## "c_t":0 - mouse || "c_t":1 - wasd
poe_bot.mover.setMoveType("wasd")


# In[ ]:


# set up build

# from utils.combat import InfernalistZoomancer
# poe_bot.combat_module.build = InfernalistZoomancer(poe_bot=poe_bot)

# from utils.combat import GenericBuild2
# poe_bot.combat_module.build = GenericBuild2(poe_bot=poe_bot)

# from utils.combat import GenericBuild2Cautious
# poe_bot.combat_module.build = GenericBuild2Cautious(poe_bot=poe_bot)

# from utils.combat import PathfinderPoisonConc2
# poe_bot.combat_module.build = PathfinderPoisonConc2(poe_bot=poe_bot)
# poe_bot.combat_module.build.auto_flasks.life_flask_recovers_es = True
# poe_bot.combat_module.build.auto_flasks.hp_thresh = 0.70

# from utils.combat import BarrierInvocationInfernalist
# poe_bot.combat_module.build = BarrierInvocationInfernalist(poe_bot)

from utils.combat import InfernalistMinion

poe_bot.combat_module.build = InfernalistMinion(poe_bot)


# In[7]:


# default mover function
poe_bot.mover.default_continue_function = poe_bot.combat_module.build.usualRoutine


# In[ ]:


mapper_settings = MapperSettings({})
# adjust mapper settings below
mapper_settings.do_rituals = True
# mapper_settings.do_rituals_buyout_function =
mapper_settings.high_priority_maps = ["Bluff"]
mapper_settings.complete_tower_maps = False
mapper_settings.min_map_tier = 4
mapper_settings.anoint_maps = False


# In[ ]:


mapper = Mapper2(poe_bot=poe_bot, settings=mapper_settings)


# In[ ]:


# set up loot filter
from utils.loot_filter import PickableItemLabel

ARTS_TO_PICK = ["Art/2DItems/Maps/DeliriumSplinter.dds", "Art/2DItems/Maps/"]

# big piles of gold
for tier in range(2, 17):
  ARTS_TO_PICK.append(f"Art/2DItems/Currency/Ruthless/CoinPileTier{tier}.dds")
# waystones
# for tier in range(mapper.settings.min_map_tier,mapper.settings.max_map_tier):
# for tier in range(1,17):
# ARTS_TO_PICK.append(f"Art/2DItems/Maps/EndgameMaps/EndgameMap{tier}.dds")


def isItemHasPickableKey(item_label: PickableItemLabel):
  if item_label.icon_render in ARTS_TO_PICK:
    return True
  elif item_label.icon_render.startswith("Art/2DItems/Currency/") and "/Ruthless/" not in item_label.icon_render: # All currency
    return True
  elif item_label.icon_render.startswith("Art/2DItems/Maps/EndgameMaps/"): # All maps
    return True
  return False


poe_bot.ui.inventory.update()

# remove line below in case you want it to pick ALL items
poe_bot.loot_picker.loot_filter.special_rules = [isItemHasPickableKey]


# In[ ]:


# TODO make it possible to wrap it into while loop, if ok, move whole mapper to utils/mapper2.py
mapper.run()


# In[ ]:


raise Exception("Script ended, restart")


# In[ ]:


mapper.doPreparations()


# In[ ]:


# testing below, wont be executed, debugging only


# In[15]:


poe_bot.refreshAll()


# In[ ]:


mapper.isMapCompleted()


# In[ ]:


mapper.cache.stage, mapper.cache.map_completed


# In[ ]:


mapper.cache.map_completed = False
mapper.cache.save()


# In[ ]:


mapper.cache.stage = 2
mapper.cache.save()


# In[ ]:


poe_bot.game_data.terrain.getCurrentlyPassableArea()


# In[ ]:


hasattr(poe_bot.game_data.terrain, "currently_passable_area")


# In[ ]:


poe_bot.game_data.terrain.currently_passable_area


# In[ ]:


poe_bot.ui.ritual_ui.update()


# In[ ]:


# open portal and enter it
def openPortal():
  poe_bot.bot_controls.releaseAll()

  time.sleep(random.randint(40, 80) / 100)
  pos_x, pos_y = random.randint(709, 711), random.randint(694, 696)
  pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y, safe=False)
  poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
  time.sleep(random.randint(40, 80) / 100)
  poe_bot.bot_controls.mouse.click()
  time.sleep(random.randint(30, 60) / 100)


map_finish_time = time.time()
time_now = time.time()
rev = bool(random.randint(0, 1))
while time_now < map_finish_time + 1:
  poe_bot.refreshInstanceData()
  killed_someone = poe_bot.combat_module.clearLocationAroundPoint(
    {"X": poe_bot.game_data.player.grid_pos.x, "Y": poe_bot.game_data.player.grid_pos.y}, detection_radius=50
  )
  res = poe_bot.loot_picker.collectLoot()
  if killed_someone is False and res is False:
    point = poe_bot.game_data.terrain.pointToRunAround(
      point_to_run_around_x=poe_bot.game_data.player.grid_pos.x,
      point_to_run_around_y=poe_bot.game_data.player.grid_pos.y,
      distance_to_point=15,
      reversed=rev,
    )
    poe_bot.mover.move(grid_pos_x=point[0], grid_pos_y=point[1])
    poe_bot.refreshInstanceData()
  time_now = time.time()

i = 0
random_click_iter = 0
can_click_portal_after = time.time()
while True:
  while True:
    poe_bot.refreshInstanceData()
    res = poe_bot.loot_picker.collectLoot()
    if res is False:
      break

  if poe_bot.game_data.invites_panel_visible is not False:
    print("[onmapfinishfunction] already loading")
  else:
    i += 1
    random_click_iter += 1
    if random_click_iter > 15:
      print("[Mapper] cannot get to portal, clicking random point around the player")
      poe_bot.ui.closeAll()
      # point = poe_bot.game_data.terrain.pointToRunAround(poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y, distance_to_point=random.randint(15,25), check_if_passable=True)
      random_click_iter = random.randint(0, 3)
    if i > 200:
      poe_bot.raiseLongSleepException("portal bug")
    nearby_portals = list(filter(lambda e: e.distance_to_player < 50, poe_bot.game_data.entities.town_portals))
    if len(nearby_portals) == 0:
      openPortal()
    nearby_portals = list(filter(lambda e: e.distance_to_player < 50, poe_bot.game_data.entities.town_portals))
    if len(nearby_portals) != 0:
      poe_bot.helper_functions.getToPortal(check_for_map_device=False, refresh_area=False)
  poe_bot.combat_module.clearLocationAroundPoint(
    {"X": poe_bot.game_data.player.grid_pos.x, "Y": poe_bot.game_data.player.grid_pos.y}, detection_radius=50
  )
  poe_bot.loot_picker.collectLoot()


# In[ ]:





# In[ ]:


raise "unreachable"


# In[ ]:


poe_bot.refreshAll()
poe_bot.game_data.terrain.getCurrentlyPassableArea()


# In[ ]:


import matplotlib.pyplot as plt

plt.imshow(poe_bot.game_data.terrain.passable)


# In[ ]:


poe_bot.ui.stash.update()

# waystone reforge logic

max_tier_to_recycle = 11

stash = poe_bot.ui.stash
stash.update()
waystone_items = list(filter(lambda i: i.map_tier != 0, stash.current_tab_items))
waystones_by_tier = {}
for item in waystone_items:
  waystone_tier = item.map_tier
  if waystone_tier > max_tier_to_recycle:
    continue
  if waystones_by_tier.get(waystone_tier, 0) == 0:
    waystones_by_tier[waystone_tier] = []
  waystones_by_tier[waystone_tier].append(item)

waystone_tiers_sorted = list(waystones_by_tier.keys())
waystone_tiers_sorted.sort()

collected_items_count = 0
poe_bot.ui.inventory.update()
max_items_can_get = len(poe_bot.ui.inventory.getEmptySlots())
for k in waystone_tiers_sorted:
  waystones_amount = len(waystones_by_tier[k])
  if waystones_amount // 3 == 0:
    continue

  collected_items_count += waystones_amount
  if collected_items_count > max_items_can_get:
    break
  poe_bot.ui.clickMultipleItems(waystones_by_tier[k])


# In[ ]:


# ritual defer logic

"""
manually calculating weights

// https://poe2scout.com/economy/ritual
table_el = document.querySelector("#root > div.css-e2yq0w > div.css-1r2vj6j > div > div > div.MuiTableContainer-root.css-1o4uwu > table > tbody")
ind_elements = Array.from(table_el.querySelectorAll("tr.MuiTableRow-root"))
prices = ind_elements.map(el=>{
  let name = el.querySelector('span').textContent;
  let price = el.querySelector('span.price-value').textContent;
  return ([name, price])
})
texts =prices.map(el=>{
  return (`"${el[0]}": ${el[1]},`)
})
console.log(texts.join(`\n`))
"""
ritual_items_weights = {
  "An Audience with the King": 1600.0,
  # omens
  "Omen of Sinistral Erasure": 5430.0,
  "Omen of Dextral Annulment": 2896.0,
  "Omen of Sinistral Annulment": 2534.0,
  "Omen of Dextral Erasure": 1991.0,
  "Omen of Whittling": 1448.0,
  "Omen of Corruption": 99.0,
  "Omen of Amelioration": 80.0,
  "Omen of Greater Annulment": 7.0,
  "Omen of Sinistral Alchemy": 3.0,
  "Omen of Resurgence": 3.0,
  "Omen of Sinistral Exaltation": 2.0,
  "Omen of Dextral Exaltation": 1.0,
  "Omen of Dextral Alchemy": 1.0,
  "Omen of Dextral Coronation": 1.0,
  "Omen of Greater Exaltation": 1.0,
  "Omen of Refreshment": 1.0,
  "Omen of Sinistral Coronation": 1.0,
  # currency
  "Mirror of Kalandra": 71857.0,
  "Perfect Jeweller's Orb": 350.0,
  "Divine Orb": 200.0,
  "Greater Jeweller's Orb": 18.0,
  "Orb of Annulment": 9.0,
  "Orb of Chance": 6.0,
  "Chaos Orb": 4.0,
  "Gemcutter's Prism": 1.7,
  "Artificer's Shard": 1.0,
  "Scroll of Wisdom": 1.0,
  "Arcanist's Etcher": 1.0,
  "Transmutation Shard": 1.0,
  "Exalted Orb": 1.0,
  "Lesser Jeweller's Orb": 1.0,
  "Glassblower's Bauble": 0.8,
  "Blacksmith's Whetstone": 0.5,
  "Armourer's Scrap": 0.5,
  "Orb of Alchemy": 0.4,
  "Artificer's Orb": 0.3,
  "Vaal Orb": 0.2,
  "Regal Shard": 0.1,
  "Regal Orb": 0.1,
  "Orb of Augmentation": 0.0,
  "Orb of Transmutation": 0.0,
  # ess
  "Greater Essence of Haste": 550.0,
  "Greater Essence of the Infinite": 120.0,
  "Greater Essence of Electricity": 60.0,
  "Greater Essence of Torment": 50.0,
  "Greater Essence of Sorcery": 50.0,
  "Greater Essence of the Mind": 20.0,
  "Greater Essence of Battle": 14.0,
  "Greater Essence of Enhancement": 13.0,
  "Greater Essence of Ruin": 13.0,
  "Greater Essence of Ice": 7.0,
  "Essence of Electricity": 5.0,
  "Greater Essence of the Body": 5.0,
  "Greater Essence of Flames": 5.0,
  "Essence of Ruin": 1.0,
  "Essence of Enhancement": 0.9,
  "Essence of Haste": 0.9,
  "Essence of Torment": 0.8,
  "Essence of Flames": 0.8,
  "Essence of the Body": 0.5,
  "Essence of the Infinite": 0.5,
  "Essence of Battle": 0.5,
  "Essence of Ice": 0.5,
  "Essence of the Mind": 0.5,
  "Essence of Sorcery": 0.5,
}

poe_bot.mover.stopMoving()
# TODO check if it's safe stop spot

poe_bot.ui.ritual_ui.update()

# Check if the ritual progress is complete and click the ritual button if so
if poe_bot.ui.ritual_ui.progress_current == poe_bot.ui.ritual_ui.progress_total:
  poe_bot.ui.ritual_ui.ritual_button.click()

poe_bot.ui.ritual_ui.update()

items_to_pay_attention = []
for item in poe_bot.ui.ritual_ui.items:
  # or item.unique_name
  item.name


# In[ ]:


# on map completion if some ritual was completed

# open ritual via ritual button
# TODO open ritual button is visible, screen position


poe_bot.ui.ritual_ui.update()
poe_bot.ui.ritual_ui.visible is True
poe_bot.ui.ritual_ui.tribute  # current tribute
poe_bot.ui.ritual_ui.reroll_cost  # 750 or 1000, depends on raw text
poe_bot.ui.ritual_ui.items  # items actually

interesting_items_names = ["An Audience with the King", "Divine orb"]

interesting_items = list(filter(lambda i: i.name == interesting_items_names, poe_bot.ui.ritual_ui.items))

for item in interesting_items:
  print(item.raw)
  item.hover()
  item_info = poe_bot.backend.getHoveredItemInfo()
  cost = int(item_info["tt"][-2][:-1])
  # do something with them, defer, reroll, buyout, whatever


# In[ ]:


poe_bot.area_raw_name


# In[ ]:


poe_bot.refreshAll()


# In[ ]:





# In[ ]:


if poe_bot.ui.map_device.place_map_window_opened is not True:
  print("[Mapper.activateMap] dropdown didnt open, clicking on nearby element and clicking back again")
  # TODO filter by if its in roi
  another_map_objects = list(filter(lambda m: m.id != map_obj.id, poe_bot.ui.map_device.avaliable_maps))
  nearest_map_objects = sorted(another_map_objects, key=lambda m: dist(map_obj.screen_zone.getCenter(), m.screen_zone.getCenter()))
  nearest_map_objects[0].click()
  time.sleep(random.uniform(0.15, 0.35))
  poe_bot.ui.map_device.update()
  map_obj = next((m for m in poe_bot.ui.map_device.avaliable_maps if m.id == map_obj.id))
  map_obj.click()
  time.sleep(random.uniform(0.15, 0.35))
  poe_bot.ui.map_device.update()

  # pos_x, pos_y = poe_bot.game_window.convertPosXY(100, 100)
  # poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
  # time.sleep(random.uniform(0.15, 0.35))
  # poe_bot.ui.map_device.update()
  # updated_map_obj = next( (m for m in poe_bot.ui.map_device.avaliable_maps if m.id == map_obj.id))
  # updated_map_obj.click()
  # time.sleep(random.uniform(0.15, 0.35))
  # poe_bot.ui.map_device.update()
  if poe_bot.ui.map_device.place_map_window_opened is False:
    print("[Mapper.activateMap] seems like map device bug")
    raise Exception("[Mapper.activateMap] cant open dropdown for map device #TODO click on other map element in roi and try again?")
    poe_bot.raiseLongSleepException("[Mapper.activateMap] cant open dropdown for map device #?")
poe_bot.ui.map_device.update()


# In[ ]:


# cwdt calc
max_hp = 592
max_es = 5652
fire_res = 77  # %

barrier_meta_gain = 124  # %g

trigger_cost = (max_hp + max_es) * ((100 - fire_res) / 100)
print(trigger_cost)
energy_gain = (trigger_cost / 5) * (1 + barrier_meta_gain / 100)
print(energy_gain)


# In[ ]:


poe_bot.refreshAll()


# In[ ]:


import matplotlib.pyplot as plt
from utils.utils import getFourPoints


# In[ ]:


poe_bot.loot_picker.loot_filter.special_rules = []


# In[ ]:


poe_bot.refreshAll()
poe_bot.bot_controls.disconnect()


# In[ ]:


interesting_entities = []
interesting_entities_ids = []


class Simulacrum:
  def __init__(self, poe_bot: Poe2Bot):
    self.poe_bot = poe_bot

  def scanForInterestingEntities(self, *args, **kwargs):
    for entity in self.poe_bot.game_data.entities.all_entities:
      if entity.id in interesting_entities_ids:
        continue
      # doors
      if "Metadata/Terrain/Gallows/Leagues/Delirium/Objects/Act1Doors/DeliriumDoorArena" in entity.path:
        print(f"found door {entity.raw}")
        interesting_entities.append(entity)
        interesting_entities_ids.append(entity.id)

    return False

  def getTargetableAfflictionator(self):
    return next(
      (
        e
        for e in self.poe_bot.game_data.entities.all_entities
        if e.is_targetable is True and e.path == "Metadata/Terrain/Gallows/Leagues/Delirium/Act1Town/Objects/DeliriumnatorAct1"
      ),
      None,
    )

  def clickAfflictionatorTillNotTargetable(self, afflictionator_entity: Entity):
    # TODO flasks and keep cwdt loop
    afflictionator_entity.clickTillNotTargetable()

  def activateWave(self):
    afflictionator_entity = self.getTargetableAfflictionator()
    if afflictionator_entity:
      poe_bot.mover.goToEntitysPoint(afflictionator_entity, release_mouse_on_end=True, custom_break_function=self.scanForInterestingEntities)
      self.clickAfflictionatorTillNotTargetable(afflictionator_entity)
      print("activated")

  def isWaveRunning(self):
    poe_bot = self.poe_bot
    if len(poe_bot.game_data.entities.attackable_entities) != 0:
      print("true cos attackable entities")
      return True
    if len(poe_bot.loot_picker.loot_filter.getPickableItems()) != 0:
      print("false bcs items are visible")
      return False
    if self.getTargetableAfflictionator() is not None:
      print("false, cos afflictionator is targetable")
      return False
    return True


simulacrum = Simulacrum(poe_bot=poe_bot)


# In[ ]:


simulacrum.scanForInterestingEntities()


# In[ ]:


poe_bot.refreshAll()
plt.imshow(poe_bot.pather.terrain_for_a_star)
plt.show()

# shut the doors
for interesting_entitiy in interesting_entities:
  print(f"closing door {interesting_entitiy.raw}")
  poe_bot.game_data.terrain.passable[
    interesting_entitiy.grid_position.y - 25 : interesting_entitiy.grid_position.y + 25,
    interesting_entitiy.grid_position.x - 25 : interesting_entitiy.grid_position.x + 25,
  ] = 0

poe_bot.game_data.terrain.getCurrentlyPassableArea(dilate_kernel_size=0)
plt.imshow(poe_bot.game_data.terrain.currently_passable_area)
plt.show()

poe_bot.pather.terrain_for_a_star[poe_bot.game_data.terrain.currently_passable_area != 1] = 65534
plt.imshow(poe_bot.pather.terrain_for_a_star)
plt.show()


# In[ ]:


simulacrum.activateWave()


# In[ ]:


poe_bot.refreshAll()
plt.imshow(poe_bot.game_data.terrain.terrain_image)
plt.show()
plt.imshow(poe_bot.game_data.terrain.passable)
plt.show()
# shut the doors
for interesting_entitiy in interesting_entities:
  poe_bot.game_data.terrain.passable[
    interesting_entitiy.grid_position.y - 25 : interesting_entitiy.grid_position.y + 25,
    interesting_entitiy.grid_position.x - 25 : interesting_entitiy.grid_position.x + 25,
  ] = 0

poe_bot.game_data.terrain.getCurrentlyPassableArea(dilate_kernel_size=0)
plt.imshow(poe_bot.game_data.terrain.currently_passable_area)
plt.show()


# In[ ]:


arena_center = poe_bot.pather.utils.getCenterOf(poe_bot.game_data.terrain.currently_passable_area)
print(f"arena center {arena_center}")

points = getFourPoints(*arena_center, 70)

run_points = []

for point in points[1:]:
  passable_point = poe_bot.game_data.terrain.checkIfPointPassable(*point)
  print(f"{point} {passable_point}")
  if passable_point:
    run_points.append(point)

plt.imshow(
  poe_bot.game_data.terrain.currently_passable_area[arena_center[1] - 75 : arena_center[1] + 75, arena_center[0] - 75 : arena_center[0] + 75]
)
plt.show()


# In[ ]:


wave_started_at = time.time()
is_wave_running = True
while is_wave_running:
  for point in run_points:
    poe_bot.mover.goToPoint(point, release_mouse_on_end=False)
    if time.time() + 10 > wave_started_at:
      is_wave_running = simulacrum.isWaveRunning()
    if is_wave_running is False:
      break
    print(f"wave running status {is_wave_running}")
print("completed")


# In[ ]:


poe_bot.refreshAll()


# In[ ]:


while True:
  poe_bot.refreshInstanceData()
  poe_bot.combat_module.build.useFlasks()
  # ('stacks count: {poe_bot.combat_module.build.getDemonFormStacks()}')


# In[ ]:


wave_started_at = time.time()
is_wave_running = True
while is_wave_running:
  poe_bot.refreshInstanceData()
  poe_bot.combat_module.build.useFlasks()
  if time.time() + 10 > wave_started_at:
    is_wave_running = simulacrum.isWaveRunning()
  print(f"wave running status {is_wave_running}")
  # ('stacks count: {poe_bot.combat_module.build.getDemonFormStacks()}')


# In[ ]:


anoint_ui = poe_bot.ui.anoint_ui
anoint_ui.update()

poe_bot.ui.inventory.open()


# In[ ]:





# In[ ]:


poe_bot.ui.inventory.update()
for i in poe_bot.ui.inventory.items:
  print(i.raw)


# In[ ]:


inventory = poe_bot.ui.inventory
inventory.update()

maps_can_run = list(filter(lambda i: i.getType() == "map", inventory.items))
for m in maps_can_run:
  print(m.raw)


# In[ ]:


inventory = poe_bot.ui.inventory
inventory.update()
maps_can_run = list(filter(lambda i: i.getType() == "map", inventory.items))

# identify logic
unidentified_maps = list(filter(lambda m: m.identified is False, maps_can_run))

# if mapper.settings.waystone_upgrade_to_rare_force


def identifyItems():
  poe_bot.ui.inventory.update()
  unidentified_items = list(filter(lambda m: m.identified is False, inventory.items))
  if len(unidentified_items) != 0:
    while True:
      poe_bot.refreshInstanceData()
      inventory.update()
      unidentified_items = list(filter(lambda m: m.identified is False, inventory.items))
      if len(unidentified_items) == 0:
        break
      doryani_entity = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Doryani"))
      doryani_entity.click(hold_ctrl=True)
      time.sleep(random.uniform(0.30, 0.60))
    poe_bot.ui.npc_dialogue.update()
    if poe_bot.ui.npc_dialogue.visible is True:
      poe_bot.ui.closeAll()


# In[ ]:


inventory = poe_bot.ui.inventory
inventory.update()
maps_can_run = list(filter(lambda i: i.getType() == "map", inventory.items))

# alch logic
maps_can_alch = list(filter(lambda m: m.corrupted is False and m.rarity == "Normal", maps_can_run))
alchemy_orb_stacks = list(filter(lambda i: i.name == "Orb of Alchemy", inventory.items))
alchemy_orb_count = sum(list(map(lambda i: i.items_in_stack, alchemy_orb_stacks)))
maps_can_alch = maps_can_alch[:alchemy_orb_count]


alchemy_orb_stacks[0].click(button="right")
time.sleep(random.uniform(0.20, 0.40))
poe_bot.ui.clickMultipleItems(maps_can_alch, hold_ctrl=False, hold_shift=True)

inventory = poe_bot.ui.inventory
inventory.update()
maps_can_run = list(filter(lambda i: i.getType() == "map", inventory.items))


# aug logic
maps_can_aug_regal = list(filter(lambda m: m.corrupted is False and m.identified is True and m.rarity == "Magic", maps_can_run))
maps_can_aug = []
maps_can_regal = []

for map_item in maps_can_aug_regal:
  map_mods = len(map_item.item_mods_raw) - len(map_item.getDeliriumMods())
  if map_mods == 1:
    maps_can_aug.append(map_item)
  else:
    maps_can_regal.append(map_item)

aug_stacks = list(filter(lambda i: i.name == "Orb of Augmentation", inventory.items))
aug_count = sum(list(map(lambda i: i.items_in_stack, aug_stacks)))
maps_can_aug = maps_can_aug[:aug_count]
maps_can_regal.extend(maps_can_aug)


aug_stacks[0].click(button="right")
time.sleep(random.uniform(0.20, 0.40))
poe_bot.ui.clickMultipleItems(maps_can_aug, hold_ctrl=False, hold_shift=True)
time.sleep(random.uniform(0.20, 0.40))

# regal logic
regal_stacks = list(filter(lambda i: i.name == "Regal Orb", inventory.items))
regal_count = sum(list(map(lambda i: i.items_in_stack, regal_stacks)))
maps_can_regal = maps_can_regal[:regal_count]


regal_stacks[0].click(button="right")
time.sleep(random.uniform(0.20, 0.40))
poe_bot.ui.clickMultipleItems(maps_can_regal, hold_ctrl=False, hold_shift=True)
time.sleep(random.uniform(0.20, 0.40))


# In[ ]:


inventory = poe_bot.ui.inventory
inventory.update()

maps_can_run = list(filter(lambda i: i.getType() == "map", inventory.items))
# anoint logic
maps_can_be_anointed = list(filter(lambda m: m.corrupted is False and len(m.getDeliriumMods()) < 3, maps_can_run))
for m in maps_can_be_anointed:
  print(m.raw)

OILS_TYPES_CAN_USE = OILS_BY_TIERS[: mapper.settings.anoint_max_tier]
oils_can_use = list(filter(lambda i: i.name in OILS_TYPES_CAN_USE, inventory.items))
oil_items = []
for oil in oils_can_use:
  for i in range(oil.items_in_stack):
    oil_items.append(oil)

while len(maps_can_be_anointed) != 0:
  map_item = maps_can_be_anointed.pop(0)
  map_deli_mods = map_item.getDeliriumMods()
  availiable_mods = 3 - len(map_deli_mods)
  if len(oil_items) < availiable_mods:
    break
  anoint_with = []
  for _i in range(availiable_mods):
    anoint_with.append(oil_items.pop(0))
  poe_bot.ui.anoint_ui.anointItem(map_item, anoint_with)

# for i in oil_items: print(i.raw)


# In[ ]:


for m in maps_can_run:
  print(m.raw)


# In[ ]:


can_use_oils_names = OILS_BY_TIERS[: mapper.settings.anoint_max_tier]
can_use_oils_names

for oil_name in can_use_oils_names:
  oil_items = list(filter(lambda i: i.name == oil_name, poe_bot.ui.inventory.items))
  if oil_items != 0:
    break

oil_items[0].click(hold_ctrl=True)
time.sleep(random.uniform(0.30, 0.60))
poe_bot.ui.anoint_ui.update()


def anointItem(item, consumables):
  anoint_ui = poe_bot.ui.anoint_ui
  anoint_ui.open(consumables[0])

  item.click(hold_ctrl=True)
  time.sleep(random.uniform(0.30, 0.60))
  poe_bot.ui.clickMultipleItems(consumables, hold_ctrl=True, random_sleep=False, skip_items=False)
  anoint_ui.anoint_button.click()
  anoint_ui.update()
  anoint_ui.placed_items[0].click(hold_ctrl=True)


# In[ ]:


mapper.doPreparations()


# In[ ]:


self = mapper
poe_bot.ui.inventory.update()
maps_in_inventory = list(
  filter(lambda i: i.map_tier and i.map_tier >= self.settings.min_map_tier and i.map_tier < self.settings.max_map_tier, poe_bot.ui.inventory.items)
)
maps_in_inventory.sort(key=lambda i: i.map_tier, reverse=prefer_high_tier)
# if the best map to run needs to be modified, pick consumables and modify all at once
need_to_modify_maps = False
while True:
  if self.settings.anoint_maps and len(maps_in_inventory[0].getDeliriumMods()) == 0:
    need_to_modify_maps = True
    break
  if (self.settings.waystone_upgrade_to_rare or self.settings.waystone_upgrade_to_rare_force) and maps_in_inventory[0].rarity != "Rare":
    need_to_modify_maps = True
    break
  break

need_to_modify_maps


# In[ ]:


if need_to_modify_maps:
  inventory = self.poe_bot.ui.inventory

  # TODO pick consumables or ensure that consumables are picked
  def identifyItems():
    poe_bot.ui.inventory.update()
    unidentified_items = list(filter(lambda m: m.identified is False, poe_bot.ui.inventory.items))
    if len(unidentified_items) != 0:
      while True:
        poe_bot.refreshInstanceData()
        poe_bot.ui.inventory.update()
        unidentified_items = list(filter(lambda m: m.identified is False, poe_bot.ui.inventory.items))
        if len(unidentified_items) == 0:
          break
        doryani_entity = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Doryani"))
        doryani_entity.click(hold_ctrl=True)
        time.sleep(random.uniform(0.30, 0.60))
      poe_bot.ui.npc_dialogue.update()
      if poe_bot.ui.npc_dialogue.visible is True:
        poe_bot.ui.closeAll()

  identifyItems()
  if inventory.is_opened is False:
    inventory.open()
  # alch logic
  if self.settings.waystone_upgrade_to_rare:
    maps_can_alch = list(filter(lambda m: m.corrupted is False and m.rarity == "Normal", maps_in_inventory))
    alchemy_orb_stacks = list(filter(lambda i: i.name == "Orb of Alchemy", inventory.items))
    alchemy_orb_count = sum(list(map(lambda i: i.items_in_stack, alchemy_orb_stacks)))
    maps_can_alch = maps_can_alch[:alchemy_orb_count]

    alchemy_orb_stacks[0].click(button="right")
    time.sleep(random.uniform(0.20, 0.40))
    poe_bot.ui.clickMultipleItems(maps_can_alch, hold_ctrl=False, hold_shift=True)
  # aug regal logic
  if self.settings.waystone_upgrade_to_rare_force:
    # aug logic
    maps_can_aug_regal = list(filter(lambda m: m.corrupted is False and m.identified is True and m.rarity == "Magic", maps_in_inventory))
    maps_can_aug = []
    maps_can_regal = []

    for map_item in maps_can_aug_regal:
      map_mods = len(map_item.item_mods_raw) - len(map_item.getDeliriumMods())
      if map_mods == 1:
        maps_can_aug.append(map_item)
      else:
        maps_can_regal.append(map_item)

    aug_stacks = list(filter(lambda i: i.name == "Orb of Augmentation", inventory.items))
    aug_count = sum(list(map(lambda i: i.items_in_stack, aug_stacks)))
    maps_can_aug = maps_can_aug[:aug_count]
    maps_can_regal.extend(maps_can_aug)

    aug_stacks[0].click(button="right")
    time.sleep(random.uniform(0.20, 0.40))
    poe_bot.ui.clickMultipleItems(maps_can_aug, hold_ctrl=False, hold_shift=True)
    time.sleep(random.uniform(0.20, 0.40))

    # regal logic
    regal_stacks = list(filter(lambda i: i.name == "Regal Orb", inventory.items))
    regal_count = sum(list(map(lambda i: i.items_in_stack, regal_stacks)))
    maps_can_regal = maps_can_regal[:regal_count]

    regal_stacks[0].click(button="right")
    time.sleep(random.uniform(0.20, 0.40))
    poe_bot.ui.clickMultipleItems(maps_can_regal, hold_ctrl=False, hold_shift=True)
    time.sleep(random.uniform(0.20, 0.40))
  # anoint logic
  if self.settings.anoint_maps:
    maps_can_be_anointed = list(filter(lambda m: m.corrupted is False and len(m.getDeliriumMods()) < 3, maps_in_inventory))
    for m in maps_can_be_anointed:
      print(m.raw)

    OILS_TYPES_CAN_USE = OILS_BY_TIERS[: self.settings.anoint_max_tier]
    oils_can_use = list(filter(lambda i: i.name in OILS_TYPES_CAN_USE, inventory.items))
    # TODO sort oils by tier
    oil_items = []
    for oil in oils_can_use:
      for i in range(oil.items_in_stack):
        oil_items.append(oil)

    while len(maps_can_be_anointed) != 0:
      map_item = maps_can_be_anointed.pop(0)
      map_deli_mods = map_item.getDeliriumMods()
      availiable_mods = 3 - len(map_deli_mods)
      if len(oil_items) < availiable_mods:
        break
      anoint_with = []
      for _i in range(availiable_mods):
        anoint_with.append(oil_items.pop(0))
      poe_bot.ui.anoint_ui.anointItem(map_item, anoint_with)
  self.poe_bot.ui.closeAll()


# In[ ]:


def manageStashAndInventory(self: Mapper2, pick_consumables=False):
  poe_bot = self.poe_bot
  stash = poe_bot.ui.stash
  all_stash_items = stash.getAllItems()
  if len(all_stash_items) == 0:
    stash.updateStashTemp()

  if pick_consumables:
    stash.open()
    # get items which we need to pick from stash
    # get stash tabs which itll iterate
    stash_tab_indexes: List[int] = []
    all_stash_items = stash.getAllItems()

    for key in mapper.keep_consumables:
      consumable: str = list(key.keys())[0]
      min_amount = key[consumable]
      consumable_in_inventory = list(filter(lambda i: i.name == consumable, inventory.items))
      amount_in_inventory = sum(list(map(lambda i: i.items_in_stack, consumable_in_inventory)))
      if amount_in_inventory < min_amount:
        similar_items_in_stash = list(filter(lambda i: i.name == consumable, all_stash_items))
        if len(similar_items_in_stash) != 0:
          key_stash_tabs = list(map(lambda i: i.tab_index, similar_items_in_stash))
          stash_tab_indexes.extend(key_stash_tabs)

    stash_tab_indexes = list(set(stash_tab_indexes))
    print(f"[Mapper.manageStashAndInventory] going to pick items from stash tabs {stash_tab_indexes}")

    try:
      stash_tab_indexes.pop(stash_tab_indexes.index(stash.current_tab_index))
    except Exception:
      print(f"[Mapper.manageStashAndInventory] tab with index {stash.current_tab_index} is not in list, but we ll still check it")
    stash_tab_indexes.insert(0, stash.current_tab_index)

    random.randint(6, 10)
    for stash_tab_index in stash_tab_indexes:
      stash.openTabIndex(stash_tab_index)
      pass

    # checks if all ok
    if len(self.getWaystonesCanUse(source="inventory")) == 0:
      poe_bot.raiseLongSleepException("[Mapper.manageStashAndInventory] dont have waystones after managing stash")
    if self.settings.anoint_maps_force:
      # check if best map is anointed or we have consumables to make it rare
      pass
    if self.settings.waystone_upgrade_to_rare_force:
      # check if best map is rare or we have consumables to make it rare
      pass


self = mapper


# In[ ]:


manageStashAndInventory(mapper, pick_consumables=True)


# In[ ]:


inventory.update()


# In[ ]:


self = mapper
stash = poe_bot.ui.stash
inventory = poe_bot.ui.inventory

stash_tab_indexes: List[int] = []
consumables_to_pick = []
oils_to_pick_count = 0
maps_to_pick_count = random.randint(6, 10)


all_waystones = self.getWaystonesCanUse()
if len(all_waystones) == 0:
  print("[Mapper.manageStashAndInventory] no waystones in stash.cache or inventory, rechecking stash")
  stash.updateStashTemp()
  all_waystones = self.getWaystonesCanUse()
  if len(all_waystones) == 0:
    poe_bot.raiseLongSleepException("[Mapper.manageStashAndInventory] no waystones found in stash and inventory after updating")
if all_waystones[0].source == "stash":
  print("[Mapper.manageStashAndInventory] best waystone is in stash")
  list(map(lambda i: stash_tab_indexes.append(i.tab_index), self.getWaystonesCanUse(source="stash")))

all_stash_items = stash.getAllItems()

for key in self.keep_consumables:
  consumable: str = list(key.keys())[0]
  min_amount = key[consumable]
  consumable_in_inventory = list(filter(lambda i: i.name == consumable, inventory.items))
  amount_in_inventory = sum(list(map(lambda i: i.items_in_stack, consumable_in_inventory)))
  need_to_pick = min_amount - amount_in_inventory
  if need_to_pick > 0:
    consumables_to_pick.append({consumable: need_to_pick})
    similar_items_in_stash = list(filter(lambda i: i.name == consumable, all_stash_items))
    if len(similar_items_in_stash) != 0:
      key_stash_tabs = list(map(lambda i: i.tab_index, similar_items_in_stash))
      stash_tab_indexes.extend(key_stash_tabs)


# In[ ]:


stash.update()
list(filter(lambda i: i.name == "Regal Orb", stash.current_tab_items))


# In[ ]:


self = mapper
stash = poe_bot.ui.stash
inventory = poe_bot.ui.inventory

stash_tab_indexes: List[int] = []
consumables_to_pick = []
oils_to_pick_count = 0
maps_to_pick_count = random.randint(6, 10)


all_waystones = self.getWaystonesCanUse()
if len(all_waystones) == 0:
  print("[Mapper.manageStashAndInventory] no waystones in stash.cache or inventory, rechecking stash")
  stash.updateStashTemp()
  all_waystones = self.getWaystonesCanUse()
  if len(all_waystones) == 0:
    poe_bot.raiseLongSleepException("[Mapper.manageStashAndInventory] no waystones found in stash and inventory after updating")
if all_waystones[0].source == "stash":
  print("[Mapper.manageStashAndInventory] best waystone is in stash")
  list(map(lambda i: stash_tab_indexes.append(i.tab_index), self.getWaystonesCanUse(source="stash")))

all_stash_items = stash.getAllItems()

for key in self.keep_consumables:
  consumable: str = list(key.keys())[0]
  min_amount = key[consumable]
  consumable_in_inventory = list(filter(lambda i: i.name == consumable, inventory.items))
  amount_in_inventory = sum(list(map(lambda i: i.items_in_stack, consumable_in_inventory)))
  need_to_pick = min_amount - amount_in_inventory
  if need_to_pick > 0:
    consumables_to_pick.append({consumable: need_to_pick})
    similar_items_in_stash = list(filter(lambda i: i.name == consumable, all_stash_items))
    if len(similar_items_in_stash) != 0:
      key_stash_tabs = list(map(lambda i: i.tab_index, similar_items_in_stash))
      stash_tab_indexes.extend(key_stash_tabs)


oils_count_to_keep_in_invnentory = self.settings.keep_waystones_in_inventory * 3
oils_in_inventory = self.getUsableOilsFromItems(inventory.items)
current_oil_count = sum(list(map(lambda i: i.items_in_stack, oils_in_inventory)))
oils_to_pick_count = oils_count_to_keep_in_invnentory - current_oil_count
if oils_to_pick_count > 0:
  oils_in_stash = self.getUsableOilsFromItems(all_stash_items)
  list(map(lambda i: stash_tab_indexes.append(i.tab_index), oils_in_stash))

stash_tab_indexes = list(set(stash_tab_indexes))
if len(stash_tab_indexes) != 0:
  stash.open()
  print(f"[Mapper.manageStashAndInventory] going to check stash tab indexes {stash_tab_indexes}")
  random.shuffle(stash_tab_indexes)
  try:
    stash_tab_indexes.pop(stash_tab_indexes.index(stash.current_tab_index))
  except Exception:
    print(f"[Mapper.manageStashAndInventory] tab with index {stash.current_tab_index} is not in list, but we ll still check it")
  stash_tab_indexes.insert(0, stash.current_tab_index)

  for stash_tab_index in stash_tab_indexes:
    print(f"[Mapper.manageStashAndInventory] getting items from stash tab {stash_tab_index}")
    items_to_pick: List[StashItem] = []
    stash.openTabIndex(stash_tab_index)
    # check if have better maps maps_to_pick_count
    if maps_to_pick_count > 0:
      all_maps = []
      maps_we_can_run_in_inventory = self.filterWaystonesCanRun(inventory.items)
      maps_we_can_run_in_stash = mapper.filterWaystonesCanRun(stash.current_tab_items)
      all_maps.extend(maps_we_can_run_in_stash)
      all_maps.extend(maps_we_can_run_in_inventory)
      self.sortWaystones(all_maps)
      for map_item in all_maps:
        if map_item.source == "stash":
          # TODO added 1 map, supposed to stash 1
          print(f"[Mapper.manageStashAndInventory] going to pick map {map_item.raw}")
          items_to_pick.append(map_item)
          maps_to_pick_count -= 1
        if maps_to_pick_count <= 0:
          break
    # check if have oils_to_pick_count
    if oils_to_pick_count > 0:
      usable_oils_in_tab = self.getUsableOilsFromItems(stash.current_tab_items)
      for oil_item in usable_oils_in_tab:
        print(f"[Mapper.manageStashAndInventory] going to pick oil {oil_item.raw}")
        items_to_pick.append(oil_item)
        oils_to_pick_count -= oil_item.items_in_stack
        if oils_to_pick_count <= 0:
          break
    # check if have consumables_to_pick
    if len(consumables_to_pick) != 0:
      indexes_to_remove = []
      for key_index in range(len(consumables_to_pick)):
        print(consumables_to_pick)
        key = consumables_to_pick[key_index]
        consumable: str = list(key.keys())[0]
        need_to_pick = consumables_to_pick[key_index][consumable]
        consumables_in_current_tab = list(filter(lambda i: i.name == consumable, stash.current_tab_items))
        consumables_in_current_tab.sort(key=lambda i: i.items_in_stack)
        for consumable_item in consumables_in_current_tab:
          items_to_pick.append(consumable_item)
          consumables_to_pick[key_index][consumable] -= consumable_item.items_in_stack
          if consumables_to_pick[key_index][consumable] <= 0:
            indexes_to_remove.append(key_index)
            break

      for key_index in indexes_to_remove[::-1]:
        print("removing index")
        consumables_to_pick.pop(key_index)
    self.stashUselessItems()
    self.poe_bot.ui.clickMultipleItems(items_to_pick, random_sleep=False)


# In[ ]:


key_index


# In[ ]:


consumables_to_pick


# In[ ]:


for i in range(len(consumables_to_pick) - 1):
  print(i)


# In[ ]:


sorted_maps


# In[ ]:


for i in oils_in_inventory:
  print(i.raw)


# In[ ]:


s = sorted(oils_in_inventory, key=lambda i: OILS_BY_TIERS.index(i.name), reverse=True)
for i in s:
  print(i.raw)


# In[ ]:





# In[ ]:





# In[ ]:


consumable


# In[ ]:




