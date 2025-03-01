import socket
import sys
import time
import _thread
import argparse

def send_commands():
    global bDone

    #Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #Setup server address: IP, Port
    server_address = ('192.168.1.221',30206)
    #Get message(s)
    with open (filename) as f:
        content = f.readlines()
        for x in content:
            try:
                print(x)
                if(x[0] == "#"):
                    print(x[1:].strip())
                else:
                    print("sending packet")
                    time.sleep(1.0)
                    message = bytes.fromhex(x)
                    print('sending "%s"' & message)
                    sent = sock.sendto(message, server_address)
            except:
                print("Exception")
                bDone = True
        sock.close()
        bDone = True

if __name__=="__main__":
    global bDone
    bDone = False
    parser = argparse.ArgumentParser("simple example")
    parser.add_argument("file", help="file path for UDP command", type=str)
    args = parser.parse_args()
    filename = args.file
    print("In main about to thread it")
    #Send lines of text file as UDP commands
    _thread.start_new_thread(send_commands,())

    while not bDone:
        pass

    time.sleep(1.0)
    print("End of main")
