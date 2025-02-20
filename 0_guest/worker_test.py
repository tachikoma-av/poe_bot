import socket

import requests as req

requests = req.Session()
requests.trust_env = False


def Main():
  serverPort = 50007
  serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  serverSocket.bind(("", serverPort))
  serverSocket.listen(1)
  print("The server is ready to recieve")
  connectionSocket, addr = serverSocket.accept()

  # Destroy the server socket; we don't need it anymore since we are not
  # accepting any connections beyond this point.
  serverSocket.close()

  while True:
    sentence = connectionSocket.recv(1024).decode()
    if sentence == "close":
      connectionSocket.close()
      break
    capSentence = sentence.upper()
    connectionSocket.send(capSentence.encode())


Main()
