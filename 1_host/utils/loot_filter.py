from __future__ import annotations

import typing
from typing import List

if typing.TYPE_CHECKING:
  from .gamehelper import PoeBot

import random
import time
from math import dist

import numpy as np

from .components import PosXY
from .constants import GOLD_COIN_ART, SHITTY_UNIQUES_ARTS
from .utils import alwaysTrueFunction, sortByHSV


class PickableItemLabel:
  def __init__(self, poe_bot: PoeBot, raw) -> None:
    self.poe_bot = poe_bot
    self.raw = raw
    self.id = raw["id"]
    self.icon_render = raw["a"]
    self.rarity = raw["r"]
    self.grid_position = PosXY(raw["gp"][0], raw["gp"][1])
    self.displayed_name = raw["dn"]

  def distanceToPlayer(self):
    self.distance_to_player = dist(
      (self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y), (self.grid_position.x, self.grid_position.y)
    )
    return self.distance_to_player

  def __str__(self) -> str:
    return str(self.raw)


class LootPicker:
  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.loot_filter = LootFilter(poe_bot=self.poe_bot)
    self.last_picking_item_id = 0
    self.last_picking_item_icon_render = ""
    self.attempting_to_pick_last_item_for_iterations = 0

  def collectLoot(self, *args):
    """
    True - if picked smth
    False - no items to pick
    """
    print(f"[LootPicker.collectLoot] call at {time.time()}")
    poe_bot = self.poe_bot
    pickable_items = poe_bot.loot_picker.loot_filter.getPickableItems()
    if len(pickable_items) == 0:
      return False
    print(f"[LootPicker.collectLoot] start at {time.time()}")
    print(f"[LootPicker.collectLoot] pickable_items {pickable_items}")
    pickable_items_sorted = sorted(pickable_items, key=lambda e: e.distanceToPlayer())
    pickable_item = pickable_items_sorted[0]
    if pickable_item.id == self.last_picking_item_id or self.last_picking_item_icon_render == pickable_item.icon_render:
      self.attempting_to_pick_last_item_for_iterations += 1
    else:
      self.last_picking_item_id = pickable_item.id
      self.last_picking_item_icon_render = pickable_item.icon_render
      self.attempting_to_pick_last_item_for_iterations = 0

    if self.attempting_to_pick_last_item_for_iterations == 6:
      print("self.attempting_to_pick_last_item_for_iterations == 5, pressing space")
      poe_bot.bot_controls.keyboard.tap("DIK_SPACE")
    if self.attempting_to_pick_last_item_for_iterations > 10:
      print(f"self.attempting_to_pick_last_item_for_iterations > 10, adding to ignore list: {str(pickable_item)}")
      poe_bot.loot_picker.loot_filter.item_id_to_ignore.append(pickable_item.id)
    print(f"[LootPicker.collectLoot] collectLootAt near {pickable_item} at {time.time()}")
    point_to_run_around = {"X": pickable_item.grid_position.x, "Y": pickable_item.grid_position.y}
    print(f"[LootPicker.collectLoot] going to clear nearby {pickable_item}")
    poe_bot.combat_module.clearLocationAroundPoint(point_to_run_around)
    print(f"[LootPicker.collectLoot] going to collect loot near {pickable_item}")
    poe_bot.last_action_time = 0
    # print(f'#collectLoot d at {time.time()}')
    if (
      dist((poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (pickable_item.grid_position.x, pickable_item.grid_position.y))
      > 19
    ):
      print("going closer to loot")
      self.poe_bot.mover.goToPoint(
        point=(pickable_item.grid_position.x, pickable_item.grid_position.y),
        custom_continue_function=poe_bot.combat_module.build.usualRoutine,
        release_mouse_on_end=True,
        min_distance=20,
        step_size=random.randint(30, 35),
      )
    else:
      self.poe_bot.mover.stopMoving()
      print("already close enough to loot")
    # print(f'#collectLoot e at {time.time()}')
    # print(f'stopped, clearing nearby {pickable_item}')
    # poe_bot.combat_module.clearLocationAroundPoint(point_to_run_around)
    # print(f'#collectLoot f at {time.time()}')
    print(f"[LootPicker.collectLoot] stopped, picking items nearby {pickable_item}")
    # time.sleep(random.randint(10,20)/100)
    self.pickupDropV7(pickable_items_sorted)
    poe_bot.refreshInstanceData(reset_timer=True)
    poe_bot.last_action_time = 0
    poe_bot.combat_module.build.staticDefence()
    print(f"[LootPicker.collectLoot] return at {time.time()}")
    return True

  def collectLootWhilePresented(self):
    loot_collected = self.collectLoot()
    while loot_collected is True:
      loot_collected = self.collectLoot()

  def checkIfItemHoveredByElement(
    self,
  ):
    pass

  def pickupDropV3(self, h_min=0, h_max=1, y_offset=100, x_offset=100, x2_offset=100, y2_offset=100, pick_highest=True):
    """
    returns True if drop available and picking it
    # by default pick ups currency on [y_offset, -y2_offset, x_offset, -x2_offset] [100:-100, 100:-100]
    if no drop returns False
    """
    # TODO SET CURSOR pos in the corner to
    poe_bot = self.poe_bot
    game_img = poe_bot.getPartialImage(y_offset, -y2_offset, x_offset, -x2_offset)
    # plt.imshow(game_img);plt.show()
    pickup_blue_items = sortByHSV(game_img, h_min, 255, 253, h_max, 255, 255)

    # plt.imshow(pickup_blue_items);plt.show()
    data = np.where(pickup_blue_items != 0)
    coords = list(zip(data[0], data[1]))

    if len(coords) == 0:
      print("no drop to pick")
      return False

    print("picking up the drop")
    if pick_highest is True:
      coords_to_click = list(coords[0])  # upper left?
      diff_of_loc = 15
    elif pick_highest is False:
      coords_to_click = list(coords[-1])  # lower left?
      diff_of_loc = -15

    coords_to_click[0] = coords_to_click[0] + y_offset  # append a bit to X coord
    coords_to_click[1] = coords_to_click[1] + x_offset  # append a bit to X coord
    print(f"picking drop at {coords_to_click}")
    pos_x, pos_y = poe_bot.convertPosXY(coords_to_click[1] + diff_of_loc, coords_to_click[0] + diff_of_loc, safe=False)
    poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y, wait_till_executed=False)
    print(f"picking drop at {pos_x, pos_y}")
    poe_bot.bot_controls.mouse.click()

  def pickupDropV6(self, items_can_pick: List[PickableItemLabel]):
    """
    returns True if drop available and picking it
    if no drop returns False
    """
    poe_bot = self.poe_bot
    pickup_drop_version = 6
    print(f"[LootPicker.pickupDropV{pickup_drop_version}] call at {time.time()}")
    nearest_pickable_item = items_can_pick[0]
    items_can_pick_at_the_same_time = list(
      filter(
        lambda i: i.grid_position.x == nearest_pickable_item.grid_position.x and i.grid_position.y == nearest_pickable_item.grid_position.y,
        items_can_pick,
      )
    )
    items_can_pick_at_the_same_time_ids = list(map(lambda i: i.id, items_can_pick_at_the_same_time))
    visible_labels = poe_bot.backend.getVisibleLabels()
    visible_labels = list(
      filter(
        lambda label: label["id"] in items_can_pick_at_the_same_time_ids
        and label["p"] == "Metadata/MiscellaneousObjects/WorldItem"
        and label["p_o_s"]["x1"] > 100
        and label["p_o_s"]["x2"] < poe_bot.game_window.width - 100
        and label["p_o_s"]["y1"] > 100
        and label["p_o_s"]["y2"] < poe_bot.game_window.height - 100,
        visible_labels,
      )
    )
    if len(visible_labels) == 0:
      print("no drop to pick")
      return False
    center_x = poe_bot.game_window.center_point[0]
    center_y = poe_bot.game_window.center_point[1] * 0.8
    random.choice([-1, 1])
    print(f"[LootPicker.pickupDropV{pickup_drop_version}] picking up the drop got {len(visible_labels)} objects")
    visible_labels_sorted = sorted(
      visible_labels,
      key=lambda label: dist(
        ((label["p_o_s"]["x1"] + label["p_o_s"]["x2"]) / 2, (label["p_o_s"]["y1"] + label["p_o_s"]["y2"]) / 2),
        (poe_bot.game_window.center_point[0], poe_bot.game_window.center_point[1]),
      ),
    )

    label_to_click = visible_labels_sorted.pop(0)
    label_to_click_id = label_to_click["id"]
    last_coords_to_click = (0, 0)
    click_count = 0
    for i in range(4):
      print(f"#pickupDropV{pickup_drop_version} label_to_click {label_to_click} at {time.time()}")
      coords_to_click = (
        int((label_to_click["p_o_s"]["y1"] + label_to_click["p_o_s"]["y2"]) / 2),
        int((label_to_click["p_o_s"]["x1"] + label_to_click["p_o_s"]["x2"]) / 2),
      )
      if coords_to_click == last_coords_to_click:
        print("coords to click didnt change, seems like we clicked it")
        click_count += 1
      if click_count > 0:
        if len(visible_labels_sorted) != 0:
          label_to_click = visible_labels_sorted.pop(0)
          click_count = 0
          coords_to_click = (
            int((label_to_click["p_o_s"]["y1"] + label_to_click["p_o_s"]["y2"]) / 2),
            int((label_to_click["p_o_s"]["x1"] + label_to_click["p_o_s"]["x2"]) / 2),
          )
        else:
          break
      last_coords_to_click = coords_to_click
      pos_x, pos_y = poe_bot.convertPosXY(coords_to_click[1], coords_to_click[0])
      print(f"#pickupDropV{pickup_drop_version} set mouse at {pos_x, pos_y} at {time.time()}")
      poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y, wait_till_executed=False)
      # time.sleep(random.randint(2,4)/100)
      print(f"pickupDropV{pickup_drop_version} click mouse at {pos_x, pos_y} at {time.time()}")
      print(f"pickupDropV{pickup_drop_version} after at {pos_x, pos_y} at {time.time()}")
      dist_x = abs(center_x - coords_to_click[1])
      dist_y = abs(center_y - coords_to_click[0])
      print(dist_x, dist_y)
      x_delay = dist_x / poe_bot.game_window.center_point[0]
      y_delay = dist_y / poe_bot.game_window.center_point[1]
      print(x_delay, y_delay)
      sleep_time = (x_delay + y_delay) / 1.6
      print(f"pickupDropV{pickup_drop_version} sleep_time {sleep_time}")
      poe_bot.bot_controls.mouse.pressAndRelease(wait_till_executed=True)
      # poe_bot.bot_controls.mouse.pressAndRelease(delay = sleep_time, wait_till_executed=True)
      visible_labels = poe_bot.backend.getVisibleLabels()
      visible_labels = list(filter(lambda label: label["id"] == label_to_click_id, visible_labels))
      if len(visible_labels) != 1:
        print(f"label with id {label_to_click_id} doesnt exist anymore or 2 labels with same id")
        break
      label_to_click = visible_labels[0]
    print(f"[LootPicker.pickupDropV{pickup_drop_version}] return at {time.time()}")
    return True

  def pickupDropV7(self, items_can_pick: List[PickableItemLabel]):
    """
    returns True if drop available and picking it
    if no drop returns False
    """
    poe_bot = self.poe_bot
    pickup_drop_version = 7
    print(f"[LootPicker.pickupDropV{pickup_drop_version}] call at {time.time()}")
    nearest_pickable_item = items_can_pick[0]
    print(f"[LootPicker.pickupDropV{pickup_drop_version}] items_can_pick {list(map(lambda i: i.raw, items_can_pick))}")
    items_can_pick_at_the_same_time = list(
      filter(
        lambda i: i.grid_position.x == nearest_pickable_item.grid_position.x and i.grid_position.y == nearest_pickable_item.grid_position.y,
        items_can_pick,
      )
    )
    items_can_pick_at_the_same_time_ids = list(map(lambda i: i.id, items_can_pick_at_the_same_time))
    print(
      f"[LootPicker.pickupDropV{pickup_drop_version}] items_can_pick_at_the_same_time {list(map(lambda i: i.raw, items_can_pick_at_the_same_time))}"
    )
    visible_labels = poe_bot.backend.getItemsOnGroundLabelsVisible()
    visible_labels = list(
      filter(
        lambda label: label["id"] in items_can_pick_at_the_same_time_ids
        and label["sz"][0] > 100
        and label["sz"][1] < poe_bot.game_window.width - 100
        and label["sz"][2] > 100
        and label["sz"][3] < poe_bot.game_window.height - 100,
        visible_labels,
      )
    )
    if len(visible_labels) == 0:
      print("no drop to pick")
      return False
    print(f"[LootPicker.pickupDropV{pickup_drop_version}] picking up the drop got {len(visible_labels)} objects")
    print(f"[LootPicker.pickupDropV{pickup_drop_version}] picking up the drop got {visible_labels} labels")
    visible_labels_sorted = sorted(
      visible_labels,
      key=lambda label: dist(
        ((label["sz"][0] + label["sz"][1]) / 2, (label["sz"][2] + label["sz"][3]) / 2),
        (poe_bot.game_window.center_point[0], poe_bot.game_window.center_point[1]),
      ),
    )
    label_to_click = visible_labels_sorted.pop(0)
    label_to_click["id"]
    print(f"[LootPicker.pickupDropV{pickup_drop_version}] nearest label to center is {label_to_click}")

    def getLabelCenterPos(label_to_click):
      coords_to_click = (int((label_to_click["sz"][0] + label_to_click["sz"][1]) / 2), int((label_to_click["sz"][2] + label_to_click["sz"][3]) / 2))
      pos_x, pos_y = poe_bot.convertPosXY(coords_to_click[0], coords_to_click[1])
      return (pos_x, pos_y)

    # firstly hover on item smooth and wait till executed, and then start doing spam
    label_center = getLabelCenterPos(label_to_click)
    poe_bot.bot_controls.mouse.setPosSmooth(label_center[0], label_center[1], wait_till_executed=True)
    last_targeted_item_id = 0
    # {id: clicked_count}
    clicked_items_ids = {}

    for iter_num in range(4):
      print(f"clicked_items_ids {clicked_items_ids}")
      visible_labels = poe_bot.backend.getItemsOnGroundLabelsVisible()
      targeted_item_can_pick = next(
        (i_raw for i_raw in visible_labels if i_raw["id"] in items_can_pick_at_the_same_time_ids and i_raw["it"] == 1), None
      )
      # targeted_items_can_pick = list(filter(lambda i_raw: i_raw["id"] in items_can_pick_at_the_same_time_ids and i_raw["it"] == 1, visible_labels))
      if iter_num != 0 and targeted_item_can_pick:
        print(f"[LootPicker.pickupDropV{pickup_drop_version}] targeted_item_can_pick {targeted_item_can_pick}")
        item_id = targeted_item_can_pick["id"]
        targeted_twice = last_targeted_item_id == item_id
        last_targeted_item_id = item_id
        if targeted_twice:
          clicked_times = clicked_items_ids.get(item_id, 0)
          if clicked_times == 0:
            clicked_items_ids[item_id] = 1
          else:
            clicked_items_ids[item_id] += 1

          if clicked_items_ids[item_id] == 3:
            print(f"[LootPicker.pickupDropV{pickup_drop_version}] clicked 2 times already")
            if len(visible_labels_sorted) == 0:
              print(f"[LootPicker.pickupDropV{pickup_drop_version}] breaking cos no more labels")
              break
            else:
              label_to_click = visible_labels_sorted.pop(0)
            targeted_item_can_pick = None
          else:
            poe_bot.bot_controls.mouse.pressAndRelease(wait_till_executed=True, delay=random.uniform(0.03, 0.06))

      if targeted_item_can_pick is None:
        last_targeted_item_id = 0
        updated_label = next((i_raw for i_raw in visible_labels if i_raw["id"] == label_to_click["id"]), None)
        if updated_label:
          print(f"[LootPicker.pickupDropV{pickup_drop_version}] going to hover on label {updated_label}")
          label_center = getLabelCenterPos(updated_label)
          poe_bot.bot_controls.mouse.setPos(label_center[0], label_center[1], wait_till_executed=True)
        else:
          break

    # for iter_num in range(4):
    #   print(f"clicked_items_ids {clicked_items_ids}")
    #   visible_labels = poe_bot.backend.getItemsOnGroundLabelsVisible()
    #   targeted_item_can_pick = next( (i_raw for i_raw in visible_labels if i_raw["id"] in items_can_pick_at_the_same_time_ids and i_raw["it"] == 1), None)
    #   # targeted_items_can_pick = list(filter(lambda i_raw: i_raw["id"] in items_can_pick_at_the_same_time_ids and i_raw["it"] == 1, visible_labels))
    #   if iter_num != 0 and targeted_item_can_pick:
    #     print(f'[LootPicker.pickupDropV{pickup_drop_version}] targeted_item_can_pick {targeted_item_can_pick}')
    #     item_id = targeted_item_can_pick["id"]
    #     clicked_times = clicked_items_ids.get(item_id, 0)
    #     if clicked_times == 0:
    #       clicked_items_ids[item_id] = 1
    #     else:
    #       clicked_items_ids[item_id] += 1

    #     if clicked_items_ids[item_id] == 3:
    #       print(f'[LootPicker.pickupDropV{pickup_drop_version}] clicked 2 times already')
    #       if len(visible_labels_sorted) == 0:
    #         print(f'[LootPicker.pickupDropV{pickup_drop_version}] breaking cos no more labels')
    #         break
    #       else:
    #         label_to_click = visible_labels_sorted.pop(0)
    #       targeted_item_can_pick = None
    #     if targeted_item_can_pick:
    #       poe_bot.bot_controls.mouse.pressAndRelease(wait_till_executed=True, delay=random.uniform(0.03, 0.06))
    #   if targeted_item_can_pick == None:
    #     updated_label = next( (i_raw for i_raw in visible_labels if i_raw["id"] == label_to_click["id"]), None)
    #     if updated_label:
    #       print(f'[LootPicker.pickupDropV{pickup_drop_version}] going to hover on label {updated_label}')
    #       label_center = getLabelCenterPos(updated_label)
    #       poe_bot.bot_controls.mouse.setPos(label_center[0],label_center[1], wait_till_executed=True)
    #       last_targeted_item_id = 0

    #     else:
    #       break
    print(f"[LootPicker.pickupDropV{pickup_drop_version}] return at {time.time()}")
    return True


