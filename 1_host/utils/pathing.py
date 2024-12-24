from __future__ import annotations
import typing
from typing import List

if typing.TYPE_CHECKING:
  from .gamehelper import PoeBot

from utils.utils import pointOnCircleByAngleAndLength, createLineIteratorWithValues, angleOfLine

import pyastar2d
import numpy as np
import random
import time
import copy
import cv2
from math import dist
import matplotlib.pyplot as plt

class Pather:
  poe_bot:PoeBot
  debug:bool
  last_generated_path = np.ndarray #nparray [[y,x]]
  terrain_for_a_star:np.ndarray # nparray2d

  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot
    self.debug = poe_bot.debug
    self.utils = Utils()

  def refreshWeightsForAStar(self, terrain_image:np.ndarray, random_val = 1, ):
    '''
    48 - 0
    49 - 1
    50 - 2
    51 - 3
    52 - 4
    53 - 5
    
    '''
    random_val = 1
    self.terrain_for_a_star = terrain_image.copy()
    self.terrain_for_a_star = self.terrain_for_a_star.astype(np.float32)
    unpassable_weight = 65534
    # self.terrain_for_a_star[self.terrain_for_a_star < 52] = 65534 # 0
    # self.terrain_for_a_star[self.terrain_for_a_star < 51] = 65534 # 0
    self.terrain_for_a_star[self.terrain_for_a_star < 50] = unpassable_weight # 0

    random_val = random.randint(1,1)

    if random_val == 1:
      self.terrain_for_a_star[self.terrain_for_a_star == 50] = 4 # 2
      self.terrain_for_a_star[self.terrain_for_a_star == 51] = 3 # 2
      self.terrain_for_a_star[self.terrain_for_a_star == 52] = 2 # 3
      self.terrain_for_a_star[self.terrain_for_a_star == 53] = 1 # 4
      self.terrain_for_a_star[self.terrain_for_a_star == 54] = 0.05 # 5
      self.terrain_for_a_star[self.terrain_for_a_star == 55] = 0.01 # 6
    elif random_val == 2:
      # self.terrain_for_a_star[self.terrain_for_a_star == 51] = 7 # 2
      self.terrain_for_a_star[self.terrain_for_a_star == 52] = 4 # 3
      self.terrain_for_a_star[self.terrain_for_a_star == 53] = 2 # 4
      self.terrain_for_a_star[self.terrain_for_a_star == 54] = 1 # 5
      self.terrain_for_a_star[self.terrain_for_a_star == 55] = 0.3 # 6
    else:
      # self.terrain_for_a_star[self.terrain_for_a_star == 51] = 2 + random.randint(-random_val,random_val)/10 # 2
      self.terrain_for_a_star[self.terrain_for_a_star == 52] = 2 + random.randint(-random_val,random_val)/10 # 3
      self.terrain_for_a_star[self.terrain_for_a_star == 53] = 2 + random.randint(-random_val,random_val)/10 # 4
      self.terrain_for_a_star[self.terrain_for_a_star == 54] = 2 + random.randint(-random_val,random_val)/10 # 5
      self.terrain_for_a_star[self.terrain_for_a_star == 55] = 2 + random.randint(-random_val,random_val)/10 # 6

  def cropPath(self,path, area_x = 25, area_y = 25, max_path_length = 100, extra_points_count = 4, *args, **kwargs):
    '''
    supposed to crop the path in radius, and if the path is getting interrupted, it'll crop it till the break

    # TODO make it as ellipse rather than circle or 
    
    '''
    current_pos_x = self.poe_bot.game_data.player.grid_pos.x
    current_pos_y = self.poe_bot.game_data.player.grid_pos.y

    cropped_path = []
    if len(path) == 0:
      return cropped_path

    for point_index in range(len(path))[::-1]:
      point = path[point_index]
      # print(f'[pather] point {point} {point_index} checking')
      if dist( (point[0], point[1]), (current_pos_y, current_pos_x)) < area_x:
        # print(f'[pather] point {point} {point_index} is in radius')
        reachable = self.poe_bot.game_data.terrain.checkIfPointIsInLineOfSight(grid_pos_y=point[0], grid_pos_x=point[1])
        if reachable != False:
          # print(f'[pather] point {point} {point_index} is reachable')
          path_part = path[point_index:point_index+1+extra_points_count]
          # print(f'[pather] path part {path_part}')
          return path_part
      else:
        continue

    print('[Pather] cant find point in los')
    return cropped_path
  
  def findBackwardsPoint(self, current_point, point_to_go, branches_width = 3):
    if branches_width > 3:
      branches_width = 3
    next_angle = angleOfLine(current_point, point_to_go)
    distance = dist(current_point, point_to_go)
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
    backwards_angles = [backwards_angle]
    backwards_values = [1]

    branch_multipliers = []
    for _i in range(1, branches_width + 1):
      branch_multipliers.append(_i)
      branch_multipliers.append(-_i)
      move_val = 1 * 0.75 ** _i 
      backwards_values.append(move_val)
      backwards_values.append(move_val)

    for _i in branch_multipliers:
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
    furthest_point_val = 0
    for angle_index in range(len(backwards_angles)):
      angle = backwards_angles[angle_index]
      angle_mult = backwards_values[angle_index]
      line_end = pointOnCircleByAngleAndLength(angle, distance, current_point)
      line_points_vals = createLineIteratorWithValues(current_point, line_end, self.poe_bot.game_data.terrain.passable)
      length = 0
      last_point = line_points_vals[0]
      for point in line_points_vals:
        if point[2] != 1:
          break
        last_point = point 
        length += 1
      dist_to_last_point = dist(current_point, (last_point[0], last_point[1]))
      last_point_val = dist_to_last_point * angle_mult
      # if furthest_point_distance < dist_to_last_point:
      
      if furthest_point_val < last_point_val:
        furthest_point_val = last_point_val
        furthest_point_distance = dist_to_last_point
        furthest_point = [int(last_point[0]), int(last_point[1])]
      print(f"angle {angle}, {angle_mult}, {length}, {last_point}, {dist_to_last_point}, {last_point_val}")
    return furthest_point

  def generatePath(self, start, end, randomize_points = False, random_val = 1):
    '''
    - start (y,x)
    - end (y,x)
    - returns: [[y,x], [y,x], [y,x], [y,x]]
    '''
    if self.debug: print(f'#generatePath {start} {end} call {time.time()}')
    # TODO randomize points and val


    # The minimum cost must be 1 for the heuristic to be valid.
    # The weights array must have np.float32 dtype to be compatible with the C++ code.
    # The start and goal coordinates are in matrix coordinates (i, j).

    # path = pyastar2d.astar_path(self.terrain_for_a_star, (int(player_pos['Y']), int(player_pos['X'])), (int(interesting_entity_grid_pos['Y']), int(interesting_entity_grid_pos['X'])), allow_diagonal=False)
    path = pyastar2d.astar_path(self.terrain_for_a_star, start, end, allow_diagonal=False)
    self.last_generated_path = path
    # print(path)
    # The path is returned as a numpy array of (i, j) coordinates.
    # array([[0, 0],
    #        [1, 1],
    #        [2, 2],
    #        [3, 3],

    if self.debug: print(f'#generatePath return {time.time()}')
    return path
  
