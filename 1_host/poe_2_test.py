#!/usr/bin/env python
# coding: utf-8

# In[1]:


import time
import random
import sys
from ast import literal_eval

from utils.gamehelper import Poe2Bot


# In[2]:


from utils.combat import InfernalistZoomancer


# In[3]:


notebook_dev = False
# readability
poe_bot_class = Poe2Bot
poe_bot: poe_bot_class


# In[4]:


default_config = {
  "REMOTE_IP": '172.22.159.221', # z2
  "unique_id": "poe_2_test",
  "build": "EaBallistasEle",
  "password": None,
  "max_lvl": 101,
  "chromatics_recipe": True,
  "force_reset_temp": False,
}



try:
  i = sys.argv[1]
  print(i)
  parsed_config = literal_eval(i)
  print(f'successfully parsed cli config')
  print(f'parsed_config: {parsed_config}')
except:
  print(f'cannot parse config from cli, using default\dev one')
  notebook_dev = True
  parsed_config = default_config
  parsed_config['unique_id'] = poe_bot_class.getDevKey()

config = {

}

for key in default_config.keys():
  config[key] = parsed_config.get(key, default_config[key])

print(f'config to run {config}')


# In[5]:


REMOTE_IP = config['REMOTE_IP'] # REMOTE_IP
UNIQUE_ID = config['unique_id'] # unique id
MAX_LVL = config.get('max_lvl')
CHROMATICS_RECIPE = config['chromatics_recipe']
BUILD_NAME = config['build'] # build_name
password = config['password']
force_reset_temp = config['force_reset_temp']
print(f'running aqueduct using: REMOTE_IP: {REMOTE_IP} unique_id: {UNIQUE_ID} max_lvl: {MAX_LVL} chromatics_recipe: {CHROMATICS_RECIPE} force_reset_temp: {force_reset_temp}')


# In[6]:


poe_bot = Poe2Bot(unique_id = UNIQUE_ID, remote_ip = REMOTE_IP, password=password)
poe_bot.refreshAll()
# poe_bot.game_data.terrain.getCurrentlyPassableArea()



# In[7]:


from utils.loot_filter import PickableItemLabel

ARTS_TO_PICK = [
  "Art/2DItems/Currency/CurrencyModValues.dds", # divine
  "Art/2DItems/Currency/CurrencyGemQuality.dds", # gemcutter
  "Art/2DItems/Currency/CurrencyRerollRare.dds", # chaos
  "Art/2DItems/Currency/CurrencyAddModToRare.dds", # exalt
  "Art/2DItems/Currency/CurrencyUpgradeToUnique.dds", # chance
]

# big piles of gold
for tier in range(2,17):
  ARTS_TO_PICK.append(f"Art/2DItems/Currency/Ruthless/CoinPileTier{tier}.dds")
# waystones
for tier in range(1,17):
  ARTS_TO_PICK.append(f"Art/2DItems/Maps/EndgameMaps/EndgameMap{tier}.dds")

def isItemHasPickableKey(item_label:PickableItemLabel):
  if item_label.icon_render in ARTS_TO_PICK:
    return True
  return False
poe_bot.loot_picker.loot_filter.special_rules = [isItemHasPickableKey]


# In[8]:


# poe_bot.mover.setMoveType('wasd')


# In[9]:


poe_bot.combat_module.build = InfernalistZoomancer(poe_bot=poe_bot)
poe_bot.mover.default_continue_function = poe_bot.combat_module.build.usualRoutine


# In[10]:


# raise 404


# In[11]:


# poe_bot.game_data.terrain.getCurrentlyPassableArea()

# from utils.constants import ESSENCES_KEYWORD
# essences = list(filter(lambda e: e.is_targetable is True and ESSENCES_KEYWORD in e.path and poe_bot.game_data.terrain.checkIfPointPassable(e.grid_position.x, e.grid_position.y), poe_bot.game_data.entities.all_entities))
# essences[0].id


# In[12]:


# poe_bot.backend.getVisibleLabels()


# In[13]:


# raise 404


# In[14]:


rares_detection_radius = 999

