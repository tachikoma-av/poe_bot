import copy
import json
import os
import random
import time
from datetime import datetime

from .utils import generateSession


class TempSkeleton:
  """
  reset(self)
  """

  do_not_save_properties = [
    "unique_id",
    "folder_dir",
    "file_path",
  ]
  filename = "empty.json"
  temp_name_for_display = "TempSkeleton"

  def __init__(self, unique_id: str, temp_folder_dir: str = "./temp", reset: bool = False):
    self.unique_id = unique_id
    if not os.path.exists(temp_folder_dir):
      os.makedirs(temp_folder_dir)
    self.folder_dir = f"./{temp_folder_dir}/{self.unique_id}"
    self.file_path = self.folder_dir + f"/{self.filename}"
    if reset is True:
      print(f"[temp] resetting {self.temp_name_for_display}")
      self.reset()
    else:
      try:
        self.load()
        print(f"[temp] loaded from file {self.temp_name_for_display}")
      except Exception:
        print(f"[temp] cant load {self.temp_name_for_display} from file, creating new")
        self.reset()
    self.customInit()

  def customInit(self):
    return False

  def reset(self):
    self.key = "value"
    self.save()

  def load(self):
    if not os.path.exists(self.folder_dir):
      os.makedirs(self.folder_dir)
    file = open(self.file_path, encoding="utf-8")
    config = json.load(file)
    file.close()
    # assign
    self.fromJson(config)

  def save(self):
    file = open(self.file_path, "w", encoding="utf-8")
    json_to_save = self.toJson()
    time_now = time.time()
    json_to_save["update_time"] = time_now
    self.update_time = time_now
    json.dump(json_to_save, file, ensure_ascii=False, indent=4)
    file.close()

  def toJson(self):
    some_dict = copy.copy(vars(self))
    for key in self.do_not_save_properties:
      del some_dict[key]
    return some_dict

  def fromJson(self, config: dict):
    for key, value in config.items():
      setattr(self, key, value)
    # self.stash_tabs_data = config['stash_tabs_data']


class MapsTempData(TempSkeleton):
  # TODO supposed to be part of global temp, smth like temp["simulacrum"]
  filename = "maps.json"
  temp_name_for_display = "MapsTempData"

  def reset(self):
    """
    0 - pick map, scarabs? whatever, qual + alch + scourg + vaal
    1 - map taken, need to place it to device
    2 - map placed, need activate
    3 - map activated, may get in
    4 - we are in, need to get pattern
    """
    self.stage = 0
    self.portals_left = 6
    self.last_transition_grid_pos = {"X": 0, "Y": 0}
    self.map_boss_killed = False
    self.map_completed = False
    self.cleared_bossrooms = []  # list of cleared bossrooms, so it wont stuck in there

    self.visited_wildwood = False
    self.invitation_progress = 0

    self.essences_opened = 0
    self.essences_to_ignore_ids = []
    self.harvests_to_ignore_ids = []

    self.valuable_beasts_killed = 0
    self.killed_map_bosses_render_names = []  # to kill staged bosses or essences with mirror image
    self.entities_to_kill_force = []  # to kill staged bosses or essences with mirror image

    self.delirium_mirror_activated = False
    self.current_map = ""
    self.current_map_name_raw = ""
    self.current_map_name = ""
    self.unvisited_transitions = []  # [raw_entity, raw_entity, ] transitions we are willing to enter to do explore\bossrush
    self.visited_transitions_ids = []  # [entity_id, entity_id, ] transitions we entered + their exit transitions
    self.transition_chain = []  # [raw_entity, raw_entity, raw_entity, ] chain of transitions from first portal
    self.currently_ignore_transitions_id = []  # [entity_id, entity_id, ] transitions we will ignore this time, cos theyre out of passable zone, so we cant reach them

    self.alvas_to_ignore_ids = []
    self.alva_pick_incursion = False
    self.used_timeless_scarab_for_alva = False
    self.need_to_place_alva_timeless_scarab = False
    self.incursion_current_room_state = None
    self.incursion_current_state = None
    self.incursions_remaining = 12

    try:
      self.map_streak
    except Exception:
      print("map streak is not specified, setting to 0")
      self.map_streak = 0

    self.save()


