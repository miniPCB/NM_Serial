import os
import socket
import json
import time

# Author: Nolan Manteufel

CONFIG_FILE = "udp_config.json"
COMMANDS_FOLDER = "commands"

def clear_screen():
    """Clear the terminal screen for a cleaner UI."""
    os.system('cls' if os.name == 'nt' else 'clear')

def save_config(udp_ip, udp_port):
    """Save UDP configuration to a JSON file."""
    config = {"udp_ip": udp_ip, "udp_port": udp_port}
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file)

def load_config():
    """Load UDP configuration from a JSON file if available."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    return None

def list_files():
    """List all files in the commands directory."""
    try:
        if not os.path.exists(COMMANDS_FOLDER):
            os.makedirs(COMMANDS_FOLDER)
        files = [f for f in os.listdir(COMMANDS_FOLDER) if os.path.isfile(os.path.join(COMMANDS_FOLDER, f))]
        return files
    except FileNotFoundError:
        print("Commands directory not found.")
        return []

def send_udp_command(file_path, udp_ip, udp_port):
    """Send the contents of a selected file as UDP packets, skipping commented lines and adding a delay between commands."""
    try:
        with open(file_path, 'r') as file:
            lines = [line.strip() for line in file.readlines() if not line.strip().startswith('#')]
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        for line in lines:
            if line:
                sock.sendto(line.encode(), (udp_ip, udp_port))
                print(f"Sent: {line}")
                time.sleep(2)  # Delay of 2 seconds between commands
        
        print(f"Finished sending data from {file_path} to {udp_ip}:{udp_port}")
        sock.close()
    except Exception as e:
        print(f"Error sending UDP data: {e}")

def main():
    ascii_header = """
    ******************************************
    *        UDP Command File Sender         *
    ******************************************
    """
    
    config = load_config()
    
    if config:
        print(ascii_header)
        print(f"Loaded saved configuration: {config['udp_ip']}:{config['udp_port']}")
        use_saved = input("Use saved configuration? (Y/N): ").strip().lower()
        if use_saved == 'y':
            udp_ip, udp_port = config['udp_ip'], config['udp_port']
        else:
            udp_ip = input("Enter UDP target IP address: ")
            udp_port = int(input("Enter UDP target port: "))
            save_config(udp_ip, udp_port)
    else:
        udp_ip = input("Enter UDP target IP address: ")
        udp_port = int(input("Enter UDP target port: "))
        save_config(udp_ip, udp_port)
    
    while True:
        clear_screen()
        print(ascii_header)
        print("\nAvailable command files:")
        files = list_files()
        
        if not files:
            print("No files found.")
        else:
            for idx, file in enumerate(files, 1):
                print(f"{idx}. {file}")
        
        print("0. Refresh file list")
        print("Q. Quit")
        choice = input("Select a file number to send or an option: ")
        
        if choice.lower() == 'q':
            break
        elif choice == '0':
            continue
        
        try:
            file_idx = int(choice) - 1
            if 0 <= file_idx < len(files):
                file_path = os.path.join(COMMANDS_FOLDER, files[file_idx])
                send_udp_command(file_path, udp_ip, udp_port)
            else:
                print("Invalid selection. Please enter a number from the list.")
        except ValueError:
            print("Invalid input. Please enter a valid number corresponding to a file.")
        
        input("Press Enter to continue...")

if __name__ == "__main__":
    main()
