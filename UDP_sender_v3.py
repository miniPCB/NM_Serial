import socket

UDP_IP = "192.168.1.20"  # Replace with your Raspberry Pi’s IP
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

message = b"Hello from Windows!"
sock.sendto(message, (UDP_IP, UDP_PORT))

print("Message sent!")