class LootFilterSettings:
  pick_portal_scrolls = True
  pick_alchemy_orbs = True
  pick_wisdom_scrolls = False
  pick_links_combination = ["bbgr"]
  min_sockets_to_pick = 6  # 7 will not consider item as pickable cos of sockets
  min_links_to_pick = 6  # 7 will not consider item as pickable cos of links
  collect_gold = False


class LootFilter:
  def __init__(self, poe_bot: PoeBot, settings=LootFilterSettings()) -> None:
    self.poe_bot = poe_bot
    self.settings = settings
    self.item_id_to_ignore = []
    self.need_to_pick_keys = {}
    self.special_rules = [alwaysTrueFunction]

  def needToPickMorePortalScrolls(self):
    print("needToPickMorePortalScrolls")
    key = "Portal Scroll"
    need_to_pick_key = self.need_to_pick_keys.get(key, None)
    if need_to_pick_key is None:
      self.poe_bot.ui.inventory.update()
      items_by_key = list(filter(lambda i: key in i.name, self.poe_bot.ui.inventory.items))
      print(f"items_by_key {items_by_key}")
      total_items_count = sum(list(map(lambda i: i.items_in_stack, items_by_key)))
      print(f"total_items_count {total_items_count}")
      res = False
      if total_items_count > 20:
        self.need_to_pick_keys[key] = False
      else:
        self.need_to_pick_keys[key] = True
        res = True
      print(f"res {res}")
      return res
    else:
      print(f"had key {key} {need_to_pick_key}")
      return need_to_pick_key

  def getPickableItems(self) -> List[PickableItemLabel]:
    """
    [{'id': 1283,
    'a': 'Art/2DItems/Currency/CurrencyIdentification.dds',
    'l': None,
    'gp': [419, 166],
    'sz': [195, 353, 334, 361]},
    {'id': 1284,
      'a': 'Art/2DItems/Armours/Shields/ShieldStrInt2.dds',
      'l': ['W', 'W', 'W'],
      'gp': [422, 166],
      'sz': [204, 379, 309, 334]}]
    """
    poe_bot = self.poe_bot
    items_to_pick = []

    item_visible_labels = poe_bot.backend.last_data["i"].copy()
    for label in item_visible_labels: # invert Y axis
      label["gp"][1] = self.poe_bot.game_data.terrain.terrain_image.shape[0] - label["gp"][1]
    item_visible_labels = list(
      filter(
        lambda l: l["a"] is not None
        and l["id"] not in self.item_id_to_ignore
        and poe_bot.game_data.terrain.checkIfPointPassable(l["gp"][0], l["gp"][1], 5),
        item_visible_labels,
      )
    )
    if self.poe_bot.debug:
      print(f"item_visible_labels {item_visible_labels}")

    for item_index in range(len(item_visible_labels)):
      item = item_visible_labels[item_index]
      print(item)
      to_display = True
      if self.settings.collect_gold is not True and item["a"] == GOLD_COIN_ART:
        to_display = False

      if item["a"] == "Art/2DItems/Currency/CurrencyPortal.dds":
        if self.settings.pick_portal_scrolls is False:
          to_display = False
          # self.item_id_to_ignore.append(item['id'])
          # continue
        else:
          to_display = self.needToPickMorePortalScrolls()
      if item["a"] == "	Art/2DItems/Currency/CurrencyUpgradeToRare.dds":
        if self.settings.pick_alchemy_orbs is False:
          to_display = False
          # self.item_id_to_ignore.append(item['id'])
          # continue
      if item["r"] == "Unique":
        if item["a"] in SHITTY_UNIQUES_ARTS:
          to_display = False

      #     item_sockets = "".join(i['l'])
      #     print(item_sockets)

      # if self.settings.min_sockets_to_pick != 0 and i['l']:
      #   if not item_sockets:
      #     item_sockets = "".join(i['l'])
      #     print(item_sockets)

      # if self.settings.min_links_to_pick != 0 and i['l']:
      #   if not item_links:
      #     item_links = "".join(i['l'])
      #     item_links = list(map(lambda l: l.sort(), i['l'] ))
      #     print(item_links)

      if to_display is False:
        print(f"item label added to ignored {item}")
        self.item_id_to_ignore.append(item["id"])
      else:
        items_to_pick.append(item)
    item_visible_labels = list(map(lambda l: PickableItemLabel(poe_bot=poe_bot, raw=l), items_to_pick))
    item_visible_labels_filtered = []
    for item_label in item_visible_labels:
      passed = False
      for rule_function in self.special_rules:
        if rule_function(item_label) is True:
          passed = True
          break
      if passed is True:
        item_visible_labels_filtered.append(item_label)
      else:
        print(f"item label added to ignored {item_label}")
        self.item_id_to_ignore.append(item_label.id)
    return item_visible_labels_filtered