class Utils:
  def getFurthestPoint(self, start, area):
    data = np.where(area != 0)
    passable_points = list(zip(data[1], data[0]))
    max_distance = 0
    furthest_unvisited = (0,0)
    for point in passable_points:
      distance = dist([point[0], point[1]], start)
      if distance > max_distance:
        max_distance = distance
        furthest_unvisited = point
    return furthest_unvisited
  def getPointOnArea(self, area:np.ndarray, point_key:str):
    '''
    1 2 3
    4 5 6
    7 8 9
    
    5 - center
    -5 furthest from center

    2 northest
    -2 furthest from northest 

    '''
    data = np.where(area != 0)
    passable_points = list(zip(data[1], data[0])) # [[x,y]]
    funcs = {
      "2": lambda: min(passable_points, key=lambda p: p[1]), # 0*
      "8": lambda: max(passable_points, key=lambda p: p[1]), # 180*
      
      "6": lambda: max(passable_points, key=lambda p: p[0]), # 90*
      "4": lambda: min(passable_points, key=lambda p: p[0]), # 270*

      "1": lambda: min(passable_points, key=lambda p: p[0] + p[1]), # 315*
      "9": lambda: max(passable_points, key=lambda p: p[0] + p[1]), # 135*

      "3": lambda: max(passable_points, key=lambda p: p[0] - p[1]), # 45*
      "7": lambda: max(passable_points, key=lambda p: p[1] - p[0]), # 225*

      "5": lambda: self.getCenterOf(area)
    }
    point:tuple[int,int] = funcs[point_key]()

    if "-" in point_key:
      point = self.getFurthestPoint(point, area)
    return point

  def getCenterOf(self, area):
    '''
    [x,y]
    '''
    data = np.where(area != 0)
    point = [int( (min(data[1]) + max(data[1]))/2), int( (min(data[0]) + max(data[0]))/2)] 
    return point
