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
  "REMOTE_IP": '172.23.178.57', # z2
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


# In[7]:


poe_bot = Poe2Bot(unique_id = UNIQUE_ID, remote_ip = REMOTE_IP, password=password)
poe_bot.refreshAll()
# poe_bot.game_data.terrain.getCurrentlyPassableArea()



# In[8]:


from utils.loot_filter import PickableItemLabel

ARTS_TO_PICK = [
  "Art/2DItems/Currency/CurrencyModValues.dds",
  "Art/2DItems/Currency/CurrencyGemQuality.dds",
  "Art/2DItems/Currency/CurrencyRerollRare.dds",
  "Art/2DItems/Currency/CurrencyAddModToRare.dds",
  "Art/2DItems/Currency/CurrencyUpgradeToUnique.dds",
  "Art/2DItems/Currency/CurrencyUpgradeToUniqueShard.dds",
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


# In[9]:


# poe_bot.mover.setMoveType('wasd')


# In[10]:


poe_bot.combat_module.build = InfernalistZoomancer(poe_bot=poe_bot)
poe_bot.mover.default_continue_function = poe_bot.combat_module.build.usualRoutine


# In[11]:


rares_detection_radius = 999

def runnerBreakFunction(*args, **kwargs):
  if rares_detection_radius != 0:
    rares_nearby = list(filter(lambda e: e.distance_to_player < rares_detection_radius, poe_bot.game_data.entities.attackable_entities_rares))
    for rare_mob in rares_nearby:
      updated_entity = list(filter(lambda e: e.id == rare_mob.id, poe_bot.game_data.entities.attackable_entities_rares))
      if len(updated_entity) != 0:
        updated_entity = updated_entity[0]
        poe_bot.combat_module.killUsualEntity(updated_entity)
        return True

  loot_collected = poe_bot.loot_picker.collectLoot()
  if loot_collected is True:
    return loot_collected
  return False
  


# In[12]:


from utils.pathing import TSP


tsp = TSP(poe_bot=poe_bot)
# tsp.generatePointsForDiscovery()
mover = poe_bot.mover
map_complete = False
while map_complete is False:
  poe_bot.refreshInstanceData()
  print(f'generating pathing points')
  tsp.generatePointsForDiscovery()
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
    need_to_explore = True
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
  killed_smth = poe_bot.combat_module.clearAreaAroundPoint(poe_bot.game_data.player.grid_pos.toList())
  if killed_smth == False:
    openPortal()
    poe_bot.helper_functions.waitForPortalNearby()
    poe_bot.helper_functions.getToPortal(check_for_map_device=False)
    killed_smth = poe_bot.combat_module.clearAreaAroundPoint(poe_bot.game_data.player.grid_pos.toList())
    if killed_smth:
      continue
    


# In[ ]:


raise 404


# In[14]:


# pos_x, pos_y = random.randint(580,640), random.randint(408,409)
# pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
# time.sleep(random.randint(20,80)/100)
# poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
# time.sleep(random.randint(20,80)/100)
# poe_bot.bot_controls.mouse.click()
# time.sleep(random.randint(30,60)/100)


# In[20]:


poe_bot.refreshInstanceData()


# In[19]:





# In[ ]:





# In[11]:


beetle_entity = next( (e for e in poe_bot.game_data.entities.attackable_entities_rares if e.render_name == "The Ninth Treasure of Keth"), None)
if beetle_entity:
  poe_bot.combat_module.killTillCorpseOrDisappeared(beetle_entity)
else:
  print(f'no entity found')


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


# In[13]:


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


# In[14]:


poe_bot.loot_picker.collectLootWhilePresented()


# In[15]:


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


# In[10]:





# In[ ]:


raise 404


# In[ ]:


poe_bot.refreshAll()


# In[37]:


for e in poe_bot.game_data.entities.all_entities:
  print(e.raw)


# In[17]:


from utils.utils import getAngle


# In[ ]:


poe_bot.refreshAll()


# In[22]:


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

