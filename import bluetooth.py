from bleak import BleakScanner, BleakClient
import asyncio
import logging
import platform
import socket
import bluetooth  # Klasszikus Bluetooth támogatáshoz

logging.basicConfig(level=logging.DEBUG)

def classic_bluetooth_connect(address):
    try:
        print(f"Klasszikus Bluetooth kapcsolódás megkezdése: {address}")
        
        # Ellenőrizzük, hogy az eszköz elérhető-e
        if not bluetooth.is_valid_address(address):
            print("Érvénytelen Bluetooth cím!")
            return None
            
        # Port keresése
        available_ports = []
        for port in range(1, 30):
            try:
                sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
                sock.connect((address, port))
                available_ports.append(port)
                sock.close()
            except:
                pass
                
        if not available_ports:
            print("Nem található elérhető port az eszközön!")
            return None
            
        # Kapcsolódás az első elérhető porton
        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        sock.connect((address, available_ports[0]))
        print(f"Klasszikus Bluetooth kapcsolat létrejött a {available_ports[0]} porton!")
        return sock
        
    except bluetooth.btcommon.BluetoothError as be:
        print(f"Bluetooth specifikus hiba: {str(be)}")
        print("Kérem ellenőrizze:")
        print("1. Az eszköz be van kapcsolva")
        print("2. Az eszköz párosítási módban van")
        print("3. A Bluetooth adapter be van kapcsolva a számítógépen")
        return None
    except Exception as e:
        print(f"Klasszikus Bluetooth kapcsolódási hiba: {str(e)}")
        return None