class TSP:
  poe_bot:PoeBot
  points_for_discovery: list # [ [x,y], [x,y] ] unordered
  tsp_points: list # [ [x,y], [x,y] ] ordered
  def __init__(self, poe_bot:PoeBot) -> None:
    self.poe_bot = poe_bot

  def generatePointsForDiscovery(self, discovery_radius = 155, debug = False):
    poe_bot = self.poe_bot
    points_for_discovery = [] # [ [x,y], [x,y]]

    currently_passable_area = poe_bot.game_data.terrain.getCurrentlyPassableArea()
    #  erode, to remove small areas, corners\edges, tiny routes
    kernel_size = 18 # 5 is too low, 20 is kinda ok, 25 looks the best
    kernel = np.ones((kernel_size,kernel_size),np.uint8)
    currently_passable_area = cv2.erode(currently_passable_area,kernel,iterations = 1)

    visited_area_copy = copy.copy(poe_bot.game_data.terrain.visited_area)
    if debug is True: plt.imshow(currently_passable_area);plt.show()
    kernel_sizes = [250,200,150,100,75,50,25,13,7]
    kernel_size = kernel_sizes.pop(0)
    print(time.time())
    #TODO stucks somewhere here
    while len(kernel_sizes):
      currently_passable_area_for_discovery = copy.copy(currently_passable_area)
      currently_passable_area_for_discovery[visited_area_copy > 1] = [0]
      kernel = np.ones((kernel_size,kernel_size),np.uint8)
      erosion = cv2.erode(currently_passable_area_for_discovery,kernel,iterations = 1)
      if debug is True: plt.imshow(visited_area_copy);plt.show()
      if debug is True: plt.imshow(erosion);plt.show()

      # start:TODO to remove?
      targets = []
      (contours, hierarchy) = cv2.findContours(
        erosion, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      targets = [] # (x,y)
      for c in contours:
          if cv2.contourArea(c) > 1:
              x, y, w, h = cv2.boundingRect(c)
              target = (int(x + w / 2), int(y + h / 2))
              targets.append(target)
      # end:TODO to remove?
      
      chosen_point = (0,0) # [x,y]


      if len(targets) == 1:
        # print(f'using contour method')
        chosen_point = (targets[0][0], targets[0][1])
        
      else:
        # print('using random method')
        data = np.where(erosion == 1)
        passable_points = list(zip(data[1], data[0]))
        if len(passable_points) != 0:
          # print('random method worked')
          if random.randint(1,2) == 1:
            chosen_point = (passable_points[0][0], passable_points[0][1])
          else:
            chosen_point = (passable_points[-1][0], passable_points[-1][1])
      
      # if no point found, lower kernel size
      if chosen_point[0] == 0 and len(kernel_sizes):
        kernel_size = kernel_sizes.pop(0)
        continue
      
      points_for_discovery.append( chosen_point )
      cv2.circle(visited_area_copy, chosen_point, discovery_radius, 127, -1)

    self.points_for_discovery = points_for_discovery
    return points_for_discovery
  def generateSortedPointsForBossRush(self, debug = False):
    poe_bot = self.poe_bot
    sorted_points_to_explore = []
    currently_passable_area = poe_bot.game_data.terrain.getCurrentlyPassableArea()
    currently_passable_area_for_discovery = copy.copy(currently_passable_area)
    currently_passable_area_for_discovery[poe_bot.game_data.terrain.visited_area > 1] = [0]
    if debug: plt.imshow(currently_passable_area_for_discovery)
    data = np.where(currently_passable_area_for_discovery == 1)
    passable_points = list(zip(data[1], data[0])) # [[x,y]]
    most_0_degree_points = sorted(passable_points, key=lambda p: p[1])
    most_270_degree_points = sorted(passable_points, key=lambda p: p[0])
    most_315_degree_points = sorted(passable_points, key=lambda p: p[0] + p[1])
    most_225_degree_points = sorted(passable_points, key=lambda p: p[0] - p[1])
    points_to_explore = []

    try:
      points = {
        "0": most_0_degree_points[0],
        "45": most_225_degree_points[-1],
        "90": most_270_degree_points[0],
        "135": most_315_degree_points[-1],
        "180": most_0_degree_points[-1],
        "225": most_225_degree_points[0],
        "270": most_270_degree_points[-1],
        "315": most_315_degree_points[0],
      }
    except Exception:
      return sorted_points_to_explore
    # exclude duplicates
    for key in points.keys():
      point = points[key] 
      if point not in points_to_explore:
        # cv2.circle(visited_area_copy, chosen_point, discovery_radius, 127, -1)
        points_to_explore.append(point)
    if debug: print(points_to_explore)

    furthest_point = [0,0] # [x,y]
    furthest_point_steps = 0
    for point in points_to_explore:
      path = poe_bot.pather.generatePath(
        (poe_bot.game_data.player.grid_pos.y, poe_bot.game_data.player.grid_pos.x),
        (point[1], point[0])
      )
      path_length = len(path)
      if furthest_point_steps < path_length:
        furthest_point = point
        furthest_point_steps = path_length

    current_pos_x = furthest_point[0]
    current_pos_y = furthest_point[1]
    sorted_points_to_explore.append(furthest_point)
    points_to_explore_copy = copy.copy(points_to_explore)
    points_to_explore_copy.pop(points_to_explore_copy.index(furthest_point))
    while len(points_to_explore_copy) != 0:
      paths = []
      paths_length = []
      for point in points_to_explore_copy:
        path = dist((current_pos_x, current_pos_y), (point[0], point[1]) )
        paths.append(point)
        paths_length.append(path)

      shortest_path_index = paths_length.index(min(paths_length))
      current_pos_x, current_pos_y  = paths[shortest_path_index][0], paths[shortest_path_index][1]
      sorted_points_to_explore.append(points_to_explore_copy.pop(shortest_path_index))
      
    self.tsp_points = sorted_points_to_explore
    return sorted_points_to_explore
  def sortedPointsForDiscovery(self, start_pos:List[int]|None = None):
    '''
    [ [x,y], [x,y] ]
    '''
    poe_bot = self.poe_bot
    if start_pos != None:
      start_pos_x, start_pos_y = start_pos
    else:
      start_pos_x = int(poe_bot.game_data.player.grid_pos.x)
      start_pos_y = int(poe_bot.game_data.player.grid_pos.y)
    current_pos_x, current_pos_y = start_pos_x, start_pos_y
    points_for_discovery = self.points_for_discovery
    tsp_points = []
    points_for_discovery_copy = copy.copy(points_for_discovery)
    while len(points_for_discovery_copy) != 0:
      paths = []
      paths_length = []
      for point in points_for_discovery_copy:
        path = dist((current_pos_x, current_pos_y), (point[0], point[1]) )
        paths.append(point)
        paths_length.append(path)

      shortest_path_index = paths_length.index(min(paths_length))
      current_pos_x, current_pos_y  = paths[shortest_path_index][0], paths[shortest_path_index][1]
      tsp_points.append(points_for_discovery_copy.pop(shortest_path_index))
    self.tsp_points = tsp_points
    return tsp_points

  # def sortedPointsForDiscoveryAStar(self, discovery_radius = 125):
  #   """
  #   todo test and optimize, threads in class
    
  #   """
  #   poe_bot = self.poe_bot

  #   points_for_discovery = self.points_for_discovery

  #   tsp_points = []
  #   points_for_discovery_copy = copy.copy(points_for_discovery)
  #   current_pos_x = int(poe_bot.game_data.player.grid_pos.x)
  #   current_pos_y = int(poe_bot.game_data.player.grid_pos.y)


  #   while len(points_for_discovery_copy) != 0:
  #     print(len(points_for_discovery_copy))
  #     paths = []
  #     paths_length = []

  #     for point in points_for_discovery_copy:
  #       path = poe_bot.pather.generatePath((current_pos_y, current_pos_x), (point[0], point[1]) )
  #       paths.append(path)
  #       path_value = 0
  #       for point in path:
  #         path_value += poe_bot.terrain_for_a_star[point[0], point[1]]
  #       paths_length.append(path_value)

  #     shortest_path_index = paths_length.index(min(paths_length))
  #     shortest_path = paths[shortest_path_index]
  #     current_pos_y, current_pos_x = shortest_path[-1][0], shortest_path[-1][1]
  #     tsp_points.append(points_for_discovery_copy.pop(shortest_path_index))
  #     for point in shortest_path[::50]:

  #       cv2.circle(poe_bot.visited_area, (point[1], point[0]), discovery_radius, 127, -1)

  #     cv2.circle(poe_bot.visited_area, (shortest_path[-1][1], shortest_path[-1][0]), discovery_radius, 127, -1)
  #   return tsp_points

  def nextPoint0(self):
    '''
    returns:
    - [x,y] point to go
    - or None if no more points
    '''
    point_to_discover = None
    if len(self.points_for_discovery):
     point_to_discover = self.points_for_discovery.pop(0)
    # or some other way to sort points
    return point_to_discover
  
  def nextPoint1(self):
    # takes inital point
    # finds nearest unvisited node to it
    # crops the area in 150-300
    # floods the area from that point
    # generate points
    return [[0,0]]
  

