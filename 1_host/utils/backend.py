from __future__ import annotations

import json
import socket
import threading
import time
import typing

if typing.TYPE_CHECKING:
  from .gamehelper import PoeBot


class Backend:
  def __init__(self, poe_bot: PoeBot, port: int = 50006) -> None:
    self.poe_bot = poe_bot
    self.port = port
    self.host = poe_bot.remote_ip
    self.debug = poe_bot.debug
    # self.debug = True
    self.sock = None
    self.lock = threading.Lock()  # For thread-safe operations

  def ensure_connection(self) -> None:
    with self.lock:
      if self.sock is None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5)
        try:
          self.sock.connect((self.host, self.port))
          if self.debug:
            print("Successfully established TCP connection")
        except socket.error as e:
          self.sock = None
          raise ConnectionError(f"Connection failed: {str(e)}")

  def do_request(self, path_with_query: str, max_retries: int = 10) -> typing.Optional[dict]:
    for attempt in range(max_retries):
      try:
        self.ensure_connection()
        with self.lock:
          self.sock.sendall(f"{path_with_query}\n".encode())
          buffer = b""
          while True:
            chunk = self.sock.recv(4096)
            if not chunk:
              break
            buffer += chunk
            if b"\n" in buffer:
              response_line, _, buffer = buffer.partition(b"\n")
              return json.loads(response_line.decode())
      except (ConnectionResetError, BrokenPipeError, socket.timeout) as e:
        with self.lock:
          if self.sock:
            self.sock.close()
            self.sock = None
        if self.debug:
          print(f"Attempt {attempt + 1} failed: {str(e)}")
        time.sleep(0.1)
      except Exception as e:
        if self.debug:
          print(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
        time.sleep(0.05)
    return None

  def do_request_till_get_json(self, path_with_query: str) -> dict:
    if self.debug:
      print(f"#do_request_till_get_json {path_with_query} call {time.time()}")
    data = self.do_request(path_with_query)
    if data is None:
      print("Data is none, refreshing area")
      self.force_refresh_area()
      time.sleep(0.2)
      data = self.do_request(path_with_query)
      if data is None:
        raise Exception(f"Wrong reply from {path_with_query}")
    return data

  def force_refresh_area(self) -> dict:
    if self.debug:
      print(f"#ForceRefreshArea call {time.time()}")
    data = self.do_request_till_get_json("/ForceRefreshArea")
    if self.debug:
      print(f"#ForceRefreshArea return {time.time()}")
    return data

  def _endpoint_request(self, endpoint: str, params: typing.Optional[dict] = None) -> dict:
    path = f"/{endpoint}"
    if params:
      query = "&".join([f"{k}={v}" for k, v in params.items()])
      path += f"?{query}"
    return self.do_request_till_get_json(path)

  def forceRefreshArea(self):
    if self.debug:
      print(f"#ForceRefreshArea call {time.time()}")
    data = self.do_request_till_get_json("/ForceRefreshArea")
    if self.debug:
      print(f"#ForceRefreshArea return {time.time()}")
    return data

  # Common method pattern for all endpoints
  def _endpoint_request(self, endpoint: str, params: dict = None):
    path = f"/{endpoint}"
    if params:
      query = "&".join([f"{k}={v}" for k, v in params.items()])
      path += f"?{query}"
    return self.do_request_till_get_json(path)

  # Modified methods using new TCP communication
  def getUltimatumNextWaveUi(self):
    return self._endpoint_request("getUltimatumNextWaveUi")

  def getAnointUi(self):
    return self._endpoint_request("getAnointUi")

  def getNpcDialogueUi(self):
    return self._endpoint_request("getNpcDialogueUi")

  def getIncursionUi(self):
    return self._endpoint_request("getIncursionUi")

  def getMapInfo(self):
    return self._endpoint_request("getMapInfo")

  def getAuctionHouseUi(self):
    return self._endpoint_request("getAuctionHouseUi")

  def getWholeData(self):
    return self._endpoint_request("getData", {"type": "full"})

  def getPartialData(self):
    if self.poe_bot.debug:
      print(f"#PoeBot.getPartialData call {time.time()}")
    data = self._endpoint_request("getData")
    if self.poe_bot.debug:
      print(f"Data received: {len(str(data)) if data else 'None'}")
    self.last_data = data
    return data

  def getPositionOfThePointOnTheScreen(self, y, x):
    return self._endpoint_request("getScreenPos", {"y": y, "x": x})  # Fixed parameter order

  def getOpenedStashInfo(self):
    data = self._endpoint_request("getOpenedStashInfo")
    try:
      data["items"] = sorted(data["items"], key=lambda item: item["LocationTopLeft"]["Y"])
      data["items"] = sorted(data["items"], key=lambda item: item["LocationTopLeft"]["X"])
    except Exception:
      print("no items getOpenedStashInfo")
      pass
    return data

  def getOpenedInventoryInfo(self):
    data = self._endpoint_request("getInventoryInfo")
    try:
      data["items"] = sorted(data["items"], key=lambda item: item["g"][2])
      data["items"] = sorted(data["items"], key=lambda item: item["g"][0])
    except Exception:
      print("no items getOpenedInventoryInfo")
      pass
    return data

  def getMinimapIcons(self):
    return self._endpoint_request("getMinimapIcons")

  def getGemsToLevelInfo(self):
    return self._endpoint_request("gemsToLevel")

  def getHoveredItemInfo(self):
    return self._endpoint_request("getHoveredItemInfo")

  def getPreloadedFiles(self):
    return self._endpoint_request("getPreloadedFiles")

  def getNecropolisPopupUI(self):
    return self._endpoint_request("getNecropolisPopupUI")

  def getVisibleLabels(self):
    return self._endpoint_request("getVisibleLabels")

  def getItemsOnGroundLabelsVisible(self):
    return self._endpoint_request("getItemsOnGroundLabelsVisible")

  def getVisibleLabelOnGroundEntities(self):
    return self._endpoint_request("getVisibleLabelOnGroundEntities")

  def getWaypointState(self):
    return self._endpoint_request("getWaypointsState")

  def getSkillBar(self):
    return self._endpoint_request("getSkillBar")

  def getQuestStates(self):
    return self._endpoint_request("getQuestStates")

  def getQuestFlags(self):
    return self._endpoint_request("getQuestFlags")

  def mapDeviceInfo(self):
    return self._endpoint_request("mapDeviceInfo")

  def getBanditDialogueUi(self):
    return self._endpoint_request("getBanditDialogueUi")

  def getKirakMissionsUi(self):
    return self._endpoint_request("getKirakMissionsUi")

  def getPurchaseWindowHideoutUi(self):
    return self._endpoint_request("getPurchaseWindowHideoutUi")

  def getRitualUi(self):
    return self._endpoint_request("getRitualUi")

  def atlasProgress(self):
    return self._endpoint_request("getAtlasProgress")

  def getWorldMapUi(self):
    return self._endpoint_request("getWorldMapUi")

  def getResurrectUi(self):
    return self._endpoint_request("getResurrectUi")

  def getLocationOnScreen(self, x, y, z):
    return self._endpoint_request("getLocationOnScreen", {"x": x, "y": y, "z": z})

  def getEntityIdByPlayerName(self, entity_ign: str):
    return self._endpoint_request("getEntityIdByPlayerName", {"type": entity_ign})

  def getPartyInfo(self):
    return self._endpoint_request("getPartyInfo")


class ExCore2Sockets(Backend):
  def __init__(self, poe_bot: PoeBot, port: int = 50006):
    super().__init__(poe_bot, port)
    self.sending = False
    self.connected = False
    self.connect()

  def connect(self) -> None:
    if self.connected:
      return
    print(f"[ExCore2Sockets] Connecting to {self.host}:{self.port}")
    self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.s.settimeout(5)
    try:
      self.s.connect((self.host, self.port))
      self.connected = True
      if self.debug:
        print("[ExCore2Sockets] Connection established")
    except socket.error as e:
      print(f"Connection failed: {e}")
      raise Exception(f"Failed to connect to {self.host}:{self.port}")