class MapperCache2(TempSkeleton):
  # TODO supposed to be part of global temp, smth like temp["simulacrum"]
  filename = "mapper2.json"
  temp_name_for_display = "MapperCache2"

  def reset(self):
    """
    0 - pick map, scarabs? whatever, qual + alch + scourg + vaal
    1 - map taken, need to place it to device
    2 - map placed, need activate
    3 - map activated, may get in
    4 - we are in, need to get pattern
    """
    self.stage = 0
    self.portals_left = 6
    self.last_transition_grid_pos = {"X": 0, "Y": 0}
    self.map_boss_killed = False
    self.map_completed = False
    self.cleared_bossrooms = []  # list of cleared bossrooms, so it wont stuck in there

    self.visited_wildwood = False
    self.invitation_progress = 0

    self.essences_opened = 0
    self.essences_to_ignore_ids = []
    self.harvests_to_ignore_ids = []

    self.valuable_beasts_killed = 0
    self.killed_map_bosses_render_names = []  # to kill staged bosses or essences with mirror image
    self.entities_to_kill_force = []  # to kill staged bosses or essences with mirror image

    self.delirium_mirror_activated = False
    self.current_map = ""
    self.current_map_name_raw = ""
    self.current_map_name = ""
    self.unvisited_transitions = []  # [raw_entity, raw_entity, ] transitions we are willing to enter to do explore\bossrush
    self.visited_transitions_ids = []  # [entity_id, entity_id, ] transitions we entered + their exit transitions
    self.transition_chain = []  # [raw_entity, raw_entity, raw_entity, ] chain of transitions from first portal
    self.currently_ignore_transitions_id = []  # [entity_id, entity_id, ] transitions we will ignore this time, cos theyre out of passable zone, so we cant reach them

    self.alvas_to_ignore_ids = []
    self.alva_pick_incursion = False
    self.used_timeless_scarab_for_alva = False
    self.need_to_place_alva_timeless_scarab = False
    self.incursion_current_room_state = None
    self.incursion_current_state = None
    self.incursions_remaining = 12

    self.ritual_ignore_ids = []

    try:
      self.map_streak
    except Exception:
      print("map streak is not specified, setting to 0")
      self.map_streak = 0

    self.save()


sessions_dict = {"12h_noafk": "12h_noafk", "12h": "12h", "16h": "16h", "20h": "20h", "24h": "24h"}

SESSIONS_DICT_KEYS_AS_LIST = list(sessions_dict.keys())


class SessionTemp(TempSkeleton):
  filename = "session_temp.json"
  temp_name_for_display = "session_temp"

  def __init__(self, unique_id: str, temp_folder_dir: str = "./temp", reset: bool = False, session_duration="16h"):
    super().__init__(unique_id, temp_folder_dir, reset)
    self.session_duration = session_duration


