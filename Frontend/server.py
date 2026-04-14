# note from viktor -
    # i can not confirm this is the most efficient way to do this
    # therefore i will not claim it is
    # i also am not claiming this is even the second least efficient way
import socket
from threading import Thread

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5002
separator_token = "<SEP>"

client_sockets = set()
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((SERVER_HOST, SERVER_PORT))
s.listen(5)


print(f"[*] Listening as {SERVER_HOST}:{SERVER_PORT}")


def listen_for_client(cs):
  while True:
    try:
      # listen for a message
      msg = cs.recv(1024).decode()
    except Exception as e:
      # if they disconnect
      print(f"Error: {e}")
      client_sockets.remove(cs)
    else:
      # receive a message
      msg = msg.replace(separator_token, ": ")
    for client_socket in client_sockets:
      # actually sending the message
      client_socket.send(msg.encode())

while True:
    client_socket, client_address = s.accept()
    print(f"{client_address} accepted.")
    client_sockets.add(client_socket)

    t = Thread(target=listen_for_client, args=(client_socket,))
    t.daemon = True
    t.start()

for cs in client_sockets:
     cs.close()
s.close()
