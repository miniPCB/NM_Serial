import sys
import os
import json
import subprocess
import socket
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QLineEdit, QPushButton,
    QTreeView, QTextEdit, QSplitter, QMenu
)
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import Qt, QPoint

SETTINGS_FILE = "settings.json"
COMMANDS_FOLDER = "commands"

class UDPTestApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UDP Test GUI")
        self.resize(800, 600)

        self.tabs = QTabWidget()
        self.setup_tab = QWidget()
        self.testing_tab = QWidget()
        
        self.tabs.addTab(self.setup_tab, "Setup")
        self.tabs.addTab(self.testing_tab, "Testing")
        
        self.init_setup_tab()
        self.init_testing_tab()
        
        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        
        self.load_settings()

    def init_setup_tab(self):
        layout = QVBoxLayout()
        form_layout = QHBoxLayout()
        
        self.ip_label = QLabel("UDP IP:")
        self.ip_input = QLineEdit()
        self.port_label = QLabel("UDP Port:")
        self.port_input = QLineEdit()
        self.save_button = QPushButton("Save Form")
        self.save_button.clicked.connect(self.save_settings)
        
        form_layout.addWidget(self.ip_label)
        form_layout.addWidget(self.ip_input)
        form_layout.addWidget(self.port_label)
        form_layout.addWidget(self.port_input)
        form_layout.addWidget(self.save_button)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        self.setup_tab.setLayout(layout)

    def init_testing_tab(self):
        layout = QVBoxLayout()

        # File browser pane
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath(COMMANDS_FOLDER)
        self.file_view = QTreeView()
        self.file_view.setModel(self.file_model)
        self.file_view.setRootIndex(self.file_model.index(COMMANDS_FOLDER))
        self.file_view.clicked.connect(self.load_script_contents)
        self.file_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_view.customContextMenuRequested.connect(self.show_file_context_menu)
        
        # Buttons layout
        button_layout = QHBoxLayout()
        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self.clear_log)
        self.run_test_button = QPushButton("Run Test")
        self.run_test_button.clicked.connect(self.run_test)
        button_layout.addWidget(self.run_test_button)
        button_layout.addWidget(self.clear_log_button)
        
        # Horizontal splitter for script content and log pane
        script_log_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Script content pane
        self.script_content = QTextEdit()
        self.script_content.setReadOnly(True)
        
        # Log output pane
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        
        script_log_splitter.addWidget(self.script_content)
        script_log_splitter.addWidget(self.log_output)
        
        layout.addWidget(self.file_view)
        layout.addLayout(button_layout)
        layout.addWidget(script_log_splitter)
        
        self.testing_tab.setLayout(layout)

    def load_script_contents(self, index):
        self.selected_file_path = self.file_model.filePath(index)
        if os.path.isfile(self.selected_file_path):
            with open(self.selected_file_path, "r", encoding="utf-8") as f:
                self.script_content.setText(f.read())

    def clear_log(self):
        self.log_output.clear()

    def run_test(self):
        udp_ip = self.ip_input.text()
        udp_port = self.port_input.text()
        
        if not udp_ip or not udp_port:
            self.log_output.append("Error: UDP IP and Port must be set.")
            return
        
        try:
            udp_port = int(udp_port)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except ValueError:
            self.log_output.append("Error: Invalid UDP Port.")
            return
        
        if hasattr(self, 'selected_file_path') and os.path.isfile(self.selected_file_path):
            with open(self.selected_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    command = line.strip()
                    if not command or command.startswith("#"):
                        continue  # Skip empty lines and comments
                    sock.sendto(command.encode(), (udp_ip, udp_port))
                    self.log_output.append(f"Sent: {command}")
            sock.close()
        else:
            self.log_output.append("Error: No command file selected.")

    def show_file_context_menu(self, position: QPoint):
        index = self.file_view.indexAt(position)
        if not index.isValid():
            return
        
        file_path = self.file_model.filePath(index)
        menu = QMenu(self)
        open_location_action = menu.addAction("Open File Location")
        action = menu.exec(self.file_view.viewport().mapToGlobal(position))
        
        if action == open_location_action:
            self.open_file_location(file_path)

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

    def save_settings(self):
        settings = {
            "udp_ip": self.ip_input.text(),
            "udp_port": self.port_input.text()
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
                self.ip_input.setText(settings.get("udp_ip", ""))
                self.port_input.setText(settings.get("udp_port", ""))

if __name__ == "__main__":
    if not os.path.exists(COMMANDS_FOLDER):
        os.makedirs(COMMANDS_FOLDER)
    
    app = QApplication(sys.argv)
    window = UDPTestApp()
    window.show()
    sys.exit(app.exec())
