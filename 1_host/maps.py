#!/usr/bin/env python
# coding: utf-8

# In[1]:


from typing import List

import pickle
import time
from math import dist
import random
import sys
from ast import literal_eval
import traceback
import json

import cv2
import numpy as np
import matplotlib.pyplot as plt

from utils.combat import CombatModule
from utils.constants import HARVEST_SEED_COLOR_WEIGHTS, SHITTY_UNIQUES_ARTS, ROGUE_EXILES_RENDER_NAMES_ENG, ULTIMATUM_ALTAR_PATH, ESSENCES_KEYWORD
from utils.controller import VMHostPuppeteer
from utils.encounters import IncursionEncounter, UltimatumEncounter, HarbringerEncounter
from utils.gamehelper import PoeBot, Entity
from utils.mapper import MapArea, MapperSettings, getMapAreaObject, MAPS_TO_IGNORE, IGNORE_BOSSROOM_MAPS
from utils.mover import Mover
from utils.pathing import TSP
from utils.temps import MapsTempData, IncursionTempData, MapperSession
from utils.ui import Item, StashItem, InventoryItem
from utils.utils import sortByHSV, raiseLongSleepException, getFourPoints, extendLine

from mapper_configs import PREDEFINED_STRATEGIES, DEFAULT_SESSION


# In[2]:


time_now = 0
notebook_dev = False


# In[3]:


# readability
poe_bot: PoeBot
bot_controls:VMHostPuppeteer
mover: Mover
combat_module:CombatModule


# '''
# functions\classes which will be moved to files
# '''

# In[7]:


def waitForPortalNearby(poe_bot:PoeBot, wait_for_seconds = 3, distance = 25):
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
def openPortal(poe_bot:PoeBot):
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
    portal_nearby = waitForPortalNearby(poe_bot=poe_bot, wait_for_seconds=1)
    poe_bot.ui.closeAll()
    print(f'portal_nearby {portal_nearby}')
  else:
    print(f'we dont have portal scrolls in inventory')
    is_portal_gem = 'town_portal' in poe_bot.backend.getSkillBar()['i_n']
    print(f'portal_gem_in_skills {is_portal_gem}')
    if is_portal_gem is False:
      print(f'is_portal_gem {is_portal_gem} swapping weapons')
      time.sleep(random.randint(10,20)/100)
      bot_controls.keyboard.tap("DIK_X")
    for i in range(random.randint(1,2)):
      time.sleep(random.randint(25,35)/100)
      bot_controls.keyboard.tap("DIK_R")
      portal_nearby = waitForPortalNearby(poe_bot=poe_bot, wait_for_seconds=1)
      if portal_nearby is True:
        break
    is_portal_gem = 'town_portal' in poe_bot.backend.getSkillBar()['i_n']
    print(f'portal_nearby {portal_nearby}')
    if is_portal_gem is True:
      print(f'is_portal_gem {is_portal_gem} swapping weapons back')
      bot_controls.keyboard.tap("DIK_X")
      time.sleep(random.randint(10,20)/100)
  
  if poe_bot.debug is True:print(f'#openPortal return {time.time()}')
  return 
def openPortal_new(poe_bot:PoeBot, swap_weapons = True):
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
    portal_nearby = waitForPortalNearby(poe_bot=poe_bot, wait_for_seconds=1)
    poe_bot.ui.closeAll()
    print(f'portal_nearby {portal_nearby}')
  else:
    print(f'we dont have portal scrolls in inventory')
    is_portal_gem = 'town_portal' in poe_bot.backend.getSkillBar()['i_n']
    if is_portal_gem is False:
      print(f'is_portal_gem {is_portal_gem} swapping weapons')
      time.sleep(random.randint(10,20)/100)
      bot_controls.keyboard.tap("DIK_X")
    for i in range(random.randint(1,2)):
      time.sleep(random.randint(25,35)/100)
      bot_controls.keyboard.tap("DIK_R")
      portal_nearby = waitForPortalNearby(poe_bot=poe_bot, wait_for_seconds=1)
      if portal_nearby is True:
        break
    is_portal_gem = 'town_portal' in poe_bot.backend.getSkillBar()['i_n']
    print(f'portal_nearby {portal_nearby}')
    if is_portal_gem is True and swap_weapons:
      print(f'is_portal_gem {is_portal_gem} swapping weapons')
      bot_controls.keyboard.tap("DIK_X")
      time.sleep(random.randint(10,20)/100)
  
  if poe_bot.debug is True:print(f'#openPortal return {time.time()}')
  return 
  


# '''
# functions\classes which are for mapper only
# '''

# In[10]:


def dealWithBestiary(search_string:str, release_beasts:bool):
  poe_bot.logger.writeLine(f'[Bestiary] dealing with bestiary params:{search_string},{release_beasts}')
  stash = poe_bot.ui.stash
  inventory = poe_bot.ui.inventory
  pick_bestiary_orbs_amount = random.randint(18,40)
  print(f"going to pick {pick_bestiary_orbs_amount} bestiary orbs")
  inventory.update()
  bestiary_orbs_in_inventory = list(filter(lambda i: 'Metadata/Items/Currency/CurrencyItemiseCapturedMonster' in i.render_art , inventory.items))
  amount_of_bestiary_orbs_in_inventory = sum([i.items_in_stack for i in bestiary_orbs_in_inventory])

  if amount_of_bestiary_orbs_in_inventory >= pick_bestiary_orbs_amount:
    print('no need to pick more bestiary orbs')
  else:
    stash.open()
    need_to_pick_more_bestiary_orbs_count = pick_bestiary_orbs_amount
    all_stash_items = stash.getAllItems()
    bestiary_orbs_in_stash = list(filter(lambda i: 'Metadata/Items/Currency/CurrencyItemiseCapturedMonster' in i.render_art,all_stash_items))
    amount_of_bestiary_orbs_in_stash = sum([i.items_in_stack for i in bestiary_orbs_in_stash])
    print(f'amount of bestiary orbs in stash: {amount_of_bestiary_orbs_in_stash}')
    if amount_of_bestiary_orbs_in_stash < pick_bestiary_orbs_amount:
      print(f'amount of bestiary_orbs_in_stash < {pick_bestiary_orbs_amount}, checking if there is more in stash')
      stash.updateStashTemp()
      all_stash_items = stash.getAllItems()
      bestiary_orbs_in_stash = list(filter(lambda i: 'Metadata/Items/Currency/CurrencyItemiseCapturedMonster' in i.render_art,all_stash_items))
      amount_of_bestiary_orbs_in_stash = sum([i.items_in_stack for i in bestiary_orbs_in_stash])
      print(f'amount of bestiary orbs in stash after update: {amount_of_bestiary_orbs_in_stash} ')
      if amount_of_bestiary_orbs_in_stash < pick_bestiary_orbs_amount:
        poe_bot.raiseLongSleepException(f'less than {pick_bestiary_orbs_amount} bestiary orbs in stash after update')
    bestiary_orbs_in_stash.sort(key=lambda item: item.items_in_stack)
    bestiary_orbs_in_stash_tab_indexes = list(set(list(map(lambda item: item.tab_index, bestiary_orbs_in_stash))))
    random.shuffle(bestiary_orbs_in_stash_tab_indexes)
    for tab_index in bestiary_orbs_in_stash_tab_indexes:
      bestiary_orbs_in_this_tab = list(filter(lambda item: item.tab_index == tab_index, bestiary_orbs_in_stash))
      # bestiary_orbs_in_tab_count = sum(item.items_in_stack for item in bestiary_orbs_in_this_tab)
      items_to_pick = []
      for item in bestiary_orbs_in_this_tab:
        if need_to_pick_more_bestiary_orbs_count < 1:
          break
        need_to_pick_more_bestiary_orbs_count -= item.items_in_stack
        items_to_pick.append(item)
      stash.openTabIndex(tab_index)
      stash.pickItems(items_to_pick)
      if need_to_pick_more_bestiary_orbs_count < 1:
        break
    time.sleep(random.randint(10,15)/100)
    bot_controls.keyboard.tap("DIK_SPACE")
  time.sleep(random.randint(20,40)/100)

  # free inventory to have at least 30 cells
  inventory.update()
  bestiary_orbs_in_inventory = list(filter(lambda i: 'Metadata/Items/Currency/CurrencyItemiseCapturedMonster' in i.render_art , inventory.items))
  if len(bestiary_orbs_in_inventory) == 0:
    poe_bot.raiseLongSleepException('no bestiary orbs in inventory')

  bestiary_orb = bestiary_orbs_in_inventory[0]
  print("opening inventory and bestiary")
  bot_controls.keyboard.tap("DIK_I")
  time.sleep(random.randint(20,40)/1000)

  bot_controls.keyboard.tap("DIK_H")
  time.sleep(random.randint(20,40)/10)

  # click bestiary
  pos_x, pos_y = 330,90
  pos_x, pos_y = poe_bot.convertPosXY(pos_x,pos_y, safe = False)
  bot_controls.mouse.setPosSmooth(pos_x,pos_y)
  time.sleep(random.randint(20,40)/100)
  bot_controls.mouse.pressAndRelease()
  time.sleep(random.randint(20,40)/100)

  # click captured beasts
  pos_x, pos_y = 435,475
  pos_x, pos_y = poe_bot.convertPosXY(pos_x,pos_y, safe = False)
  bot_controls.mouse.setPosSmooth(pos_x,pos_y)
  time.sleep(random.randint(20,40)/100)
  bot_controls.mouse.pressAndRelease()
  time.sleep(random.randint(20,40)/100)
  print("wait for beastiary tab loaded")
  while True:
    beast_presented = checkIfBeastPresented()
    if beast_presented is True:
      break

  bot_controls.setClipboardText(search_string)
  time.sleep(random.randint(20,40)/100)
  bot_controls.keyboard_pressKey('DIK_LCONTROL')
  time.sleep(random.randint(20,40)/100)
  bot_controls.keyboard.tap("DIK_F")
  time.sleep(random.randint(20,40)/100)
  bot_controls.keyboard.tap("DIK_V")
  time.sleep(random.randint(20,40)/100)
  bot_controls.keyboard_releaseKey('DIK_LCONTROL')
  time.sleep(random.randint(20,40)/100)

  
  # storing beasts
  print("storing beasts")
  while True:
    # check if beast there  
    beast_presented = checkIfBeastPresented()
    if beast_presented is False:
      print(f'beast_presented {beast_presented}, breaking')
      break

    inventory.update()
    bestiary_orbs = list(filter(lambda i: i.render_art == 'Metadata/Items/Currency/CurrencyItemiseCapturedMonster', inventory.items))
    if len(bestiary_orbs) == 0:

      print(f'click on an empty cell in case if has item on cursor')
      inventory_free_slots = inventory.getEmptySlots()
      for empty_inv_slot in range(random.randint(1,2)):
        inventory.clickOnAnEmptySlotInInventory()
      poe_bot.ui.closeAll()
      itemised_beasts = list(filter(lambda i: 'Metadata/Items/Currency/CurrencyItemisedCapturedMonster' in i.render_art,inventory.items))
      poe_bot.logger.writeLine(f'bestiary, going to stash {len(itemised_beasts)} beasts because run no bestiary orbs left')
      stash.placeItemsAcrossStash(itemised_beasts)
      print(f'stashed beasts, restarting')
      print("opening inventory and bestiary")
      time.sleep(random.randint(5,15)/10)
      poe_bot.ui.closeAll()
      raise Exception("need to take more bestiary orbs")
    
    inventory_free_slots = inventory.getEmptySlots()
    if len(inventory_free_slots) == 0:
      poe_bot.raiseLongSleepException('inventory is full completley')
    if len(inventory_free_slots) < 4:
      time.sleep(random.randint(120,200)/100)
      inventory.update()
      inventory_free_slots = inventory.getEmptySlots()
      inventory_free_slot = inventory_free_slots[0]
      pos_x, pos_y = inventory.getItemCoordinates(item_pos_x=inventory_free_slot[0], item_pos_y=inventory_free_slot[1])
      pos_x, pos_y = poe_bot.convertPosXY(pos_x,pos_y, safe = False)
      bot_controls.mouse.setPosSmooth(pos_x,pos_y)
      time.sleep(random.randint(20,40)/100)
      bot_controls.mouse.pressAndRelease()
      time.sleep(random.randint(20,40)/100)
      print(f'inventory is full, stashing some')
      poe_bot.ui.closeAll()
      itemised_beasts = list(filter(lambda i: 'Metadata/Items/Currency/CurrencyItemisedCapturedMonster' in i.render_art,inventory.items))
      poe_bot.logger.writeLine(f'bestiary, going to stash {len(itemised_beasts)} beasts because inventory is full')
      stash.placeItemsAcrossStash(itemised_beasts)
      print(f'stashed beasts, restarting')
      print("opening inventory and bestiary")
      poe_bot.ui.closeAll()
      inventory.open()
      time.sleep(random.randint(20,40)/1000)
      bot_controls.keyboard.tap("DIK_H")
      time.sleep(random.randint(20,40)/10)
      continue

    inventory_free_slot = inventory_free_slots[0]

    bestiary_orb = bestiary_orbs[0]
    bestiary_orb.hover()
    time.sleep(random.randint(20,40)/100)
    bestiary_orb.click(button="right")
    time.sleep(random.randint(20,40)/100)

    pos_x, pos_y = 90, 200
    pos_x, pos_y = poe_bot.convertPosXY(pos_x,pos_y, safe = False)
    bot_controls.mouse.setPosSmooth(pos_x,pos_y)
    time.sleep(random.randint(20,40)/100)
    bot_controls.mouse.pressAndRelease()
    time.sleep(random.randint(20,40)/100)


    # print(inventory_free_slot)
    pos_x, pos_y = inventory.getItemCoordinates(item_pos_x=inventory_free_slot[0], item_pos_y=inventory_free_slot[1])
    pos_x, pos_y = poe_bot.convertPosXY(pos_x,pos_y, safe = False)
    bot_controls.mouse.setPosSmooth(pos_x,pos_y)
    time.sleep(random.randint(20,40)/100)
    bot_controls.mouse.pressAndRelease()
    time.sleep(random.randint(20,40)/100)

  time.sleep(random.randint(20,40)/100)

  bot_controls.keyboard_pressKey('DIK_LCONTROL')
  time.sleep(random.randint(20,40)/100)
  bot_controls.keyboard.tap("DIK_F")
  time.sleep(random.randint(20,40)/100)
  bot_controls.keyboard.tap("DIK_A")
  time.sleep(random.randint(20,40)/100)
  bot_controls.keyboard.tap("DIK_BACK")
  time.sleep(random.randint(20,40)/100)
  bot_controls.keyboard_releaseKey('DIK_LCONTROL')

  time.sleep(random.randint(20,40)/100)
  print(f'[Bestiary] release_beasts {release_beasts}')
  if release_beasts != False:
    bot_controls.keyboard_pressKey('DIK_LCONTROL')
    for i in [0]:
      pos_x, pos_y = 63+i*110,170 # first
      pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y, safe=False)
      bot_controls.mouse.setPosSmooth(pos_x,pos_y)
      time.sleep(random.randint(15,25)/100)

    print("[Bestiary] releasing useless beasts, donot open the virtual machine, if you move the mouse on it, restart the script")
    i = 0
    pos_x, pos_y = 63+i*110,170 # first
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y, safe=False)
    bot_controls.mouse.setPosSmooth(pos_x,pos_y)
    time.sleep(random.randint(9,10)/100)
    for i in range(9999):
      # check if beast there 
      if random.randint(1,100) == 1:
        print("[Bestiary] still releasing useless beasts, donot open the virtual machine, if you move the mouse on it, restart the script")
        bot_controls.keyboard_releaseKey('DIK_LCONTROL')
        time.sleep(random.randint(3,12))
        bot_controls.keyboard_pressKey('DIK_LCONTROL')
      beast_presented = checkIfBeastPresented()
      if beast_presented is False:
        print(f'beast_presented {beast_presented}, breaking')
        break
      releaseThreeBeasts()
    bot_controls.keyboard_releaseKey('DIK_LCONTROL')


  print(f'click on an empty cell in case if has item on cursor')
  inventory.clickOnAnEmptySlotInInventory()
  time.sleep(random.randint(20,40)/100)
  bot_controls.keyboard.tap('DIK_ESCAPE')
  time.sleep(random.randint(20,40)/100)
  bot_controls.keyboard.tap('DIK_ESCAPE')
  time.sleep(random.randint(20,40)/100)
  bot_controls.keyboard.tap("DIK_SPACE")
  time.sleep(random.randint(20,40)/100)
  inventory.update()
  itemised_beasts = list(filter(lambda i: 'Metadata/Items/Currency/CurrencyItemisedCapturedMonster' in i.render_art,inventory.items))
  bestiary_orbs = list(filter(lambda i: 'Metadata/Items/Currency/CurrencyItemiseCapturedMonster' in i.render_art,inventory.items))
  items_to_stash = itemised_beasts + bestiary_orbs
  poe_bot.logger.writeLine(f'bestiary, going to stash {len(itemised_beasts)} beasts')
  stash.placeItemsAcrossStash(items_to_stash)
  time.sleep(random.randint(20,40)/100)
def releaseRandomBeast():
  '''
  releases beast
  '''
  i = random.choice([0,0,0,0,0,1]) # 1/6 that itll release second one
  pos_x, pos_y = 63+i*110,170 # first

  pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y, safe=False)
  bot_controls.mouse.setPosSmooth(pos_x,pos_y)
  time.sleep(random.randint(9,14)/100)
  bot_controls.mouse.pressAndRelease()

  pos_x, pos_y = 336,418
  pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y, safe=False)
  bot_controls.mouse.setPosSmooth(pos_x,pos_y)
  time.sleep(random.randint(9,14)/100)
  bot_controls.mouse.pressAndRelease()
def checkIfBeastPresented():
  '''
  function checks if there is a beast in opened beastiary
  in a left top position

  - returns bool, true if presented
  - false if not
  
  '''
  game_img = poe_bot.getImage()
  # plt.imshow(game_img);plt.show()

  beast_lvl_part = game_img[170:180, 120:150]
  # plt.imshow(beast_lvl_part);plt.show()
  sorted_img = sortByHSV(beast_lvl_part, 0, 0, 127, 0, 0, 255)
  # plt.imshow(sorted_img);plt.show()
  beast_presented = len(sorted_img[sorted_img != 0]) > 30
  if beast_presented is False:
    print(f'beast_presented {beast_presented} looks like no beasts left, double check')
    time.sleep(random.randint(10,20)/10)
    game_img = poe_bot.getImage()
    # plt.imshow(game_img);plt.show()

    beast_lvl_part = game_img[170:180, 120:150]
    # plt.imshow(beast_lvl_part);plt.show()
    sorted_img = sortByHSV(beast_lvl_part, 0, 0, 127, 0, 0, 255)
    # plt.imshow(sorted_img);plt.show()
    beast_presented = len(sorted_img[sorted_img != 0]) > 30
    if beast_presented is False:
      print(f'beast_presented {beast_presented}, looks like real')
  return beast_presented
def releaseSingleBeast():
  bot_controls.mouse.pressAndRelease(delay=random.randint(10,40)/100)
  time.sleep(random.randint(10,60)/100)
  # bot_controls.keyboard.tap("DIK_RETURN")
  # time.sleep(random.randint(40,60)/100)
  # 10 + 40 to 10+60
def releaseThreeBeasts():
  # i = 0
  # pos_x, pos_y = 63+i*110,170 # first
  # pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y, safe=False)
  # bot_controls.mouse.setPosSmooth(pos_x,pos_y)
  # time.sleep(random.randint(9,10)/100)
    
  
  for _i in range(3):
    releaseSingleBeast()
  return True


# In[11]:


maps_to_ignore = MAPS_TO_IGNORE
ignore_bossroom_maps = IGNORE_BOSSROOM_MAPS


# In[12]:


# Harvest
harvest_seed_tier_weights = {
  1: 0,
  2: 10,
  3: 100,
  4: 100000
}
HARVEST_MOBS_TIERS_AND_COLOURS = {
  "Wild Ursaling": [1,"Wild"], # tier colour
  "Wild Hellion": [1,"Wild"], # tier colour
  "Wild Thornwolf": [1,"Wild"], # tier colour
  "Wild Ape": [1,"Wild"], # tier colour
  "Wild Hatchling": [1,"Wild"], # tier colour

  "Vivid Arachnid": [1,"Vivid"], # tier colour
  "Vivid Weta": [1,"Vivid"], # tier colour
  "Vivid Leech": [1,"Vivid"], # tier colour
  "Vivid Scorpion": [1,"Vivid"], # tier colour
  "Vivid Thornweaver": [1,"Vivid"], # tier colour

  "Primal Rhoa": [1,"Primal"], # tier colour
  "Primal Dustspitter": [1,"Primal"], # tier colour
  "Primal Feasting Horror": [1,"Primal"], # tier colour
  "Primal Maw": [1,"Primal"], # tier colour
  "Primal Cleaveling": [1,"Primal"], # tier colour

  "Wild Bristlebeast": [2,"Wild"], # tier colour
  "Wild Snap Hound": [2,"Wild"], # tier colour
  "Wild Homunculus": [2,"Wild"], # tier colour
  "Wild Chieftain": [2,"Wild"], # tier colour
  "Wild Spikeback": [2,"Wild"], # tier colour

  "Vivid Razorleg": [2,"Vivid"], # tier colour
  "Vivid Sapsucker": [2,"Vivid"], # tier colour
  "Vivid Parasite": [2,"Vivid"], # tier colour
  "Vivid Striketail": [2,"Vivid"], # tier colour
  "Vivid Nestback": [2,"Vivid"], # tier colour

  "Primal Rhex": [2,"Primal"], # tier colour
  "Primal Dustcrab": [2,"Primal"], # tier colour
  "Primal Viper": [2,"Primal"], # tier colour
  "Primal Chimeral": [2,"Primal"], # tier colour
  "Primal Scrabbler": [2,"Primal"], # tier colour

  "Wild Bristle Matron": [3,"Wild"], # tier colour
  "Wild Hellion Alpha": [3,"Wild"], # tier colour
  "Wild Thornmaw": [3,"Wild"], # tier colour
  "Wild Brambleback": [3,"Wild"], # tier colour
  "Wild Infestation Queen": [3,"Wild"], # tier colour

  "Vivid Whipleg": [3,"Vivid"], # tier colour
  "Vivid Watcher": [3,"Vivid"], # tier colour
  "Vivid Vulture": [3,"Vivid"], # tier colour
  "Vivid Abberarach": [3,"Vivid"], # tier colour
  "Vivid Devourer": [3,"Vivid"], # tier colour

  "Primal Rhex Matriarch": [3,"Primal"], # tier colour
  "Primal Crushclaw": [3,"Primal"], # tier colour
  "Primal Blisterlord": [3,"Primal"], # tier colour
  "Primal Cystcaller": [3,"Primal"], # tier colour
  "Primal Reborn": [3,"Primal"], # tier colour

  "Ersi, Mother of Thorns": [4,"Wild"], # tier colour wild

  "Namharim, Born of Night": [4,"Vivid"], # tier colour vivid

  "Janaar, the Omen": [4,"Primal"], # tier colour primal

}
def getIrrigatorTierAndColour(irrigator_label):
  colour = None
  max_tier = 0
  for line in irrigator_label['texts']:
    mob_name = line.split("}")[-1]
    tier, colour = HARVEST_MOBS_TIERS_AND_COLOURS[mob_name]
    if tier > max_tier:
      max_tier = tier
  return max_tier, colour