class MapperSession(TempSkeleton):
  filename = "mapper_session.json"
  temp_name_for_display = "MapperSession"

  def __init__(self, unique_id: str, temp_folder_dir: str = "./temp", reset: bool = False, session_duration="16h"):
    super().__init__(unique_id, temp_folder_dir, reset)
    self.session_duration = session_duration

  def generateSession(self):  # ['12h', '16h', '20h', '24h']
    print(f"generating session for {self.session_duration}")
    duration = self.session_duration
    if duration == "12h_noafk":
      return [12, 12]
    if duration == "12h":
      return generateSession(12, 8, 8)
    elif duration == "16h":
      return generateSession(16, 6, 6)
    elif duration == "20h":
      return generateSession(20, 0, 8)
    elif duration == "24h":
      return []

  def reset(self):
    print(f"[sessions] resetting sessions {self.session_duration}")
    self.session_params = self.generateSession()
    print(f"[sessions] session params are {self.session_params}")
    play_times = self.session_params[::2]
    sleep_times = self.session_params[1::2]
    self.prev_session_params = self.session_params
    self.sessions = []
    random.shuffle(play_times)
    # random.shuffle(sleep_times)
    for i in range(len(sleep_times)):
      self.sessions.append([play_times[i], sleep_times[i]])
    total_play_time = sum(play_times)
    total_sleep_time = sum(sleep_times)
    print(f"[sessions] generated sessions {self.sessions}, total play time: {total_play_time}, total sleep time {total_sleep_time}")
    self.shiftSession()

  def getCurrentSessionPlayTimeLeft(self):
    if self.session_duration == "24h":
      print("[sessions] 24h session, so no sleep")
      return 9999
    else:
      return self.current_session_started_at + self.current_session[0] * 60 * 60 - time.time()

  def getCurrentSessionSleepTime(self):
    print(f"[sessions] current_session {self.current_session} session_")
    return self.current_session[1] * 60 * 60

  def shiftSession(self):
    if self.session_duration == "24h":
      self.current_session_started_at = 0
      self.current_session = []
      self.save()
      return
    if len(self.sessions) == 0:
      self.reset()
    self.current_session = self.sessions.pop()
    self.current_session_started_at = 0
    self.save()

  def setSessionTime(self):
    if self.session_duration == "24h":
      return
    if len(self.sessions) == 0:
      self.reset()
    time_diff = int(self.current_session[0] * 60 * 60 * 0.1)
    self.current_session_started_at = time.time() + random.randint(-time_diff, time_diff)
    print(f"[sessions] current session start time set to {self.current_session_started_at}")
    self.save()


class StashTempData(TempSkeleton):
  # TODO supposed to be part of global temp, smth like temp["simulacrum"]
  filename = "stash.json"
  temp_name_for_display = "StashTempData"

  def allItems(self):
    all_items_in_stash = []
    for stash_tab in self.stash_tabs_data:
      all_items_in_stash.extend(stash_tab["items"])
    return all_items_in_stash

  def reset(self):
    self.stash_tabs_data = []
    self.unsorted_items = []
    self.affinities = {
      "blight": None,
      "currency": None,
      "delirium": None,
      "delve": None,
      "div_cards": None,
      "essence": None,
      "fragments": None,
      "map": None,
      "catalysts": None,
      "unique": None,
      "flask": None,
      "gem": None,
    }
    self.save()

  def addItemToTab(self, item_raw, tab_index=None, save=False):
    found_index = False
    if tab_index is not None:
      needed_tab = next((i for i in self.stash_tabs_data if i["tab_index"] == tab_index), None)
      if needed_tab:
        found_index = True
        needed_tab["items"].append(item_raw)
    if tab_index is None or found_index is False:
      self.unsorted_items.append(item_raw)
    if save is True:
      self.save()

  def updateTabInfo(self, current_stash_info):
    """
    current_stash_info is a variabale from poe_bot.getOpenedStashInfo()
    """
    tab_index = current_stash_info["tab_index"]
    print(f"updateTabInfo for tab with index {tab_index}")

    tab_updated = False
    for stash_tab in self.stash_tabs_data:
      if tab_index == stash_tab["tab_index"]:
        print(f"updating stash tab with index {tab_index}")
        index_in_temp = self.stash_tabs_data.index(stash_tab)

        self.stash_tabs_data[index_in_temp] = {"last_update_time": time.time(), "tab_index": tab_index, "items": current_stash_info["items"]}
        tab_updated = True
        break
    if tab_updated is False:
      print(f"tab_updated is {tab_updated}, so appending new object into .stash_tabs_data")
      self.stash_tabs_data.append({"last_update_time": time.time(), "tab_index": tab_index, "items": current_stash_info["items"]})
    self.save()


