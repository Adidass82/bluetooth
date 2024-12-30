from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QListWidget, QLabel, QWidget
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from bleak import BleakScanner, BleakClient
import bluetooth  # Klasszikus Bluetooth támogatáshoz
import asyncio
import logging
import sys
import re

logging.basicConfig(level=logging.DEBUG)

class DeviceScanner(QThread):
    devices_found = pyqtSignal(list)

    def run(self):
        asyncio.run(self.scan_devices())

    async def scan_devices(self):
        devices = await BleakScanner.discover(timeout=5.0)
        device_list = [f"{d.name} ({d.address})" for d in devices ]
        self.devices_found.emit(device_list)

class BluetoothApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bluetooth Manager")
        self.setGeometry(200, 200, 800, 800)
        self.initUI()
        self.client = None  # BLE client inicializálása

    def initUI(self):
        # Main layout
        central_widget = QWidget()
        layout = QVBoxLayout()
        
        # Bluetooth scanning button
        self.scan_button = QPushButton("Keresés")
        self.scan_button.clicked.connect(self.start_device_scan)
        layout.addWidget(self.scan_button)
        
        # Device list
        self.device_list = QListWidget()
        layout.addWidget(self.device_list)
        
        # Connect button
        self.connect_button = QPushButton("Kapcsolódás a választott eszközhöz")
        self.connect_button.clicked.connect(self.connect_device)
        layout.addWidget(self.connect_button)
        
        # Status label
        self.status_label = QLabel("Status: Kész")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Status indicator
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(100, 30)
        self.status_indicator.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_indicator)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def start_device_scan(self):
        self.device_list.clear()
        self.status_label.setText("Eszközök keresése...")
        self.status_indicator.setStyleSheet("background-color: yellow;")  # Kapcsolódás alatt
        self.thread = DeviceScanner()
        self.thread.devices_found.connect(self.update_device_list)
        self.thread.start()

    def update_device_list(self, devices):
        if devices:
            self.device_list.addItems(devices)
            self.status_label.setText("Keresés kész")
            self.status_indicator.setStyleSheet("background-color: green;")  # Keresés kész
        else:
            self.status_label.setText("Nem található Bluetooth eszköz.")
            self.status_indicator.setStyleSheet("background-color: red;")  # Nincs eszköz

    def connect_device(self):
        selected_item = self.device_list.currentItem()
        if selected_item:
            device_address = selected_item.text().split("(")[1].strip(")")
            self.status_label.setText(f"Kapcsolódás a {selected_item.text()}...")
            self.status_indicator.setStyleSheet("background-color: yellow;")  # Kapcsolódás alatt
            if "BLE" in selected_item.text():  # BLE eszköz
                asyncio.run(self.connect_to_device(device_address))
            else:  # Klasszikus Bluetooth eszköz
                self.connect_classic_bluetooth(device_address)
        else:
            self.status_label.setText("Nincs kiválasztott eszköz!")
            self.status_indicator.setStyleSheet("background-color: red;")  # Nincs eszköz

    async def connect_to_device(self, address):
        try:
            async with BleakClient(address) as client:
                self.client = client
                self.status_label.setText(f"Sikeresen csatlakozva: {address}")
                self.status_indicator.setStyleSheet("background-color: green;")  # Sikeres kapcsolat
                await asyncio.sleep(5)  # Példa: várakozás 5 másodpercig
                await self.run_commands()
        except Exception as e:
            self.status_label.setText(f"Hiba a csatlakozás során: {str(e)}")
            self.status_indicator.setStyleSheet("background-color: red;")  # Hiba

    def connect_classic_bluetooth(self, address):
        try:
            print(f"Klasszikus Bluetooth kapcsolódás megkezdése: {address}")
            if not re.match(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", address):
                print("Érvénytelen MAC cím formátum!")
                return
            
            # Bluetooth adapter ellenőrzése
            socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            socket.connect((address, 1))  # Csatlakozás az első RFCOMM porthoz
            self.status_label.setText(f"Sikeresen csatlakozva klasszikus Bluetooth eszközhöz: {address}")
            self.status_indicator.setStyleSheet("background-color: green;")  # Sikeres kapcsolat
            socket.close()  # Kapcsolat lezárása
        except Exception as e:
            self.status_label.setText(f"Hiba a klasszikus Bluetooth csatlakozás során: {str(e)}")
            self.status_indicator.setStyleSheet("background-color: red;")  # Hiba

    async def run_commands(self):
        # Itt implementálhatod a további parancsokat
        self.status_label.setText("Parancsok futtatása...")
        await asyncio.sleep(2)  # Példa: várakozás 2 másodpercig
        self.status_label.setText("Parancsok befejezve.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BluetoothApp()
    window.show()
    sys.exit(app.exec_())
