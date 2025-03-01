import sys
import os
import time
import socket
import threading
import pyvisa  # Required for Keysight oscilloscope integration
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, 
    QTextEdit, QListWidget, QTabWidget, QLabel, QHBoxLayout, QMessageBox
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QThread, pyqtSignal, QDateTime

# Configure default directories (Modify these as needed)
UDP_COMMANDS_DIR = "./commands"  # Folder storing command files
SCOPESHOT_DIR = "./scopeshots"   # Folder to save oscilloscope images

# Ensure the directories exist
os.makedirs(UDP_COMMANDS_DIR, exist_ok=True)
os.makedirs(SCOPESHOT_DIR, exist_ok=True)

class UdpSenderThread(QThread):
    log_signal = pyqtSignal(str)

    def __init__(self, filename, server_address, parent=None):
        super().__init__(parent)  # Pass the optional parent argument
        self.filename = filename
        self.server_address = server_address

    def run(self):
        """Send UDP commands from the selected file."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            with open(self.filename, 'r') as f:
                for line in f:
                    line = line.strip().split('#')[0].strip()  # Remove inline comments
                    if not line:
                        continue  # Skip empty lines
                    try:
                        message = bytes.fromhex(line)  # Convert hex to bytes
                        self.log_signal.emit(f"Sending: {message}")
                        sock.sendto(message, self.server_address)
                        time.sleep(1.0)
                    except Exception as e:
                        self.log_signal.emit(f"Error sending command: {e}")
            sock.close()
            self.log_signal.emit("UDP Transmission Completed.")
        except Exception as e:
            self.log_signal.emit(f"UDP Error: {e}")

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UDP Command Sender")
        self.resize(800, 600)

        # Layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # File List Pane
        self.file_list = QListWidget()
        self.load_files()
        layout.addWidget(self.file_list)

        # Buttons Layout
        button_layout = QHBoxLayout()
        
        # Button to send selected commands
        self.send_button = QPushButton("Send Selected Commands")
        self.send_button.clicked.connect(self.send_selected_commands)
        button_layout.addWidget(self.send_button)
        
        # Button to clear log
        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self.clear_log)
        button_layout.addWidget(self.clear_log_button)
        
        layout.addLayout(button_layout)

        # Log Pane
        self.log_pane = QTextEdit()
        self.log_pane.setReadOnly(True)
        layout.addWidget(self.log_pane)

        # Oscilloscope Control
        self.scope_button = QPushButton("Capture Scopeshot")
        self.scope_button.clicked.connect(self.capture_scopeshot)
        layout.addWidget(self.scope_button)

        # Tab Widget for Scopeshots
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

    def load_files(self):
        """Load command files into the file list."""
        self.file_list.clear()
        for file in os.listdir(UDP_COMMANDS_DIR):
            if file.endswith(".txt"):  # Ensure only text files are shown
                self.file_list.addItem(file)

    def log(self, message):
        """Log messages to the GUI log pane."""
        self.log_pane.append(message)
    
    def clear_log(self):
        """Clear the log pane."""
        self.log_pane.clear()

    def send_selected_commands(self):
        """Send the selected command file via UDP."""
        selected_item = self.file_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Warning", "No file selected!")
            return
        filename = os.path.join(UDP_COMMANDS_DIR, selected_item.text())
        server_address = ('192.168.1.221', 30206)  # Modify IP and port if needed
        
        self.log(f"Sending commands from {filename}")
        self.udp_thread = UdpSenderThread(filename, server_address)
        self.udp_thread.log_signal.connect(self.log)
        self.udp_thread.start()

    def capture_scopeshot(self):
        """Capture and save a scopeshot from the Keysight oscilloscope."""
        timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss")
        image_path = os.path.join(SCOPESHOT_DIR, f"scopeshot_{timestamp}.png")

        try:
            rm = pyvisa.ResourceManager()
            oscilloscope = rm.open_resource("TCPIP0::192.168.1.100::INSTR")  # Modify IP
            oscilloscope.write(":DISPlay:DATA? PNG")
            image_data = oscilloscope.read_raw()
            with open(image_path, "wb") as img_file:
                img_file.write(image_data)
            self.log(f"Scopeshot saved: {image_path}")
            self.display_image(image_path)
        except Exception as e:
            self.log(f"Scopeshot error: {e}")

    def display_image(self, image_path):
        """Display captured scopeshot in a new tab."""
        tab_name = os.path.basename(image_path)
        label = QLabel()
        pixmap = QPixmap(image_path)
        label.setPixmap(pixmap)
        label.setScaledContents(True)
        self.tab_widget.addTab(label, tab_name)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
