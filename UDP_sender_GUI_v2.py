import sys
import os
import time
import socket
import threading
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QListWidget, QTabWidget, QLabel, QHBoxLayout, QMessageBox, QSplitter
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QThread, pyqtSignal, QDateTime, Qt

# Configure default directories (Modify these as needed)
UDP_COMMANDS_DIR = "./commands"  # Folder storing command files
SCOPESHOT_DIR = "./scopeshots"   # Folder to save oscilloscope images

# Ensure the directories exist
os.makedirs(UDP_COMMANDS_DIR, exist_ok=True)
os.makedirs(SCOPESHOT_DIR, exist_ok=True)

class UdpSenderThread(QThread):
    log_signal = pyqtSignal(str)

    def __init__(self, filename, server_address, parent=None):
        super().__init__(parent)
        self.filename = filename
        self.server_address = server_address

    def run(self):
        """Send UDP commands from the selected file."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            with open(self.filename, 'r') as f:
                for line in f:
                    line = line.strip().split('#')[0].strip()
                    if not line:
                        continue
                    try:
                        message = bytes.fromhex(line)
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

        # Tab Widget
        self.tab_widget = QTabWidget()
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)

        # Tests Tab
        self.tests_tab = QWidget()
        tests_layout = QVBoxLayout()
        self.tests_tab.setLayout(tests_layout)
        self.tab_widget.addTab(self.tests_tab, "Tests")

        # Splitter for file list and file content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        tests_layout.addWidget(splitter)

        # File List Pane
        self.file_list = QListWidget()
        self.load_files()
        self.file_list.itemSelectionChanged.connect(self.display_selected_file)
        splitter.addWidget(self.file_list)

        # File Content Pane
        self.file_content = QTextEdit()
        self.file_content.setReadOnly(True)
        splitter.addWidget(self.file_content)

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
        
        tests_layout.addLayout(button_layout)

        # Log Pane
        self.log_pane = QTextEdit()
        self.log_pane.setReadOnly(True)
        tests_layout.addWidget(self.log_pane)

        # Scopeshots Tab
        self.scopeshots_tab = QWidget()
        self.scopeshots_layout = QVBoxLayout()
        self.scopeshots_tab.setLayout(self.scopeshots_layout)
        self.tab_widget.addTab(self.scopeshots_tab, "Scopeshots")

    def load_files(self):
        """Load command files into the file list."""
        self.file_list.clear()
        for file in os.listdir(UDP_COMMANDS_DIR):
            if file.endswith(".txt"):
                self.file_list.addItem(file)

    def display_selected_file(self):
        """Display the contents of the selected command file."""
        selected_item = self.file_list.currentItem()
        if not selected_item:
            self.file_content.clear()
            return
        filename = os.path.join(UDP_COMMANDS_DIR, selected_item.text())
        try:
            with open(filename, 'r') as f:
                content = f.read()
            self.file_content.setText(content)
        except Exception as e:
            self.file_content.setText(f"Error reading file: {e}")

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
        server_address = ('192.168.1.221', 30206)
        
        self.log(f"Sending commands from {filename}")
        self.udp_thread = UdpSenderThread(filename, server_address)
        self.udp_thread.log_signal.connect(self.log)
        self.udp_thread.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())