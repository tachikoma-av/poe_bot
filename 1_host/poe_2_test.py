#!/usr/bin/env python
# coding: utf-8

import time
import random
import sys

from poe2_strategies.helpers.hideout_detector import HideoutDetector
from poe2_strategies.helpers.runner_break_function import RunnerBreaker
from poe2_strategies.map_traverser import MapTraverserStrategy
from poe2_strategies.open_new_map_if_required import OpenNewMapIfRequiredStrategy
from poe2_strategies.return_from_map_to_hideout import ReturnFromMapToHideoutStrategy
from utils.gamehelper import Poe2Bot
from config import Config
from pick_strategy import PickStrategy, PickAllStrategy
from map_selection_strategy import SelectMapToRunStrategy
from poe2_strategies import (
    EnterPortalStrategy,
    CleanInventoryStrategy,
    HideoutPreparations
)
from utils.combat import DonColdMonkBuild

# Initialize configuration
config = Config(sys.argv[1] if len(sys.argv) > 1 else None,
                max_map_lvl=5, # maximum level of map to run. Inclusive
                alch_map_if_possible=True,
                prefer_high_tier=True,
                rares_detection_radius=999
                )

# readability
poe_bot_class = Poe2Bot
poe_bot: poe_bot_class

poe_bot = Poe2Bot(
    unique_id=config.unique_id, 
    remote_ip=config.remote_ip, 
    password=config.password
)
poe_bot.refreshAll()

#
# SETUP COMBAT BUILD
#
poe_bot.combat_module.build = DonColdMonkBuild(poe_bot=poe_bot)
#from utils.combat import PathfinderPoisonConc2
# poe_bot.combat_module.build = InfernalistZoomancer(poe_bot=poe_bot)
#poe_bot.combat_module.build = PathfinderPoisonConc2(poe_bot=poe_bot)

def custom_default_continue_function(*args, **kwargs):
  pass

poe_bot.mover.default_continue_function = poe_bot.combat_module.build.usualRoutine


# 
# Initialize strategies
#


# Initialize pick strategy
# 

#pick_strategy = PickStrategy() # pick only specific items
pick_strategy = PickAllStrategy() # pick all items


poe_bot.loot_picker.loot_filter.special_rules = [pick_strategy.should_pick_item]
if config.alch_map_if_possible:
  pick_strategy.add_art("Art/2DItems/Currency/CurrencyUpgradeToRare.dds")


# Initialize map selection strategy
map_selection_strategy = SelectMapToRunStrategy(
    should_run_bosses=False,
    should_run_towers=False,
    ignored_map_names=["MapAugury_NoBoss",
                       "MapVaalFactory_NoBoss"] # doors + levers = stuck
)

# initialize other strategies
hideout_detector = HideoutDetector(poe_bot)
runner_breaker = RunnerBreaker(poe_bot, config)
map_traverser = MapTraverserStrategy(runnerBreakFunction=runner_breaker.runnerBreakFunction)

# Initialize hideout preparation strategies
hideout_preparations = HideoutPreparations([
            CleanInventoryStrategy(config.prefer_high_tier),
            OpenNewMapIfRequiredStrategy(config, map_selection_strategy),
            EnterPortalStrategy()
        ])

# poe_bot.game_data.terrain.getCurrentlyPassableArea()

# from utils.constants import ESSENCES_KEYWORD
# essences = list(filter(lambda e: e.is_targetable is True and ESSENCES_KEYWORD in e.path and poe_bot.game_data.terrain.checkIfPointPassable(e.grid_position.x, e.grid_position.y), poe_bot.game_data.entities.all_entities))
# essences[0].id


while True:
  poe_bot.refreshAll()

  # if we are in hideout, we need to prepare for the run
  # clean inventory
  # open new map if required
  # enter portal
  if hideout_detector.is_hideout():
      hideout_preparations(poe_bot)
  else:
      print("DEBUG: not in hideout, skipping hideout preparations")

  # Next step is to complete map itself
  map_traverser(poe_bot)

  # And return back to hideout
  ReturnFromMapToHideoutStrategy()(poe_bot)





# %%

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





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





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



# In[18]:


from utils.pathing import TSP


# In[ ]:


tsp = TSP(poe_bot)

tsp.generatePointsForDiscovery()
#TODO astar sorting
discovery_points = tsp.sortedPointsForDiscovery()


# In[ ]:


poe_bot.game_data.player.grid_pos.toList()


# In[ ]:


discovery_points