def calculateIrrigatorValue(irrigator_label):
  value = 0
  for line in irrigator_label['texts']:
    mob_name = line.split("}")[-1]
    try:
      amount = int(''.join(list(filter(lambda x: x.isdigit(), line))))
    except:
      amount = 1
    tier, colour = HARVEST_MOBS_TIERS_AND_COLOURS[mob_name]
    value += harvest_seed_tier_weights[tier] * amount * HARVEST_SEED_COLOR_WEIGHTS[colour]
  # print(irrigator_label)
  # print(value)
  return value
def finishSeedPatch(irrigator_to_open:Entity):

  # go to it
  while True:
    # res = mover.goToEntity(
    #   irrigator_to_open,

    res = mover.goToPoint(
      [irrigator_to_open.grid_position.x, irrigator_to_open.grid_position.y],
      min_distance=35,
      custom_continue_function=build.usualRoutine,
      custom_break_function=poe_bot.loot_picker.collectLoot,
      release_mouse_on_end=True,
      step_size=random.randint(25,33)
    )
    if res is None:
      break
    elif res == 'doesnt_exist':
      print(f'seems like we are out of harvest')

  visible_labels = poe_bot.backend.getVisibleLabels()

  print('clicking on irrigator')
  for i in range(100):
    i += 1 
    visible_labels = poe_bot.backend.getVisibleLabels()
    irrigator_to_do_labels = list(filter(lambda l: l["id"] == irrigator_to_open.id, visible_labels))
    if len(irrigator_to_do_labels) == 0:
      break

    if i > 80:
      raise Exception('cannot activate irrigator')
    irrigator_to_do_label = irrigator_to_do_labels[0]
    pos_x,pos_y = poe_bot.convertPosXY(
      x=int((irrigator_to_do_label['p_o_s']['x1']+irrigator_to_do_label['p_o_s']['x2'])/2),
      y=int((irrigator_to_do_label['p_o_s']['y1']+irrigator_to_do_label['p_o_s']['y2'])/2)
    )
    bot_controls.mouse.setPosSmooth(pos_x,pos_y)
    time.sleep(random.randint(10,20)/100)
    bot_controls.mouse.click()
    time.sleep(random.randint(30,60)/100)


  print('clicking on extractor')
  extractor_id = None
  for i in range(100):
    i += 1 
    visible_labels = poe_bot.backend.getVisibleLabels()
    extractor_to_do_labels = list(filter(lambda l: l['p'] == 'Metadata/MiscellaneousObjects/Harvest/Extractor', visible_labels))
    if len(extractor_to_do_labels) == 0:
      break

    if i > 80:
      raise Exception('cannot activate extractor')
    extractor_to_do_label = extractor_to_do_labels[0]
    extractor_id = extractor_to_do_label['id']
    pos_x,pos_y = poe_bot.convertPosXY(
      x=int((extractor_to_do_label['p_o_s']['x1']+extractor_to_do_label['p_o_s']['x2'])/2),
      y=int((extractor_to_do_label['p_o_s']['y1']+extractor_to_do_label['p_o_s']['y2'])/2)
    )
    bot_controls.mouse.setPosSmooth(pos_x,pos_y)
    time.sleep(random.randint(10,20)/100)
    bot_controls.mouse.click()
    time.sleep(random.randint(30,60)/100)

  print(f'clearing mobs')
  extractor_entity = list(filter(lambda e: e.id == extractor_id, poe_bot.game_data.entities.all_entities))[0]
  clockwise = random.choice([True, False])
  for i in range(100):
    i += 1 
    if i > 80:
      raise Exception('cannot finish harvest encounter')
    poe_bot.refreshInstanceData()
    killed_someone = combat_module.clearLocationAroundPoint({"X": extractor_entity.grid_position.x, "Y": extractor_entity.grid_position.y}, detection_radius=140)
    if killed_someone is False:
      point = poe_bot.game_data.terrain.pointToRunAround(
        point_to_run_around_x=extractor_entity.grid_position.x,
        point_to_run_around_y=extractor_entity.grid_position.y,
        distance_to_point=15,
        reversed = clockwise 
      )
      mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
      poe_bot.refreshInstanceData()
    minimap_icons = poe_bot.backend.getMinimapIcons()
    extractor_minimap_icons = list(filter(lambda i:i['i'] == extractor_id, minimap_icons))
    extractor_minimap_icon = extractor_minimap_icons[0]
    if extractor_minimap_icon['h'] == 1:
      print('extractor is dead, seems like we finished it')
      break
def doHarvestEncounter(harvest_enter_portal:Entity, leave_harvest = True):

  # TODO
  # if the other pair wasnt opened
  # crop rotation logic
  # as an encounter class
  portal_entity = harvest_enter_portal
  while True:
    res = mover.goToPoint(
      (portal_entity.grid_position.x, portal_entity.grid_position.y),
      min_distance=30,
      custom_continue_function=build.usualRoutine,
      custom_break_function=poe_bot.loot_picker.collectLoot,
      release_mouse_on_end=False,
      step_size=random.randint(25,33)
    )
    if res is None:
      break
  mover.enterTransition(portal_entity)
  time.sleep(random.randint(40,70)/100)
  poe_bot.refreshInstanceData()
  poe_bot.game_data.terrain.getCurrentlyPassableArea()

  portal_entity = list(filter(lambda e: e.path == 'Metadata/Terrain/Leagues/Harvest/Objects/HarvestPortalToggleableReverseReturn', poe_bot.game_data.entities.all_entities))[0]
  point = extendLine( (portal_entity.grid_position.x, portal_entity.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), 2)
  mover.move(point[0], point[1])


  visible_labels = poe_bot.backend.getVisibleLabels()
  irrigator_labels = list(filter(lambda l: l['p'] == 'Metadata/MiscellaneousObjects/Harvest/Irrigator', visible_labels))
  if len( list(filter(lambda l: l['v'] == 0, irrigator_labels )) ):
    print(f'some extractor wasnt finished')
    oshabi_entity = list(filter(lambda e: e.path == "Metadata/NPC/League/Harvest/HarvestNPCGardenTutorial", poe_bot.game_data.entities.all_entities))[0]
    i = 0
    while True:
      i += 1
      if i > 80:
        poe_bot.helper_functions.relog()
        raise Exception('stuck on clearing mobs from extractor')
      point = poe_bot.game_data.terrain.pointToRunAround(oshabi_entity.grid_position.x, oshabi_entity.grid_position.y, distance_to_point=150)
      combat_module.clearLocationAroundPoint(
        {"X": point[0],"Y": point[1]},
        detection_radius=100

      )
      visible_labels = poe_bot.backend.getVisibleLabels()
      irrigator_labels = list(filter(lambda l: l['p'] == 'Metadata/MiscellaneousObjects/Harvest/Irrigator', visible_labels))
      if not len( list(filter(lambda l: l['v'] == 0,irrigator_labels )) ):
        break


  crop_rotation = False
  if crop_rotation is False:
    irrigators_ids = list(map(lambda l: l['id'], irrigator_labels))
    irrigators_ids.sort()
    # irrigators_ids.pop(random.randint(0, len(irrigators_ids)-1))
    print(f'irrigators_ids {irrigators_ids}')

    # split by pairs
    irrigators_pairs = []
    paired = []
    for i in range(len(irrigators_ids)):
      # print(i)
      irrigator_label_id = irrigators_ids[i]
      # print(irrigator_label_id)
      if irrigator_label_id in paired:
        continue

      close_one = list(filter(lambda id: id != irrigator_label_id and id + 2 >= irrigator_label_id and id - 2 <= irrigator_label_id, irrigators_ids)) 
      if len(close_one) != 0:
        irrigators_pairs.append([irrigator_label_id, close_one[0]])
        paired.append(close_one[0])
      else:
        irrigators_pairs.append([irrigator_label_id])

    print(irrigators_pairs)
    irrigators_entities = list(filter(lambda e: e.id in irrigators_ids, poe_bot.game_data.entities.all_entities))
    print(f'irrigators {irrigators_entities}')

    for irrigator_pair in irrigators_pairs:
      irrigator_pair_labels = []
      for id in irrigator_pair:
        irrigator_pair_labels.append(list(filter(lambda l: l["id"] == id, visible_labels))[0])

      irrigator_values = []
      for irrigator_pair_label in irrigator_pair_labels:
        irrigator_values.append(calculateIrrigatorValue(irrigator_pair_label))
      max_pair_value = max(irrigator_values)
      print(f'max_pair_value {max_pair_value}')
      irrigator_to_open_id = irrigator_pair.pop(irrigator_values.index(max_pair_value))
      
      irrigator_to_do:Entity = next((e for e in irrigators_entities if e.id == irrigator_to_open_id), None)
      if irrigator_to_do:
        print(f"doing {irrigator_to_do.id}")
        finishSeedPatch(irrigator_to_do)
      else:
        poe_bot.raiseLongSleepException('irrigator is not visible')
      if len(irrigator_pair) != 0:
        irrigator_to_open_id = irrigator_pair[0]
        print('candomore')
        # check if the other patch is still openable
        visible_labels = poe_bot.backend.getVisibleLabels()
        irrigator_to_do_labels = list(filter(lambda l: l["id"] == irrigator_to_open_id, visible_labels))
        if len(irrigator_to_do_labels) != 0:
          print(f'other irrigator looks openable, finishing it')
          irrigator_to_do:Entity = next((e for e in irrigators_entities if e.id == irrigator_to_open_id), None)
          if irrigator_to_do:
            print(f"doing {irrigator_to_do.id}")
            finishSeedPatch(irrigator_to_do)
          else:
            poe_bot.raiseLongSleepException('irrigator is not visible')
            poe_bot.helper_functions.relog()
            raise Exception('irrigator is not visible')




  # crop rotation logic
  else:
    for irrigator_label in irrigator_labels:
      tier, colour = getIrrigatorTierAndColour(irrigator_label=irrigator_label)
      print(tier, colour)
      value = calculateIrrigatorValue(irrigator_label=irrigator_label)
      print(value)
    poe_bot.raiseLongSleepException('crop rotation isnt done')


  portal_entity = list(filter(lambda e: e.path == 'Metadata/Terrain/Leagues/Harvest/Objects/HarvestPortalToggleableReverseReturn', poe_bot.game_data.entities.all_entities))[0]
  while True:
    res = mover.goToPoint(
      (portal_entity.grid_position.x, portal_entity.grid_position.y),
      min_distance=20,
      custom_continue_function=build.usualRoutine,
      custom_break_function=poe_bot.loot_picker.collectLoot,
      release_mouse_on_end=False,
      step_size=random.randint(25,33)
    )
    if res is None:
      break
  mover.enterTransition(portal_entity)
  poe_bot.game_data.terrain.getCurrentlyPassableArea()
def seekForHarvests():
  harvest_enterances = list(filter(lambda e: e.is_targetable is True and e.path == 'Metadata/Terrain/Leagues/Harvest/Objects/HarvestPortalToggleableReverse' in e.path, poe_bot.game_data.entities.all_entities))
  return harvest_enterances
# Harvest end


# In[14]:


# incursion start
def lookForAlvaNarbyEntrancePortal(portal_entity:Entity):
  poe_bot.game_data.updateLabelsOnGroundEntities()
  search_distance = 20
  portal_entity_grid_pos_x, portal_entity_grid_pos_y = portal_entity.grid_position.x, portal_entity.grid_position.y
  alva_entity = next( (e for e in poe_bot.game_data.labels_on_ground_entities if e.render_name == "Alva, Master Explorer" and e.id not in mapper.temp.alvas_to_ignore_ids and e.isOnPassableZone() and dist( (portal_entity_grid_pos_x, portal_entity_grid_pos_y), (e.grid_position.x, e.grid_position.y)) < search_distance) , None)
  return alva_entity
def lookForAlvaNarbyEntrancePortal_d(portal_entity:Entity):
  search_distance = 20
  portal_entity_grid_pos_x, portal_entity_grid_pos_y = portal_entity.grid_position.x, portal_entity.grid_position.y
  alva_entities = list(filter(lambda e: e.render_name == "Alva, Master Explorer", poe_bot.game_data.entities.npcs))
  print(f'found alvas {list(map(lambda e: e.raw, alva_entities))}')
  alva_entities = list(filter(lambda e: e.id not in mapper.temp.alvas_to_ignore_ids, alva_entities))
  print(f'found alvas {list(map(lambda e: e.raw, alva_entities))}')
  alva_entities = list(filter(lambda e: e.isOnPassableZone(), alva_entities))
  print(f'found alvas {list(map(lambda e: e.raw, alva_entities))}')
  alva_entities = list(filter(lambda e: dist( (portal_entity_grid_pos_x, portal_entity_grid_pos_y), (e.grid_position.x, e.grid_position.y)) < search_distance, alva_entities))
  print(f'found alvas {list(map(lambda e: e.raw, alva_entities))}')
  print('lookForAlvaNarbyEntrancePortal_d return')
  if len(alva_entities) != 0:
    return alva_entities[0]
  else:
    return None
