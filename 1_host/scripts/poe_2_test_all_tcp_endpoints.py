import json
import socket
import sys

HOSTNAME = "WIN-POE1"
HOST = socket.gethostbyname(HOSTNAME)  # or ip
PORT = 50006


def read_response(sock):
  buffer = bytearray()
  while True:
    chunk = sock.recv(4096)
    if not chunk:
      break
    buffer.extend(chunk)
    if b"\n" in buffer:
      index = buffer.index(b"\n")
      data = buffer[:index]
      del buffer[: index + 1]
      return data.decode("utf-8-sig").rstrip("\r")
  return buffer.decode("utf-8-sig") if buffer else ""


def send_request(sock, path, params=None):
  request = path
  if params:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    request += f"?{query}"
  request += "\n"
  sock.sendall(request.encode("utf-8"))
  return read_response(sock)


def parse_response(response):
  if not response:
    return {}
  try:
    return json.loads(response)
  except json.JSONDecodeError:
    return {"error": "Invalid JSON", "raw_response": response}


def check_endpoint(sock, endpoint):
  response = send_request(sock, endpoint)
  parsed = parse_response(response)
  return {
    "endpoint": endpoint,
    "status": "success" if "error" not in parsed else "failed",
    "response": parsed,
  }


if __name__ == "__main__":
  results = []

  if len(sys.argv) > 1:
    ENDPOINTS = [sys.argv[1]]
  else:
    ENDPOINTS = [
      "/getData",
      "/getInventoryInfo",
      "/getOpenedStashInfo",
      "/gemsToLevel",
      "/getVisibleLabelOnGroundEntities",
      "/getItemsOnGroundLabelsVisible",
      "/mapDeviceInfo",
      "/getAtlasProgress",
      "/getVisibleLabels",
      "/getHoveredItemInfo",
      "/getSkillBar",
      "/getQuestStates", #TODO: check
      "/getWaypointsState", #TODO: check
      "/getMinimapIcons",
      "/getRitualUi", #TODO: check
      "/getWorldMapUi",
      "/getResurrectUi", #TODO: check
      "/getPurchaseWindowHideoutUi", #TODO: check
      "/getKirakMissionsUi", #TODO: check
      "/getQuestFlags", #TODO: check
      "/getAuctionHouseUi", #TODO: check
      "/getBanditDialogueUi", #TODO: check
      "/ForceRefreshArea",
      "/getNecropolisPopupUI", #TODO: check
      "/getMapInfo",
      "/getAnointUi", #TODO: check
      "/getEntityIdByPlayerName",
      "/getPartyInfo",
      "/getNpcDialogueUi", #TODO: check
    ]

  for endpoint in ENDPOINTS:
    try:
      with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        result = check_endpoint(s, endpoint)
    except Exception as e:
      result = {"endpoint": endpoint, "status": "failed", "response": {"error": str(e)}}
    results.append(result)
    print(json.dumps(result, indent=2))

  # Print summary
  print("\nSummary:")
  for result in results:
    print(f"{result['endpoint']}: {result['status']}")