class AfkTempData(TempSkeleton):
  filename = "afk.json"
  temp_name_for_display = "AfkTempData"

  def reset(self):
    # to disconnect or stay for doing nothing for 4-7 hours + random seconds
    self.resetLongSleep()
    # to go afk for 15-30 minutes + random seconds
    self.resetAfkSleep()
    # to go afk for 5-30 seconds
    self.resetShortSleep()

  def resetLongSleep(self):
    """
    long sleep for 4-6 hours with delay 18-20 hours
    """
    time_now = time.time()
    self.last_long_sleep_time = time_now
    self.next_long_sleep = time_now + random.randint(18, 20) * 60 * 60 + random.randint(0, 60) * 60 + random.randint(0, 60)
    self.long_sleep_duration = random.randint(4, 6) * 60 * 60 + random.randint(0, 60) * 60 + random.randint(0, 60)
    self.long_sleep_delay = random.randint(1, 3)
    self.long_sleep_tries = 0
    self.resetAfkSleep()
    self.resetShortSleep()
    self.save()

  def resetAfkSleep(self):
    """
    afk sleep for 15-30 minutes once in 1-5 hours
    """
    time_now = time.time()
    self.last_afk_time = time_now
    self.next_afk_sleep = time_now + random.randint(4, 7) * 60 * 60 + random.randint(0, 60) * 60 + random.randint(0, 60)
    self.afk_sleep_duration = random.randint(16, 30) * 60 + random.randint(0, 60)
    self.afk_sleep_delay = random.randint(1, 13)
    self.afk_sleep_tries = 0
    self.resetShortSleep()
    self.save()

  def resetShortSleep(self):
    """
    short sleep for 5-30 seconds once in
    """
    time_now = time.time()
    self.last_short_sleep = time_now
    self.next_short_sleep = time_now + random.randint(5, 59) * 60 + random.randint(0, 60)
    self.short_sleep_duration = random.randint(5, 60)
    self.short_sleep_delay = random.randint(1, 13)
    self.short_sleep_tries = 0
    self.save()

  def performAfkSleep(self, return_sleep_val=False):
    """
    afk sleep for 15-30 minutes once in 1-5 hours
    """
    time_now = time.time()
    # check if time to sleep
    if time_now < self.next_afk_sleep:
      return False

    self.afk_sleep_tries += 1
    # check if the delay is correct
    if self.afk_sleep_tries < self.afk_sleep_delay:
      self.save()
      return False

    print(f"[AFK] long afk for {self.afk_sleep_duration} seconds started at:{datetime.fromtimestamp(time_now)}")
    # print(f'performAfkSleep time_now:{time_now} self.last_afk_time:{self.last_afk_time}')
    # print(f'self.afk_sleep_tries:{self.afk_sleep_tries} self.afk_sleep_delay:{self.afk_sleep_delay}')
    # print(f"self.afk_sleep_duration:{self.afk_sleep_duration}")
    if return_sleep_val is False:
      time.sleep(self.afk_sleep_duration)

    self.resetAfkSleep()
    return self.afk_sleep_duration

  def performShortSleep(self, return_sleep_val=False):
    time_now = time.time()
    # check if time to sleep
    if time_now < self.next_short_sleep:
      return False
    self.short_sleep_tries += 1
    # check if the delay is correct
    if self.short_sleep_tries < self.short_sleep_delay:
      # save?
      return False
    print(f"[AFK] afk a bit for {self.short_sleep_duration} seconds started at:{datetime.fromtimestamp(time_now)}")
    # print(f'performShortSleep time_now:{time_now} self.last_short_sleep:{self.last_short_sleep}')
    # print(f'self.short_sleep_tries:{self.short_sleep_tries} self.short_sleep_delay:{self.short_sleep_delay}')
    # print(f"self.short_sleep_duration:{self.short_sleep_duration}")
    if return_sleep_val is False:
      time.sleep(self.short_sleep_duration)
    self.resetShortSleep()
    return self.short_sleep_duration


