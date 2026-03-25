import socket
c = socket.socket()
c.connect(("localhost", 8888))
print(c.recv(1024).decode())
while 1:
    c.send(input("\n> ").encode())
    r = c.recv(4096).decode()
    if r == "OK": continue
    print(r)