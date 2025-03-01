import socket
import sys
import time
import threading
import argparse

def send_commands(filename, stop_event):
    """Send UDP commands from a file to the target server."""
    try:
        # Create a UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_address = ('192.168.1.221', 30206)

        # Read the file line by line
        with open(filename, 'r') as f:
            content = f.readlines()
            for x in content:
                try:
                    x = x.strip()  # Remove trailing newline and spaces
                    if not x:  # Skip empty lines
                        continue

                    if x[0] == "#":
                        print(x[1:].strip())  # Print comment lines
                    else:
                        print("Sending packet")
                        time.sleep(1.0)
                        message = bytes.fromhex(x)  # Convert hex string to bytes
                        print(f'Sending "{message}"')
                        sock.sendto(message, server_address)
                except Exception as e:
                    print(f"Exception: {e}")

        sock.close()
    finally:
        stop_event.set()  # Signal the main thread that we're done

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send UDP commands from a file.")
    parser.add_argument("file", help="File path containing UDP command hex strings", type=str)
    args = parser.parse_args()
    filename = args.file

    stop_event = threading.Event()
    
    print("Starting UDP command sender thread...")
    sender_thread = threading.Thread(target=send_commands, args=(filename, stop_event))
    sender_thread.start()

    # Wait for the thread to complete
    stop_event.wait()

    print("End of main")