class SimulacrumTempData(TempSkeleton):
  # TODO supposed to be part of global temp, smth like temp["simulacrum"]
  filename = "simulacrum.json"
  temp_name_for_display = "SimulacrumTempData"

  def reset(self):
    self.stage = 0
    """
    0 - pick map, scarabs? whatever, qual + alch + scourg + vaal
    1 - map taken, need to place it to device
    2 - map placed, need activate
    3 - map activated, may get in
    4 - we are in, need to get pattern

    5 - pattern found, may do wave cycle
    44 - 
    """
    self.simulacrum_pattern = 0
    self.wave = 0
    self.prev_biggest_world_item_id = 0
    self.wave_started = False
    self.drop_picked = False
    self.instance_over = False
    self.wave_start_time = time.time()
    self.save()


class SimulacrumCache2(SimulacrumTempData):
  filename = "simulacrum2.json"
  temp_name_for_display = "SimulacrumCache2"


class FollowerTempData(TempSkeleton):
  # TODO supposed to be part of global temp, smth like temp["simulacrum"]
  filename = "follower.json"
  temp_name_for_display = "FollowerTempData"

  def reset(self):
    self.stashing_routine_done = False
    self.ultimatum_finished = False
    self.save()


class QuestTempData(TempSkeleton):
  # TODO supposed to be part of global temp, smth like temp["simulacrum"]
  filename = "quest.json"
  temp_name_for_display = "QuestTempData"

  def reset(self):
    self.stage = 0
    """
    0 - pick map, scarabs? whatever, qual + alch + scourg + vaal
    1 - map taken, need to place it to device
    2 - map placed, need activate
    3 - map activated, may get in
    4 - we are in, need to get pattern

    5 - pattern found, may do wave cycle
    44 - 
    """
    self.explore_points = []
    self.current_area_hash = 0
    self.json = {}
    self.save()


class IncursionTempData(TempSkeleton):
  # TODO supposed to be part of global temp, smth like temp["simulacrum"]
  filename = "incursion.json"
  temp_name_for_display = "IncursionTempData"

  def reset(self):
    self.current_temple_state_dict = {}
    self.need_to_use_timeless_scarab = False
    self.first_run = False
    self.do_incursion_strategy = []
    self.save()


class AreaTempData(TempSkeleton):
  # TODO supposed to be part of global temp, smth like temp["simulacrum"]
  filename = "area.json"
  temp_name_for_display = "AreaTempData"

  def reset(self):
    self.area_hash = 0
    self.passable_transitions_ids = []
    self.transitions_exits_ids = []
    self.blockades = []
    self.save()


class LauncherMapConfigs(TempSkeleton):
  # TODO supposed to be part of global temp, smth like temp["simulacrum"]
  filename = "mapper_configs.json"
  temp_name_for_display = "LauncherMapConfigs"

  def reset(self):
    self.mapper_configs = {}
    self.save()


class Logger:
  def __init__(self, unique_id: str) -> None:
    self.unique_id = unique_id
    self.folder_dir = f"./temp/{self.unique_id}/logs"
    if not os.path.exists(self.folder_dir):
      print("creating logs dir")
      os.makedirs(self.folder_dir)
    self.file = None

  def openFile(self):
    current_dateTime = datetime.now()
    self.filename = f"{current_dateTime.year}_{current_dateTime.month}_{current_dateTime.day}.txt"
    self.full_filename = f"{self.folder_dir}/{self.filename}"

  def writeLine(self, text: str):
    print(text)
    if self.file is None:
      self.openFile()

    dt = datetime.now().isoformat(timespec="seconds")
    line = f"{dt} {text}"
    with open(self.full_filename, "a") as the_file:
      the_file.write(f"{line}\n")
