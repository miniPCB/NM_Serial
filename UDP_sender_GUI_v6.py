import sys
import os
import time
import socket
import threading
import subprocess
import sys
import pyvisa
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QListWidget, QTabWidget,
    QLabel, QHBoxLayout, QMessageBox, QSplitter, QMenu, QLineEdit, QFormLayout, QProgressBar
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QThread, pyqtSignal, QDateTime, Qt, QTimer

# Configure default directories (Modify these as needed)
UDP_COMMANDS_DIR = "./commands"  # Folder storing command files
SCOPESHOT_DIR = "./scopeshots"   # Folder to save oscilloscope images
LOG_DIR = "./logs"  # Folder to save logs

# Ensure the directories exist
os.makedirs(UDP_COMMANDS_DIR, exist_ok=True)
os.makedirs(SCOPESHOT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

class PingThread(QThread):
    ping_result = pyqtSignal(bool)
    progress_update = pyqtSignal(int)

    def __init__(self, scope_ip):
        super().__init__()
        self.scope_ip = scope_ip

    def run(self):
        """Ping the oscilloscope and emit connection status."""
        param = "-n" if sys.platform == "win32" else "-c"
        try:
            for i in range(1, 101, 20):
                self.progress_update.emit(i)
                time.sleep(0.1)
            result = subprocess.run(["ping", param, "1", self.scope_ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            connected = result.returncode == 0
        except Exception:
            connected = False
        self.progress_update.emit(100)
        self.ping_result.emit(connected)

class UdpSenderThread(QThread):
    log_signal = pyqtSignal(str)

    def __init__(self, filename, server_address, parent=None):
        super().__init__(parent)
        self.filename = filename
        self.server_address = server_address

    def capture_scopeshot(self, scopeshot_folder):
        """Capture a screenshot from the oscilloscope and save it to the scopeshot folder."""
        oscilloscope_ip = self.get_scope_ip()  # Retrieve oscilloscope IP from user input
        oscilloscope_resource = f"TCPIP0::{oscilloscope_ip}::INSTR"
        
        try:
            rm = pyvisa.ResourceManager()
            oscilloscope = rm.open_resource(oscilloscope_resource)
            oscilloscope.write(":DISPlay:DATA? PNG")  # SCPI Command to request screenshot data
            image_data = oscilloscope.read_raw()  # Read the raw image data

            # Generate a filename with timestamp including milliseconds
            timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss_zzz")
            image_path = os.path.join(scopeshot_folder, f"{timestamp}_scopeshot.png")

            with open(image_path, "wb") as img_file:
                img_file.write(image_data)

            self.log_signal.emit(f"Scopeshot saved: {image_path}")

        except Exception as e:
            self.log_signal.emit(f"Scopeshot error: {e}")

    def run(self):
        """Send UDP commands from the selected file and log to a file."""
        timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss_zzz")
        scopeshot_name = os.path.splitext(os.path.basename(self.filename))[0]  # Remove .txt
        log_filename = os.path.join(LOG_DIR, f"{timestamp}_{scopeshot_name}.txt")  # ✅ Fixed missing .txt extension
        scopeshot_folder = os.path.join(SCOPESHOT_DIR, f"{timestamp}_{scopeshot_name}")
        os.makedirs(scopeshot_folder, exist_ok=True)  # Ensure the scopeshot folder exists

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            with open(self.filename, 'r') as f, open(log_filename, 'w') as log_file:
                for line in f:
                    line = line.strip()

                    # Skip empty lines
                    if not line:
                        continue

                    # Handle Scopeshot Capture
                    if line.startswith("#SCOPE CAPTURE"):
                        log_entry = "Triggering Oscilloscope Capture...\n"
                        self.log_signal.emit(log_entry.strip())
                        log_file.write(log_entry)
                        self.capture_scopeshot(scopeshot_folder)  # ✅ Fixed incorrect argument count
                        continue  # Move to the next command

                    # Process Regular UDP Commands
                    line = line.split('#')[0].strip()  # Remove inline comments
                    if not line:
                        continue
                    try:
                        message = bytes.fromhex(line)
                        log_entry = f"Sending: {message}\n"
                        self.log_signal.emit(log_entry.strip())
                        log_file.write(log_entry)
                        sock.sendto(message, self.server_address)
                        time.sleep(1.0)
                    except Exception as e:
                        log_entry = f"Error sending command: {e}\n"
                        self.log_signal.emit(log_entry.strip())
                        log_file.write(log_entry)

                log_entry = "UDP Transmission Completed.\n"
                self.log_signal.emit(log_entry.strip())
                log_file.write(log_entry)

        except Exception as e:
            log_entry = f"UDP Error: {e}\n"
            self.log_signal.emit(log_entry.strip())
            with open(log_filename, 'a') as log_file:
                log_file.write(log_entry)
        finally:
            sock.close()

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

        # Setup Tab
        self.setup_tab = QWidget()
        setup_layout = QVBoxLayout()
        self.setup_tab.setLayout(setup_layout)
        self.tab_widget.addTab(self.setup_tab, "Setup")

        form_layout = QFormLayout()
        self.udp_ip_input = QLineEdit("192.168.1.221")  # Default UDP IP
        self.udp_port_input = QLineEdit("30206")  # Default UDP Port
        self.scope_ip_input = QLineEdit("192.168.1.100")  # Default Scope IP
        self.scope_username_input = QLineEdit("Administrator")  # Default Scope Username
        self.scope_password_input = QLineEdit("Keysight")  # Default Scope Password
        self.scope_password_input.setEchoMode(QLineEdit.EchoMode.Password)  # Hide password input
        
        # Add password visibility toggle button
        self.toggle_password_button = QPushButton("Show Password")
        self.toggle_password_button.setCheckable(True)
        self.toggle_password_button.toggled.connect(self.toggle_password_visibility)

        form_layout.addRow("UDP IP:", self.udp_ip_input)
        form_layout.addRow("UDP Port:", self.udp_port_input)
        form_layout.addRow("Oscilloscope IP:", self.scope_ip_input)
        form_layout.addRow("Oscilloscope Username:", self.scope_username_input)
        form_layout.addRow("Oscilloscope Password:", self.scope_password_input)
        form_layout.addRow("", self.toggle_password_button)  # Button aligned with password field
        
        # Connection Status Label
        self.connection_status = QLabel("OSCILLOSCOPE DISCONNECTED")
        self.connection_status.setFixedHeight(30)  # Set single-line height
        self.connection_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_connection_status(False)
        setup_layout.addWidget(self.connection_status)
        
        # Connection Progress Bar
        self.connection_progress = QProgressBar()
        self.connection_progress.setValue(0)
        setup_layout.addWidget(self.connection_progress)
        
        setup_layout.addLayout(form_layout)
        
        self.save_button = QPushButton("Save Settings")
        self.save_button.clicked.connect(self.save_settings)
        setup_layout.addWidget(self.save_button)

        self.check_connection_button = QPushButton("Check Connection")
        self.check_connection_button.clicked.connect(self.check_scope_connection)
        setup_layout.addWidget(self.check_connection_button)

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
        # Command Files Context Menu
        self.file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self.show_command_file_context_menu)

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
        scopeshots_layout = QVBoxLayout()
        self.scopeshots_tab.setLayout(scopeshots_layout)
        self.tab_widget.addTab(self.scopeshots_tab, "Scopeshots")

        # Splitter for scopeshots folder list and images
        scopeshot_splitter = QSplitter(Qt.Orientation.Horizontal)
        scopeshots_layout.addWidget(scopeshot_splitter)

        # Scopeshot Folder List on the left
        self.scopeshot_folder_list = QListWidget()  # ✅ THIS LINE INITIALIZES IT
        self.scopeshot_folder_list.itemSelectionChanged.connect(self.display_scopeshot_images)
        scopeshot_splitter.addWidget(self.scopeshot_folder_list)

        # Scopeshot Image List on the right
        self.scopeshot_image_list = QListWidget()
        self.scopeshot_image_list.itemSelectionChanged.connect(self.display_selected_scopeshot)
        self.scopeshot_image_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.scopeshot_image_list.customContextMenuRequested.connect(self.show_image_context_menu)  # ✅ Connect to context menu function
        scopeshot_splitter.addWidget(self.scopeshot_image_list)

        # Scopeshot Image Display on the right
        self.scopeshot_display = QLabel()
        self.scopeshot_display.setScaledContents(True)
        scopeshots_layout.addWidget(self.scopeshot_display)

        # Log Files Tab
        self.log_files_tab = QWidget()
        log_files_layout = QVBoxLayout()
        self.log_files_tab.setLayout(log_files_layout)
        self.tab_widget.addTab(self.log_files_tab, "Log Files")
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # Splitter for log file list and content
        log_splitter = QSplitter(Qt.Orientation.Horizontal)
        log_files_layout.addWidget(log_splitter)

        # Log Files List on the left
        self.log_file_list = QListWidget()
        self.load_log_files()
        self.log_file_list.itemSelectionChanged.connect(self.display_selected_log_file)
        log_splitter.addWidget(self.log_file_list)
        # Log Files Context Menu
        self.log_file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.log_file_list.customContextMenuRequested.connect(self.show_log_file_context_menu)

        # Log File Content Pane on the right
        self.log_file_content = QTextEdit()
        self.log_file_content.setReadOnly(True)
        log_splitter.addWidget(self.log_file_content)

    def get_scope_ip(self):
        """Retrieve the current oscilloscope IP from input field."""
        return self.scope_ip_input.text()
    
    def get_udp_address(self):
        """Retrieve the current UDP IP and Port from input fields."""
        return self.udp_ip_input.text(), int(self.udp_port_input.text())

    def toggle_password_visibility(self, checked):
        """Toggle password visibility."""
        if checked:
            self.scope_password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_password_button.setText("Hide Password")
        else:
            self.scope_password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_password_button.setText("Show Password")
    
    def update_connection_status(self, connected):
        """Update the connection status label color and text."""
        if connected:
            self.connection_status.setText("OSCILLOSCOPE CONNECTED")
            self.connection_status.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        else:
            self.connection_status.setText("OSCILLOSCOPE DISCONNECTED")
            self.connection_status.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        
        # Hide progress bar after 2 seconds
        QTimer.singleShot(2000, lambda: self.connection_progress.hide())
    
    def check_scope_connection(self):
        """Ping the oscilloscope asynchronously and update UI."""
        self.connection_progress.setValue(0)
        self.connection_progress.show()
        scope_ip = self.scope_ip_input.text()
        self.ping_thread = PingThread(scope_ip)
        self.ping_thread.ping_result.connect(self.update_connection_status)
        self.ping_thread.progress_update.connect(self.connection_progress.setValue)
        self.ping_thread.start()
    
    def save_settings(self):
        """Save settings for UDP and Oscilloscope."""
        udp_ip = self.udp_ip_input.text()
        udp_port = self.udp_port_input.text()
        scope_ip = self.scope_ip_input.text()
        scope_username = self.scope_username_input.text()
        scope_password = self.scope_password_input.text()
        
        settings = {
            "udp_ip": udp_ip,
            "udp_port": udp_port,
            "scope_ip": scope_ip,
            "scope_username": scope_username,
            "scope_password": scope_password
        }
        
        with open("settings.txt", "w") as f:
            for key, value in settings.items():
                f.write(f"{key}={value}\n")
        
        QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")

    def show_command_file_context_menu(self, position):
        """Show context menu for command files."""
        selected_item = self.file_list.currentItem()
        if not selected_item:
            return
        file_path = os.path.join(UDP_COMMANDS_DIR, selected_item.text())
        
        menu = QMenu()
        open_folder_action = menu.addAction("Open File Location")
        action = menu.exec(self.file_list.mapToGlobal(position))
        
        if action == open_folder_action:
            self.open_file_location(file_path)

    def show_log_file_context_menu(self, position):
        """Show context menu for log files."""
        selected_item = self.log_file_list.currentItem()
        if not selected_item:
            return
        file_path = os.path.join(LOG_DIR, selected_item.text())
        
        menu = QMenu()
        open_folder_action = menu.addAction("Open File Location")
        action = menu.exec(self.log_file_list.mapToGlobal(position))
        
        if action == open_folder_action:
            self.open_file_location(file_path)

    def show_image_context_menu(self, position):
        """Show context menu for scopeshot images."""
        selected_folder = self.scopeshot_folder_list.currentItem()
        selected_image = self.scopeshot_image_list.currentItem()
        
        if not selected_folder or not selected_image:
            return

        folder_path = os.path.join(SCOPESHOT_DIR, selected_folder.text())
        image_path = os.path.join(folder_path, selected_image.text())
        
        menu = QMenu()
        open_folder_action = menu.addAction("Open File Location")
        action = menu.exec(self.scopeshot_image_list.mapToGlobal(position))

        if action == open_folder_action:
            self.open_file_location(image_path)

    def open_file_location(self, file_path):
        """Open the file location in the system file explorer and highlight the file."""
        abs_file_path = os.path.abspath(file_path)
        abs_folder_path = os.path.dirname(abs_file_path)

        if sys.platform == "win32":
            subprocess.run(["explorer", "/select,", abs_file_path], check=False)
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", abs_file_path], check=False)
        else:
            subprocess.run(["xdg-open", abs_folder_path], check=False)

    def load_scopeshot_folders(self):
        """Load scopeshot folders into the list and prevent crashes if empty."""
        self.scopeshot_folder_list.clear()
        folders = sorted(os.listdir(SCOPESHOT_DIR))

        # If there are no folders, add a placeholder message
        if not folders:
            self.scopeshot_folder_list.addItem("(No Scopeshots Available)")
            return

        for folder in folders:
            folder_path = os.path.join(SCOPESHOT_DIR, folder)
            if os.path.isdir(folder_path):
                self.scopeshot_folder_list.addItem(folder)

    def display_scopeshot_images(self):
        """Display images from the selected scopeshot folder and prevent crashes if empty."""
        selected_item = self.scopeshot_folder_list.currentItem()
        
        # Prevent crash if no valid folder is selected
        if not selected_item or selected_item.text() == "(No Scopeshots Available)":
            self.scopeshot_image_list.clear()
            return

        folder_path = os.path.join(SCOPESHOT_DIR, selected_item.text())
        self.scopeshot_image_list.clear()
        
        images = [file for file in sorted(os.listdir(folder_path)) if file.lower().endswith(('.png', '.jpg', '.jpeg'))]

        # If there are no images, add a placeholder message
        if not images:
            self.scopeshot_image_list.addItem("(No Images Found)")
            return

        for image in images:
            self.scopeshot_image_list.addItem(image)

    def display_selected_scopeshot(self):
        """Display the selected scopeshot image and prevent crashes if none exist."""
        selected_folder = self.scopeshot_folder_list.currentItem()
        selected_image = self.scopeshot_image_list.currentItem()

        # Prevent crash if no folder or image is selected
        if not selected_folder or not selected_image or selected_image.text() == "(No Images Found)":
            self.scopeshot_display.clear()
            return

        image_path = os.path.join(SCOPESHOT_DIR, selected_folder.text(), selected_image.text())
        pixmap = QPixmap(image_path)
        self.scopeshot_display.setPixmap(pixmap)

    def on_tab_changed(self, index):
        """Reload log files and scopeshots when their respective tabs are selected."""
        if self.tab_widget.tabText(index) == "Log Files":
            self.load_log_files()
        elif self.tab_widget.tabText(index) == "Scopeshots":
            self.load_scopeshot_folders()

    def load_files(self):
        """Load command files into the file list."""
        self.file_list.clear()
        for file in os.listdir(UDP_COMMANDS_DIR):
            if file.endswith(".txt"):
                self.file_list.addItem(file)

    def load_log_files(self):
        """Load log files into the log file list."""
        self.log_file_list.clear()
        for file in os.listdir(LOG_DIR):
            if file.endswith(".txt"):
                self.log_file_list.addItem(file)

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

    def display_selected_log_file(self):
        """Display the contents of the selected log file."""
        selected_item = self.log_file_list.currentItem()
        if not selected_item:
            self.log_file_content.clear()
            return
        filename = os.path.join(LOG_DIR, selected_item.text())
        try:
            with open(filename, 'r') as f:
                content = f.read()
            self.log_file_content.setText(content)
        except Exception as e:
            self.log_file_content.setText(f"Error reading file: {e}")
    
    def send_selected_commands(self):
        """Send the selected command file via UDP."""
        selected_item = self.file_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Warning", "No file selected!")
            return
        filename = os.path.join(UDP_COMMANDS_DIR, selected_item.text())
        #server_address = ('192.168.0.11', 5005)  # Update as needed
        server_address = self.get_udp_address()
        
        self.log_pane.append(f"Sending commands from {filename}")
        self.udp_thread = UdpSenderThread(filename, server_address)
        self.udp_thread.log_signal.connect(self.log_pane.append)
        self.udp_thread.start()
    
    def clear_log(self):
        """Clear the log pane."""
        self.log_pane.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