def doAlvaEncounter(entrance_portal_entity:Entity):
  print(f'#doAlvaEncounter call {time.time()}')
  poe_bot.logger.writeLine('alva, going to run incursion')
  alva_appear_time = 10
  incursion_ui = poe_bot.ui.incursion_ui
  bot_controls = poe_bot.bot_controls

  last_incursion_before_temple = False
  print(f'entrance_portal_entity {entrance_portal_entity.raw}')

  print(f'going to alva encounter')
  poe_bot.mover.goToPoint(
    point=(entrance_portal_entity.grid_position.x, entrance_portal_entity.grid_position.y),
    custom_continue_function=poe_bot.combat_module.build.usualRoutine,
    release_mouse_on_end=False,
    min_distance = 30,
  )
  alva_entity = lookForAlvaNarbyEntrancePortal(entrance_portal_entity)
  start_time = time.time()
  time_since_refresh = time.time()
  print('waiting for alva to appear')
  while alva_entity is None:
    alva_entity = lookForAlvaNarbyEntrancePortal(entrance_portal_entity)
    time_passed = time.time() - start_time
    time_passed_since_refresh = time.time() - time_since_refresh
    print(f'waiting for alva to appear for {time_passed}')
    print(f'time_passed_since_refresh {time_passed_since_refresh}')
    if alva_entity is None:
      killed_someone = combat_module.clearLocationAroundPoint(
        {"X":entrance_portal_entity.grid_position.x, "Y":entrance_portal_entity.grid_position.y}, 
        detection_radius=30, 
        ignore_keys=mapper.current_map.entities_to_ignore_in_bossroom_path_keys
      )
      if killed_someone is False:
        point = poe_bot.game_data.terrain.pointToRunAround(
          point_to_run_around_x=entrance_portal_entity.grid_position.x,
          point_to_run_around_y=entrance_portal_entity.grid_position.y,
          distance_to_point=30,
        )
        poe_bot.mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
        if time_passed_since_refresh > 5:
          print(f'refreshing area')
          poe_bot.backend.forceRefreshArea()
          time_since_refresh = time.time()
      poe_bot.refreshInstanceData(reset_timer=killed_someone)
      if time_passed > alva_appear_time:
        another_portals = list(filter(lambda e: e.path == "Metadata/Terrain/Leagues/Incursion/Objects/IncursionPortal1", poe_bot.game_data.entities.all_entities))
        print(f'another portals {list(map(lambda e:e.raw, another_portals))}')
        lookForAlvaNarbyEntrancePortal_d(entrance_portal_entity)
        poe_bot.logger.writeLine(f'alva didnt appear for {alva_appear_time} seconds {poe_bot.backend.last_data}')
        if mapper.settings.use_timeless_scarab_if_connected_or_presented:
          poe_bot.on_stuck_function()
        else:
          # mapper.temp.alvas_to_ignore_ids.append(alva_entity.id)
          mapper.temp.alvas_to_ignore_ids.append(entrance_portal_entity.id)
          mapper.temp.save()
          return True

      # poe_bot.raiseLongSleepException('arrived to incursion entrance, but alva is not presented')
  print(f'clearing around alva')
  poe_bot.combat_module.clearLocationAroundPoint({"X":entrance_portal_entity.grid_position.x, "Y":entrance_portal_entity.grid_position.y})
  print(f'going to alva {alva_entity.raw}')
  incursion_ui = poe_bot.ui.incursion_ui
  while True:
    res = mover.goToPoint(
      point=(alva_entity.grid_position.x, alva_entity.grid_position.y),
      min_distance=30,
      custom_continue_function=poe_bot.combat_module.build.usualRoutine,
      custom_break_function=poe_bot.loot_picker.collectLoot,
      release_mouse_on_end=False,
      # release_mouse_on_end=True,
      step_size=random.randint(25,33)
    )
    if res is None:
      break
  refreshed_portal_entity = entrance_portal_entity
  if refreshed_portal_entity is None:
    poe_bot.raiseLongSleepException('cannot find new state of portal')
  print(f'refreshed portal entity: {refreshed_portal_entity.raw}')
  if refreshed_portal_entity.is_targetable is False:
    print(f'portal is not targetable, looking for alva')
    alva_bugged = False
    def openIncursionWindow(check_if_entrance_portal_targetable=False):
      poe_bot.bot_controls.keyboard_pressKey('DIK_LCONTROL')
      poe_bot.refreshInstanceData()
      incursion_ui.update()
      open_incursion_ui_i = 0
      while incursion_ui.visible is False:
        open_incursion_ui_i +=1
        print(f'open_incursion_ui_i {open_incursion_ui_i}  {mapper.incursion_temp.first_run}')
        if open_incursion_ui_i == 15:
          poe_bot.logger.writeLine(f'open incursion window bug, item is hovered or whatever')
          # poe_bot.raiseLongSleepException(f'open incursion window bug')
          mapper.temp.alvas_to_ignore_ids.append(alva_entity.id)
          mapper.temp.alvas_to_ignore_ids.append(entrance_portal_entity.id)
          mapper.temp.save()
          if mapper.incursion_temp.need_to_use_timeless_scarab is True:
            print(f'seems like we placed timeless scarab already, will skip the others alvas on map')
            mapper.settings.do_alva = False
            mapper.incursion_temp.reset()
          poe_bot.ui.closeAll()
          poe_bot.bot_controls.keyboard_releaseKey('DIK_LCONTROL')
          return None
        if open_incursion_ui_i % 5 == 0:
          poe_bot.backend.forceRefreshArea()
        poe_bot.refreshInstanceData()
        if check_if_entrance_portal_targetable:
          incursion_enter_portal = next( (e for e in poe_bot.game_data.labels_on_ground_entities if e.path == "Metadata/Terrain/Leagues/Incursion/Objects/IncursionPortal1"), None)
          if incursion_enter_portal:
            print(f'found portal on opening incursion room')
            poe_bot.bot_controls.keyboard_releaseKey('DIK_LCONTROL')
            # poe_bot.ui.closeAll()
            return incursion_enter_portal
        entity_to_click = lookForAlvaNarbyEntrancePortal(entrance_portal_entity)
        if entity_to_click is None:
          print(f'alva disappeared?')
          dist_to_alva = dist( (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (entrance_portal_entity.grid_position.x, entrance_portal_entity.grid_position.y) )
          if dist_to_alva > 30:
            print(f'moved too far away from entrance portal ')
            poe_bot.bot_controls.keyboard_releaseKey('DIK_LCONTROL')
            poe_bot.mover.goToPoint(
              point=(entrance_portal_entity.grid_position.x, entrance_portal_entity.grid_position.y),
              custom_continue_function=poe_bot.combat_module.build.usualRoutine,
              release_mouse_on_end=True,
              min_distance = 30,
            )
          poe_bot.bot_controls.keyboard_pressKey('DIK_LCONTROL')
          continue

        if poe_bot.league == "Necropolis":
          poe_bot.helper_functions.clickNecropolisTabletIfPresentedNearEntity(entity_to_click)
        print(f'open_incursion_ui_i dupl {open_incursion_ui_i}  {mapper.incursion_temp.first_run}')
        if mapper.incursion_temp.first_run is True and open_incursion_ui_i % 3 == 0:
          print('closing alva dialogue')
          # poe_bot.ui.closeAll()
          bot_controls.keyboard.tap('DIK_SPACE')
          time.sleep(random.randint(10,20)/100)
          # time.sleep(random.randint(5,10)/100)
          incursion_ui.update()
          continue
        entity_to_click.click(update_screen_pos=True)
        time.sleep(random.randint(20,30)/100)
        incursion_ui.update()
      poe_bot.bot_controls.keyboard_releaseKey('DIK_LCONTROL')
      return None
    
    poe_bot.combat_module.build.prepareToFight(alva_entity)
    openIncursionWindow()
    if incursion_ui.incursions_remaining == 0:
      print('no alvas left on this map, and need to pick incursion from alva in hideout')
      poe_bot.ui.closeAll()
      mapper.settings.do_alva = False
      mapper.incursion_temp.reset()
      return True

    if incursion_ui.current_room is None:
      print('current alva is finished')
      poe_bot.ui.closeAll()
      mapper.temp.alvas_to_ignore_ids.append(alva_entity.id)
      mapper.temp.alvas_to_ignore_ids.append(entrance_portal_entity.id)
      mapper.temp.save()
      return True
    
    print(incursion_ui.current_room)
    mapper.incursion_temp.current_temple_state_dict = incursion_ui.raw
    mapper.incursion_temp.save()

    # reward start
    directions = ['left', 'right']
    must_do_reward = None
    need_to_do_scarab = False
    for valuable_room in mapper.settings.use_timeless_scarab_if_connected_or_presented:
      for reward in incursion_ui.rewards:
        if valuable_room in reward:
          must_do_reward = reward
          break
    if must_do_reward:
      print(f'found {must_do_reward} in rewards, doing it')
      must_do_reward_index = incursion_ui.rewards.index(must_do_reward)
      if incursion_ui.current_room.connected_to_entrance is True:
        if mapper.settings.use_timeless_scarab_if_connected_or_presented:
          print(f'upgrading this room will make it valuable')
          need_to_do_scarab = True

      # input('#TODO check if scarab is used in map device before running the map')
    else:
      print(f'didnt find any of {mapper.settings.use_timeless_scarab_if_connected_or_presented} in rewards')
      must_do_reward_index = 1

    incursion_explore_direction = directions[must_do_reward_index]
    kill_architect_priority = incursion_ui.architects_names[must_do_reward_index]
    # reward end

    # preferable room start
    preferable_rooms_to_open_sorted = []
    # valid room objects
    rooms_can_be_opened = list(filter(lambda room: room, incursion_ui.current_room_can_be_connected_to_rooms))
    print(f'rooms can be opened {list(map(lambda r: r.name, rooms_can_be_opened))}')
    # not apex
    rooms_can_be_opened = list(filter(lambda room: room.name != 'Apex of Atzoatl', rooms_can_be_opened))
    print(f'rooms not apex {list(map(lambda r: r.name, rooms_can_be_opened))}')
    # not rooms which are already in a chain with current room
    rooms_can_be_opened = list(filter(lambda room: room.index not in incursion_ui.current_room.connected_to_rooms, rooms_can_be_opened))
    print(f'rooms not in a chain with current room {list(map(lambda r: r.name, rooms_can_be_opened))}')
    # ??
    # rooms_can_be_opened = list(filter(lambda room: room.connected_to_entrance is False, incursion_ui.current_room_can_be_connected_to_rooms))

    need_to_open_more_rooms = True

    if mapper.settings.use_timeless_scarab_if_connected_or_presented:
      valuable_rooms = list(filter(lambda room: room.name in mapper.settings.use_timeless_scarab_if_connected_or_presented, incursion_ui.all_rooms))
      if valuable_rooms:
        print(f'valuable rooms exist in current temple state theyre {list(map(lambda r: r.name, valuable_rooms))}')
        if all(list(map(lambda room: room.connected_to_entrance == True, valuable_rooms))):
          print(f'all valuable rooms are already connected to entrance, dont open new rooms')
          preferable_rooms_to_open_sorted = []
          need_to_do_scarab = True
          need_to_open_more_rooms = False
        else:
          print(f'all valuable rooms are NOT connected to entrance')
          if all(list(map(lambda room: incursion_ui.current_room.index in room.connected_to_rooms, valuable_rooms))):
            print(f'all valuable rooms are in chain with current room, going to open nearest room which is connected to entrance')
            if incursion_ui.current_room.connected_to_entrance == True: input('valuable rooms are in chain with this room, not connected to entrance, but this room is connected to entrance')
            rooms_to_open_connected_to_entrance = list(filter(lambda room: room.connected_to_entrance == True, rooms_can_be_opened))
            if rooms_to_open_connected_to_entrance:
              print(f'going to open {list(map(lambda r: r.name, rooms_to_open_connected_to_entrance))} itll make valuable rooms connected to entrance as well')
              preferable_rooms_to_open_sorted = rooms_to_open_connected_to_entrance
              need_to_do_scarab = True
            else:
              print(f'none of the rooms to open is connected to entrance, trying to find rooms which has 1 step to entrance or rooms which have more chances to be connected to entrance pic.7')
              print(f'#TODO find shortest route from current room to room with entrance?')
          else:
            print(f'all valuable rooms are NOT connected to current room pics: 1 2 3 4 5 6')
            valuable_rooms_and_connected_to_them_indexes = list(map(lambda room: room.connected_to_rooms, valuable_rooms))
            valuable_rooms_and_connected_to_them_indexes_flat = [item for row in valuable_rooms_and_connected_to_them_indexes for item in row]
            valuable_rooms = list(map(lambda room_index: incursion_ui.all_rooms[room_index],valuable_rooms_and_connected_to_them_indexes_flat))
            print(f'valuable rooms and rooms connected to them {list(map(lambda r: r.name, valuable_rooms))}')
            valuable_rooms_can_be_connected = list(filter(lambda room: room in valuable_rooms, rooms_can_be_opened))
            print(f'valuable rooms can be connected {list(map(lambda r: r.name, valuable_rooms_can_be_connected))}')
            if valuable_rooms_can_be_connected:
              print('we can connect to valuable rooms chain pic 3, 4')
              preferable_rooms_to_open_sorted = valuable_rooms_can_be_connected
              if incursion_ui.current_room.connected_to_entrance:
                print(f'pic 3')
                need_to_do_scarab = True
            else:
              print('we cannot connect to valuable rooms chain pic 1,2,5,6')
              if incursion_ui.current_room.connected_to_entrance:
                print(f'current rooms is connected to entrance pic 1,6')
                # valuable_rooms_chain_can_have_connections_indexes = list(map(lambda val_room: incursion_ui.incursion_room_possible_connections[val_room.index], valuable_rooms_can_be_connected))
                # valuable_rooms_chain_can_have_connections_indexes_flat = [item for row in valuable_rooms_and_connected_to_them_indexes for item in row]
                # valuable_rooms_chain_can_have_connections = list(map(lambda room_index: incursion_ui.all_rooms[room_index],valuable_rooms_and_connected_to_them_indexes_flat))

                valuable_rooms_chain_can_have_connections_indexes = list(map(lambda val_room: incursion_ui.incursion_room_possible_connections[val_room.index], valuable_rooms_can_be_connected))
                valuable_rooms_chain_can_have_connections_indexes_flat = [item for row in valuable_rooms_chain_can_have_connections_indexes for item in row]
                valuable_rooms_chain_can_have_connections = list(map(lambda room_index: incursion_ui.all_rooms[room_index],valuable_rooms_chain_can_have_connections_indexes_flat))


                if valuable_rooms_chain_can_have_connections:
                  print(f'valuable_rooms_chain_can_have_connections {list(map(lambda r: r.name, valuable_rooms_chain_can_have_connections))}')
                  print(f'pic.1')
                  preferable_rooms_to_open_sorted = valuable_rooms_chain_can_have_connections
                else:
                  print('pic.6, usual temple open?')
              else:
                print(f'current rooms is NOT connected to entrance doing usual strat pic 2,5, usual temple open?')
      else:
        print(f'valuable rooms arent in current temple state')
    else:
      print(f'TODO check if any of valuable rooms was opened this run, if yeah, dont do alva for this map cos room procs once per map')

    # preferable room start
    if preferable_rooms_to_open_sorted == [] and need_to_open_more_rooms:
    # if preferable_rooms_to_open_sorted == []:
      if incursion_ui.current_room.connected_to_entrance:
        print(f'room is connected to entrance')
        rooms_which_are_not_connected_to_entrance = list(filter(lambda room: room.connected_to_entrance is False, rooms_can_be_opened))
        if rooms_which_are_not_connected_to_entrance:
          preferable_rooms_to_open_sorted = rooms_can_be_opened
          print(f'going to open {list(map(lambda r: r.name, rooms_which_are_not_connected_to_entrance))}, itll bring more connections')
      else:
        print(f'room is NOT connected to entrance')
        rooms_which_are_connected_to_entrance = sorted(rooms_can_be_opened, key = lambda room:room.connected_to_entrance is True, reverse=True)
        # rooms_which_are_connected_to_entrance = list(filter(lambda room: room.connected_to_entrance is True, rooms_can_be_opened))
        if rooms_which_are_connected_to_entrance:
          print(f'going to open {rooms_which_are_connected_to_entrance} itll make current room connected to entrance as well')
          preferable_rooms_to_open_sorted = rooms_which_are_connected_to_entrance
        else:
          print(f'going to open {list(map(lambda r: r.name, rooms_can_be_opened))}, itll bring more connections')
          preferable_rooms_to_open_sorted = sorted(rooms_can_be_opened, key=lambda room: len(room.connected_to_rooms), reverse=True)
    # preferable room end

    preferable_rooms_to_open_sorted = list(map(lambda room: room.name, preferable_rooms_to_open_sorted)) 
    print(f'going to open {preferable_rooms_to_open_sorted}')

    if need_to_do_scarab:
      if mapper.temp.used_timeless_scarab_for_alva == False:
        if incursion_ui.incursions_remaining > 0:
          poe_bot.logger.writeLine(f'alva, going to place scarab on next run and skip alva till end of map')
          mapper.incursion_temp.need_to_use_timeless_scarab = True
          mapper.incursion_temp.save()
          mapper.settings.do_alva = False
          poe_bot.ui.closeAll()
          return True

    if incursion_ui.incursions_remaining == 1:
      print(f'last incursion before temple')
      last_incursion_before_temple = True
      mapper.incursion_temp.reset()

    # enter incursion
    print(incursion_explore_direction, kill_architect_priority, preferable_rooms_to_open_sorted)
    mapper.incursion_temp.do_incursion_strategy = [incursion_explore_direction, kill_architect_priority, preferable_rooms_to_open_sorted]
    mapper.incursion_temp.first_run = False
    mapper.incursion_temp.save()
    def openIncursionRoom():
      start_time = time.time()
      print(f'openIncursionRoom call at {start_time}')
      open_room_wait_time_secs = 3
      refresh_area_threshhold = open_room_wait_time_secs/2
      cycle = 0
      
      incursion_ui.clickEnterIncursion()
      incursion_ui.visible = False
      refreshed_area_in_this_cycle = False
      last_open_incursion_time = time.time()

      while True:
        time_passed_since_start = time.time() - last_open_incursion_time
        print(f'cycle: {cycle} time_passed_since_start: {time_passed_since_start}')
        if cycle > 10 or time_passed_since_start > 30:
          poe_bot.logger.writeLine(f'cannot open incursion for 10 cycles')
          poe_bot.on_stuck_function()
        if time_passed_since_start > refresh_area_threshhold and refreshed_area_in_this_cycle is False:
          print(f'force refreshing area')
          poe_bot.backend.forceRefreshArea()
          refreshed_area_in_this_cycle = True
        poe_bot.refreshInstanceData()
        poe_bot.game_data.updateLabelsOnGroundEntities()
        incursion_enter_portal = next( (e for e in poe_bot.game_data.labels_on_ground_entities if e.path == "Metadata/Terrain/Leagues/Incursion/Objects/IncursionPortal1"), None)
        print('incursion_enter_portal: ', incursion_enter_portal)
        if incursion_enter_portal:
          print(f'openIncursionRoom return at {time.time()}')
          return incursion_enter_portal
        else:
          if time_passed_since_start > open_room_wait_time_secs:
            print("opening portal again")
            cycle += 1
            opened = openIncursionWindow(check_if_entrance_portal_targetable=True)
            if opened is None:
              incursion_ui.clickEnterIncursion()
            incursion_ui.visible = False
            refreshed_area_in_this_cycle = False
            last_open_incursion_time = time.time()
            continue

          killed_someone = combat_module.clearLocationAroundPoint(
            {"X":alva_entity.grid_position.x, "Y":alva_entity.grid_position.y}, 
            detection_radius=30, 
            ignore_keys=mapper.current_map.entities_to_ignore_in_bossroom_path_keys
          )
          if killed_someone is False:
            point = poe_bot.game_data.terrain.pointToRunAround(
              point_to_run_around_x=alva_entity.grid_position.x,
              point_to_run_around_y=alva_entity.grid_position.y,
              distance_to_point=15,
              check_if_passable=True
            )
            poe_bot.mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
            poe_bot.combat_module.build.staticDefence()
    incursion_enter_portal = openIncursionRoom()
  else:
    print(f'portal is targetable, no need to open incursion again')
    incursion_enter_portal = entrance_portal_entity 
    incursion_ui.update()
    incursion_explore_direction, kill_architect_priority, preferable_rooms_to_open_sorted = mapper.incursion_temp.do_incursion_strategy
  # if portal is visible continue from here
  distance_to_incursion_portal = dist( (poe_bot.game_data.player.grid_pos.x,poe_bot.game_data.player.grid_pos.y), (incursion_enter_portal.grid_position.x, incursion_enter_portal.grid_position.y))
  print(f'distance to incursion portal {distance_to_incursion_portal}')
  if distance_to_incursion_portal > 50:
    poe_bot.mover.goToEntitysPoint(incursion_enter_portal, custom_continue_function=poe_bot.combat_module.build.staticDefence)
  poe_bot.mover.enterTransition(incursion_enter_portal, screen_pos_offset=[7,7])
  mapper.temp.alvas_to_ignore_ids.append(alva_entity.id)
  mapper.temp.alvas_to_ignore_ids.append(entrance_portal_entity.id)
  mapper.temp.save()
  # wait till loaded
  incursion_encounter = IncursionEncounter(poe_bot=poe_bot)
  if mapper.settings.alva_ignore_temple_mechanics is True:
    preferable_rooms_to_open_sorted = []
    kill_architect_priority = "ignoring_architect_priority"
  need_to_clear_room = False
  if mapper.settings.alva_clear_room != False or (preferable_rooms_to_open_sorted != [] and mapper.settings.alva_clear_room_if_need_to_connect != False):
    need_to_clear_room = True

  incursion_encounter.doIncursionRoom(incursion_explore_direction, kill_architect_priority, preferable_rooms_to_open_sorted, need_to_clear_room)

  if mapper.temp.used_timeless_scarab_for_alva is True:
    print("len(mapper.temp.alvas_to_ignore_ids): ",len(mapper.temp.alvas_to_ignore_ids))
    if len(mapper.temp.alvas_to_ignore_ids) == 6 or last_incursion_before_temple:
      end_time = time.time() + random.randint(13,15)
      clockwise = random.choice([True, False])
      poe_bot.ui.inventory.update()
      itemised_temples_in_inventory = list(filter(lambda item: item.name == "Chronicle of Atzoatl", poe_bot.ui.inventory.items))
      collect_loot_i = 0
      while time.time() < end_time:
        collect_loot_i += 1
        if collect_loot_i % 5 ==0:
          incursion_ui.update()
          if incursion_ui.visible is True:
            poe_bot.ui.closeAll()
        poe_bot.refreshInstanceData()
        picked_smth = poe_bot.loot_picker.collectLoot()
        if picked_smth != True:
          point = poe_bot.game_data.terrain.pointToRunAround(
            point_to_run_around_x=alva_entity.grid_position.x,
            point_to_run_around_y=alva_entity.grid_position.y,
            distance_to_point=20,
            reversed = clockwise,
            check_if_passable=True
          )
          mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
          poe_bot.combat_module.build.staticDefence()
        else:
          poe_bot.ui.inventory.update()
          itemised_temples_in_inventory_now = list(filter(lambda item: item.name == "Chronicle of Atzoatl", poe_bot.ui.inventory.items))
          if len(itemised_temples_in_inventory_now) > len(itemised_temples_in_inventory):
            print(f'picked temple')
            break

  poe_bot.logger.writeLine('alva, finished incursion')
  if last_incursion_before_temple is False:
    if mapper.incursion_temp.current_temple_state_dict != {}:
      if incursion_ui.incursions_remaining == 0:
        incursion_ui.update(mapper.incursion_temp.current_temple_state_dict, update_current_room=False)
      mapper.incursion_temp.current_temple_state_dict['irt'] = f"{incursion_ui.incursions_remaining-1} Incursions Remaining"
      mapper.incursion_temp.save()
  print(f'#doAlvaEncounter nearby {alva_entity.raw} return at {time.time()}')
  return True
# incursion end


# In[15]:


BEASTS_KEYWORDS = {
  "Craicic Chimeral": ["Metadata/Monsters/LeagueBestiary/GemFrogBestiary"], # Craicic Chimeral
  "Vivid Watcher": ["Metadata/Monsters/LeagueHarvest/Green/HarvestSquidT3_", "Metadata/Monsters/LeagueHarvest/Green/HarvestSquidT3MemoryLine_"], # vivid watcher
  "Vivid Vulture": ["Metadata/Monsters/LeagueHarvest/Green/HarvestVultureParasiteT3", "Metadata/Monsters/LeagueHarvest/Green/HarvestVultureParasiteT3MemoryLine"], # vivid vulture
  "Wild Bristle Matron": ["Metadata/Monsters/LeagueHarvest/Red/HarvestBeastT3", "Metadata/Monsters/LeagueHarvest/Red/HarvestBeastT3MemoryLine_"], # Wild Bristle Matron
  "Wild Hellion Alpha": ["Metadata/Monsters/LeagueHarvest/Red/HarvestHellionT3", "Metadata/Monsters/LeagueHarvest/Red/HarvestHellionT3MemoryLine"], # Wild Hellion Alpha
  "Black Morrigan": ["Metadata/Monsters/LeagueAzmeri/GullGoliathBestiary_"], # The Black Mórrigan
}
VALUABLE_BEASTS_KEYWORDS = []
for val in BEASTS_KEYWORDS.values(): VALUABLE_BEASTS_KEYWORDS.extend(val)
def doEncounter(entity:Entity):
  pass
def doNearestEncounter(encounters:List[Entity]):
  encounters_sorted = sorted(encounters, key=lambda e: e.distance_to_player)
  pass

def seekForValuableBeasts():
  valuable_beasts = list(filter(lambda e: e.path.split('@')[0] in VALUABLE_BEASTS_KEYWORDS and poe_bot.game_data.terrain.checkIfPointPassable(e.grid_position.x, e.grid_position.y), poe_bot.game_data.entities.all_entities))
  return valuable_beasts

def seekForEssences(search_loc = None):
  '''
  search_loc: [gridx,gridy]
  '''
  essences = list(filter(lambda e: e.is_targetable is True and ESSENCES_KEYWORD in e.path and poe_bot.game_data.terrain.checkIfPointPassable(e.grid_position.x, e.grid_position.y), poe_bot.game_data.entities.all_entities))
  return essences

def seekForHarbringers():
  harbringers = list(filter(lambda e: "Metadata/Monsters/Avatar/Avatar" in e.path, poe_bot.game_data.entities.all_entities))
  return harbringers

def seekForLegionMonolith():
  legion_monoliths = list(filter(lambda e: "Metadata/Terrain/Leagues/Legion/Objects/LegionInitiator" in e.path and e.is_targetable is True, poe_bot.game_data.entities.all_entities))
  return legion_monoliths

def doEssenceEncounter(essence:Entity):
  # debug
  # poe_bot.refreshInstanceData()
  # go to around essence
  inventory = poe_bot.ui.inventory


  essence_monolith = essence
  print(f'#doEssenceEncounter nearby {essence_monolith} call at {time.time()}')
  essence_opened = False
  essence_monolith_id = essence_monolith.id
  grid_pos_x = essence_monolith.grid_position.x
  grid_pos_y = essence_monolith.grid_position.y


  while True:
    res = mover.goToPoint(
      point=(grid_pos_x, grid_pos_y),
      min_distance=75,
      custom_continue_function=build.usualRoutine,
      custom_break_function=poe_bot.loot_picker.collectLoot,
      release_mouse_on_end=False,
      # release_mouse_on_end=True,
      step_size=random.randint(25,33)
    )
    if res is None:
      break

  valuable_essences = ["Misery", "Envy", "Dread", "Scorn"]
  visible_labels = poe_bot.backend.getVisibleLabels()

  essence_label = list(filter(lambda label:label['id'] == essence_monolith_id,visible_labels))[0]
  essence_label_id = essence_label['id']
  print(f'essence_label {essence_label}')
  essence_texts = ' '.join(essence_label['texts'])

  shrieking_count = len(essence_texts.split("Shrieking"))-1
  screaming_count = len(essence_texts.split("Screaming"))-1
  deafening_count = len(essence_texts.split("Deafening"))-1
  remnant_of_corruption_count = len(essence_texts.split('Remnant of Corruption'))-1

  print(f'screaming_count {screaming_count}')
  print(f'shrieking_count {shrieking_count}')
  print(f'deafening_count {deafening_count}')

  valuable_mods_count = shrieking_count + screaming_count + deafening_count + remnant_of_corruption_count
  if any(list(map(lambda string: string in essence_texts, ["Horror", "Delirium", "Hysteria"]))):
    valuable_mods_count += 2
  print(f'valuable_mods_count {valuable_mods_count}')
  if mapper.settings.essences_do_all is False and valuable_mods_count < 1:
    print(f'not worth to open this essence')
    mapper.temp.essences_to_ignore_ids.append(essence_label_id)
    return True


  combat_module.clearLocationAroundPoint({"X": essence_monolith.grid_position.x, "Y": essence_monolith.grid_position.y}, detection_radius=45)


  poe_bot.refreshInstanceData()
  essence_mobs = list(filter(lambda e: e.grid_position.x == essence_monolith.grid_position.x and e.grid_position.y == essence_monolith.grid_position.y and e.rarity == 'Rare', poe_bot.game_data.entities.all_entities))
  
  essences = list(filter(lambda entity: essence_monolith_id == entity.id,poe_bot.game_data.entities.all_entities))
  if len(essences) == 0:
    print(f'len(essences) == 0 after we arrived')
    return False

  print(f'essence_mobs {essence_mobs}')

  # opening essence
  essence_monolith = essences[0]
  build.prepareToFight(essence_monolith)

  need_to_corrupt = False
  if any(list(map(lambda key: key in essence_texts, valuable_essences))) is True:
    need_to_corrupt = True

  essence_mods_len = shrieking_count + screaming_count
  print(f'essences_count in essence: {essence_mods_len}, min essences to corrupt {mapper.settings.essences_min_to_corrupt}')
  if essence_mods_len >= mapper.settings.essences_min_to_corrupt:
    need_to_corrupt = True

  # need_to_corrupt = True;print('#debug remove need_to_corrupt = True')
  if 'Remnant of Corruption' in essence_texts or "Corrupted" in essence_label['texts']:
    need_to_corrupt = False
  print(f'need_to_corrupt {need_to_corrupt}')


  print(f'mapper.settings.essences_can_corrupt {mapper.settings.essences_can_corrupt} need_to_corrupt {need_to_corrupt}')
  # if False:
  if mapper.settings.essences_can_corrupt is True and need_to_corrupt is True:
    inventory_items = inventory.update()
    remnants_of_corruptions = list(filter(lambda item: item.name == 'Remnant of Corruption', inventory.items))
    if len(remnants_of_corruptions) != 0:
      print(f'have {len(remnants_of_corruptions)} remnantofcorruption, corrupting it')
      essence_corrupted = False
      while True:
        
        # get to it
        print('going to essence to corrupt it')
        while True:
          poe_bot.refreshInstanceData()
          poe_bot.last_action_time = 0
          res = mover.goToPoint(
            point=(grid_pos_x, grid_pos_y),
            min_distance=30,
            custom_continue_function=build.usualRoutine,
            release_mouse_on_end=True,
            # release_mouse_on_end=False,
            step_size=random.randint(25,33)
          )
          if res is None:
            break

        visible_labels = poe_bot.backend.getVisibleLabels()
        updated_essence_label = list(filter(lambda label: label['id'] == essence_label_id, visible_labels))[0]
        print(f'updated_essence_label {updated_essence_label}')
        

        poe_bot.bot_controls.keyboard_pressKey('DIK_LSHIFT')
        inventory.open()
        remnant_of_corruptions = remnants_of_corruptions[0]
        remnant_of_corruptions.hover()
        time.sleep(random.randint(2,4)/100)
        remnant_of_corruptions.click(button='right')
        poe_bot.bot_controls.keyboard_pressKey('DIK_LSHIFT')
        for i in range(10):
          visible_labels = poe_bot.backend.getVisibleLabels()
          updated_essence_labels = list(filter(lambda label: label['id'] == essence_label_id, visible_labels))
          if len(updated_essence_labels) == 0:
            print(f'seems like we opened essence:(')
            essence_corrupted = True
            break
          updated_essence_label = updated_essence_labels[0]
          print(f'updated_essence_label {updated_essence_label}')
          if 'Corrupted' in updated_essence_label['texts']:
            print(f'essence is corrupted, success')
            essence_corrupted = True
            break
          essence_label_center = [ (updated_essence_label['p_o_s']['x1'] + updated_essence_label['p_o_s']['x2'])/2, (updated_essence_label['p_o_s']['y1'] + updated_essence_label['p_o_s']['y2'])/2 ]
          if essence_label_center[0] > 512:
            essence_label_center[0] = 512
          item_pos_x,item_pos_y = poe_bot.convertPosXY(essence_label_center[0],essence_label_center[1])
          bot_controls.mouse.setPosSmooth(int(item_pos_x),int(item_pos_y))
          time.sleep(random.randint(2,4)/100)
          bot_controls.mouse.click()
          
          visible_labels = poe_bot.backend.getVisibleLabels()
          updated_essence_label = next( (label for label in visible_labels if label['id'] == essence_label_id), None)
          if updated_essence_label == None:
            print(f'essence opened by itself')
            essence_corrupted = True
            essence_opened = True
            break
          updated_essence_label = list(filter(lambda label: label['id'] == essence_label_id, visible_labels))[0]
          print(f'updated_essence_label {updated_essence_label}')
        poe_bot.bot_controls.keyboard_releaseKey('DIK_LSHIFT')
        for i in range(random.randint(2,3)):
          poe_bot.bot_controls.keyboard.tap('DIK_SPACE', wait_till_executed=False)
        if essence_corrupted is True:
          break


    else:
      print('dont have remnant of corruption')
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
    print(f'essence_monolith {essence_monolith}')
    if essence_monolith.distance_to_player > 40:
      print(f'essence_monolith distance to player is too far away, getting closer')
      mover.goToEntity(
        entity_to_go=essence_monolith, 
        custom_continue_function=build.usualRoutine, 
        release_mouse_on_end=False,
        # release_mouse_on_end=True,
        step_size=random.randint(25,33)
      )
      continue
    pos_x, pos_y = poe_bot.convertPosXY(essence_monolith.location_on_screen.x,essence_monolith.location_on_screen.y)
    print(f'opening essence on {pos_x, pos_y}')
    poe_bot.bot_controls.mouse.setPosSmooth(pos_x,pos_y)
    # time.sleep(random.randint(5,7)/100)
    poe_bot.bot_controls.mouse.click()
    # time.sleep(random.randint(7,10)/100)
    poe_bot.refreshInstanceData()
    poe_bot.last_action_time = 0
    essences = list(filter(lambda entity: essence_monolith_id == entity.id,poe_bot.game_data.entities.all_entities))
    if len(essences) == 0 or essences[0].is_targetable is False :
      break
  print('essence opened')
  if len(essence_mobs) != 0:
    main_essence_mob = essence_mobs[0]
    print(f'main_essence_mob {main_essence_mob}')
    # entities_to_kill = list(filter(lambda e: e.path == main_essence_mob.path and e.distance_to_player < 40 and e.rarity == 'Rare', poe_bot.game_data.entities.all_entities))
    entities_to_kill = list(filter(lambda e: e.path == main_essence_mob.path and e.distance_to_player < 40 and e.rarity == 'Rare' and e.is_attackable is True, poe_bot.game_data.entities.all_entities))
    print(f'entities_to_kill {entities_to_kill}')
    for entity in entities_to_kill:
      combat_module.killTillCorpseOrDisappeared(entity)
  else:
    point_to_run_around = {"X": essence.grid_position.x, "Y": essence.grid_position.y}
    combat_module.clearLocationAroundPoint(point_to_run_around)

  poe_bot.refreshInstanceData()
  print(f'#doEssenceEncounter nearby {essence_monolith} return at {time.time()}')
def doLegionEncounter(legion_monolith:Entity):
  print(f'#doLegionEncounter nearby {legion_monolith} call at {time.time()}')

  stasis_duration = 13
  legion_monolith_id = legion_monolith.id
  grid_pos_x = legion_monolith.grid_position.x
  grid_pos_y = legion_monolith.grid_position.y
  mover.goToPoint(
    point=(grid_pos_x, grid_pos_y),
    min_distance=30,
    custom_continue_function=build.usualRoutine, 
    release_mouse_on_end=False,
    step_size=random.randint(25,33)
  )



  # activating monolith
  stasis_stance = True

  _i = 0
  while legion_monolith.is_targetable is True:
    _i += 1
    if _i > 50:
      poe_bot.raiseLongSleepException('cannot open legion_monolith for 50 iterations')

    legion_monolith = list(filter(lambda entity: legion_monolith_id == entity.id,poe_bot.game_data.entities.all_entities))[0]
    if legion_monolith.distance_to_player > 40:
      mover.goToPoint(
        point=(grid_pos_x, grid_pos_y),
        min_distance=30,
        custom_continue_function=build.usualRoutine, 
        release_mouse_on_end=False,
        step_size=random.randint(25,33)
      )
      continue

    pos_x, pos_y = poe_bot.convertPosXY(legion_monolith.location_on_screen.x,legion_monolith.location_on_screen.y)
    print(f'opening legion_monolith on {pos_x, pos_y}')
    poe_bot.bot_controls.mouse.setPosSmooth(pos_x,pos_y)
    poe_bot.bot_controls.mouse.click()
    poe_bot.refreshInstanceData()
    legion_monoliths = list(filter(lambda entity: legion_monolith_id == entity.id,poe_bot.game_data.entities.all_entities))
    if len(legion_monoliths) == 0 or legion_monoliths[0].is_targetable is False :
      break
  monolith_opened_at = time.time()
  print(f'legion_monolith opened at {monolith_opened_at}')

  time_now = time.time()

  # stuff we are going to kill after stasis
  chests_generals_sergants = []
  # guaranteed stasis duration
  while time_now < monolith_opened_at + stasis_duration:
    time_now = time.time()
    mob_to_kill = findMoreValuableMobInStasisToKill()
    if mob_to_kill is not None:
      combat_module.killUsualEntity(mob_to_kill)
    else:
      mover.goToPoint(
        point=(grid_pos_x, grid_pos_y),
        min_distance=50,
        custom_continue_function=build.usualRoutine, 
        release_mouse_on_end=False,
        step_size=random.randint(25,33)
      )
      mob_to_kill = findMoreValuableMobInStasisToKill()
      if mob_to_kill is None:
        mob_to_kill = findMoreValuableMobInStasisToKill(include_normal=True)
      if mob_to_kill is not None:
        combat_module.killUsualEntity(mob_to_kill)
    poe_bot.refreshInstanceData()
  print(f'stasis stage is over at {time_now}')
  # after stasis
  while True:
    legion_mobs = []
    for e in poe_bot.game_data.entities.attackable_entities:
      if not "/LegionLeague/" in e.path:
        continue
      print(e.raw)
      legion_mobs.append(e)
    if len(legion_mobs) == 0:
      break
    for e in legion_mobs:
      combat_module.killUsualEntity(e)
    poe_bot.loot_picker.collectLoot()
  poe_bot.loot_picker.collectLoot()
  print(f'#doLegionEncounter nearby {legion_monolith} return at {time.time()}')
def killUniqueEntityIfFound(mover=None):
  unique_entities = list(filter(lambda e: e.rarity == 'Unique' and poe_bot.game_data.terrain.checkIfPointPassable(e.grid_position.x, e.grid_position.y),poe_bot.game_data.entities.attackable_entities))
  if len(unique_entities) != 0:
    print("#killUniqueEntityIfFound found unique entity, killing it")
    for unique_entity in unique_entities:
      combat_module.killUsualEntity(unique_entity)
    return True
  return False
def doPartyUltimatumOnMap(ultimatum_altar:Entity):
  print(f'#doPartyUltimatumOnMap nearby {ultimatum_altar} call at {time.time()}')
  grid_pos_x = ultimatum_altar.grid_position.x
  grid_pos_y = ultimatum_altar.grid_position.y
  print(f'going to altar ')
  while True:
    res = mover.goToPoint(
      point=(grid_pos_x, grid_pos_y),
      min_distance=50,
      custom_continue_function=build.usualRoutine,
      custom_break_function=poe_bot.loot_picker.collectLoot,
      release_mouse_on_end=True,
      step_size=random.randint(25,33)
    )
    if res is None:
      break
  
  print(f'gonna open portal near ultimatum')
  portal_nearby = waitForPortalNearby(poe_bot=poe_bot, wait_for_seconds=0.1)
  while portal_nearby is False:
    openPortal(poe_bot=poe_bot, swap_weapons=False)
    portal_nearby = waitForPortalNearby(poe_bot=poe_bot, wait_for_seconds=0.1)

  poe_bot.coordinator.setGroupCommand('run_ultimatum')
  input('waiting for party members')
  ultimatum_encounter = UltimatumEncounter(poe_bot=poe_bot, ultimatum_altar=ultimatum_altar)
  poe_bot.refreshInstanceData()
  ultimatum_encounter.start()

  ultimatum_started = False
  ultimatum_altar:Entity
  trialmaster_entity = next( (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/NPC/League/Ultimatum/UltimatumNPC"), None)
  if trialmaster_entity is None:
    poe_bot.raiseLongSleepException('trialmaster is none')
  while ultimatum_started is False:
    # use flasks if needed, pf especially
    poe_bot.combat_module.build.auto_flasks.useFlasks()
    trialmaster_entity = next( (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/NPC/League/Ultimatum/UltimatumNPC"), None)
    possible_ultimatum_altar:Entity = next( (e for e in poe_bot.game_data.entities.all_entities if e.path == ULTIMATUM_ALTAR_PATH), None)
    if possible_ultimatum_altar:
      ultimatum_altar = possible_ultimatum_altar
    if trialmaster_entity:
      print(f'trialmaster_entity.is_targetable {trialmaster_entity.is_targetable}')
      if trialmaster_entity.is_targetable is False:
        print(f'seems like ultimatum started')
        ultimatum_started = True
        break
    poe_bot.refreshInstanceData()

  print(f'ultimatum encounter started')
  ultimatum_encounter.run()
  # collect loot
  ultimatum_encounter.pickupLootAfterUltimatum()
  poe_bot.helper_functions.getToPortal(refresh_area=True, check_for_map_device=False)
  poe_bot.coordinator.setGroupCommand('stay_hideout')
  ultimatum_encounter.doUltimatumStashingRoutine(keep_scarabs_and_maps=True)
  mapper.temp.map_completed = True
  raise Exception('forcing it to start again since its a only party ultimatum guy')
class Mapper:
  poe_bot:PoeBot
  temp:MapsTempData
  incursion_temp:IncursionTempData
  current_map: MapArea
  last_seen_einhar:Entity = None

  ignore_bossroom = None

  # pre map behavior
  boss_rush = False # will use different TSP strategy and consider map as finished after kill the boss
  atlas_explorer = False # prefer to run higher tier maps over lower tier
  prefer_high_tier = True # prefer to run higher tier maps over lower tier
  modify_maps = [] # ['chisel_alch', 'chaos_reroll_or_scour_alch', 'vaal'] \ vendor restricted maps

  musthave_map_device_modifiers = [] # items to place in addition to map in map device, will throw an error if wont have them in inventory before running map

  # behaivior on map
  one_portal = True # if True won't try to go back to map if died during it
  force_kill_boss = True # will seek for boss room\boss if didnt kill it before getting back to HO
  ignore_map_boss = False # will ignore bossrooms and map bosses if found

  do_legion = False # will do legion if find it
  do_blight = False # will do blight if find it
  do_harvest = False # will do harvest if find it
  
  
  can_pick_drop = None
  activated_activator_in_bossroom = False
  maps_in_inventory = None
  need_to_visit_wildwood = False
  started_running_map_at = 0
  
  def __init__(self, poe_bot:PoeBot, strategy:dict):

    self.poe_bot = poe_bot
    self.temp = MapsTempData(unique_id=poe_bot.unique_id, reset=force_reset_temp)
    self.settings = MapperSettings(strategy)
    self.mapper_session_temp = MapperSession(unique_id=poe_bot.unique_id, session_duration = self.settings.session_duration)

    try: self.one_portal = strategy['one_portal']
    except: pass
    try: self.atlas_explorer = strategy['atlas_explorer']
    except: pass

    try: self.boss_rush = strategy['boss_rush']
    except: pass

    try: self.prefer_high_tier = strategy['prefer_high_tier']
    except: pass

    try: self.force_kill_boss = strategy['force_kill_boss']
    except: pass

    try: self.ignore_map_boss = strategy['ignore_map_boss']
    except: pass

    try: self.do_legion = strategy['do_legion']
    except: pass

    try: self.do_blight = strategy['do_blight']
    except: pass

    try: self.musthave_map_device_modifiers = strategy['musthave_map_device_modifiers']
    except: pass

    if self.settings.do_alva:
      self.incursion_temp = IncursionTempData(unique_id=self.poe_bot.unique_id)
  @staticmethod
  def getConfigs():
    file_path = './temp/launcher/mapper_configs.json'
    try:
      print(f'loading config from {file_path}')
      file = open(file_path, encoding='utf-8')
    except FileNotFoundError:
      file_path = './defaults/mapper_configs.json'
      print(f'launcher config not found loading default mapper_configs {file_path}')
      file = open(file_path, encoding='utf-8')

    config = json.load(file)
    file.close()
    return config
  @staticmethod
  def getDefaultSessionTime():
    file_path = './temp/launcher/mapper_configs.json'
    try:
      print(f'loading config from {file_path}')
      file = open(file_path, encoding='utf-8')
    except FileNotFoundError:
      file_path = './defaults/mapper_configs.json'
      print(f'launcher config not found loading default mapper_configs {file_path}')
      file = open(file_path, encoding='utf-8')

    config = json.load(file)
    file.close()
    return config

  def activateCrystalMemory(self):
    def checkIfMemoryActivated():
      # open dialogue with einhar
      # get his texts to click
      # check if Crystal Memory or smth presented
      pass
    def activateMemoryOn(pos_x:int, pos_y:int):
      # ctrl g
      # open inventory
      # right click on memory
      # click on pixels
      # check if item disappeared

      pass
    memory_activated = checkIfMemoryActivated()
    if memory_activated == False:
      activateMemoryOn(1,1)
      # open dialgue with einhar

    
    
    pass

  def getMapsCanRun(self, priority='inventory', source='all'):
    inventory = self.poe_bot.ui.inventory
    stash = self.poe_bot.ui.stash
    
    all_maps:List[Item] = []
    maps_we_can_run_in_inventory:List[InventoryItem] = []
    maps_we_can_run_in_stash:List[StashItem] = []

    
    
    if source != 'stash':
      inventory.update()
      maps_we_can_run_in_inventory = self.filterMapsCanRun(inventory.items)
    if source != 'inventory':
      all_stash_items = stash.getAllItems()
      maps_we_can_run_in_stash = self.filterMapsCanRun(all_stash_items)

    if priority == 'inventory':
      all_maps.extend(maps_we_can_run_in_inventory)
      all_maps.extend(maps_we_can_run_in_stash)
    else:
      all_maps.extend(maps_we_can_run_in_stash)
      all_maps.extend(maps_we_can_run_in_inventory)
      
    sorted_maps = self.sortMaps(all_maps)
    return sorted_maps
  def updateAlvaInHideout(self):
    incursion_ui = poe_bot.ui.incursion_ui
    itemized_temple_taken = False
    poe_bot.ui.incursion_ui.open()
    if incursion_ui.incursions_remaining == 0:
      print("can take itemized temple")
      itemized_temple_taken = True
      incursion_ui.takeItemizedTemple()
      poe_bot.logger.writeLine('alva, taken itemized temple')
      poe_bot.ui.closeAll()
      time.sleep(random.randint(20,40)/100)
      poe_bot.ui.incursion_ui.open()
      time.sleep(random.randint(10,50)/10)
    if self.settings.use_timeless_scarab_if_connected_or_presented:
      connected_rooms = list(filter(lambda room: room.connected_to_entrance is True, incursion_ui.all_rooms))
      connected_valuable_rooms = list(filter(lambda room: room.name in self.settings.use_timeless_scarab_if_connected_or_presented, connected_rooms))
      if connected_valuable_rooms != []:
        print(f'already have {connected_valuable_rooms} in connected rooms')
        self.incursion_temp.need_to_use_timeless_scarab = True
    self.incursion_temp.current_temple_state_dict = incursion_ui.raw
    if itemized_temple_taken is True or incursion_ui.incursions_remaining == 12: self.incursion_temp.first_run = True
    self.incursion_temp.save()
    poe_bot.ui.closeAll()
    incursion_ui.visible = False
    time.sleep(1)
  def putIncursionScarabs(self, do_place = True):
    map_device = poe_bot.ui.map_device
    inventory = poe_bot.ui.inventory
    incursion_scarab_render_path = 'Art/2DItems/Currency/Scarabs/Tier4ScarabIncursion.dds'
    map_device.update() # remove
    scarabs_in_map_device = list(filter(lambda i: i.render_path == incursion_scarab_render_path, map_device.items))
    if do_place is True:
      # place in if 0
      if len(scarabs_in_map_device) == 0:
        inventory.update() # remove
        incursion_timelines_scarabs_in_inventory = list(filter(lambda i: i.render_path == incursion_scarab_render_path, inventory.items))
        if len(incursion_timelines_scarabs_in_inventory) == 0:
          poe_bot.raiseLongSleepException('no timeless scarabs in inventory')
        incursion_timelines_scarabs_in_inventory.sort(key=lambda i: i.items_in_stack)
        incursion_timelines_scarabs_in_inventory[0].click(hold_ctrl=True)
        time.sleep(random.randint(50,120)/100)
        map_device.update() # remove
        return True
    else:
      # take out
      if len(scarabs_in_map_device) != 0:
        poe_bot.ui.clickMultipleItems(scarabs_in_map_device, hold_ctrl=True)
    return True
  def sortAndFilterItemizedTemples(self):
    stash = poe_bot.ui.stash
    inventory = poe_bot.ui.inventory

    #TODO check if stash tab index is 0
    if stash.is_opened is False or stash.current_tab_index != 0:
      print(f'{stash.is_opened} or {stash.current_tab_index}, dont do anything here')
      return False
    # stash all temples first
    inventory.update()
    items = list(filter(lambda item: item.render_path == 'Art/2DItems/Maps/TempleMap.dds', inventory.items))
    inventory.stashItems(items)

    stash.update()
    items = stash.current_tab_items
    items = list(filter(lambda item: item.render_path == 'Art/2DItems/Maps/TempleMap.dds', stash.current_tab_items))
    to_exec = [
      lambda: items.sort(key=lambda item: item.grid_position.x1, reverse=bool(random.randint(0,1)) ),
      lambda: items.sort(key=lambda item: item.grid_position.y1, reverse=bool(random.randint(0,1)) )
    ] 
    random.shuffle(to_exec)
    for exec in to_exec:
      exec()
    if len(items) < 40:
      print(f'[Mapper.sortAndFilterItemizedTemples] there are {len(items)} in stash, recycling them is too early?')
      return False
    time.sleep(0.05)
    for item in items:
      while True:
        item.hover()
        time.sleep(random.randint(10,50)/100)
        hovered_item_info = poe_bot.backend.getHoveredItemInfo()
        break
      item.clipboard_text = " ".join(hovered_item_info['tt'])
      time.sleep(random.randint(10,50)/100)

    if self.settings.use_timeless_scarab_if_connected_or_presented != []:
      possible_keys = ["Locus of Corruption (Tier 3)", "Doryani's Institute (Tier 3)"]
      keys_to_keep = list(filter(lambda possible_key:  any(list(map(lambda room_for_scarab: room_for_scarab in possible_key , self.settings.use_timeless_scarab_if_connected_or_presented))), possible_keys))
    else:
      keys_to_keep = ["Locus of Corruption (Tier 3)", "Doryani's Institute (Tier 3)"]
    keys_to_keep.extend(self.settings.alva_also_keep_temples_with)
    poe_bot.logger.writeLine(f'keys to keep {keys_to_keep}')
    items_to_keep:List[StashItem] = []
    items_to_sell:List[StashItem] = []
    for item in items:
      item_text = item.clipboard_text
      # print(item_text)
      item_text_cropped = item_text.split('Obstructed Rooms:')[0].split('Apex of Atzoatl')[0].split('Open Rooms:')[1]
      print(item_text_cropped)
      if list(filter(lambda key: key in item_text_cropped, keys_to_keep)) != []:
        print(f'gonna keep it')
        items_to_keep.append(item)
      else:
        print('recycle')
        items_to_sell.append(item)


    poe_bot.logger.writeLine(f'alva, temples, recycling:{len(items_to_sell)}, keeping:{len(items_to_keep)}')
    if len(items_to_keep) != 0:
      inventory.update()
      items_grid_position_backup = list(map(lambda i: (i.grid_position.x1, i.grid_position.y1), inventory.items))
      empty_slots = inventory.getEmptySlots()
      items_to_keep = items_to_keep[:len(empty_slots)]
      poe_bot.ui.clickMultipleItems(items_to_keep)
      inventory.update()
      new_items = list(filter(lambda i: not (i.grid_position.x1, i.grid_position.y1) in items_grid_position_backup, inventory.items))
      stash.placeItemsAcrossStash(new_items)

    stash.openTabIndex(0)
    inventory.update()
    items_grid_position_backup = list(map(lambda i: (i.grid_position.x1, i.grid_position.y1), inventory.items))
    empty_slots = inventory.getEmptySlots()
    items_to_sell = items_to_sell[:len(empty_slots)]
    poe_bot.ui.clickMultipleItems(items_to_sell)
    inventory.update()
    new_items = list(filter(lambda i: not (i.grid_position.x1, i.grid_position.y1) in items_grid_position_backup, inventory.items))

    poe_bot.ui.closeAll()
    poe_bot.helper_functions.sellItems(items_to_sell=new_items, skip_items = False,shuffle_items = False)

    stash.open()
  def sortMaps(self, items:List[Item]):
    # low tier, high tier
    items = sorted(items, key=lambda i: i.map_tier, reverse=self.prefer_high_tier)
    # print(f'sort maps items names by tier{list(map(lambda item: item.name, items))}')
    if self.settings.prefered_tier:
      if self.settings.prefered_tier == 'yellow':
        items = sorted(items, key=lambda i: i.map_tier == 4, reverse=True)
        items = sorted(items, key=lambda i: i.map_tier > 5 and i.map_tier < 11, reverse=True)
        # items = sorted(items, key=lambda i: i.map_tier > 5 and i.map_tier < 11)
    # print(f'sort maps items names by prefered yellow tier{list(map(lambda item: item.name, items))}')
    # print("settings.low_priority_maps: ",self.settings.low_priority_maps)
    for map_priority in self.settings.low_priority_maps:
      items = sorted(items, key=lambda i: map_priority in i.name)
    # print(f'sort maps items names {list(map(lambda item: item.name, items))}')

    # print("map priorities: ", self.settings.map_priorities)
    # print("map priorities: ", self.map_priorities)
    for map_priority in self.map_priorities[::-1]:
      items = sorted(items, key=lambda i: map_priority in i.name, reverse=True)
    # print(f'sort maps items names map priorities {list(map(lambda item: item.name, items))}')

    if self.atlas_explorer is True:
      list_of_completed_maps = poe_bot.game_data.completed_atlas_maps.getCompletedMaps()
      completed_maps = list(filter(lambda i: i.name not in list_of_completed_maps, items))
      # completed_maps = sorted(completed_maps, key=lambda i: i.map_tier, reverse=False)
      completed_maps = sorted(completed_maps, key=lambda i: i.map_tier, reverse=True)
      non_completed_maps = list(filter(lambda i: i.name in list_of_completed_maps, items))
      completed_maps.extend(non_completed_maps)
      items = completed_maps
    # print(f'sort maps items names atlas explorer {list(map(lambda item: item.name, items))}')

    if self.settings.invitation_rush is True:
      pass

    items.sort(key= lambda i: i.rarity != "Unqiue")
    return items
  def filterMapsCanRun(self, items:List[Item]):
    restricted_mods_keys = [
      "MapConquerorContainsBoss", # sirus boss
      "MapElderContainsBoss", # elder boss
      'InfectedMap', # blight
    ]
    
    maps_we_can_run_ = list(filter(lambda i: i.rarity != "Unique" and i.getType() == 'map' and not i.name in maps_to_ignore, items))
    maps_we_can_run:List[Item] = []
    for item in maps_we_can_run_:
      item_mods_raw_line = "".join(item.item_mods_raw)
      if not any(list(map(lambda restricted_key: restricted_key in item_mods_raw_line, restricted_mods_keys))):
        maps_we_can_run.append(item)
    
    if self.atlas_explorer is True:
      maps_we_can_run = list(filter(lambda i: not i.name in ignore_bossroom_maps, maps_we_can_run))
      
    return maps_we_can_run
  def getDataAboutMapsInStash(self):
    key_type = 'map'
    key_items = []
    unsorted_items = list(map(lambda i_raw: Item(poe_bot, i_raw), self.poe_bot.ui.stash.temp.unsorted_items))
    for item in unsorted_items:
      if item.getType() == key_type:
        key_items.append(item)
    for item in self.poe_bot.ui.stash.getAllItems():
      if item.getType() == key_type:
        key_items.append(item)
    key_items_count = len(key_items)
    if self.poe_bot.debug: print(f'{key_items_count} items in {key_items}')
    return key_items
  def onMapFinishedFunction(self):
    poe_bot = self.poe_bot
    self.temp.map_streak += 1
    self.temp.map_completed = True
    self.temp.save()
    print(f'[Mapper] onMapFinishedFunction call at {time.time()}')
    self.deactivateDeliriumMirror()

    map_finish_time = time.time() 
    time_now = time.time()
    rev = bool(random.randint(0,1))
    while time_now < map_finish_time + 1 :
      poe_bot.refreshInstanceData()
      killed_someone = combat_module.clearLocationAroundPoint({"X":self.poe_bot.game_data.player.grid_pos.x, "Y":self.poe_bot.game_data.player.grid_pos.y},detection_radius=50)
      res = self.exploreRoutine()
      if killed_someone is False and res is False:
        point = poe_bot.game_data.terrain.pointToRunAround(
          point_to_run_around_x=self.poe_bot.game_data.player.grid_pos.x,
          point_to_run_around_y=self.poe_bot.game_data.player.grid_pos.y,
          distance_to_point=15,
          reversed=rev
        )
        mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
        poe_bot.refreshInstanceData()
      time_now = time.time()

    print(f'[Mapper] onMapFinishedFunction leveling gems at {time.time()}')
    poe_bot.refreshInstanceData()
    for i in range(random.randint(3,5)):
      res = poe_bot.helper_functions.lvlUpGem()
      if res != 1:
        break

    i = 0
    random_click_iter = 0
    can_click_portal_after = time.time()
    while True:
      while True:
        poe_bot.refreshInstanceData()
        res = poe_bot.loot_picker.collectLoot()
        if res is False:
          break
      
      if poe_bot.game_data.invites_panel_visible != False:
        print(f'[onmapfinishfunction] already loading')
      else:
        i+= 1
        random_click_iter += 1
        if random_click_iter > 15:
          print('[Mapper] cannot get to portal, clicking random point around the player')
          poe_bot.ui.closeAll()
          # points = getFourPoints(x = poe_bot.game_data.player.grid_pos.x, y = poe_bot.game_data.player.grid_pos.y, radius = random.randint(7,13))
          # point = random.choice(points)
          point = poe_bot.game_data.terrain.pointToRunAround(poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y, distance_to_point=random.randint(15,25), check_if_passable=True)
          pos_x, pos_y = poe_bot.getPositionOfThePointOnTheScreen(y=point[1], x=point[0])
          pos_x, pos_y = poe_bot.convertPosXY(x=pos_x, y=pos_y)
          bot_controls.mouse.setPosSmooth(pos_x, pos_y)
          bot_controls.mouse.click()
          random_click_iter = random.randint(0,3)
        if i > 200:
          raiseLongSleepException('portal bug')
        nearby_portals = list(filter(lambda e: "Metadata/MiscellaneousObjects/MultiplexPortal" in e.path and e.distance_to_player < 50, poe_bot.game_data.entities.all_entities))
        if len(nearby_portals) == 0:
          openPortal(poe_bot=poe_bot)
          nearby_portals = list(filter(lambda e: "Metadata/MiscellaneousObjects/MultiplexPortal" in e.path and e.distance_to_player < 50, poe_bot.game_data.entities.all_entities))

        if len(nearby_portals) != 0 and time.time() > can_click_portal_after:
          print(f'[mapper] clicking on portal')
          poe_bot.refreshInstanceData()
          nearby_portals = list(filter(lambda e: "Metadata/MiscellaneousObjects/MultiplexPortal" in e.path and e.distance_to_player < 50, poe_bot.game_data.entities.all_entities))
          nearby_portals.sort(key=lambda e: e.distance_to_player)
          nearest_portal = nearby_portals[0]
          nearest_portal.click()
          can_click_portal_after = time.time() + random.randint(5,15)/10
          print(f'[mapper] can_click_portal_after {can_click_portal_after}')
      combat_module.clearLocationAroundPoint({"X": self.poe_bot.game_data.player.grid_pos.x, "Y": self.poe_bot.game_data.player.grid_pos.y},detection_radius=50)
      self.exploreRoutine()
    print(f'[Mapper] onMapFinishedFunction return at {time.time()}')
  def activateKiracMissionMap(self):
    print(f'#activateKiracMissionMap call at {time.time()}')
    poe_bot = self.poe_bot
    poe_bot.ui.kirak_missions.open()
    sorted_maps_can_run = self.sortMaps(self.filterMapsCanRun(poe_bot.ui.kirak_missions.items))
    if self.atlas_explorer is True:
      _sorted_maps_can_run = sorted_maps_can_run
      sorted_maps_can_run:List[Item] = []
      shitty_maps_can_run:List[Item] = []
      for map_item in _sorted_maps_can_run:
        if map_item.map_tier > 10 and map_item.corrupted is False:
          shitty_maps_can_run.append(map_item)
        else:
          sorted_maps_can_run.append(map_item)
      sorted_maps_can_run.extend(shitty_maps_can_run)
    else:
      poe_bot.raiseLongSleepException('no maps to run, atlas explorer is false, not implemented yet:(')
      # sorted_maps_can_run = _sorted_maps_can_run

    map_to_activate = sorted_maps_can_run[0]
    print(f'map_to_activate {map_to_activate.raw}')
    # map_to_activate.hover()
    time.sleep(random.randint(5,20)/100)
    map_to_activate.click()
    time.sleep(random.randint(5,20)/10)
    poe_bot.ui.kirak_missions.activate()
    time.sleep(random.randint(5,20)/10)
    return map_to_activate
  def buyMapsFromKirac(self):
    poe_bot = self.poe_bot
    bought_maps_can_run = False
    i = 0
    while 1:
      i += 1
      if i > 40:
        poe_bot.raiseLongSleepException('cant open commander kirac purchase window')

      poe_bot.ui.purchase_window_hideout.update()
      if poe_bot.ui.purchase_window_hideout.visible is True:
        time.sleep(random.randint(10,20)/10)
        break
      poe_bot.refreshInstanceData(reset_timer=True)
      commander_kirac = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Commander Kirac"), None)
      if commander_kirac is None:
        poe_bot.raiseLongSleepException("if commander_kirac is None:")
      commander_kirac.click(hold_ctrl=True)
      time.sleep(random.randint(50,100)/100)

    sorted_maps_can_run = self.sortMaps(self.filterMapsCanRun(poe_bot.ui.purchase_window_hideout.items))
    if self.atlas_explorer is True:
      _sorted_maps_can_run = sorted_maps_can_run
      sorted_maps_can_run = []
      completed_atlas_maps = poe_bot.game_data.completed_atlas_maps.getCompletedMaps()
      picked_already = []
      for map_item in _sorted_maps_can_run:
        if not map_item.name in completed_atlas_maps and not map_item.name in picked_already:
          print(map_item.name)
          picked_already.append(map_item.name)
          sorted_maps_can_run.append(map_item)
    else:
      sorted_maps_can_run = sorted_maps_can_run[-4:]
    if len(sorted_maps_can_run) != 0:
      poe_bot.ui.clickMultipleItems(sorted_maps_can_run)
      bought_maps_can_run = True
    poe_bot.ui.closeAll()
    for i in range(random.randint(1,3)):
      time.sleep(random.randint(10,20)/100)
      poe_bot.ui.closeAll()
    time.sleep(random.randint(10,20)/10)
    return bought_maps_can_run
  def setIgnoreBossroom(self):
    self.ignore_bossroom = self.temp.current_map in ignore_bossroom_maps
    '''

    if self.map in ignore_bossroom_maps:
      self.ignore_bossroom = True
    else:
      self.ignore_bossroom = False
    
    return
    
    '''
    pass
  def seekForMapBosses(self):
    map_bosses = list(filter(lambda e: e.life.health.current != 0 and e.render_name in self.current_map.boss_render_names and poe_bot.game_data.terrain.checkIfPointPassable(e.grid_position.x, e.grid_position.y) , self.poe_bot.game_data.entities.unique_entities))
    return map_bosses
  def seekForBossrooms(self):
    bossrooms = list(filter(lambda e: e.render_name == self.current_map.arena_render_name and e.id not in self.temp.cleared_bossrooms and poe_bot.game_data.terrain.checkIfPointPassable(e.grid_position.x, e.grid_position.y), self.poe_bot.game_data.entities.area_transitions))
    return bossrooms
  def invRushCanBurnMap(self, in_hideout=True):
    if self.temp.invitation_progress < 27:
      if self.maps_in_inventory is None:
        self.poe_bot.ui.inventory.update()
        self.maps_in_inventory = self.filterMapsCanRun(self.poe_bot.ui.inventory.items)

      maps_in_inventory_count = len(self.maps_in_inventory) + int(not in_hideout)
      print(f'inv rush is true maps_in_inventory_count {maps_in_inventory_count}')
      if in_hideout is True:
        self.maps_in_inventory = None
      min_maps_to_allow_burn = 8
      if maps_in_inventory_count > min_maps_to_allow_burn:
        print(f' > {min_maps_to_allow_burn}')
        return True
    return False
  def exploreRoutine(self, mover=None):
    '''
    if function returns True, itll regenerate it's path
    '''
    if self.started_running_map_at + self.settings.max_map_run_time < time.time():
      poe_bot.logger.writeLine(f'started at {self.started_running_map_at}, limit {self.settings.max_map_run_time}, time now {time.time()}, stuck')
      poe_bot.on_stuck_function() 

    if self.force_deli is True and self.temp.delirium_mirror_activated is False:
      # activate it
      delirium_mirrors = list(filter(lambda entity: "AfflictionInitiator" in entity.path, poe_bot.game_data.entities.all_entities))
      if len(delirium_mirrors) != 0:
        delirium_mirror = delirium_mirrors[0]
        print(f'going to delirium mirror {delirium_mirror}')
        result = mover.goToPoint(
          min_distance = 30, 
          point=[delirium_mirror.grid_position.x, delirium_mirror.grid_position.y],
          custom_continue_function=build.usualRoutine,
          release_mouse_on_end=False
        )
        self.activateDeliriumMirror(delirium_mirror)
        self.temp.delirium_mirror_activated = True
        self.temp.save()
        return True
    if self.settings.party_ultimatum is True:
      ultimatum_altar = next( (e for e in poe_bot.game_data.entities.all_entities if e.path == ULTIMATUM_ALTAR_PATH), None)
      if ultimatum_altar:
        doPartyUltimatumOnMap(ultimatum_altar)
    if self.settings.do_alva:
      entrance_portal_entity = next( (e for e in poe_bot.game_data.entities.area_transitions_all if e.path == "Metadata/Terrain/Leagues/Incursion/Objects/IncursionPortal1" and e.id not in self.temp.alvas_to_ignore_ids and e.isOnPassableZone()) , None)
      if entrance_portal_entity:
        doAlvaEncounter(entrance_portal_entity)
        if self.settings.alva_skip_map_if_finished_incursion == True or self.settings.alva_skip_map_if_finished_incursion_and_have_priority_map_in_inventory == True:
          amount_of_alvas_ignore_ids = len(self.temp.alvas_to_ignore_ids)
          if self.settings.do_alva == False or amount_of_alvas_ignore_ids > 4:
            poe_bot.logger.writeLine(f'alva rush, willing to skip map since cant do more alva or amount of ignored alvas exceed thresh {self.settings.alva_skip_map_if_finished_incursion} {self.settings.alva_skip_map_if_finished_incursion_and_have_priority_map_in_inventory}')
            can_skip_map = True
            if self.settings.alva_skip_map_if_finished_incursion_and_have_priority_map_in_inventory and self.map_priorities != []:
              self.poe_bot.ui.inventory.update()
              priority_maps_in_inventory = list(filter(lambda i: i.name in self.map_priorities, self.poe_bot.ui.inventory.items))
              priority_maps_in_inventory_count = len(priority_maps_in_inventory)
              maps_in_stash = self.getDataAboutMapsInStash()
              priority_maps_in_stash = list(filter(lambda i: i.name in self.map_priorities, maps_in_stash))
              priority_maps_in_stash_count = len(priority_maps_in_stash)
              priority_maps_total_count = priority_maps_in_inventory_count + priority_maps_in_stash_count
              poe_bot.logger.writeLine(f'alva rush, priority_maps_in_inventory_count {priority_maps_in_inventory_count} stash {priority_maps_in_stash_count} total {priority_maps_total_count}')
              if priority_maps_total_count > 30:
                pass
              else:
                can_skip_map = False
            if can_skip_map:
              poe_bot.logger.writeLine(f'alva rush, skipping rest of map because doesnt need to do more alva {self.settings.do_alva} {amount_of_alvas_ignore_ids} {can_skip_map}')
              self.temp.map_completed = True
              return None
        return True
    if self.current_map.activators_on_map:
      activators_on_map = list(filter(lambda e: e.is_targetable is True and e.path == self.current_map.activators_on_map, poe_bot.game_data.entities.all_entities))
      if len(activators_on_map) != 0:
        print(f'found activators_on_map')
        self.activate(activator=activators_on_map[0])
        return True
    # if self.settings.atlas_explorer != False:
    #   quest_flags = poe_bot.game_data.quest_states.getOrUpdate()
    #   have_tangle = quest_flags.get("HaveTangleMapDeviceAlteration", False)
    #   have_cleansing_fire = quest_flags.get("HaveCleansingFireMapDeviceAlteration", False)
    #   if have_cleansing_fire != True or have_tangle != True:
    #     pass
    #   # "Metadata/NPC/Epilogue/EnvoyTangle"
    #   # "Metadata/NPC/Epilogue/EnvoyCleansingFire"

    #   # "HaveTangleMapDeviceAlteration"
    #   # "HaveCleansingFireMapDeviceAlteration"
    #   pass

    if self.settings.invitation_rush is True:
      can_burn_map = self.invRushCanBurnMap(in_hideout=False)
      if can_burn_map is True:
        altar_mob = next( (e for e in self.poe_bot.game_data.entities.all_entities if 'AtlasInvaders' in e.path), None)
        if altar_mob is not None:
          print(f'can burn map is true and altar mob found, can consider as finished')
          self.temp.map_completed = True
          return None
      else:
        if self.settings.force_kill_blue is False:
          print(f'since we have little maps for inv rush, force_kill_blue')
          self.settings.force_kill_blue = True
    if self.settings.force_kill_rogue_exiles is True:
      rogue_exiles = list(filter(lambda e: e.is_attackable is True and e.distance_to_player < 100 and e.isOnPassableZone() and e.render_name in ROGUE_EXILES_RENDER_NAMES_ENG, poe_bot.game_data.entities.unique_entities))
      for rare_mob in rogue_exiles:
        updated_entity = list(filter(lambda e: e.id == rare_mob.id, poe_bot.game_data.entities.unique_entities))
        if len(updated_entity) != 0:
          updated_entity = updated_entity[0]
          print(f'going to kill rogue exile {updated_entity.raw}')
          combat_module.killUsualEntity(updated_entity)
          return True
    if self.settings.force_kill_rares is True:
      rares_nearby = list(filter(lambda e: e.distance_to_player < 60 and e.isOnPassableZone(), poe_bot.game_data.entities.attackable_entities_rares))
      for rare_mob in rares_nearby:
        updated_entity = next( (e for e in poe_bot.game_data.entities.attackable_entities_rares if e.id == rare_mob.id), None)
        if updated_entity:
          combat_module.killUsualEntity(updated_entity)
          return True
    if self.settings.force_kill_blue is True:
      rares_nearby = list(filter(lambda e: e.distance_to_player < 60 and e.isOnPassableZone(), poe_bot.game_data.entities.attackable_entities_blue))
      for blue_mob in rares_nearby:
        updated_entity = next( (e for e in poe_bot.game_data.entities.attackable_entities_blue if e.id == blue_mob.id), None)
        if updated_entity:
          combat_module.killUsualEntity(updated_entity)
          return True
    if self.settings.clear_around_shrines:
      shrine = next( (e for e in poe_bot.game_data.entities.all_entities if e.is_targetable and "Metadata/Shrines/Shrine"), None)
      if shrine:
        print(f'found shrine {shrine.raw}')
        poe_bot.combat_module.clearLocationAroundPoint(point_to_run_around={"X": shrine.grid_position.x, "Y":shrine.grid_position.y})
        return True
    if self.settings.do_essences is True:
      if len(self.poe_bot.game_data.entities.essence_monsters) != 0:
        print(f'got essenced mobs, killing them')
        for entity in self.poe_bot.game_data.entities.essence_monsters:
          self.poe_bot.combat_module.killUsualEntity(entity=entity)
        return True

      essences = seekForEssences()
      essences = list(filter(lambda e: e.id not in self.temp.essences_to_ignore_ids, essences))
      if len(essences) != 0:
        essence = essences[0]
        doEssenceEncounter(essence)
        poe_bot.loot_picker.collectLoot()
        return True
    if self.settings.do_beasts:
      # TODO check if einhar is somewhere around
      einhar_entity = next( (e for e in poe_bot.game_data.entities.all_entities if "Metadata/Monsters/Masters/Einhar" in e.path), None)
      if einhar_entity:
        print(f'spotted einhar {einhar_entity.raw}')
        if self.last_seen_einhar is None:
          poe_bot.logger.writeLine(f'first spotted einhar {einhar_entity.raw}')
        self.last_seen_einhar = einhar_entity
    valuable_beasts = seekForValuableBeasts()
    if len(valuable_beasts) != 0:
      valuable_beast = valuable_beasts[0]
      print(f'found valuable beast, killing it {valuable_beast.raw}')
      distance_to_einhar = 0
      if self.last_seen_einhar:
        distance_to_einhar = dist( (self.last_seen_einhar.grid_position.x, self.last_seen_einhar.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y))
      poe_bot.logger.writeLine(f'bestiary, killing valuable beast id: {valuable_beast.id} {valuable_beast.render_name} , distance_to_einhar: {distance_to_einhar}')
      if distance_to_einhar > 300:
        poe_bot.logger.writeLine(f'bestiary, killing valuable beast, going to bring einhar back')
        res = self.poe_bot.mover.goToPoint(
          point=(self.last_seen_einhar.grid_position.x, self.last_seen_einhar.grid_position.y),
          min_distance=75,
          custom_continue_function=build.usualRoutine,
          release_mouse_on_end=False,
          # release_mouse_on_end=True,
          step_size=random.randint(25,33)
        )
        res = self.poe_bot.mover.goToPoint(
          point=(valuable_beasts.grid_position.x, valuable_beasts.grid_position.y),
          min_distance=75,
          custom_continue_function=build.usualRoutine,
          release_mouse_on_end=False,
          # release_mouse_on_end=True,
          step_size=random.randint(25,33)
        )    
      
      # check if essence encounter in radius of 5-10, so itll prevent us from trying to kill the beast inside essence
      essences = seekForEssences()
      for essence in essences:
        distance_to_essence = dist((essence.grid_position.x, essence.grid_position.y), (valuable_beast.grid_position.x,valuable_beast.grid_position.y))
        if distance_to_essence < 15:
          doEssenceEncounter(essence)
      


      is_dead = combat_module.killUsualEntity(valuable_beast)
      if is_dead is False:
        poe_bot.logger.writeLine('bestiary, einhar bug')
        poe_bot.helper_functions.relog()
        raise Exception('beast didnt die in 90 secs, einhar bug or beast is too strong?')
      return True
    
    if self.settings.do_harvest is True:
      harvests = seekForHarvests()
      harvests = list(filter(lambda e: e.id not in self.temp.harvests_to_ignore_ids, harvests))
      if len(harvests) != 0:
        harvest = harvests[0]
        doHarvestEncounter(harvest_enter_portal=harvest, leave_harvest=(not self.settings.harvest_rush))
        self.temp.harvests_to_ignore_ids.append(harvest.id)
        if self.settings.harvest_rush is True:
          self.onMapFinishedFunction()
        poe_bot.loot_picker.collectLoot()
        return True
    if self.do_legion is True:
      legion_encounters = seekForLegionMonolith()
      if len(legion_encounters) != 0:
        legion_monolith = legion_encounters[0]
        doLegionEncounter(legion_monolith)
        poe_bot.loot_picker.collectLoot()
        return True
    if self.settings.do_harbringers is True:
      harbringer_entity = next( (e for e in poe_bot.game_data.entities.all_entities if "Metadata/Monsters/Avatar/Avatar" in e.path), None)
      if harbringer_entity:
        HarbringerEncounter(poe_bot=poe_bot, harbringer_entity=harbringer_entity).do()
        poe_bot.loot_picker.collectLoot()
        return True
    # map bosses
    # kill map bosses if theyre presented on maps
    if self.ignore_bossroom is None:
      self.setIgnoreBossroom()
    if self.ignore_bossroom is False and self.current_map.ignore_bossroom is False:
      if self.current_map.bossroom_activator:
        bossroom_activator = next( (e for e in poe_bot.game_data.entities.all_entities if e.is_targetable is True and e.path == self.current_map.bossroom_activator), None)
        if bossroom_activator:
          bossroom_activator.clickTillNotTargetable()
          return True

        # bossroom_activators = list(filter(lambda e: e.is_targetable is True and e.path == self.current_map.bossroom_activator, poe_bot.game_data.entities.all_entities))
        # if len(bossroom_activators) != 0:
        #   print(f'found bossroom activator')
        #   bossroom_activators[0].clickTillNotTargetable()
        #   # self.activate(activator=bossroom_activators[0])
        #   return True
      bossrooms = self.seekForBossrooms()
      if len(bossrooms) != 0:
        bossroom = bossrooms[0]
        self.clearBossroom(bossroom=bossrooms[0])
        self.temp.cleared_bossrooms.append(bossroom.id)
        self.temp.save()
        return True
    map_bosses = self.seekForMapBosses()
    if len(map_bosses) != 0:
      print(f'going to kill boss {map_bosses[0]}')
      map_boss = map_bosses[0]
      self.killMapBoss(map_boss, clear_around_radius=50)
      # combat_module.killUsualEntity(map_boss)
      self.temp.map_boss_killed = True
      self.temp.save()
      return True
    # pickable drop
    if self.can_pick_drop is None:
      if len(self.poe_bot.ui.inventory.getFilledSlots()) > 51:
        self.can_pick_drop = False
      else:
        self.can_pick_drop = True
    if self.can_pick_drop is False:
      print(f'self.can_pick_drop is False')
      return False
    loot_collected = poe_bot.loot_picker.collectLoot()
    if loot_collected is True:
      if len(self.poe_bot.ui.inventory.getFilledSlots()) > 51:
        self.can_pick_drop = False
      else:
        self.can_pick_drop = True
      return loot_collected
    
    # TODO check if area is on a currently passable area or somewhere around
    # area_transitions = list(filter(lambda e: e.rarity == 'White' and e.render_name != 'Arena' and e.id not in mapper.temp.visited_transitions_ids and e.id not in unvisited_transitions_ids, poe_bot.game_data.entities.area_transitions))
    unvisited_transitions_ids = list(map(lambda e: e['i'], self.temp.unvisited_transitions))
    area_transitions = list(filter(lambda e: 
      e.rarity == 'White' 
      and e.is_targetable == True 
      and e.render_name != '' 
      and e.render_name != "Twisted Burrow" # affliction enterance
      and e.path != "Metadata/Terrain/Leagues/Azmeri/WoodsEntranceTransition" # affliction enterance
      and e.path != "Metadata/MiscellaneousObjects/PortalToggleableNew" # affliction enterance
      and e.path != "Metadata/MiscellaneousObjects/PortalToggleable" # affliction enterance
      and e.render_name != self.current_map.arena_render_name 
      and e.render_name not in self.current_map.transitions_to_ignore_render_names
      # and (len(self.current_map.transitions_to_ignore_render_names) != 0 and e.render_name not in self.current_map.transitions_to_ignore_render_names)
      and e.render_name != 'Syndicate Laboratory' # betrayal Laboratory 
      and "Metadata/Terrain/Leagues/Incursion/Objects/IncursionPortal" not in e.path # alva
      and 'Metadata/QuestObjects/Labyrinth/LabyrinthTrialPortal' not in e.path # lab trial
      and e.id not in self.temp.visited_transitions_ids 
      and e.id not in unvisited_transitions_ids 
      and e.id not in self.temp.currently_ignore_transitions_id
      and e.render_name != "Starfall Crater",
    poe_bot.game_data.entities.area_transitions))
    if len(area_transitions) != 0:
      new_transition_found = False
      for area_transition in area_transitions:
        object_reachable = poe_bot.game_data.terrain.checkIfPointPassable(area_transition.grid_position.x, area_transition.grid_position.y)
        if object_reachable is False:
          self.temp.currently_ignore_transitions_id.append(area_transition.id)
        else:
          print(f'found new transition {str(area_transition)}')
          self.temp.unvisited_transitions.append(area_transition.raw)
          new_transition_found = True
      
      if new_transition_found is True:
        return True  
      
      return True
    return False
  def checkIfSessionEnded(self):
    poe_bot = self.poe_bot
    if self.mapper_session_temp.current_session_started_at == 0:
      poe_bot.logger.writeLine(f'[session] session time is 0')
      self.mapper_session_temp.setSessionTime()
    time_left_to_next_session = self.mapper_session_temp.getCurrentSessionPlayTimeLeft()
    print(f'time left for session swap {time_left_to_next_session}')
    if time_left_to_next_session < 0:
      poe_bot.logger.writeLine('time to swap sessions')
      time_to_sleep = self.mapper_session_temp.getCurrentSessionSleepTime()
      sleep_in_main_menu = False
      if time_to_sleep > 60*60:
        poe_bot.logger.writeLine('going to wait in main menu because sleep time > 60*60')
        sleep_in_main_menu = True
      if random.randint(1,5) == 1:
        poe_bot.logger.writeLine('going to wait in main menu because 20%')
        sleep_in_main_menu = True
      poe_bot.logger.writeLine(f'session swap sleep for {time_to_sleep} seconds')
      self.mapper_session_temp.shiftSession()
      if sleep_in_main_menu == True:
        poe_bot.helper_functions.getToMainMenu()
        time.sleep(time_to_sleep)
        poe_bot.logger.writeLine('logging in after session sleep')
        poe_bot.helper_functions.logIn()
        poe_bot.logger.writeLine('session swapped')
        self.mapper_session_temp.setSessionTime()
        raise Exception('session swap')
      else:
        self.poe_bot.afk_temp.short_sleep_duration += time_to_sleep
        self.poe_bot.afk_temp.save()
        self.mapper_session_temp.current_session_started_at = self.poe_bot.afk_temp.next_short_sleep + time_to_sleep
        poe_bot.logger.writeLine(f'current session start time set to {self.mapper_session_temp.current_session_started_at}')
        self.mapper_session_temp.save()
        poe_bot.logger.writeLine('added sleep time to short sleep')
  def activate(self, activator: Entity):
    while True:
      res = mover.goToPoint(
        point=[activator.grid_position.x, activator.grid_position.y],
        min_distance=30,
        release_mouse_on_end=False,
        custom_continue_function=build.usualRoutine,
        custom_break_function=poe_bot.loot_picker.collectLoot,
        step_size=random.randint(25,33)
      )
      if res is None:
        break
    i = 0
    while True:
      i+=1
      if i>80:
        poe_bot.raiseLongSleepException('cannot activate activator on map')
      

      activator_found = False
      for i in range(3):
        activators = list(filter(lambda e: e.id == activator.id, poe_bot.game_data.entities.all_entities))
        if len(activators) != 0:
          activator_found = True
          break
        else:
          print('activator disappeared, trying to find it again')
          poe_bot.refreshInstanceData()
          
      if activator_found is False:
        print(f'activator disappeared')
        poe_bot.raiseLongSleepException('activator disappeared')

      activated = activators[0].is_targetable is False
      if activated is False:
        activators[0].click()
        poe_bot.refreshInstanceData()
      else:
        break
  def clearBossroom(self, bossroom:Entity):
    bossroom_id = bossroom.id
    print(f'going to clear the bossroom {bossroom}')

    while True:
      res = mover.goToPoint(
        point=[bossroom.grid_position.x, bossroom.grid_position.y],
        min_distance=30,
        release_mouse_on_end=False,
        # TODO add picking drop logic
        custom_continue_function=build.usualRoutine,
        custom_break_function=poe_bot.loot_picker.collectLoot,
        step_size=random.randint(25,33)
      )
      if res is None:
        break
    
    mover.enterTransition(bossroom)
    if self.current_map.refresh_terrain_data_in_bossroom:
      self.poe_bot.refreshAll(refresh_visited=False)
      self.poe_bot.game_data.terrain.getCurrentlyPassableArea()
    poe_bot.refreshInstanceData()
    exit_transitions = list(filter(lambda e: e.id != bossroom_id, poe_bot.game_data.entities.area_transitions))
    exit_transitions = sorted(exit_transitions, key=lambda entity: entity.distance_to_player)
    if len(exit_transitions) != 0:
      exit_transition_test = exit_transitions[0]
      print(f'exit_transition_test {exit_transition_test.raw}')
    exit_pos_x, exit_pos_y = poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y
    print(f'entered bossroom exit_pos_x, exit_pos_y {exit_pos_x, exit_pos_y}')

    unique_entities = self.seekForMapBosses()
    if len(unique_entities) != 0:
      print(f'unique_entities: {unique_entities}')
      for entity in unique_entities:
        self.killMapBoss(entity=entity)
    else:
      print(f'unique_entities empty, exploring and killing uniques')
      # grid_pos_to_go_x, grid_pos_to_go_y = getFurtherstPassablePoint(poe_bot=poe_bot)
      grid_pos_to_go_x, grid_pos_to_go_y = poe_bot.pather.utils.getFurthestPoint(poe_bot.game_data.player.grid_pos.toList(), poe_bot.game_data.terrain.currently_passable_area)
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
          custom_continue_function=build.usualRoutine,
          custom_break_function=self.killBossEntityIfFound,
          step_size=random.randint(25,33)
        )
        if res is None or res is True:
          break
      unique_entities = self.seekForMapBosses()
      print(f'unique_entities after explore: {unique_entities}')
      for entity in unique_entities:
        self.killMapBoss(entity=entity)

    poe_bot.refreshInstanceData()
    print(f'bossroom cleared')
    loot_collected = poe_bot.loot_picker.collectLoot() 
    while loot_collected is True:
      loot_collected = poe_bot.loot_picker.collectLoot() 
    need_to_explore_more = False
    print(f'len(discovery_points) {len(discovery_points)}')
    if len(discovery_points) != 0:
      need_to_explore_more = True

    if point_to_go is not None:
      need_to_explore_point = poe_bot.game_data.terrain.isPointVisited(point_to_go[0], point_to_go[1])
      print(f'need_to_explore_point {need_to_explore_point}')
      if need_to_explore_point is True:
        need_to_explore_more = True

    discovered_percent = poe_bot.game_data.terrain.getPassableAreaDiscoveredForPercent(total=True)
    if discovered_percent < self.settings.discovery_percent:
      need_to_explore_more = True

    print(f'need_to_explore_more {need_to_explore_more}')
    if need_to_explore_more is True:
      if self.current_map.need_to_leave_bossroom_through_transition is False:
        print("self.current_map.need_to_leave_bossroom_through_transition is False")
        poe_bot.refreshAll(refresh_visited=False)
      else:
        bossroom_leave_iteration = 0
        while True:
          bossroom_leave_iteration += 1
          if bossroom_leave_iteration == 50:
            print("bossroom_leave_iteration == 50, stuck, relog")
            poe_bot.on_stuck_function()
            raise Exception('look_for_exit_transition > 100:')

          print(f'going to leave bossroom')
          print(f'discovery_points {discovery_points}')
          print(f'exit_pos_x, exit_pos_y {exit_pos_x, exit_pos_y}')
          while True:
            print(f'going 100 to exit point {exit_pos_x, exit_pos_y}')
            res = mover.goToPoint(
              point=[exit_pos_x, exit_pos_y],
              min_distance=100,
              release_mouse_on_end=False,
              custom_continue_function=build.usualRoutine,
              custom_break_function=self.killBossEntityIfFound,
              step_size=random.randint(25,33)
            )

            loot_collected = poe_bot.loot_picker.collectLoot() 
            while loot_collected is True:
              loot_collected = poe_bot.loot_picker.collectLoot() 

            if res is None:
              break
          while True:
            print(f'going 30 to exit point {exit_pos_x, exit_pos_y}')
            res = mover.goToPoint(
              point=[exit_pos_x, exit_pos_y],
              min_distance=30,
              release_mouse_on_end=False,
              custom_continue_function=build.usualRoutine,
              custom_break_function=self.killBossEntityIfFound,
              step_size=random.randint(25,33)
            )

            loot_collected = poe_bot.loot_picker.collectLoot() 
            if loot_collected is True:
              continue

            if res is None:
              break
          # exit_transitions = list(filter(lambda e: e.id != bossroom_id and dist((e.grid_position.x, e.grid_position.y), (exit_pos_x, exit_pos_y)) < 40, poe_bot.game_data.entities.area_transitions))
          exit_transitions = list(filter(lambda e: e.id != bossroom_id and poe_bot.game_data.terrain.checkIfPointPassable(e.grid_position.x, e.grid_position.y), poe_bot.game_data.entities.area_transitions))
          
          if len(exit_transitions) == 0:
            print('exit transition is not visible or doesnt exist')
            grid_pos_to_go_x, grid_pos_to_go_y = poe_bot.pather.utils.getFurthestPoint(poe_bot.game_data.player.grid_pos.toList(), poe_bot.game_data.terrain.currently_passable_area)
            # grid_pos_to_go_x, grid_pos_to_go_y = getFurtherstPassablePoint(poe_bot=poe_bot)
            #TODO infinite loop if failure onenter transition
            while True:
              res = mover.goToPoint(
                point=[grid_pos_to_go_x, grid_pos_to_go_y],
                min_distance=50,
                release_mouse_on_end=False,
                custom_continue_function=build.usualRoutine,
                custom_break_function=self.killBossEntityIfFound,
                step_size=random.randint(25,33)
              )
              if res is None:
                break
            # unique_entities = list(filter(lambda e: e.rarity == 'Unique' , poe_bot.game_data.entities.attackable_entities))
            # print(f'unique_entities after explore: {unique_entities}')
            # for entity in unique_entities:
            #   combat_module.killUsualEntity(entity)
            continue
          
          exit_transition = exit_transitions[0]
          mover.enterTransition(exit_transition)
          self.temp.visited_transitions_ids.append(exit_transition.id)
          print('left the bossroom')
          break
      poe_bot.game_data.terrain.getCurrentlyPassableArea() # to refresh currently passable area

    self.temp.visited_transitions_ids.append(bossroom_id)
    self.temp.map_boss_killed = True
    self.temp.save()
  def killMapBoss(self, entity:Entity, clear_around_radius = 150):
    start_time = time.time()
    print(f'#killmapboss {start_time} {entity.raw}')
    boss_entity = entity
    boss_entity_id = boss_entity.id

    if boss_entity.is_targetable is False or boss_entity.is_attackable is False:
      print(f'boss is not attackable or not targetable, going to it and activating it')
      while True:
        if self.current_map.activator_inside_bossroom is not None and self.activated_activator_in_bossroom is False:
          activator:Entity = next((e for e in poe_bot.game_data.entities.all_entities if e.path == self.current_map.activator_inside_bossroom), None)
          if activator:
            if activator.is_targetable is True:
              self.activate(activator)
            self.activated_activator_in_bossroom = True
        res = mover.goToPoint(
          (boss_entity.grid_position.x, boss_entity.grid_position.y),
          min_distance=15,
          custom_continue_function=build.usualRoutine,
          # custom_break_function=poe_bot.loot_picker.collectLoot,
          release_mouse_on_end=False,
          step_size=random.randint(25,33),
          possible_transition = self.current_map.possible_transition_on_a_way_to_boss
        )
        if res is None:
          break
      last_boss_pos_x, last_boss_pos_y = boss_entity.grid_position.x, boss_entity.grid_position.y
      
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
        if boss_entity.is_targetable is False or boss_entity.is_attackable is False:
          print(f'boss is not attackable or not targetable, going to it clearing around it {boss_entity.raw}')
          killed_someone = combat_module.clearLocationAroundPoint(
            {"X":boss_entity.grid_position.x, "Y":boss_entity.grid_position.y}, 
            detection_radius=clear_around_radius, 
            ignore_keys=self.current_map.entities_to_ignore_in_bossroom_path_keys
          )
          if killed_someone is False:
            point = poe_bot.game_data.terrain.pointToRunAround(
              point_to_run_around_x=last_boss_pos_x,
              point_to_run_around_y=last_boss_pos_y,
              distance_to_point=15,
            )
            mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
          poe_bot.refreshInstanceData(reset_timer=killed_someone)
        else:
          print(f'boss is attackable and targetable, going to kill it')
          combat_module.killUsualEntity(boss_entity, max_kill_time_sec=30)
          last_boss_pos_x, last_boss_pos_y = boss_entity.grid_position.x, boss_entity.grid_position.y
    else:
      print(f'boss is attackable and targetable, going to kill it')
      if boss_entity.distance_to_player > 40:
        while True:
          res = mover.goToPoint(
            (boss_entity.grid_position.x, boss_entity.grid_position.y),
            min_distance=35,
            custom_continue_function=build.usualRoutine,
            # custom_break_function=poe_bot.loot_picker.collectLoot,
            release_mouse_on_end=False,
            step_size=random.randint(25,33),
            possible_transition = self.current_map.possible_transition_on_a_way_to_boss
          )
          if res is None:
            break
      combat_module.killUsualEntity(boss_entity)
    self.temp.map_boss_killed = True
    self.temp.killed_map_bosses_render_names.append(entity.render_name)
  def killBossEntityIfFound(self, mover=None):
    if self.current_map.activator_inside_bossroom is not None and self.activated_activator_in_bossroom is False:
      activator:Entity = next((e for e in poe_bot.game_data.entities.all_entities if e.path == self.current_map.activator_inside_bossroom), None)
      if activator:
        if activator.is_targetable is True:
          self.activate(activator)
        self.activated_activator_in_bossroom = True
        return False
    unique_entities = self.seekForMapBosses()
    if len(unique_entities) != 0:
      print("#killBossEntityIfFound found boss entity, killing it")
      for unique_entity in unique_entities:
        self.killMapBoss(unique_entity)
      return True
    return False
  def resetTransitions(self):
    self.temp.unvisited_transitions = []
    self.temp.visited_transitions_ids = []
    self.temp.transition_chain = []
    self.temp.currently_ignore_transitions_id = []
    self.temp.save()
  def onDeathFunc(self):
    print(f'#mapper.onDeathFunc call')
    # if self.atlas_explorer is True or self.boss_rush is True and self:
    discovered_percent = poe_bot.game_data.terrain.getPassableAreaDiscoveredForPercent(total=True)
    print(f'died, discovered_percent {discovered_percent}')
    if discovered_percent < 0.8:
      print(f'died, discovered_percent {discovered_percent} < 0.8, running again')
      self.resetTransitions()
    else:
      print(f'died, discovered_percent {discovered_percent} > 0.8, resetting')
      self.temp.reset()
    self.poe_bot.resurrectAtCheckpoint(check_if_area_changed=True)
    print(f'#mapper.onDeathFunc return')
    raise Exception("character is dead")
  def activateDeliriumMirror(self, deli_mirror:Entity):
    print(f'[mapper] activating delirium mirror at {time.time()}')
    points = getFourPoints(x = deli_mirror.grid_position.x, y = deli_mirror.grid_position.y, radius = random.randint(7,13))
    points.pop(0) # remove middle
    points_to_hover = []
    sorted_points = []
    pairs = [[0,1], [2,3]]
    random.shuffle(pairs)
    for pair in pairs:
      random.shuffle(pair)
      points_to_hover.append([deli_mirror.grid_position.x, deli_mirror.grid_position.y])
      for point in pair:
        x_pos = points[point][0]
        y_pos = points[point][1]
        points_to_hover.append([x_pos, y_pos])
        sorted_points.append(point)
    print(f'[mapper] activating delirium mirror sorted points {sorted_points}')
    print(f'[mapper] activating delirium mirror points_to_hover {points_to_hover}')
    for point in points_to_hover:
      x_pos = point[0]
      y_pos = point[1]
      print(f'[mapper] activating delirium mirror on {x_pos,y_pos}')
      x_pos,y_pos = poe_bot.getPositionOfThePointOnTheScreen(x = x_pos , y = y_pos )
      x_pos, y_pos = poe_bot.convertPosXY(x_pos,y_pos)
      print(x_pos, y_pos) 
      poe_bot.bot_controls.mouse.setPosSmooth(x_pos,y_pos)
      time.sleep(random.randint(25,55)/100)
    return True  


  def deactivateDeliriumMirror(self):
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    if self.temp.delirium_mirror_activated is True:
      end_pos = poe_bot.player_pos
      time_till_drop = random.randint(35,40)/10
      print('deactivating deli mirror')
      pos_x, pos_y = 667, 670
      # pos_x, pos_y = 667, 610 #necropolis
      pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y, safe = False)
      bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      time.sleep(random.randint(11,14)/100)
      bot_controls.mouse.pressAndRelease()
      bot_controls.mouse.pressAndRelease()
      print('deli mirror deactivated')
      if self.wait_for_deli_drops is True:
        print('start waiting till some deli drops appear')
        deli_close_time = time.time() 
        time_now = time.time()
        while time_now  < deli_close_time + time_till_drop :
          poe_bot.refreshInstanceData()
          combat_module.clearLocationAroundPoint(end_pos,detection_radius=50)
          self.exploreRoutine()
          time_now = time.time()
        print('finished waiting till some deli drops appear')
      # self.temp.delirium_mirror_activated = False
      return True


# "end of functions\classes which are for mapper only"

# In[16]:


default_config = {
  "REMOTE_IP": '172.21.164.37', # z2
  "unique_id": "jupyterNotebookTest",
  "GROUP_ID": "ult_1",
  "COORD_ID": "127.0.0.1",
  "force_reset_temp": False,
  "password": None,
  "custom_strategy": '',
  "predefined_strategy": "atlas_explorer",
  "build": "GenericHitter"
}

try:
  i = "".join(sys.argv[1:])
  print(i)
  parsed_config = literal_eval(i)
  print(f'successfully parsed cli config')
  print(f'parsed_config: {parsed_config}')
except:
  print(f'cannot parse config from cli, using default\dev one')
  notebook_dev = True
  parsed_config = default_config
  parsed_config['unique_id'] = PoeBot.getDevKey()

config = {}

for key in default_config.keys():
  try:
    config[key] = parsed_config[key]
  except:
    config[key] = default_config[key]
print(f'config to run {config}')


# In[17]:


strategy = PREDEFINED_STRATEGIES[config['predefined_strategy']]
# strategy = Mapper.getConfigs()[config['predefined_strategy']]


# In[18]:


REMOTE_IP = config['REMOTE_IP'] # REMOTE_IP
UNIQUE_ID = config['unique_id'] # UNIQUE_ID
GROUP_ID = config['GROUP_ID'] # GROUP_ID
COORD_ID = config['COORD_ID'] # COORD_ID
force_reset_temp = config['force_reset_temp']
build_name = config['build']
print(f'[mapper] using: REMOTE_IP: {REMOTE_IP} unique_id: {UNIQUE_ID} GROUP_ID: {GROUP_ID} COORD_ID {COORD_ID} force_reset_temp: {force_reset_temp}')
print(f'build: {build_name}')
print(f'strategy: {strategy}')


# In[19]:


poe_bot = PoeBot(unique_id=UNIQUE_ID, remote_ip = REMOTE_IP, group_id=GROUP_ID, password = config.get("password", None), coordinator_ip = COORD_ID)
mapper = Mapper(poe_bot=poe_bot, strategy = strategy)
poe_bot.allowed_exception_values.extend([
  "map is completed and in hideout, restart",
  "map completed",
  "no portals left to enter",
  'session swap',
  "attempting to generate path points in hideout, restart",
])
def onStuckFunction():
  poe_bot.helper_functions.relog()
  mapper.temp.reset()
  raise Exception('got stuck, relogged')
def onDisconnectFunc():
  poe_bot.logger.writeLine(f'#onDisconnectFunc call at{time.time()}')
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
      poe_bot.raiseLongSleepException('onDisconnectFunc cannot get to main menu')
    time.sleep(0.1)
    game_state = poe_bot.backend.getPartialData()['g_s']
    if game_state == 1:
      break
    
  time_to_sleep = random.randint(60, 180)
  print(f'going to sleep for {time_to_sleep} seconds')
  time.sleep(time_to_sleep)
  poe_bot.helper_functions.logIn()
  raise Exception('logged in, success')
poe_bot.on_death_function = mapper.onDeathFunc
poe_bot.on_stuck_function = onStuckFunction
poe_bot.on_disconnect_function = onDisconnectFunc
poe_bot.refreshAll()
poe_bot.combat_module.assignBuild(build_name)


# In[56]:


# aliases
bot_controls = poe_bot.bot_controls
stash = poe_bot.ui.stash
inventory = poe_bot.ui.inventory
map_device = poe_bot.ui.map_device
afk_temp = poe_bot.afk_temp
mover = poe_bot.mover
combat_module = poe_bot.combat_module
build = poe_bot.combat_module.build


# In[57]:


def defaultSortFunction(items:List[StashItem]):
  return items
class StashManagerSettings:
  def __init__(self) -> None:
    self.recycle_essences = False
    self.recycle_scarabs = False
    self.recycle_catalysts = False
    self.recycle_essences = False
    self.recycle_maps = True
    self.recycle_maps_count = 80
    self.recycle_maps_sort_function = defaultSortFunction
    self.cannot_sell_min_links = 5
    self.keep_portal_scrolls_count = 1
    self.keep_scroll_of_wisdom_count = 1
class StashManager:
  def __init__(
      self, 
      poe_bot: PoeBot, 
      max_items_in_inventory = 30,
      settings=StashManagerSettings(), 
    ) -> None:
    self.poe_bot = poe_bot
    self.settings = settings
    self.max_items_in_inventory = max_items_in_inventory

  def manage(self):
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    afk_temp = poe_bot.afk_temp
    stash_ui = poe_bot.ui.stash
    inventory_ui = poe_bot.ui.inventory

    # free our stash if its full

    # recycle stuff from inventory, sell some shitty uniques/recycle essences, etc./ maps

    # pick maps and consumables from stash? heist\mapper\simulacrum\questbot has different requierments

    return True

  def canSellItemsInInventory(self):
    inventory.update()
    portal_scrolls_count = 0
    scroll_of_wisdom_count = 0
    items_can_sell:List[InventoryItem] = []
    for item in inventory.items:
      if item.rarity == "Unique":
        if item.render_path in SHITTY_UNIQUES_ARTS:
          items_can_sell.append(item)
      elif item.name == "Coffin" or item.render_art == "Metadata/Items/Currency/CurrencyItemisedNecropolisCorpse":
        items_can_sell.append(item)
      elif item.sockets is not None:
        
        if any(list(map(lambda link: len(link) > self.settings.cannot_sell_min_links - 1, item.links))):
          continue
        else:
          items_can_sell.append(item)
      elif item.name == 'Portal Scroll':
        if portal_scrolls_count != self.settings.keep_portal_scrolls_count:
          portal_scrolls_count += 1
        else:
          items_can_sell.append(item)
      elif item.name == 'Scroll of Wisdom':
        if scroll_of_wisdom_count != self.settings.keep_scroll_of_wisdom_count:
          scroll_of_wisdom_count += 1
        else:
          items_can_sell.append(item)
    return items_can_sell
  
  def needToManage(self):
    need_to_manage = False
    if self.settings.recycle_essences is True:
      pass # and we have some essences in non essence tab to recycle
    if self.needToFreeInventory() is True:
      need_to_manage = True
    return need_to_manage
  
  def needToFreeInventory(self):
    return len(self.poe_bot.ui.inventory.getFilledSlots()) > self.max_items_in_inventory
  
  def sellItems(self,items_to_sell:List[InventoryItem]):
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


    self.poe_bot.ui.clickMultipleItems(items_to_sell)

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
  
  def recycleIfNeeded(self):
    stash = self.poe_bot.ui.stash
    recycled_smth = False
    if self.settings.recycle_maps is True:
      print(f'checking if need to recycle maps')
      key_type = 'map'
      key_items = []
      key_items_to_recycle_count = self.settings.recycle_maps_count
      key_sort_function = self.settings.recycle_maps_sort_function
      key_item_in_unsorted = False
      unsorted_items = list(map(lambda i_raw: Item(poe_bot, i_raw), stash.temp.unsorted_items))
      for item in unsorted_items:
        if item.getType() == key_type:
          key_items.append(item)
          key_item_in_unsorted = True
      for item in stash.getAllItems():
        if item.getType() == key_type:
          key_items.append(item)
      key_items_count = len(key_items)
      print(f'{key_items_count} items in {key_items}')
      stash.update()
      if key_items_count > key_items_to_recycle_count:
        if stash.is_opened is False:
          stash.open()
        print(f'need to recycle "{key_type}" type items')
        if key_item_in_unsorted is True:
          stash.updateStashTemp()
        key_items = list(filter(lambda item: item.getType() == key_type, stash.getAllItems()))
        tab_indexes = {}
        for item in key_items:
          if tab_indexes.get(item.tab_index, None):
            tab_indexes[item.tab_index] += 1
          else:
            tab_indexes[item.tab_index] = 1
        priority_tab = max(tab_indexes, key=tab_indexes.get)
        stash.openTabIndex(priority_tab)
        items_can_recycle_in_this_tab = list(filter(lambda i: i.getType() == key_type, stash.current_tab_items))
        items_can_recycle_in_this_tab_sorted = key_sort_function(items_can_recycle_in_this_tab)
        empty_cells_in_inventory_count = len(inventory.getEmptySlots())
        will_pick_items_count = int(empty_cells_in_inventory_count * 0.9)
        print(f'will_pick_items_count {will_pick_items_count} to recycle')
        poe_bot.logger.writeLine(f'recycle {will_pick_items_count} {key_type}')
        items_to_pick_from_stash = items_can_recycle_in_this_tab_sorted[:will_pick_items_count]
        print(f'going to pick items to recycle names {list(map(lambda item: item.name, items_to_pick_from_stash))}')
        stash.pickItems(items_to_pick_from_stash)
        stash.update()
        inventory.update()
        will_sell_items = list(filter(lambda item: item.getType() == key_type, inventory.items))
        will_sell_items_sorted = key_sort_function(will_sell_items)[:will_pick_items_count]
        poe_bot.ui.closeAll()
        time.sleep(random.randint(5,15)/10)
        self.sellItems(will_sell_items_sorted)
        recycled_smth = True

      return recycled_smth
def recycleMapsSortFunction(items:List[StashItem]):
  res = mapper.sortMaps(items)
  res.reverse()
  return res
stash_manager = StashManager(poe_bot=poe_bot)
poe_bot.stash_manager = stash_manager
stash_manager.settings.recycle_maps_sort_function = recycleMapsSortFunction


# In[58]:


def getMapsCanRun(priority='inventory', source='all'):
  all_maps:List[Item] = []
  maps_we_can_run_in_inventory:List[InventoryItem] = []
  maps_we_can_run_in_stash:List[StashItem] = []
  
  if source != 'stash':
    inventory.update()
    maps_we_can_run_in_inventory = mapper.filterMapsCanRun(inventory.items)
  if source != 'inventory':
    all_stash_items = stash.getAllItems()
    maps_we_can_run_in_stash = mapper.filterMapsCanRun(all_stash_items)

  if priority == 'inventory':
    all_maps.extend(maps_we_can_run_in_inventory)
    all_maps.extend(maps_we_can_run_in_stash)
  else:
    all_maps.extend(maps_we_can_run_in_stash)
    all_maps.extend(maps_we_can_run_in_inventory)
    
  sorted_maps = mapper.sortMaps(all_maps)
  return sorted_maps
def getItemsToKeepByKey(key_list:List[str], keep_stacks=1, max_count = 40):
  '''
    keep_stacks - if key_list is [a,b,c,d,e,f] and keep_stacks 2, itll possible leave 2 objects of key_list  
    max_count - if key_list is [a,b,c,d,e,f] and max_count = 4 itll possibly take 4 elements
  '''
  current_count = 0
  consumables_to_keep_in_inventory: List[InventoryItem] = []
  inventory_items_copy = inventory.items[:]
  for consumable in key_list:
    similar_inventory_items = list(filter(lambda i: consumable == i.name, inventory_items_copy))
    if len(similar_inventory_items) != 0:
      print(f'already have {consumable} key_list in inventory in getItemsToKeepByKey')
      similar_items = similar_inventory_items[:keep_stacks]
      consumables_to_keep_in_inventory.extend(similar_items)
      list(map(lambda i: inventory_items_copy.remove(i), similar_items))
      continue
    if current_count == max_count:
      print('current_count == max_count, wont check more')
      break
  return consumables_to_keep_in_inventory
def getItemsToKeepInInventory():
  inventory_items = sorted(inventory.items, key = lambda i: i.items_in_stack, reverse=True)
  items_to_keep_in_inventory:List[InventoryItem] = []
  items_to_keep_in_inventory.extend(list(filter(lambda i: i.name == "Portal Scroll", inventory_items))[:1])
  items_to_keep_in_inventory.extend(getMapsCanRun(source='inventory')[:random.randint(6,10)])
  items_to_keep_in_inventory.extend(getItemsToKeepByKey(mapper.settings.keep_consumables))
  items_to_keep_in_inventory.extend(getItemsToKeepByKey(mapper.settings.musthave_map_device_modifiers, keep_stacks=random.randint(2,3), max_count = 3))
  items_to_keep_in_inventory.extend(getItemsToKeepByKey(mapper.settings.prefered_map_device_modifiers, keep_stacks=random.randint(2,3), max_count = 3))
  if mapper.settings.essences_can_corrupt is True:
    items_to_keep_in_inventory.extend(list(filter(lambda i: i.name == "Remnant of Corruption", inventory_items))[:3])
  if mapper.settings.alch_chisel is True:
    items_to_keep_in_inventory.extend(list(filter(lambda i: i.name == "Cartographer's Chisel", inventory_items))[:1])
    items_to_keep_in_inventory.extend(list(filter(lambda i: i.name == "Orb of Alchemy", inventory_items))[:2])
  if mapper.settings.use_timeless_scarab_if_connected_or_presented:
    items_to_keep_in_inventory.extend(list(filter(lambda i: i.name == "Incursion Scarab of Timelines", inventory_items))[:2])
    

  return items_to_keep_in_inventory
def useItemOnItem(item_to_use_key:str, item_to_be_modified:Item, iterations = 1):
  """
  return True if used something, Flase if item is not in inventory
  """
  items_to_use = list(filter(lambda i:i.name == item_to_use_key,inventory.items))
  if len(items_to_use) != 0:
    item_to_use = items_to_use[0]
    item_to_use.click(button="right")
    time.sleep(random.randint(10,30)/100)

    if iterations > 1:
      poe_bot.bot_controls.keyboard_pressKey("DIK_LSHIFT")
      time.sleep(random.randint(10,30)/100)


    for _ in range(iterations):
      item_to_be_modified.click()
      time.sleep(random.randint(10,30)/100)

    if iterations > 1:
      poe_bot.bot_controls.keyboard_releaseKey("DIK_LSHIFT")

    time.sleep(random.randint(10,30)/100)

    return True
  return False
def doPreparations():
  print(f'doing preparations for mapping streak {mapper.temp.map_streak}')
  activated_map_can_run = False
  need_to_pick_something = False
  managed_stash = False
  keys_to_pick_from_stash = []
  keys_stash_tabs = []
  items_to_keep_in_inventory:List[InventoryItem] = []

  def checkWhatKeysToPick(key_list: List[str], keep_stacks=1, max_stacks_count = 40, append_to_list = None):
    need_to_pick_something = False
    current_count = 0
    keys_to_pick_from_stash_temp = []
    inventory_items_copy = inventory.items[:]
    for consumable in key_list:
      similar_inventory_items = list(filter(lambda i: consumable == i.name, inventory_items_copy))
      if len(similar_inventory_items) != 0:
        print(f'already have {consumable} key_list in inventory in checkWhatKeysToPick')
        similar_items = similar_inventory_items[:keep_stacks]
        items_to_keep_in_inventory.extend(similar_items)
        list(map(lambda i: inventory_items_copy.remove(i), similar_items))
        current_count += 1
        continue
      if current_count == max_stacks_count:
        print('current_count == max_count, wont check more')
        break
      similar_stash_items = list(filter(lambda i: consumable == i.name, all_stash_items))
      if len(similar_stash_items) != 0:
        print(f"can pick {consumable} key_list from stash")
        need_to_pick_something = True
        keys_stash_tabs.extend(list(map(lambda i: i.tab_index, similar_stash_items)))
      keys_to_pick_from_stash_temp.append(consumable)
    
    if current_count != max_stacks_count:
      keys_to_pick_from_stash.extend(keys_to_pick_from_stash_temp)

    return need_to_pick_something

  all_stash_items = stash.getAllItems()

  if mapper.temp.map_streak > mapper.collect_beasts_every_x_maps:
    print(f'going to release beasts this time')
    keys_stash_tabs.insert(0, 0)
    need_to_pick_something = True

  if len(all_stash_items) == 0:
    print('no data about items in stash, updating')
    stash.updateStashTemp()
    all_stash_items = stash.getAllItems()

  # check if we have better maps in stash
  sorted_maps = getMapsCanRun()

  if len(sorted_maps) == 0:
    print(f'cannot find maps in stash.temp or inventory, checking stash')
    stash.open()
    stash.updateStashTemp()
    sorted_maps = getMapsCanRun()
    if len(sorted_maps) == 0:
      print(f'no maps in stash after check, activating kirak mission, buying maps')
      poe_bot.ui.closeAll()
      time.sleep(random.randint(10,20)/100)
      map_device.open()
      if not any(list(map(lambda mission_count: mission_count != 0, map_device.kirak_missions_count))):
        poe_bot.raiseLongSleepException('no kirac missions avaliable')
      activated_map = mapper.activateKiracMissionMap()
      poe_bot.helper_functions.waitForNewPortals()
      mapper.buyMapsFromKirac()
      if mapper.atlas_explorer is True and not activated_map.name in poe_bot.game_data.completed_atlas_maps.getCompletedMaps():
        return True, False
      else:
        sorted_maps = getMapsCanRun()

  # check if we have any better map to run in our inventory or stash
  if sorted_maps[0].source != 'inventory':
    print('we have better map in stash')
    _maps_in_stash = list(filter(lambda i: i.source == 'stash', sorted_maps))
    keys_stash_tabs.extend(list(map(lambda i: i.tab_index, _maps_in_stash)))
    need_to_pick_something = True
  
  # check if we have consumables or we can pick them from stash which are needed for mapping
  nps = checkWhatKeysToPick(mapper.settings.keep_consumables)
  if nps is True: need_to_pick_something = True
  if mapper.settings.growing_hordes is True:
    print('mapper.growing_hordes is True: #TODO')
  else:
    # TODO rewrite
    nps = checkWhatKeysToPick(mapper.settings.musthave_map_device_modifiers, keep_stacks=random.randint(1,2), max_stacks_count = 4)
    if nps is True: need_to_pick_something = True
    nps = checkWhatKeysToPick(mapper.settings.prefered_map_device_modifiers, keep_stacks=random.randint(1,2), max_stacks_count = 4)
    if nps is True: need_to_pick_something = True
  
  # if the best map is in stash, itll call procedure of stashing 
  print(need_to_pick_something)
  if need_to_pick_something is True:
    print('need to pick something from stash')
    
    items_can_sell = stash_manager.canSellItemsInInventory()
    if len(items_can_sell) != 0:
      print(f'can sell {items_can_sell}')
      stash_manager.sellItems(items_can_sell)
      inventory.update()


    keys_stash_tabs = list(set(keys_stash_tabs))
    items_to_keep_in_inventory = getItemsToKeepInInventory()
    print(f"items_to_keep_in_inventory {items_to_keep_in_inventory}")

    print(f"keys_to_pick_from_stash {keys_to_pick_from_stash}")
    print(f"keys_stash_tabs {keys_stash_tabs}")
    stash.open()

    print(f'current tab index {stash.current_tab_index}')
    random.shuffle(keys_stash_tabs)

    try:
      keys_stash_tabs.pop(keys_stash_tabs.index(stash.current_tab_index))
    except Exception as e:
      print("current tab index is not in list, but we ll still check it")
    keys_stash_tabs.insert(0, stash.current_tab_index)

    print(f"keys_stash_tabs {keys_stash_tabs}")

    can_pick_maps_count = random.randint(6,10)
    for tab_index in keys_stash_tabs:
      items_to_pick_in_this_stash_tab:List[StashItem] = []
      all_maps = []

      # break if we have picked enough items
      # if can_pick_maps_count == 0 and len(keys_to_pick_from_stash) == 0:
      #   break
      afk_temp.performShortSleep()
      stash.openTabIndex(tab_index)
      afk_temp.performShortSleep()
      inventory.update()
      maps_we_can_run_in_inventory = mapper.filterMapsCanRun(inventory.items)
      maps_we_can_run_in_stash = mapper.filterMapsCanRun(stash.current_tab_items)
      all_maps.extend(maps_we_can_run_in_stash)
      all_maps.extend(maps_we_can_run_in_inventory)
      sorted_maps = mapper.sortMaps(all_maps)

      # check if we have better map in this stash tab
      # if have, pick it
      for sorted_map_item in sorted_maps:
        if can_pick_maps_count == 0:
          break
        if sorted_map_item.source != "stash":
          break
        can_pick_maps_count -= 1
        items_to_pick_in_this_stash_tab.append(sorted_map_item)

      indexes_to_remove = []
      stash_current_tab_items_copy = stash.current_tab_items[:]
      for key_index in range(len(keys_to_pick_from_stash)):
        key = keys_to_pick_from_stash[key_index]
        similar_item = next((i for i in stash_current_tab_items_copy if key == i.name), None)
        if similar_item is not None:
          print(f'gonna pick {key} {similar_item.raw}')
          items_to_pick_in_this_stash_tab.append(similar_item)
          indexes_to_remove.append(key_index)
          stash_current_tab_items_copy.remove(similar_item)

      for key_index in indexes_to_remove[::-1]: keys_to_pick_from_stash.pop(key_index)
        
      if mapper.settings.growing_hordes is True:
        print('#if mapper.growing_hordes is True: #TODO')
        # poe_bot.raiseLongSleepException('#if mapper.growing_hordes is True: #TODO')
        # items_to_pick_in_this_stash_tab.append('')

      if len(items_to_pick_in_this_stash_tab) != 0:
        time.sleep(random.randint(10,30)/10)

      # stash items if we have lots of items
      inventory.update()
      items_grid_position_backup = list(map(lambda i: (i.grid_position.x1, i.grid_position.y1), items_to_keep_in_inventory))
      can_stash_items = list(filter(lambda i: not (i.grid_position.x1, i.grid_position.y1) in items_grid_position_backup, inventory.items))
      inventory.stashItems(can_stash_items)
      picked_items = stash.pickItems(items_to_pick_in_this_stash_tab)
      items_to_keep_in_inventory.extend(picked_items)

      if mapper.settings.do_alva == True and stash.current_tab_index == 0:
        sortAndFilterItemizedTemples()

      if mapper.temp.map_streak > mapper.collect_beasts_every_x_maps:
        if mapper.settings.do_beasts is True:
          dealWithBestiary(mapper.settings.beast_search_string, mapper.settings.release_beasts)
          streak_random_val = int(mapper.collect_beasts_every_x_maps*0.2)
          mapper.temp.map_streak = 0 + random.randint(-streak_random_val, streak_random_val)
        else:
          mapper.temp.map_streak = 0
        mapper.temp.save()
      # next tab
      time.sleep(random.randint(10,30)/10)

  afk_temp.performShortSleep()
  stash_manager.recycleIfNeeded()
  if stash.is_opened is True:
    poe_bot.ui.closeAll()
  
  if mapper.settings.do_alva:
    if mapper.incursion_temp.current_temple_state_dict == {}:
      print(f'current incursion temple state is empty, updating it')
      mapper.updateAlvaInHideout()


  afk_temp.performShortSleep()
  afk_temp.save()
  return activated_map_can_run, managed_stash

def checkIfmusthave_map_device_modifiersExistsInStash(consumable):
  print(f"#checkIfmusthave_map_device_modifiersExistsInStash call at {time.time()}")
  # update stash
  poe_bot.ui.closeAll()
  time.sleep(random.randint(20,40)/100)
  poe_bot.ui.stash.updateStashTemp()
  similar_items_in_stash = list(filter(lambda stash_item: stash_item.name == consumable, poe_bot.ui.stash.getAllItems()))
  if len(similar_items_in_stash) != 0:
    mapper.temp.reset()
    raise Exception(f'seems like {consumable} wasnt in inventory but appeared to be in stash, restarting')
  else:
    poe_bot.raiseLongSleepException(f'mapper.settings.musthave_map_device_modifiers {consumable} len(similar_items) == 0')


def activateMap():
  if mapper.settings.essences_do_memory:
    mapper.activateCrystalMemory()
    return
  need_to_identify = False
  need_to_scour = False
  need_to_alch = False
  need_to_vaal = False
  need_to_transmute = False
  inventory.update()
  for consumable in mapper.musthave_map_device_modifiers:
    similar_items = list(filter(lambda i: consumable == i.name, inventory.items))
    if len(similar_items) == 0:
      checkIfmusthave_map_device_modifiersExistsInStash(consumable)
  maps_we_can_run_in_inventory = mapper.sortMaps(mapper.filterMapsCanRun(inventory.items))



  # if dont have any better map for explore, activate mission, buy maps from kirak
  if len(maps_we_can_run_in_inventory) == 0:
    mapper.temp.reset()
    raise Exception("len(maps_we_can_run_in_inventory) == 0 in activateMap")
  afk_temp.performShortSleep()
  map_device.open()
  afk_temp.performShortSleep()

  # if dont have any better map for explore, activate mission, buy maps from kirak
  if mapper.atlas_explorer is True:
    if maps_we_can_run_in_inventory[0].name in poe_bot.game_data.completed_atlas_maps.getCompletedMaps() and any(list(map(lambda mission_count: mission_count != 0, map_device.kirak_missions_count))):
      print(f'mapper.atlas_explorer is True and best map is completed, activating kirak mission and buying new maps')
      activated_map = mapper.activateKiracMissionMap()
      poe_bot.helper_functions.waitForNewPortals()
      mapper.buyMapsFromKirac()
      poe_bot.ui.closeAll()
      time.sleep(random.randint(5,20)/10)
      if not activated_map.name in poe_bot.game_data.completed_atlas_maps.getCompletedMaps():
        print(f'can run currently activated map')
        return activated_map
      map_device.open()

  items_in_map_device = list(filter(lambda i: i['RenderArt'] is not None,map_device.placed_items))
  maps_in_map_device = list(filter(lambda i: i['RenderArt'] is not None and "Metadata/Items/Maps/" in i['RenderArt'], items_in_map_device))
  if len(maps_in_map_device) > 1:
    poe_bot.raiseLongSleepException('2 or more maps in map device')
  elif len(maps_in_map_device) == 0:
    empty_slots_in_map_device = map_device.number_of_slots - len(items_in_map_device)
    if empty_slots_in_map_device == 0:
      poe_bot.raiseLongSleepException('no empty slots in map device to place a map')
  else:
    print(f'there is a map in map device already, activating it')
    poe_bot.logger.writeLine('activated map which was in map device')
    map_device.activate()
    return maps_in_map_device[0]
  
  if mapper.settings.invitation_rush is True:
    can_burn_map = mapper.invRushCanBurnMap()
    progress_text_index = 1 if mapper.settings.invitation_type == 'blue' else 0
    invitation_progress = int(map_device.raw['i_p'][progress_text_index].split(': ')[1].split('/')[0])
    print(f'invitation_progress = {invitation_progress}')
    mapper.temp.invitation_progress = invitation_progress
    if invitation_progress >= 27:
      can_burn_map = False
      print(f'going to run map with nearest boss')

    print(f'can_burn_map: {can_burn_map}')
    if can_burn_map == False:
      # choose good map

      pass
    else:
      mapper.settings.alch_chisel = False
      # choose shitty map
      pass
  map_to_run = maps_we_can_run_in_inventory[0]

  print(f'going to run map {map_to_run.name}')
  if mapper.atlas_explorer is True:
    poe_bot.game_data.completed_atlas_maps.getCompletedMaps()
    # modify map
    completed_maps = poe_bot.game_data.completed_atlas_maps.getCompletedMaps()
    print(f'completed_maps {completed_maps}')
    if not map_to_run.name in completed_maps:
      print(f'mapper.atlas_explorer is True and we are going to run unfinished map')
      need_to_identify = False
      need_to_scour = False
      need_to_alch = False
      need_to_vaal = False
      need_to_transmute = False
      if map_to_run.rarity != 'Normal':
        if map_to_run.map_tier > 5 and map_to_run.rarity == 'Magic':
          print("map yellow\red tier and map is blue(magic)")
          need_to_scour = True
          # if identified is 0
          if map_to_run.identified is False:
            print("map not identified")
            need_to_identify = True
          need_to_alch = True
      # alch even blue maps
      else:
        if map_to_run.map_tier > 5:
          print("map is normal, alch it")
          need_to_alch = True
        else:
          need_to_transmute = True
      # if red and not corrupted
      if map_to_run.map_tier > 10 and map_to_run.corrupted is False:
        if map_to_run.identified == 0:
          print("map not identified")
          need_to_identify = True
          print("tier is > 10 and not corrupted")
        need_to_vaal = True

    # if current map is passed and we have kirak mission, activate most preferable kirak mission and buy maps from kirak
    # else:
      # if any(list(map(lambda count: count != 0, map_device.kirak_missions_count))):
        # open kirak mission
        # activate some map
        
        # if map is uncomplete flag it, so well run it

        # buy unfinished maps from kirak
        # mapper.buyMapsFromKirac()

  #TODO modify map if needed, alch + go or atlas_rush
  if any([need_to_alch, need_to_identify, need_to_scour, need_to_vaal, need_to_transmute]):
    print('[need_to_alch, need_to_identify, need_to_scour, need_to_vaal, need_to_transmute]')
    print([need_to_alch, need_to_identify, need_to_scour, need_to_vaal, need_to_transmute])
    for i in range(1):
      if need_to_alch:
        alch_in_inventory = list(filter(lambda i: i.name == 'Orb of Alchemy', inventory.items))
        binding_in_inventory = list(filter(lambda i: i.name == 'Orb of Binding', inventory.items))
        if len(alch_in_inventory) == 0 and len(binding_in_inventory) == 0:
          print('dont have alch_in_inventory or binding_in_inventory')
          break
      if need_to_identify:
        wisdom_in_inventory = list(filter(lambda i: i.name == 'Scroll of Wisdom', inventory.items))
        if len(wisdom_in_inventory) == 0:
          print('dont have wisdom_in_inventory')
          break
      if need_to_vaal:
        vaal_in_inventory = list(filter(lambda i: i.name == 'Vaal Orb', inventory.items))
        if len(vaal_in_inventory) == 0:
          print('dont have vaal_in_inventory')
          break
      if need_to_scour:
        scouring_in_inventory = list(filter(lambda i: i.name == 'Orb of Scouring', inventory.items))
        if len(scouring_in_inventory) == 0:
          print('dont have scouring_in_inventory')
          break
      if need_to_transmute:
        transmute_in_inventory = list(filter(lambda i: i.name == 'Orb of Transmutation', inventory.items))
        if len(transmute_in_inventory) == 0:
          print('dont have transmute_in_inventory')
          alch_in_inventory = list(filter(lambda i: i.name == 'Orb of Alchemy', inventory.items))
          binding_in_inventory = list(filter(lambda i: i.name == 'Orb of Binding', inventory.items))
          if len(alch_in_inventory) == 0 and len(binding_in_inventory) == 0:
            print('and dont have alchs and bindings')
            break
          else:
            print('but have alch_in_inventory or binding_in_inventory, so ok')

      inventory.open()
      afk_temp.performShortSleep()
      if need_to_identify is True:
        useItemOnItem('Scroll of Wisdom', map_to_run)
        time.sleep(random.randint(5,20)/10)
      if need_to_transmute is True:
        if len(transmute_in_inventory) != 0:
          useItemOnItem('Orb of Transmutation', map_to_run)
        else:
          if len(binding_in_inventory) != 0:
            useItemOnItem('Orb of Binding', map_to_run)
          else:
            useItemOnItem('Orb of Alchemy', map_to_run)
        time.sleep(random.randint(5,20)/10)
      if need_to_scour is True:
        useItemOnItem('Orb of Scouring', map_to_run)
        time.sleep(random.randint(5,20)/10)
      if need_to_alch is True:
        if len(binding_in_inventory) != 0:
          useItemOnItem('Orb of Binding', map_to_run)
        else:
          useItemOnItem('Orb of Alchemy', map_to_run)
        time.sleep(random.randint(5,20)/10)
      if need_to_vaal is True:
        useItemOnItem('Vaal Orb', map_to_run)
        time.sleep(random.randint(5,20)/10)
    # place map into map device

  if mapper.settings.alch_chisel is True:
    print(f'needs to use alch and chisel')
    for _ in range(1):
      if map_to_run.identified is False:
        break
      if map_to_run.rarity == 'Normal':
        chisels_in_inventory = list(filter(lambda i: i.name == "Cartographer's Chisel", inventory.items))
        alch_in_inventory = list(filter(lambda i: i.name == 'Orb of Alchemy', inventory.items))
        if len(alch_in_inventory) == 0:
          print(f'wont chisel since alchs: {len(alch_in_inventory) == 0}')
          break
        useItemOnItem("Cartographer's Chisel", map_to_run, iterations=random.randint(4,6))
        useItemOnItem('Orb of Alchemy', map_to_run)
        break

  # place map
  afk_temp.performShortSleep()
  map_to_run.click(hold_ctrl=True)
  afk_temp.performShortSleep()

  placed_maps = list(filter(lambda i:i.getType() == "map",map_device.items))
  _i = 0
  map_placed = False
  while _i < 30:
    _i += 1
    if len(placed_maps) == 0:
      print(f'len(placed_maps) == 0 {placed_maps}')
    elif len(placed_maps) != 1:
      print(f'len(placed_maps) != 1 {placed_maps}')
    else:
      map_placed = True
      break
    time.sleep(0.5)
    map_device.update()
    placed_maps = list(filter(lambda i:i.getType() == "map",map_device.items))
  placed_map = placed_maps[0]
  print(f'[Mapper] placed_map is {placed_map.name}')
  if map_placed is False:
    afk_temp.performShortSleep()
    poe_bot.ui.inventory.clickOnAnEmptySlotInInventory()
    time.sleep(random.randint(20,40)/100)
    poe_bot.ui.closeAll()
    time.sleep(random.randint(20,40)/100)
    time.sleep(random.randint(20,40)/100)
    poe_bot.ui.closeAll()
    time.sleep(random.randint(20,40)/100)
    mapper.temp.reset()
    raise Exception(f"map_placed is False {placed_maps}")
  

  # place modifiers if needed into map device
  if mapper.settings.do_alva:
    if mapper.incursion_temp.need_to_use_timeless_scarab:
      print('need to place timeless scarab')
      afk_temp.performShortSleep()
      mapper.putIncursionScarabs(True)
      mapper.temp.used_timeless_scarab_for_alva = True
      mapper.temp.save()
    else:
      print('remove timeless scarab if its there')
      mapper.putIncursionScarabs(False)

  if True:
    items_to_place_in_map_device = []
    items_to_place_in_map_device.extend(mapper.settings.prefered_map_device_modifiers)
    items_to_place_in_map_device.extend(mapper.settings.musthave_map_device_modifiers)
    if len(items_to_place_in_map_device) != 0:
      map_device.update()
      print(f'items_to_place_in_map_device: {items_to_place_in_map_device}')
      items_to_place_in_map_device = items_to_place_in_map_device[:map_device.number_of_slots-1]
      print(f'map device has {map_device.number_of_slots}, so cut to {len(items_to_place_in_map_device)}')
      must_have_items = []
      map_device_placed_items_copy = map_device.placed_items[:]
      # check if modifiers already placed in map device
      for modifier in items_to_place_in_map_device:
        similar_item =  next( (i for i in map_device_placed_items_copy if i['Name'] is not None and modifier == i['Name']), None)
        if similar_item:
          print(f'In map device already: {similar_item["Name"]} ')
          map_device_placed_items_copy.remove(similar_item)
        else:
          print(f'Can also place in map device: {modifier}')
          must_have_items.append(modifier)

      if len(must_have_items) != 0:
        print(f'{must_have_items} arent in map device, placing them from inventory')
        for item in must_have_items:
          print(f'Want place in map device: {item}')
          inventory.update()
          # to_pick = list(filter(lambda i: item in i.name, inventory.items))
          to_pick = next( (i for i in inventory.items if i.name == item), None)
          if not to_pick:
            print(f'{item} doesnt exist in the inventory')
            # if items is in settings.musthave_map_device_modifiers
            if item in mapper.settings.musthave_map_device_modifiers:
              # extract map
              poe_bot.ui.clickMultipleItems(placed_maps, hold_ctrl=True)
              checkIfmusthave_map_device_modifiersExistsInStash(item)
            continue
          else:
            print(f'placing {item}, from inventory {to_pick.raw}')
            to_pick.click(hold_ctrl=True)
            afk_temp.performShortSleep()
            time.sleep(random.randint(10,20)/100)

  # check map device option if needed
  if mapper.map_device_option is not None and mapper.map_device_option != '' :
    print(f"[Mapper] setting mapper.map_device_option {mapper.map_device_option}")
    afk_temp.performShortSleep()
    map_device.setOption(mapper.map_device_option)
  # activate
  time.sleep(random.randint(5,20)/10)
  poe_bot.logger.writeLine(f'[Mapper] activated map {placed_map.name}')
  afk_temp.performShortSleep()
  map_device.activate()
  afk_temp.performShortSleep()
  afk_temp.save()
  time.sleep(random.randint(3,7)/10)
  # poe_bot.ui.closeAll() # why?

  poe_bot.helper_functions.waitForNewPortals()
  return map_to_run
def doStashing():
  # poe_bot = self.poe_bot
  inventory = poe_bot.ui.inventory
  inventory.update()
  if stash_manager.needToFreeInventory() is True:
    print(f'stash_manager.needToFreeInventory() is True')
    items_can_sell = stash_manager.canSellItemsInInventory()
    if len(items_can_sell) != 0:
      print(f'can sell {items_can_sell}')
      stash_manager.sellItems(items_can_sell)
      inventory.update()
      
    if stash_manager.needToFreeInventory() is True:
      print('still full inventory after selling useless items, stashing, recycling')
      items_to_keep = getItemsToKeepInInventory()
      print(f'items_to_keep {items_to_keep}')
      stash.open()
      if mapper.settings.do_alva == True:
        sortAndFilterItemizedTemples()
      inventory.update()
      items_grid_position_backup = list(map(lambda i: (i.grid_position.x1, i.grid_position.y1), items_to_keep))
      can_stash_items = list(filter(lambda i: not (i.grid_position.x1, i.grid_position.y1) in items_grid_position_backup, inventory.items))
      inventory.stashItems(can_stash_items)
      recycled = stash_manager.recycleIfNeeded()
      if recycled is True:
        if stash_manager.needToFreeInventory() is True:
          print('inventory is full after recycling, stashing items')
          items_to_keep = getItemsToKeepInInventory()
          print(f'items_to_keep {items_to_keep}')
          stash.open()
          inventory.update()
          items_grid_position_backup = list(map(lambda i: (i.grid_position.x1, i.grid_position.y1), items_to_keep))
          can_stash_items = list(filter(lambda i: not (i.grid_position.x1, i.grid_position.y1) in items_grid_position_backup, inventory.items))
          inventory.stashItems(can_stash_items)
      poe_bot.ui.closeAll()
def run(nested=False):
  activated_map = False
  in_instance = not 'Hideout' in poe_bot.game_data.area_raw_name# and not "_town_" in poe_bot.game_data.area_raw_name
  print(f'current instance: {poe_bot.game_data.area_raw_name} in_instance {in_instance}')
  if mapper.temp.stage == 0:
    mapper.checkIfSessionEnded()
    activated_map_can_run, managed_stash = doPreparations()
    print(f"activated_map_can_run {activated_map_can_run}")
    mapper.temp.stage = 2 if activated_map_can_run is True else 1
    mapper.temp.save()
  if mapper.temp.stage == 1:
    activateMap()
    mapper.temp.stage = 2
    mapper.temp.save()
  if mapper.temp.stage == 2:
    build.doPreparations()
    if in_instance is False:
      if mapper.temp.map_completed is True:
        mapper.temp.reset()
        if mapper.temp.used_timeless_scarab_for_alva is True and len(mapper.temp.alvas_to_ignore_ids) == 0:
          poe_bot.logger.writeLine('alva, placed timeless scarab and didnt do any incursion during map, resetting temp, bug')
          mapper.incursion_temp.reset()
        poe_bot.logger.writeLine('map completed')
        
        if nested == False:
          run(True);return
        else:
          raise Exception('map is completed and in hideout, restart')
      if activated_map == True:
        pass
      doStashing()
      try:
        poe_bot.helper_functions.getToPortal(refresh_area=True)
      except Exception as e:
        traceback.print_exc()
        if e.__str__() == 'No portals':
          mapper.temp.reset()
        raise Exception('no portals left to enter')


# In[59]:


time_now = time.time()
reset_afk_temp = False

if notebook_dev:
  poe_bot.debug = True
  reset_afk_temp = True

time_since_last_afk_temp_update = time_now - afk_temp.update_time
if time_since_last_afk_temp_update > 60 * 60 * 4:
  text = f'last afk temp update was {int(time_since_last_afk_temp_update)} seconds passed since last afk temp update, resetting afk temp'
  poe_bot.logger.writeLine(text)
  reset_afk_temp = True

if reset_afk_temp == True:
  afk_temp.reset()


time_since_last_mapper_temp_update = time_now - mapper.temp.update_time
if time_since_last_mapper_temp_update > 60 * 5:
  text = f'{time_since_last_mapper_temp_update} seconds passed since last mapper temp update, resetting mapper temp'
  poe_bot.logger.writeLine(text)
  print(text)
  mapper.temp.reset()

if mapper.settings.do_alva:
  time_since_last_alva_update = time_now - mapper.incursion_temp.update_time
  if time_since_last_alva_update > 60 * 5:
    text = f'{time_since_last_alva_update} seconds passed since last alva update, resetting incursion temp'
    print(text)
    poe_bot.logger.writeLine(text)
    mapper.incursion_temp.reset()
  # print(f'{time_now - mapper.temp.wave_start_time} passed since last wave start, resetting afk_temp')
  # afk_temp.reset()


# In[ ]:


# get into hideout if needed
in_town = '_town' in poe_bot.game_data.area_raw_name and ("2_" in poe_bot.game_data.area_raw_name or "1_" in poe_bot.game_data.area_raw_name)
if in_town is True:
  original_location_raw_name = poe_bot.game_data.area_raw_name
  print(f'in town, going to hideout')
  bot_controls.keyboard.tap('DIK_SPACE')
  poe_bot.helper_functions.getToHideout()
  for i in range(100):
    if i == 90:
      poe_bot.raiseLongSleepException('something wrong on getting to hideout')
    time.sleep(2)
    poe_bot.refreshAll()
    if poe_bot.game_data.area_raw_name != original_location_raw_name:
      if poe_bot.game_data.is_loading is True:
        print('loading')
      else:
        print(f'loaded')
        break
    else:
      print('nothing happened') 

if "MapSideArea" in poe_bot.game_data.area_raw_name:
  print(f'seems to be a vaal side area, {poe_bot.game_data.area_raw_name}')
  mapper.temp.reset()
  onStuckFunction()

if 'Hideout' in poe_bot.game_data.area_raw_name:
  print(f'in hideout')
  # build.doPreparations()
else:
  print(f'seems like we are in instance or somewhere else')



# In[ ]:


run()


# In[ ]:


# poe_bot.refreshAll()
tsp = TSP(poe_bot=poe_bot)
poe_bot.discovery_radius = 110

"""
harvest metadata
Metadata/Terrain/Leagues/Harvest/Objects/HarvestFeatureChest; Harvest; ff36B400
Metadata/Terrain/Leagues/Harvest/harvest_encounter.arm; Harvest; ff36B400

"""

mapper.current_map = getMapAreaObject(poe_bot.game_data.area_raw_name)
if mapper.temp.visited_wildwood is False and mapper.settings.wildwood_jewel_farm is True:
  preloaded_files = poe_bot.backend.getPreloadedFiles()
  if "Art/Models/Terrain/Woods/Tiles/OldForestWoods/AzmeriArena/tgms/arenaTransition_01_c1r3.tgm" in preloaded_files:
    print("we have wildwood boss")
    mapper.need_to_visit_wildwood = True
    # input('wildwood debug') 

print(f'poe_bot.game_data.area_raw_name {poe_bot.game_data.area_raw_name}')
in_instance = not 'Hideout' in poe_bot.game_data.area_raw_name
if in_instance is False:
  raise Exception("attempting to generate path points in hideout, restart")
print(f'current map {mapper.current_map}')
mapper.started_running_map_at = time.time()
poe_bot.logger.writeLine(f'started running map at {mapper.started_running_map_at}')


# In[ ]:


mapper.temp.map_completed = False
can_go_to_another_transition = False
while mapper.temp.map_completed is False:
  poe_bot.refreshInstanceData()
  print(f'generating pathing points')
  if mapper.boss_rush is True:
    tsp.generatePointsForDiscovery()
    discovery_points = tsp.sortedPointsForDiscovery(poe_bot.pather.utils.getFurthestPoint(poe_bot.game_data.player.grid_pos.toList()))
  else:
    tsp.generatePointsForDiscovery()
    discovery_points = tsp.sortedPointsForDiscovery()
    print(f'len(discovery_points) {len(discovery_points)}')
    discovery_points = list(filter(lambda p: poe_bot.game_data.terrain.checkIfPointPassable(p[0], p[1]), discovery_points))
    print(f'len(discovery_points) {len(discovery_points)} after sorting')
  if len(discovery_points) == 0:
    print(f'len(discovery_points) == 0 after points generation')
    mapper.temp.map_completed = True
    break
  point_to_go = discovery_points.pop(0)
  while point_to_go is not None and mapper.temp.map_completed is False:
    # check if point needs to be explored
    need_to_explore = poe_bot.game_data.terrain.isPointVisited(point_to_go[0], point_to_go[1])
    if need_to_explore is True:
      print(f'exploring point {point_to_go}')
    else:
      print(f'surrounding around {point_to_go} discovered, skipping')
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
      custom_break_function=mapper.exploreRoutine,
      custom_continue_function=build.usualRoutine,
      step_size=random.randint(30,35)
    )
    # then, it result is True, False or None
    print(f"mover.goToPoint result {result}")

    if mapper.boss_rush is True and mapper.temp.map_boss_killed is True:
      print(f'mapper.boss_rush is True and mapper.temp.map_boss_killed is True')
      mapper.temp.map_completed = True
      break

    # check if we have transitions (excluding bossrooms, vaal, #TODO hideout, betrayal,)
    if len(mapper.temp.unvisited_transitions):
      need_to_go_to_next_transition = can_go_to_another_transition
      if mapper.boss_rush is True:
        need_to_go_to_next_transition = True
      else:
        print(f'mapper.temp.unvisited_transitions {mapper.temp.unvisited_transitions}')
        passable_area_discovered_percent = poe_bot.game_data.terrain.getPassableAreaDiscoveredForPercent(total=False)
        print(f'passable_area_discovered_percent {passable_area_discovered_percent}')
        # check if current area visited percent > 75%:
        if passable_area_discovered_percent > 0.75:
          need_to_go_to_next_transition = True

      if need_to_go_to_next_transition is True:
        # check if unvisited transitions == 1: otherwise raise error
        raw_transition_entity = mapper.temp.unvisited_transitions.pop(0)
        # mapper.temp.save()
        transition_entity = Entity(poe_bot, raw_transition_entity)
        while True:
          res = mover.goToPoint(
            point=[transition_entity.grid_position.x, transition_entity.grid_position.y],
            min_distance=30,
            release_mouse_on_end=False,
            custom_continue_function=build.usualRoutine,
            custom_break_function=poe_bot.loot_picker.collectLoot,
            step_size=random.randint(25,33)
          )
          if res is None:
            break
        mover.enterTransition(transition_entity)
        poe_bot.refreshInstanceData()
        exit_transitions = []
        look_for_exit_transition = 0
        while len(exit_transitions) == 0:
          look_for_exit_transition += 1
          if look_for_exit_transition == 20 or look_for_exit_transition == 40:
            poe_bot.backend.forceRefreshArea()
          if look_for_exit_transition > 100:
            poe_bot.on_stuck_function()
            raise Exception('look_for_exit_transition > 100:')
            # poe_bot.raiseLongSleepException('look_for_exit_transition > 100:')
            # break
          poe_bot.refreshInstanceData(reset_timer=True)
          exit_transitions = list(filter(lambda e: e.rarity == 'White' and e.id != transition_entity.id, poe_bot.game_data.entities.area_transitions))

          
        exit_transition = exit_transitions[0]
        mapper.temp.visited_transitions_ids.append(exit_transition.id)
        mapper.temp.visited_transitions_ids.append(transition_entity.id)
        mapper.temp.transition_chain.append(transition_entity.raw)
        mapper.temp.save()
        can_go_to_another_transition = False
        break

    # if map was discovered
    if mapper.boss_rush is False and (mapper.atlas_explorer is False or mapper.temp.map_boss_killed is True) and poe_bot.game_data.terrain.getPassableAreaDiscoveredForPercent(total=True) >= mapper.settings.discovery_percent:
      if mapper.temp.unvisited_transitions != []:
        print(f'willing to finish the map, but got another transition to visit')
        can_go_to_another_transition = True
        continue
      print(f'discovered for more than {int(mapper.settings.discovery_percent*100)} percents, breaking')
      mapper.temp.map_completed = True
      break

    
    # if we arrived to discovery point and nothing happened
    if result is None:
      while True:
        if len(discovery_points) == 0:
          if mapper.boss_rush is True or mapper.settings.discovery_percent > mapper.settings.default_discovery_percent:
            print(f'mapper.boss_rush is True or custom_discovery_percent and len(discovery_points) == 0')
            print(f'generating new points')
            point_to_go = None
            break
          else:
            point_to_go = None
            mapper.temp.map_completed = True
            print(f'len(discovery_points) == 0, breaking')
            break

        point_to_go = discovery_points.pop(0)
        print(f'willing to explore next point {point_to_go}')
        need_to_explore = poe_bot.game_data.terrain.isPointVisited(point_to_go[0], point_to_go[1])

        if need_to_explore is True:
          print(f'exploring point {point_to_go}')
          break
        else:
          print(f'surrounding around {point_to_go} discovered, skipping')
          continue 
    
    poe_bot.refreshInstanceData()
    poe_bot.last_action_time = 0
  # if possible_transition to explore, go to it, run discovery again


# In[ ]:


poe_bot.game_data.terrain.getPassableAreaDiscoveredForPercent(total=True)
mapper.onMapFinishedFunction()


# In[ ]:


print(f'discovery_points {discovery_points}')
mapper.temp.map_streak += 1
mapper.temp.map_completed = True
mapper.temp.save()
end_pos = poe_bot.player_pos
mapper.deactivateDeliriumMirror()


# In[ ]:


mapper.temp.reset()


# In[ ]:


#TODO stash shit


# ''' end of script '''

# In[ ]:


raise Exception('Script ended, restart')


# In[ ]:


plt.imshow(poe_bot.game_data.terrain.passable);plt.show()
plt.imshow(poe_bot.game_data.terrain.currently_passable_area);plt.show()


# In[ ]:


poe_bot.refreshInstanceData()


# In[ ]:


entrance_portal_entity = next( (e for e in poe_bot.game_data.entities.area_transitions_all if e.path == "Metadata/Terrain/Leagues/Incursion/Objects/IncursionPortal1" and e.id not in mapper.temp.alvas_to_ignore_ids) , None)
entrance_portal_entity


# In[ ]:


poe_bot.refreshAll()


# In[ ]:


print('poe_bot.passable')
plt.imshow(poe_bot.game_data.terrain.passable);plt.show()
print('poe_bot.visited_area')
plt.imshow(poe_bot.game_data.terrain.visited_area);plt.show()
# currently_passable_area = poe_bot.generateCurrentlyPassableArea()
# print('currently_passable_area')
# plt.imshow(currently_passable_area);plt.show()
# currently_passable_area_for_discovery = currently_passable_area - poe_bot.visited_area
# print('currently_passable_area_for_discovery')
# plt.imshow(currently_passable_area_for_discovery);plt.show()
print('poe_bot._generateColorfulImage')
game_img = poe_bot.getImage()
print('game_img')
plt.imshow(game_img);plt.show()

pickle_img = game_img
cv2.imwrite('./inventory_and_chest_opened.bmp', game_img)

f = open('./blue_drops.pickle', 'wb')
pickle.dump(pickle_img, f)
f.close()


# In[22]:


poe_bot.refreshAll()


# In[23]:


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
  exit_portal = next( (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Leagues/Incursion/Objects/IncursionPortal2" and e.distance_to_player < 50), None)
  poe_bot.refreshInstanceData()


# In[531]:


import numpy as np

np_arr = np.ones((100,100))


# In[ ]:





# In[541]:


arr = np_arr
pos = 4,4
area = 10
pos_x_min = pos[0]-area
if pos_x_min < 0:
    pos_x_min = 0
pos_x_max = pos[0]+area

pos_y_min = pos[1]-area
pos_y_max = pos[1]+area
arr[0:9999999999, 0:14].shape