class CustomLootFilter:
  jewellery_keys = ["Art/2DItems/Amulets/", "Art/2DItems/Rings/", "Art/2DItems/Belts/Belt"]
  map_key = "Art/2DItems/Maps/Atlas2Maps"

  def __init__(
    self,
    collect_rgb=False,
    collect_small_rgb=False,
    collect_rare_jewellery=True,
    collect_6s=True,
    collect_rare_keys=[],
    collect_links=["GGG"],
    collect_maps=True,
  ) -> None:
    self.collect_rgb = collect_rgb
    self.collect_small_rgb = collect_small_rgb
    self.collect_rare_jewellery = collect_rare_jewellery
    self.collect_6s = collect_6s
    self.collect_rare_keys = collect_rare_keys
    self.collect_links = collect_links
    self.collect_maps = collect_maps

  def isItemPickable(self, item: PickableItemLabel):
    print(f"[CustomLootFilter] gonna check if need to pick {item.raw}")

    if item.rarity == "Unique":
      return True
    if item.rarity == "Rare":
      for key in self.jewellery_keys:
        if key in item.icon_render:
          return True
      for key in self.collect_rare_keys:
        if key in item.icon_render:
          return True
    if self.collect_maps and self.map_key in item.icon_render:
      return True
    if "Art/2DItems/Gems/" in item.icon_render and item.icon_render != "Art/2DItems/Gems/BlackGem.dds":
      return False
    if "Art/2DItems/Flasks/" in item.icon_render:
      if (
        "Art/2DItems/Flasks/hybridflask" in item.icon_render
        or "Art/2DItems/Flasks/manaflask" in item.icon_render
        or "Art/2DItems/Flasks/lifeflask" in item.icon_render
      ):
        return False
      return True
    if item.rarity is None:
      return True
    return False
