from bleak import BleakScanner, BleakClient
import asyncio
import logging
import platform
import socket
import bluetooth  # Klasszikus Bluetooth támogatáshoz
import subprocess
import re
import time
import netifaces  # pip install netifaces
import nmap  # pip install python-nmap
import lightblue

logging.basicConfig(level=logging.DEBUG)

def lightblue_connect(address):
    try:
        print(f"\nLightblue kapcsolódás megkezdése: {address}")
        
        # MAC cím formátum ellenőrzése
        if not re.match(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", address):
            print("Érvénytelen MAC cím formátum!")
            return None
            
        # Bluetooth adapter ellenőrzése
        try:
            lightblue.finddevices()
        except lightblue.BluetoothError:
            print("Nem található aktív Bluetooth adapter!")
            return None
            
        print("Szolgáltatások keresése...")
        services = lightblue.findservices(address)
        
        if not services:
            print("Nem található szolgáltatás az eszközön!")
            return None
            
        try:
            # Kapcsolódás az első szolgáltatáshoz
            socket = lightblue.socket()
            socket.settimeout(15)  # 15 másodperces timeout
            socket.connect((address, services[0][0]))
            print(f"Lightblue kapcsolat létrejött a {services[0][0]} porton!")
            return socket
            
        except lightblue.BluetoothError as be:
            print(f"Lightblue kapcsolódási hiba: {str(be)}")
            print("\nKérem ellenőrizze:")
            print("1. Az eszköz be van kapcsolva")
            print("2. Az eszköz párosítási módban van")
            print("3. A Bluetooth adapter be van kapcsolva")
            print("4. A MAC cím helyes")
            
            return None



def classic_bluetooth_connect(address):
    try:
        print(f"\nKlasszikus Bluetooth kapcsolódás megkezdése: {address}")
        
        # MAC cím formátum ellenőrzése
        if not re.match(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", address):
            print("Érvénytelen MAC cím formátum!")
            return None
            
        # Bluetooth adapter ellenőrzése
        try:
            socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        except bluetooth.BluetoothError:
            print("Nem található aktív Bluetooth adapter!")
            return None
            
        print("Elérhető portok keresése...")
        available_ports = []
        for port in range(1, 30):
            try:
                test_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
                test_socket.connect((address, port))
                available_ports.append(port)
                test_socket.close()
            except:
                continue
                
        if not available_ports:
            print("Nem található elérhető port az eszközön!")
            return None
            
        try:
            # Kapcsolódás az első elérhető porton
            socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            socket.settimeout(15)  # 15 másodperces timeout
            socket.connect((address, available_ports[0]))
            print(f"Klasszikus Bluetooth kapcsolat létrejött a {available_ports[0]} porton!")
            return socket
            
        except bluetooth.btcommon.BluetoothError as be:
            print(f"Bluetooth kapcsolódási hiba: {str(be)}")
            print("\nKérem ellenőrizze:")
            print("1. Az eszköz be van kapcsolva")
            print("2. Az eszköz párosítási módban van")
            print("3. A Bluetooth adapter be van kapcsolva")
            print("4. A MAC cím helyes")
            return None
            
    except Exception as e:
        print(f"Váratlan hiba történt: {str(e)}")
        print(f"Hiba típusa: {type(e).__name__}")
        return None
    finally:
        try:
            if 'test_socket' in locals():
                test_socket.close()
        except:
            pass

async def ble_connect_with_retry(address, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            print(f"\nBLE Csatlakozási kísérlet {attempt + 1}/{max_attempts}")
            client = BleakClient(address, timeout=10.0)
            await client.connect(timeout=10.0)
            return client
        except Exception as e:
            print(f"BLE Kísérlet {attempt + 1} sikertelen: {str(e)}")
            if attempt < max_attempts - 1:
                print("Újrapróbálkozás 5 másodperc múlva...")
                await asyncio.sleep(5)
    return None

def get_android_hotspot_info():
    try:
        # Windows esetén
        if platform.system() == "Windows":
            result = subprocess.check_output(["netsh", "wlan", "show", "interfaces"], encoding='utf-8')
            
            # Részletes információk gyűjtése
            connection_info = {
                'ssid': None,
                'signal': None,
                'ip': None,
                'gateway': None,
                'dns': None,
                'frequency': None,
                'tx_rate': None,
                'rx_rate': None
            }
            
            # SSID és jelerősség kinyerése
            for line in result.split('\n'):
                if "SSID" in line and "BSSID" not in line:
                    connection_info['ssid'] = line.split(":")[1].strip()
                elif "Signal" in line:
                    signal_str = line.split(":")[1].strip().rstrip('%')
                    connection_info['signal'] = int(signal_str) if signal_str.isdigit() else None
                elif "Receive rate" in line:
                    connection_info['rx_rate'] = line.split(":")[1].strip()
                elif "Transmit rate" in line:
                    connection_info['tx_rate'] = line.split(":")[1].strip()

            # IP információk beszerzése
            for iface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(iface)
                if netifaces.AF_INET in addrs:  # Ha van IPv4 cím
                    for addr in addrs[netifaces.AF_INET]:
                        if 'addr' in addr and addr['addr'] != '127.0.0.1':
                            connection_info['ip'] = addr['addr']
                            
            # Gateway információ
            gws = netifaces.gateways()
            if 'default' in gws and netifaces.AF_INET in gws['default']:
                connection_info['gateway'] = gws['default'][netifaces.AF_INET][0]

            # DNS szerverek lekérése
            try:
                dns_output = subprocess.check_output(["ipconfig", "/all"], encoding='utf-8')
                dns_servers = []
                for line in dns_output.split('\n'):
                    if "DNS Servers" in line:
                        dns_line = next((l for l in dns_output.split('\n')[dns_output.split('\n').index(line)+1:] if l.strip()), '')
                        if dns_line.strip():
                            dns_servers.append(dns_line.strip())
                connection_info['dns'] = dns_servers
            except:
                connection_info['dns'] = ["Nem elérhető"]

            return connection_info
    except Exception as e:
        print(f"Hiba az Android hotspot információk lekérése közben: {str(e)}")
        return None

def monitor_connection_quality(duration=5):
    """Kapcsolat minőségének monitorozása megadott időtartamon keresztül"""
    print(f"\nKapcsolat minőségének mérése ({duration} másodperc)...")
    measurements = []
    
    try:
        start_time = time.time()
        while time.time() - start_time < duration:
            result = subprocess.check_output(["netsh", "wlan", "show", "interfaces"], encoding='utf-8')
            for line in result.split('\n'):
                if "Signal" in line:
                    signal_str = line.split(":")[1].strip().rstrip('%')
                    if signal_str.isdigit():
                        measurements.append(int(signal_str))
            time.sleep(1)
        
        if measurements:
            avg_signal = sum(measurements) / len(measurements)
            min_signal = min(measurements)
            max_signal = max(measurements)
            
            print("\nKapcsolat minőség statisztika:")
            print(f"  Átlagos jelerősség: {avg_signal:.1f}%")
            print(f"  Minimum jelerősség: {min_signal}%")
            print(f"  Maximum jelerősség: {max_signal}%")
            print(f"  Jelerősség ingadozás: {max_signal - min_signal}%")
            
            # Kapcsolat minőségének értékelése
            if avg_signal >= 80:
                print("  Minősítés: Kiváló kapcsolat")
            elif avg_signal >= 60:
                print("  Minősítés: Jó kapcsolat")
            elif avg_signal >= 40:
                print("  Minősítés: Közepes kapcsolat")
            else:
                print("  Minősítés: Gyenge kapcsolat")
    except Exception as e:
        print(f"Hiba a kapcsolat monitorozása közben: {str(e)}")

def get_connected_device_info(target_ip):
    try:
        print("\nKapcsolódott eszköz inform��cióinak lekérése...")
        nm = nmap.PortScanner()
        
        # Alapvető szkennelés az eszközön
        nm.scan(hosts=target_ip, arguments='-sn')
        
        device_info = {
            'ip': target_ip,
            'hostname': None,
            'mac': None,
            'vendor': None,
            'open_ports': [],
            'status': None
        }

        if target_ip in nm.all_hosts():
            host = nm[target_ip]
            
            # Részletes szkennelés
            nm.scan(target_ip, arguments='-sS -sV -O --version-intensity 5')
            
            device_info.update({
                'hostname': nm[target_ip].hostname() if 'hostname' in dir(nm[target_ip]) else 'Ismeretlen',
                'mac': host['addresses'].get('mac', 'Ismeretlen') if 'addresses' in host else 'Ismeretlen',
                'vendor': host.get('vendor', {}).get(device_info['mac'], 'Ismeretlen'),
                'status': host.get('status', {}).get('state', 'Ismeretlen'),
                'os': nm[target_ip].get('osmatch', [{'name': 'Ismeretlen'}])[0]['name']
            })

            # Nyitott portok ellenőrzése
            if 'tcp' in nm[target_ip]:
                for port, port_info in nm[target_ip]['tcp'].items():
                    if port_info['state'] == 'open':
                        service_info = f"Port {port} ({port_info.get('name', 'ismeretlen')})"
                        if port_info.get('version'):
                            service_info += f" - Verzió: {port_info['version']}"
                        device_info['open_ports'].append(service_info)

        return device_info

    except Exception as e:
        print(f"Hiba az eszköz információk lekérése közben: {str(e)}")
        return None

def get_device_signal_strength(mac_address):
    try:
        print(f"\nJelerősség mérése a következő eszközhöz: {mac_address}")
        
        # Csak eszköz keresés és RSSI mérés
        print("Eszköz keresése és jelerősség mérése...")
        
        nearby_devices = bluetooth.discover_devices(
            duration=8,  # Hosszabb keresési idő
            lookup_names=True,
            lookup_class=True,
            device_id=-1,
            flush_cache=True
        )
        
        for addr, name, device_class in nearby_devices:
            if addr.upper() == mac_address.upper():
                # Eszköz osztály alapján signal becslés
                major_class = (device_class >> 8) & 0x1F
                minor_class = (device_class >> 2) & 0x3F
                
                print(f"Eszköz megtalálva: {name}")
                print(f"Eszköz típus: {get_device_class_name(major_class)}")
                
                # Közelség becslése az eszköz megtalálásának gyorsasága alapján
                signal_quality = estimate_signal_quality(device_class)
                
                return {
                    'device_name': name,
                    'device_class': get_device_class_name(major_class),
                    'quality': signal_quality['quality'],
                    'strength': signal_quality['strength'],
                    'status': 'Elérhető'
                }
        
        print("Eszköz nem található a közelben")
        return {
            'device_name': 'Nem található',
            'device_class': 'Ismeretlen',
            'quality': 'Nem mérhető',
            'strength': 'Nem elérhető',
            'status': 'Nem elérhető'
        }
        
    except Exception as e:
        print(f"Hiba a jelerősség mérése közben: {str(e)}")
        return None

def get_device_class_name(major_class):
    """Eszköz osztály nevének meghatározása"""
    class_names = {
        0: "Egyéb",
        1: "Számítógép",
        2: "Telefon",
        3: "LAN/Hálózati eszköz",
        4: "Audio/Video",
        5: "Periféria",
        6: "Képalkotó eszköz",
        7: "Hordozható eszköz",
        8: "Játék",
        9: "Egészségügyi eszköz"
    }
    return class_names.get(major_class, "Ismeretlen")

def estimate_signal_quality(device_class):
    """Jelerősség becslése az eszköz osztálya alapján"""
    # Telefon és számítógép esetén általában jobb minőségű a kapcsolat
    major_class = (device_class >> 8) & 0x1F
    
    if major_class in [1, 2]:  # Számítógép vagy telefon
        return {
            'quality': 'Jó',
            'strength': 'Erős (75-100%)'
        }
    else:
        return {
            'quality': 'Megfelelő',
            'strength': 'Közepes (50-74%)'
        }

def monitor_device_connection(mac_address, duration=5):
    """Egyszerűsített eszköz elérhetőség monitorozás"""
    print(f"\nEszköz elérhetőség monitorozása ({duration} másodperc)...")
    detections = 0
    total_checks = duration
    
    for i in range(total_checks):
        try:
            print(f"Ellenőrzés {i+1}/{total_checks}...", end='\r')
            nearby_devices = bluetooth.discover_devices(
                duration=1,
                lookup_names=True,
                flush_cache=True
            )
            
            if any(addr.upper() == mac_address.upper() for addr, name in nearby_devices):
                detections += 1
                
        except Exception as e:
            print(f"\nHiba az ellenőrzés során: {str(e)}")
        time.sleep(1)
    
    detection_rate = (detections / total_checks) * 100
    
    print("\nEszköz elérhetőség:")
    print(f"Sikeres észlelések: {detections}/{total_checks} ({detection_rate:.1f}%)")
    
    if detection_rate > 80:
        print("Minősítés: Stabil elérhetőség")
    elif detection_rate > 50:
        print("Minősítés: Változó elérhetőség")
    else:
        print("Minősítés: Gyenge elérhetőség")

async def main():
    print("Bluetooth eszközök keresése...")
    print(f"Operációs rendszer: {platform.system()} {platform.release()}")
    
    try:
        # BLE eszközök keresése
        print("\nBLE eszközök keresése...")
        ble_devices = await BleakScanner.discover(timeout=15.0)
        
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
                                print(f"  Távoli eszköz cime: {peer_name[0]}")
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
                            print("\nJelerősség információk lekérése...")
                            signal_info = get_device_signal_strength(kiválasztott_eszköz['address'])
                            
                            if signal_info:
                                print("\nKapcsolat információk:")
                                print(f"Eszköz neve: {signal_info['device_name']}")
                                print(f"Válaszidő: {signal_info['response_time']}")
                                print(f"Kapcsolat minősége: {signal_info['quality']}")
                                print(f"Jelerősség: {signal_info['strength']}")
                                
                                # Rövid kapcsolat monitorozás
                                monitor_device_connection(kiválasztott_eszköz['address'])
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
                            print("Ismeretlen parancs! Használja az alábbi parancsok egyikét:")
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