def runnerBreakFunction(*args, **kwargs):
  switch_nearby = next( (e for e in poe_bot.game_data.entities.all_entities if e.is_targetable and e.path == "Metadata/Terrain/Maps/Crypt/Objects/CryptSecretDoorSwitch" and e.distance_to_player < 30), None)
  if switch_nearby:
    poe_bot.mover.goToEntitysPoint(switch_nearby)
    poe_bot.combat_module.clearAreaAroundPoint(switch_nearby.grid_position.toList())
    switch_nearby.clickTillNotTargetable()
    return True

  if rares_detection_radius != 0:
    rares_nearby = list(filter(lambda e: e.distance_to_player < rares_detection_radius, poe_bot.game_data.entities.attackable_entities_rares))
    for rare_mob in rares_nearby:
      updated_entity = list(filter(lambda e: e.id == rare_mob.id, poe_bot.game_data.entities.attackable_entities_rares))
      if len(updated_entity) != 0:
        updated_entity = updated_entity[0]
        poe_bot.mover.goToEntitysPoint(updated_entity, min_distance=50)
        poe_bot.combat_module.killUsualEntity(updated_entity)
        return True

  loot_collected = poe_bot.loot_picker.collectLoot()
  if loot_collected is True:
    return loot_collected
  return False
  


# In[15]:


# raise 404
poe_bot.refreshAll()


# In[16]:


prefer_high_tier = True
alch_map_if_possible = True

# free inventory if neededS
poe_bot.ui.inventory.update()
empty_slots = poe_bot.ui.inventory.getEmptySlots()
if len(empty_slots) < 40:
  poe_bot.ui.stash.open()
  items_to_keep = []
  poe_bot.ui.inventory.update()
  waystones_to_keep = list(filter(lambda i: i.map_tier, poe_bot.ui.inventory.items))
  waystones_to_keep.sort(key=lambda i: i.map_tier, reverse=prefer_high_tier)
  items_to_keep.extend(waystones_to_keep[:4])
  alchemy_orbs = list(filter(lambda i: i.name == "Orb of Alchemy", poe_bot.ui.inventory.items))
  items_to_keep.extend(alchemy_orbs[:1])
  items_can_stash = list(filter(lambda i: i not in items_to_keep, poe_bot.ui.inventory.items))
  poe_bot.ui.clickMultipleItems(items_can_stash)
  poe_bot.ui.closeAll()
  time.sleep(random.uniform(0.3, 1.4))

