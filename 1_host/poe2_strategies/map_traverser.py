import time
import random
from typing import List, Tuple
import math

from poe2_strategies.helpers.runner_break_function import RunnerBreaker
from utils.pathing import TSP
from utils.utils import angleOfLine, pointOnCircleByAngleAndLength, createLineIteratorWithValues
from .base_strategy import Strategy

class MapTraverserStrategy(Strategy):
    def __init__(self, runnerBreakFunction):
        self.runnerBreakFunction = runnerBreakFunction

    def findBackwardsPoint(self, current_point: List[int], point_to_go: List[int]) -> List[int]:
        """Find the furthest passable point in the opposite direction of movement."""
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
        return furthest_point


    def __call__(self, poe_bot) -> None:
        """Main map traversal logic."""
        tsp = TSP(poe_bot=poe_bot)
        mover = poe_bot.mover
        map_complete = False

        while map_complete is False:
            poe_bot.refreshInstanceData()
            print('generating pathing points')
            tsp.generatePointsForDiscovery()
            discovery_points = tsp.sortedPointsForDiscovery()
            print(f'len(discovery_points) {len(discovery_points)}')
            discovery_points = list(filter(
                lambda p: poe_bot.game_data.terrain.checkIfPointPassable(p[0], p[1]), 
                discovery_points
            ))
            print(f'len(discovery_points) {len(discovery_points)} after sorting')
            print(f'discovery_points {discovery_points}')
            
            if len(discovery_points) == 0:
                print('len(discovery_points) == 0 after points generation')
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

                # Go to point to make it explored
                result = mover.goToPoint(
                    point=point_to_go,
                    min_distance=50,
                    release_mouse_on_end=False,
                    custom_break_function=self.runnerBreakFunction,
                    step_size=random.randint(30,35)
                )
                print(f"mover.goToPoint result {result}")

                # If we arrived at discovery point and nothing happened
                if result is None:
                    while True:
                        if len(discovery_points) == 0:
                            point_to_go = None
                            map_complete = True
                            print('len(discovery_points) == 0, breaking')
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

                poe_bot.refreshInstanceData()
                poe_bot.last_action_time = 0 