async def ble_connect_with_retry(address, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            print(f"\nBLE Csatlakozási kísérlet {attempt + 1}/{max_attempts}")
            client = BleakClient(address, timeout=20.0)
            await client.connect(timeout=20.0)
            return client
        except Exception as e:
            print(f"BLE Kísérlet {attempt + 1} sikertelen: {str(e)}")
            if attempt < max_attempts - 1:
                print("Újrapróbálkozás 5 másodperc múlva...")
                await asyncio.sleep(5)
    return None

async def main():
    print("Bluetooth eszközök keresése...")
    print(f"Operációs rendszer: {platform.system()} {platform.release()}")
    
    try:
        # BLE eszközök keresése
        print("\nBLE eszközök keresése...")
        ble_devices = await BleakScanner.discover(timeout=10.0)
        
        # Klasszikus Bluetooth eszközök keresése
        print("\nKlasszikus Bluetooth eszközök keresése...")
        classic_devices = bluetooth.discover_devices(lookup_names=True)
        
        all_devices = []
        
        # BLE eszközök hozzáadása a listához
        for device in ble_devices:
            all_devices.append({
                'name': device.name,
                'address': device.address,
                'type': 'BLE'
            })
        
        # Klasszikus Bluetooth eszközök hozzáadása a listához
        for device in classic_devices:
            all_devices.append({
                'name': device[1],
                'address': device[0],
                'type': 'Classic'
            })
        
        if not all_devices:
            print("Nem található bluetooth eszköz a közelben")
            return
            
        print("\nTalált eszközök:")
        for i, device in enumerate(all_devices, 1):
            print(f"{i}. {device['name'] or 'Ismeretlen eszköz'} ({device['address']})")
            print(f"   Típus: {device['type']}")
            # Az RSSI és metadata csak BLE eszközöknél érhető el
            if device['type'] == 'BLE':
                original_device = next(d for d in ble_devices if d.address == device['address'])
                print(f"   RSSI: {original_device.rssi} dBm")
                print(f"   Metadata: {original_device.metadata}")
                if hasattr(original_device, 'details'):
                    print(f"   Details: {original_device.details}")
        
        választás = int(input("\nVálasszon egy eszközt (írja be a számát): ")) - 1
        if választás < 0 or választás >= len(all_devices):
            print("Érvénytelen választás!")
            return
                
        kiválasztott_eszköz = all_devices[választás]
        print(f"\nKiválasztott eszköz: {kiválasztott_eszköz['name'] or 'Ismeretlen eszköz'}")
        print(f"Eszköz címe: {kiválasztott_eszköz['address']}")
        
        if kiválasztott_eszköz['type'] == 'BLE':
            client = await ble_connect_with_retry(kiválasztott_eszköz['address'])
            if client and client.is_connected:
                print("\nSikeresen csatlakozva BLE eszközhöz!")
                try:
                    # BLE specifikus műveletek
                    services = await client.get_services()
                    print("\nElérhető szolgáltatások:")
                    for service in services:
                        print(f"\nService: {service.uuid}")
                        for char in service.characteristics:
                            print(f"  Characteristic: {char.uuid}")
                            print(f"  Properties: {char.properties}")
                finally:
                    if client.is_connected:
                        await client.disconnect()
        else:
            socket = classic_bluetooth_connect(kiválasztott_eszköz['address'])
            if socket:
                print("\nSikeresen csatlakozva klasszikus Bluetooth eszközhöz!")
                print("\nElérhető parancsok:")
                print("1. 'send': Üzenet küldése az eszköznek")
                print("2. 'receive': Üzenet fogadása az eszköztől")
                print("3. 'status': Kapcsolat állapotának lekérdezése")
                print("4. 'info': Részletes eszközinformációk")
                print("5. 'signal': Jelerősség információk")
                print("6. 'services': Elérhető szolgáltatások listázása")
                print("7. 'exit': Kapcsolat bontása és kilépés")
                
                try:
                    while True:
                        command = input("\nKérem adja meg a parancsot: ").lower()
                        
                        if command == 'exit':
                            print("Kilépés...")
                            break
                        elif command == 'send':
                            message = input("Írja be az üzenetet: ")
                            try:
                                socket.send(message.encode())
                                print("Üzenet elküldve!")
                            except Exception as e:
                                print(f"Hiba az üzenet küldése közben: {str(e)}")
                        elif command == 'receive':
                            try:
                                data = socket.recv(1024)
                                print(f"Fogadott üzenet: {data.decode()}")
                            except Exception as e:
                                print(f"Hiba az üzenet fogadása közben: {str(e)}")
                        elif command == 'status':
                            try:
                                socket.getpeername()
                                print("\nKapcsolat állapota:")
                                print("✓ Kapcsolat aktív")
                                peer_name = socket.getpeername()
                                print(f"  Távoli eszköz címe: {peer_name[0]}")
                                print(f"  Port: {peer_name[1]}")
                                print(f"  Kapcsolat típusa: Klasszikus Bluetooth")
                            except:
                                print("✗ A kapcsolat megszakadt!")
                                break
                        elif command == 'info':
                            try:
                                print("\nEszköz információk:")
                                try:
                                    device_name = bluetooth.lookup_name(kiválasztott_eszköz['address'])
                                    print(f"  Eszköz neve: {device_name or 'Ismeretlen'}")
                                except:
                                    print("  Eszköz neve: Nem elérhető")
                                
                                print(f"  MAC cím: {kiválasztott_eszköz['address']}")
                                print(f"  Protokoll: RFCOMM")
                                
                                try:
                                    socket_info = socket.getsockname()
                                    print(f"  Helyi port: {socket_info[1]}")
                                    peer_info = socket.getpeername()
                                    print(f"  Távoli port: {peer_info[1]}")
                                except:
                                    print("  Port információk nem elérhetőek")
                                
                                print("\nKapcsolat státusz:")
                                try:
                                    socket.getpeername()
                                    print("  ✓ Aktív")
                                except:
                                    print("  ✗ Megszakadt")
                                    
                            except Exception as e:
                                print(f"Hiba az információk lekérése közben: {str(e)}")
                        elif command == 'signal':
                            try:
                                print("\nJelerősség információk:")
                                # Próbáljuk lekérni az RSSI értéket
                                # Megjegyzés: nem minden eszköz támogatja
                                try:
                                    rssi = socket.getsockopt(bluetooth.SOL_BLUETOOTH, bluetooth.SO_RXPOWER)
                                    print(f"  RSSI: {rssi} dBm")
                                except:
                                    print("  RSSI érték nem elérhető")
                                
                                # Kapcsolat minőségének ellenőrzése
                                try:
                                    link_quality = socket.getsockopt(bluetooth.SOL_BLUETOOTH, bluetooth.SO_LINK_QUALITY)
                                    print(f"  Kapcsolat minősége: {link_quality}%")
                                except:
                                    print("  Kapcsolat minőség nem elérhető")
                            except Exception as e:
                                print(f"Hiba a jelerősség lekérése közben: {str(e)}")
                        elif command == 'services':
                            try:
                                print("\nElérhető szolgáltatások keresése...")
                                services = bluetooth.find_service(address=kiválasztott_eszköz['address'])
                                if services:
                                    print("\nTalált szolgáltatások:")
                                    for svc in services:
                                        print(f"\n  Szolgáltatás neve: {svc.get('name', 'Ismeretlen')}")
                                        print(f"  Protokoll: {svc.get('protocol', 'Ismeretlen')}")
                                        print(f"  Port: {svc.get('port', 'Ismeretlen')}")
                                        print(f"  Service ID: {svc.get('service-id', 'Ismeretlen')}")
                                else:
                                    print("Nem található elérhető szolgáltatás")
                            except Exception as e:
                                print(f"Hiba a szolgáltatások lekérése közben: {str(e)}")
                        else:
                            print("Ismeretlen parancs! Haszn��lja az alábbi parancsok egyikét:")
                            print("send, receive, status, info, signal, services, exit")
                            
                except KeyboardInterrupt:
                    print("\nKapcsolat megszakítva a felhasználó által.")
                finally:
                    socket.close()
                    print("Kapcsolat lezárva.")
            else:
                print("Nem sikerült kapcsolódni az eszközhöz.")
                
    except KeyboardInterrupt:
        print("\nProgram leállítva.")
    except Exception as e:
        print(f"Váratlan hiba történt: {str(e)}")
        print(f"Hiba típusa: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(main())