# open map device
poe_bot.refreshInstanceData()
map_device_entity = next( (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Missions/Hideouts/Objects/MapDeviceVariants/ZigguratMapDevice"), None)
map_device_entity.hover()
poe_bot.refreshInstanceData()
map_device_entity = next( (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Missions/Hideouts/Objects/MapDeviceVariants/ZigguratMapDevice"), None)
if map_device_entity.is_targeted == True:
  print('targeted')
  map_device_entity.click()
  _i = 0
  while True:
    _i += 1
    if _i == 100:
      poe_bot.raiseLongSleepException('cannot open map device')

    poe_bot.ui.map_device.update()
    if poe_bot.ui.map_device.is_opened == True:
      break
    time.sleep(random.uniform(1.3, 1.4))
  time.sleep(random.uniform(1.3, 1.4))
else:
  poe_bot.raiseLongSleepException("couldnt target map device, restart or debug")
# move to map, open dropdown
poe_bot.ui.map_device.update()
possible_to_run_maps = list(filter(lambda m: 
  m.is_boss == False and # some bosses have unique logic?
  m.is_tower == False and# cant run tower maps yet
  m.name_raw != 'MapAugury_NoBoss' # activators
, poe_bot.ui.map_device.avaliable_maps))
map_obj = random.choice(possible_to_run_maps)
print(map_obj.raw)
poe_bot.ui.map_device.moveScreenTo(map_obj)
time.sleep(random.uniform(0.15, 0.35))


poe_bot.ui.map_device.update()
for i in range(3):
  updated_map_obj = next( (m for m in poe_bot.ui.map_device.avaliable_maps if m.id == map_obj.id))
  time.sleep(random.uniform(0.15, 0.35))
  updated_map_obj.hover()
  time.sleep(random.uniform(0.15, 0.35))
  updated_map_obj.click(hover=False)
  time.sleep(random.uniform(0.15, 0.35))
  poe_bot.ui.map_device.update()

  if poe_bot.ui.map_device.place_map_window_opened == True:
    break
if poe_bot.ui.map_device.place_map_window_opened != True:
  poe_bot.raiseLongSleepException("cant open dropdown for map device")




# In[17]:


poe_bot.ui.inventory.update()
maps_in_inventory = list(filter(lambda i: i.map_tier, poe_bot.ui.inventory.items))
maps_in_inventory.sort(key=lambda i: i.map_tier, reverse=prefer_high_tier)
map_to_run = maps_in_inventory[0]
print(f'placing map {map_to_run.raw}')

if alch_map_if_possible == True:
  ARTS_TO_PICK.append("Art/2DItems/Currency/CurrencyUpgradeToRare.dds")
  for _i in range(1):
    if map_to_run.rarity != "Normal":
      break
    alchemy_orbs = list(filter(lambda i: i.name == "Orb of Alchemy", poe_bot.ui.inventory.items))
    if len(alchemy_orbs) == 0:
      break
    alchemy_orb = alchemy_orbs[0]
    alchemy_orb.click(button="right")
    time.sleep(random.uniform(0.4, 1.2))
    map_to_run.click()
    time.sleep(random.uniform(0.8, 1.2))

map_to_run.click(hold_ctrl=True)
poe_bot.ui.map_device.update()
#TODO sometimes activate button is outside roi
poe_bot.ui.map_device.checkIfActivateButtonIsActive()


# In[18]:


poe_bot.ui.map_device.activate()

time.sleep(random.uniform(0.8, 1.6))
poe_bot.helper_functions.waitForNewPortals()

poe_bot.refreshInstanceData()
try:
  poe_bot.helper_functions.getToPortal(check_for_map_device=False)
except Exception as e:
  if e.__str__() == 'Portal is too far away':
    print(f'portal became too far away')
    original_area_name = poe_bot.game_data.area_raw_name
    _i = 0
    while True:
      _i += 1
      if _i == 100:
        poe_bot.raiseLongSleepException('coudlnt get to portal')
      poe_bot.refreshAll()
      
      if poe_bot.game_data.area_raw_name != original_area_name:
        break

  else:
    print(e.__str__())
    raise Exception('smth happened on getToPortal')


# In[19]:


# raise 404


# In[ ]:


from utils.pathing import TSP


tsp = TSP(poe_bot=poe_bot)
# tsp.generatePointsForDiscovery()
mover = poe_bot.mover
map_complete = False
while map_complete is False:
  poe_bot.refreshInstanceData()
  print(f'generating pathing points')
  tsp.generatePointsForDiscovery()
  #TODO astar sorting
  discovery_points = tsp.sortedPointsForDiscovery()
  print(f'len(discovery_points) {len(discovery_points)}')
  discovery_points = list(filter(lambda p: poe_bot.game_data.terrain.checkIfPointPassable(p[0], p[1]), discovery_points))
  print(f'len(discovery_points) {len(discovery_points)} after sorting')
  print(f'discovery_points {discovery_points}')
  if len(discovery_points) == 0:
    print(f'len(discovery_points) == 0 after points generation')
    map_complete = True
    break
  point_to_go = discovery_points.pop(0)
  while point_to_go is not None:
    need_to_explore = poe_bot.helper_functions.needToExplore(point_to_go=point_to_go)
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
      custom_break_function=runnerBreakFunction,
      step_size=random.randint(30,35)
    )
    # then, it result is True, False or None
    print(f"mover.goToPoint result {result}")


    # if we arrived to discovery point and nothing happened
    if result is None:
      while True:
        if len(discovery_points) == 0:
          point_to_go = None
          map_complete = True
          print(f'len(discovery_points) == 0, breaking')
          break

        point_to_go = discovery_points.pop(0)
        print(f'willing to explore next point {point_to_go}')
        need_to_explore = poe_bot.helper_functions.needToExplore(point_to_go=point_to_go)

        if need_to_explore is True:
          print(f'exploring point {point_to_go}')
          break
        else:
          print(f'surrounding around {point_to_go} discovered, skipping')
          continue
    
    # if explorer_break_function() is True:
    #   map_complete = True
    #   break

    poe_bot.refreshInstanceData()
    poe_bot.last_action_time = 0
  # if possible_transition to explore, go to it, run discovery again


# In[ ]:


# open portal and enter it
def openPortal():
  poe_bot.bot_controls.releaseAll()

  time.sleep(random.randint(40,80)/100)
  pos_x, pos_y = random.randint(709,711), random.randint(694,696)
  pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y, safe=False)
  poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
  time.sleep(random.randint(40,80)/100)
  poe_bot.bot_controls.mouse.click()
  time.sleep(random.randint(30,60)/100)

while True:
  try:
    poe_bot.refreshInstanceData()
    killed_smth = poe_bot.combat_module.clearAreaAroundPoint(poe_bot.game_data.player.grid_pos.toList())
    if killed_smth == False:
      openPortal()
      poe_bot.helper_functions.waitForPortalNearby()
      poe_bot.helper_functions.getToPortal(check_for_map_device=False, refresh_area=False)
      poe_bot.refreshInstanceData()
      killed_smth = poe_bot.combat_module.clearAreaAroundPoint(poe_bot.game_data.player.grid_pos.toList())
      if killed_smth:
        continue
  except Exception as e:
    if e.__str__() == 'Area changed but refreshInstanceData was called before refreshAll':
      time.sleep(5)
      break
    


# In[ ]:


raise 404


# In[24]:


prefer_high_tier = True


# In[19]:


poe_bot.refreshAll()


# In[ ]:





# In[ ]:





# In[ ]:


# pos_x, pos_y = random.randint(580,640), random.randint(408,409)
# pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
# time.sleep(random.randint(20,80)/100)
# poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
# time.sleep(random.randint(20,80)/100)
# poe_bot.bot_controls.mouse.click()
# time.sleep(random.randint(30,60)/100)


# In[ ]:


start_time = time.time()

def destroyCorpse(corpse_entity:Entity):
  print(f'destroying corpse {corpse_entity.raw}')
  while True:
    poe_bot.refreshInstanceData()
    updated_corpse_entity = next( (e for e in poe_bot.game_data.entities.all_entities if e.id == corpse_entity.id), None)
    if updated_corpse_entity:
      if updated_corpse_entity.distance_to_player > 25:
        poe_bot.mover.goToEntitysPoint(updated_corpse_entity)
      else:
        if poe_bot.combat_module.build.detonate_dead:
          if poe_bot.combat_module.build.detonate_dead.use(updated_entity=updated_corpse_entity, force=True) != False:
            continue
        if poe_bot.combat_module.build.unearth and poe_bot.combat_module.build.unearth.canUse():
          if poe_bot.combat_module.build.unearth.use(updated_entity=updated_corpse_entity) != False:
            continue
    else:
      break
beetle_corpse = next( (e for e in poe_bot.game_data.entities.all_entities if e.render_name == "The Ninth Treasure of Keth"), None)
if beetle_corpse:
  destroyCorpse(beetle_corpse)


# In[ ]:


entity_to_run_around = None
if beetle_corpse:
  print(f'running around corpse {beetle_corpse}')
  entity_to_run_around = beetle_corpse
elif beetle_entity:
  print(f'running around entity {beetle_entity}')

  entity_to_run_around = beetle_entity

if entity_to_run_around:
  start_time = time.time()
  run_duration_seconds = 5
  end_at = start_time + run_duration_seconds
  kite_distance = 10
  reversed_run = random.choice([True, False])
  while time.time() < end_at:
    poe_bot.refreshInstanceData()
    poe_bot.combat_module.build.auto_flasks.useFlasks()  
    print('kiting')
    point = poe_bot.game_data.terrain.pointToRunAround(entity_to_run_around.grid_position.x, entity_to_run_around.grid_position.y, kite_distance+random.randint(-1,1), check_if_passable=True, reversed=reversed_run)
    poe_bot.mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
else:
  poe_bot.refreshInstanceData()


# In[ ]:


poe_bot.loot_picker.collectLootWhilePresented()


# In[ ]:


def respawnAtCheckPoint():
  poe_bot.bot_controls.keyboard.tap('DIK_ESCAPE')
  time.sleep(random.randint(40,80)/100)
  pos_x, pos_y = random.randint(450,550), random.randint(289,290)
  pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
  poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
  time.sleep(random.randint(40,80)/100)
  poe_bot.bot_controls.mouse.click()
  time.sleep(random.randint(30,60)/100)

  pos_x, pos_y = random.randint(580,640), random.randint(408,409)
  pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
  time.sleep(random.randint(20,80)/100)
  poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
  time.sleep(random.randint(20,80)/100)
  poe_bot.bot_controls.mouse.click()
  time.sleep(random.randint(30,60)/100)
  return True
poe_bot.bot_controls.releaseAll()
respawnAtCheckPoint()
while True:
  poe_bot.refreshInstanceData()
  beetle_entity = next( (e for e in poe_bot.game_data.entities.all_entities if e.render_name == "The Ninth Treasure of Keth"), None)
  if beetle_entity:
    break


# In[ ]:


raise 404


# In[ ]:


poe_bot.refreshInstanceData()
poe_bot.loot_picker.collectLoot()


# In[ ]:





# In[17]:


from utils.utils import getAngle


# In[ ]:


poe_bot.refreshAll()


# In[ ]:


poe_bot.refreshInstanceData()
map_device_entity = next( (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Missions/Hideouts/Objects/MapDeviceVariants/ZigguratMapDevice"), None)
map_device_entity.hover()
poe_bot.refreshInstanceData()
map_device_entity = next( (e for e in poe_bot.game_data.entities.all_entities if e.path == "Metadata/Terrain/Missions/Hideouts/Objects/MapDeviceVariants/ZigguratMapDevice"), None)
if map_device_entity.is_targeted == True:
  print('targeted')
  map_device_entity.click()


# In[ ]:


import time
while True:
  time.sleep(0.2)
  poe_bot.refreshInstanceData()
  player_pos = poe_bot.game_data.player.grid_pos.toList()
  p1 = player_pos
  p0 = (player_pos[0], player_pos[1]+50)

  for e in poe_bot.game_data.entities.all_entities:
    if e.id != 11:
      continue
    print(e.raw)
    print(getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True))


# In[ ]:





# In[ ]:


poe_bot.refreshAll()
poe_bot.bot_controls.releaseAll()

our_pos = [poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y]
# entity pos
pos_x, pos_y = poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y

distance_to_point = 45

reversed = True
check_if_passable = True


# In[ ]:


import time
from math import dist

while True:
  time.sleep(0.2)
  poe_bot.refreshInstanceData()

  our_pos = [poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y]
  points_around = [
    [pos_x+distance_to_point,pos_y], # 90
    [int(pos_x+distance_to_point*0.7),int(pos_y-distance_to_point*0.7)], # 45
    [pos_x,pos_y-distance_to_point], # 0
    [int(pos_x-distance_to_point*0.7),int(pos_y-distance_to_point*0.7)], # 315
    [pos_x-distance_to_point,pos_y], # 270
    [int(pos_x-distance_to_point*0.7),int(pos_y+distance_to_point*0.7)], # 215
    [pos_x,pos_y+distance_to_point], # 180
    [int(pos_x+distance_to_point*0.7),int(pos_y+distance_to_point*0.7)], # 135
  ]
  if reversed is True:
    points_around.reverse()
  distances = list(map(lambda p: dist(our_pos, p),points_around))
  nearset_pos_index = distances.index(min(distances))
  distances = list(map(lambda p: dist(our_pos, p),points_around))
  nearset_pos_index = distances.index(min(distances))
  # TODO check if next point is passable
  current_pos_index = nearset_pos_index+1
  if current_pos_index > len(points_around)-1: current_pos_index -= len(points_around)
  point = points_around[current_pos_index]
  if check_if_passable is True:
    if poe_bot.game_data.terrain.checkIfPointPassable(point[0], point[1], radius=1) is False:
      start_index = current_pos_index+1
      point_found = False
      for i in range(len(points_around)-2):
        current_index = start_index + i
        if current_index > len(points_around)-1: current_index -= len(points_around)
        point = points_around[current_index]
        if poe_bot.game_data.terrain.checkIfPointPassable(point[0], point[1], radius=1) is True:
          point_found = True
          break
      if point_found is True:
        pass
  print(point)
  poe_bot.mover.move(point[0], point[1])


# In[ ]:


# move back or move to safe grid if enemies on a way
# map device
poe_bot.ui.map_device.update()


# In[13]:


from utils.ui import MapDevice_Poe2
poe_bot.ui.map_device = MapDevice_Poe2(poe_bot)
poe_bot.ui.map_device.update()


# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:


raise 404


# In[ ]:


from utils.utils import sortByHSV
x1 = poe_bot.ui.map_device.activate_button_pos.x1 +5
x2 = poe_bot.ui.map_device.activate_button_pos.x2 -5
y1 = poe_bot.ui.map_device.activate_button_pos.y1 +5
y2 = poe_bot.ui.map_device.activate_button_pos.y2 -5
game_img = poe_bot.getImage()
activate_button_img = game_img[y1:y2, x1:x2]
# print('activate_button_img')
# plt.imshow(activate_button_img);plt.show()
# plt.imshow(third_skill);plt.show()
sorted_img = sortByHSV(activate_button_img, 0, 0, 0, 255, 30, 180)
# plt.imshow(sorted_img);plt.show()
activate_button_is_active = not len(sorted_img[sorted_img != 0]) > 30
# print(sorted_img[sorted_img != 0])
print(f"activate_button_is_active {activate_button_is_active}")


# In[ ]:


x1 = poe_bot.ui.map_device.activate_button_pos.x1 +5
x2 = poe_bot.ui.map_device.activate_button_pos.x2 -5
y1 = poe_bot.ui.map_device.activate_button_pos.y1 +5
y2 = poe_bot.ui.map_device.activate_button_pos.y2 -5
game_img = poe_bot.getImage()
active_button = game_img[y1:y2, x1:x2]


# In[ ]:


x1 = poe_bot.ui.map_device.activate_button_pos.x1 +5
x2 = poe_bot.ui.map_device.activate_button_pos.x2 -5
y1 = poe_bot.ui.map_device.activate_button_pos.y1 +5
y2 = poe_bot.ui.map_device.activate_button_pos.y2 -5
game_img = poe_bot.getImage()
inactive_button = game_img[y1:y2, x1:x2]


# In[ ]:


active_sorted_img = sortByHSV(active_button, 0,0,0, 255, 30, 180)
plt.imshow(active_sorted_img);plt.show()
inactive_sorted_img = sortByHSV(inactive_button, 0,0,0, 255, 30, 180)
plt.imshow(inactive_sorted_img);plt.show()


# In[ ]:


raise 404


# In[ ]:


from utils.ui import MapDevice_Poe2
poe_bot.ui.map_device = MapDevice_Poe2(poe_bot)
poe_bot.ui.map_device.update()
map_obj = random.choice(poe_bot.ui.map_device.avaliable_maps)
print(map_obj.raw)
poe_bot.ui.map_device.moveScreenTo(map_obj)
time.sleep(random.uniform(0.15, 0.35))
poe_bot.ui.map_device.update()
updated_map_obj = next( (m for m in poe_bot.ui.map_device.avaliable_maps if m.id == map_obj.id))
time.sleep(random.uniform(0.15, 0.35))
updated_map_obj.hover()
time.sleep(random.uniform(0.15, 0.35))
updated_map_obj.click()


# In[ ]:


poe_bot.ui.map_device.update()
updated_map_obj = next( (m for m in poe_bot.ui.map_device.avaliable_maps if m.id == map_obj.id))
time.sleep(random.uniform(0.15, 0.35))
updated_map_obj.hover()
time.sleep(random.uniform(0.15, 0.35))
updated_map_obj.click()


# In[ ]:


poe_bot.ui.map_device.update()
# find a map to go
# for map_obj in poe_bot.ui.map_device.avaliable_maps[0:1]:
map_obj = random.choice(poe_bot.ui.map_device.avaliable_maps)
print(f'going to drag to {map_obj.id}')
orig_id = map_obj.id
while True:
  poe_bot.ui.map_device.update()
  if poe_bot.ui.map_device.is_opened == False:
    raise poe_bot.raiseLongSleepException('map device closed during dragging to map object')
  map_obj = next( (m for m in poe_bot.ui.map_device.avaliable_maps if m.id == orig_id))

  poe_bot.ui.inventory.update()
  x_center = poe_bot.game_window.center_point[0]
  borders = poe_bot.game_window.borders[:]
  borders[2] = 80
  if poe_bot.ui.inventory.is_opened:
    borders[1] = 545
    x_center = int(x_center)/2
  roi_borders = [
    int((borders[0] + borders[1])/2 - 100),
    int((borders[0] + borders[1])/2 + 100),
    int((borders[2] + borders[3])/2 - 150),
    int((borders[2] + borders[3])/2 + 50),
  ]

  if poe_bot.game_window.isInRoi(map_obj.screen_pos.x, map_obj.screen_pos.y, custom_borders=roi_borders):
    break
  print(f"map_obj.screen_pos {map_obj.screen_pos.toList()}")
  drag_from = poe_bot.game_window.convertPosXY(map_obj.screen_pos.x, map_obj.screen_pos.y, custom_borders=borders)
  # ignore the inventory panel if it's opened
  if poe_bot.ui.inventory.is_opened == True:
    print('inventory is opened, different borders and roi')
  drag_to = poe_bot.game_window.convertPosXY(x_center, poe_bot.game_window.center_point[1], custom_borders=borders)
  poe_bot.bot_controls.mouse.drag(drag_from, drag_to)
  time.sleep(random.uniform(0.15, 0.35))
# map_obj.click()
# time.sleep(random.uniform(0.15, 0.35))


# In[ ]:


poe_bot.refreshAll()


# In[ ]:


player_pos = poe_bot.game_data.player.grid_pos.toList()
pos_to_go = [player_pos[0]+3, player_pos[1]-50]
print(player_pos, pos_to_go)


# In[ ]:


from utils.utils import angleOfLine, pointOnCircleByAngleAndLength, createLineIteratorWithValues

def findBackwardsPoint(current_point, point_to_go):
  next_angle = angleOfLine(current_point, point_to_go)
  distance = math.dist(current_point, point_to_go)
  backwards_angle_raw = next_angle - 180
  if backwards_angle_raw < 0:
    backwards_angle_raw += 360
  if backwards_angle_raw == 360:
    backwards_angle_raw = 0
  angle_mult = backwards_angle_raw // 45
  angle_leftover = backwards_angle_raw % 45
  if angle_leftover > 22.5:
    angle_mult += 1

  backwards_angle = int(angle_mult * 45)
  if backwards_angle == 360:
    backwards_angle = 0
  backwards_angle
  backwards_angles = [backwards_angle]
  for _i in [-1,1]:
    branch = backwards_angle + 45 * _i
    if branch < 0:
      branch += 360
    if branch > 360:
      branch -= 360
    if branch == 360:
      branch = 0
    backwards_angles.append(branch)

  furthest_point = current_point
  furthest_point_distance = 0
  for angle in backwards_angles:
    line_end = pointOnCircleByAngleAndLength(angle, distance, current_point)
    line_points_vals = createLineIteratorWithValues(current_point, line_end, poe_bot.game_data.terrain.passable)
    length = 0
    last_point = line_points_vals[0]
    for point in line_points_vals:
      if point[2] != 1:
        break
      last_point = point 
      length += 1
    dist_to_last_point = math.dist(current_point, (last_point[0], last_point[1]))
    if furthest_point_distance < dist_to_last_point:
      furthest_point_distance = dist_to_last_point
      furthest_point = [int(last_point[0]), int(last_point[1])]
    print(f"angle {angle} {length}, {last_point}, {dist_to_last_point}")
  return furthest_point
findBackwardsPoint(player_pos, pos_to_go)

