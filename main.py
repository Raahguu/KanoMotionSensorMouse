import asyncio

from bleak import BleakClient, BleakScanner
from bleak.assigned_numbers import CharacteristicPropertyName
from bleak.backends import device
from bleak.backends.service import BleakGATTService
from bleak.exc import BleakError

# global vars
left_click_down = False
right_click_down = False


async def scan_ble_devices() -> None:
    """
    Prints out all the BLE devices available for connection.
    Prints out their name and Bluetooth MAC Address
    """
    print("Scanning...")
    devices: list[device.BLEDevice] = await BleakScanner.discover()

    if not devices:
        print("No BLE devices found")
        return

    print(f"Found {len(devices)} devices")
    for d in devices:
        print(f"  Name: {d.name if d.name else 'N/A'}, Address: {d.address}")

async def get_all_charcateristics(address : str) -> None:
    """
    Prints out all the data on what queries can be made to the given device.\n
        'address' paramater is the Bluetooth MAC Address
    """
    # Connect
    async with BleakClient(address) as client:
        # If the Connection failed
        if not client.is_connected:
            print("Failed to connect")
            return

        # Connected
        print(f"Connected to {client.name if client.name else client.address}")
        print("Services")
        # List through the services
        for service in client.services:
            print(f"UUID: {service.uuid}")
            print(f"Handle: {service.handle}")
            print(f"Description: {service.description}")
            print("    Characterists:")
            # List through the characteristics
            for characteristic in service.characteristics:
                print(f"        UUID: {characteristic.uuid}")
                print(f"        Handle: {characteristic.handle}")
                print(f"        Description: {characteristic.description}")
                print(f"        Max Write Size: {characteristic.max_write_without_response_size}")
                print("        Descriptiors:")
                # List through the descriptors of these characteristics
                for desc in characteristic.descriptors:
                    print(f"            UUID: {desc.uuid}")
                    print(f"            Handle: {desc.handle}")
                    print(f"            Description: {desc.description}")
                    print()
                print("        Properties:")
                #List through the descriptor's properties
                for prop in characteristic.properties:
                    print(f"            {prop}")
                print()
            print("-" * 20)

async def get_all_characteristic_values(address : str, service_handle : int) -> None:
    """
    Gets all the characteristic values of a certain service on a device\n
    Only gets the value of characteristics with the 'read' property\n
        'address' is the Bluetooth MAC Address of the device\n
        'service_handle' should be the handle of the service
    """
    # Connect
    async with BleakClient(address, use_cached_services=False) as client:
        # If not Connected
        if not client.is_connected:
            print("Failed to connect")
            return

        print(f"Connected to {client.name if client.name else client.address}")

        # Get the service
        targeted_service : BleakGATTService
        for service in client.services:
            if service.handle != service_handle:
                continue

            print(f"Found service: {service_handle}\n")
            targeted_service = service
            break
        else:
            print(f"Could not find service: {service_handle}")
            return

        # Now we can read each characteristic
        for characteristic in targeted_service.characteristics:
            print("-"*20)
            # Print basic info
            print(f"Characteristic: {characteristic.handle}")
            print(f"Description: {characteristic.description}")
		
            # Read the descriptors, if they exist
            if characteristic.descriptors: print("\nDescriptors")
            for desc in characteristic.descriptors:
                print(f"Descriptor Handle: {desc.handle}")
                desc_val = await client.read_gatt_descriptor(desc.handle)
                print(f"value: {desc_val}\n")


            # Check the characteristic supports read first
            print("Base characteristic")
            can_read : bool = "read" in characteristic.properties
            if not can_read:
                print("Does not support read\n")
                continue

            # Read from charcateristic
            try:
                char_value = await client.read_gatt_char(characteristic.handle)
                print(f"value: {char_value}")
            except BleakError as e:
                print(f"Error Reading: {str(e)}")

            print()

async def write_to_characteristic(address : str, characteristic_handle : int, new_value : bytes) -> None:
    """
    Used to write new data into a characteristic\n
        'address' is the Bluetooth MAC Address of the target device\n
        'characteristic_handle' is the handle of the characteristic to be written to\n
        'new_value' is the new value to be written to this characteristic
    """
    async with BleakClient(address, use_caches_services=False) as client:
        # If the client failed to connect
        if not client.is_connected:
            print("Failed to connect")
            return
        
        print(f"Connected to {client.name if client.name else client.address}")
        
        # Write the data
        try:
            await client.write_gatt_char(characteristic_handle, new_value, response=True)
        except BleakError as e:
            print(f"Error Writing: {str(e)}")
            

def write_handler(address : str):
    """
    A function that provides a UI for the user to write data into characteristics
    """
    print("Which characteristic do you want to write to:")
    print("(N)ame of the device")
    print("(U)nknown Characteristic 28")
    print("(K)eep alive")
    print("(G)lobal brightness")
    inp = input().lower().strip()
    
    match inp:
        case "n": 
            print("Enter the new name")
            name = input().strip()
            asyncio.run(write_to_characteristic(address, 2, bytes(name, encoding="utf-8")))
        case "u":
        	print("?")
        	new = input().strip().lower()
        	asyncio.run(write_to_characteristic(address, 28, bytes(new, encoding="utf-8")))
        case "k":
            while True:
                print("0 or 1")
                try:
                    keep = int(input().strip())
                    if keep not in [0, 1]: raise IndexError

                    asyncio.run(write_to_characteristic(address, 30, bytes(str(keep), encoding="utf-8")))
                    break
                except (IndexError, ValueError):
                    print("It must be a one or zero")
        case "g":
            while True:
                print("0 to 255")
                try:
                    keep = int(input().strip())
                    if keep < 0 or keep > 255: raise IndexError
                
                    asyncio.run(write_to_characteristic(address, 30, bytes(str(keep), encoding="utf-8")))
                    break
                except (IndexError, ValueError):
                    print("It must be between 0 and 255")

        	
def notification_handler(sender, data):
    # For non motion sensing
    if sender.handle != 24:
        print(f"Notification from {sender.handle}: {data}")
        
    # For the motion
    cursor_speed_mult = 0.1
    global left_click_down
    global right_click_down
    
    import pyautogui    
    # Up: data[0]}
    # Right: data[1]
    # Down: data[2]
    # Left: data[3]
    
    # Remove pauses
    pyautogui.PAUSE = 0
    
    # Mouse clicking
    if data[1] < 25 and data[2] < 25 and data[3] < 25:
        # Left click
        if data[0] < 25:
            if not left_click_down:
                if right_click_down:
                    print("Right click Up")
                    pyautogui.mouseUp(button='right')
                    right_click_down = False
            
                print("Left click Down")
                pyautogui.mouseDown(button="left")
                left_click_down = True
        # Right click
        else:
            if not right_click_down:
            	if left_click_down:
            	    print("Left click up")
            	    pyautogui.mouseUp(button='left')
            	    left_click_down = False
            	
            	print("Right click Down")
            	pyautogui.mouseDown(button="right")
            	right_click_down = True
        return
    
    if left_click_down:
        print("Left click up")
        pyautogui.mouseUp(button='left')
        left_click_down = False
    if right_click_down:
        print("Right click up")
        pyautogui.mouseUp(button='right')
        right_click_down = False
    
    # move the cursor
    # The values  are 0-255, 
    # with 0 being they are at max closeness, 
    # and 255 being the hand is not there
    right_movement = ((255 - data[1]) - (255 - data[3])) * cursor_speed_mult
    down_movement =  ((255 - data[2]) - (255 - data[0])) * cursor_speed_mult
    
    pyautogui.move(right_movement, down_movement)
    

async def notify_for_motion(address):
    """
    Sets up the continous notifying for the device as long as the program is open
    """
    
    print("Connecting")
    async with BleakClient(address, use_cached_services=False) as client:
        if not client.is_connected:
            print("Could not connect")
            return
        
        print(f"Connected to {client.name if client.name else client.address}")
        
        print("Turning on notifying")
        try:
            await client.start_notify(24, notification_handler)
        except BleakError as e:
            print(f"Error: {str(e)}")
        
        print("Notifications on")
        while True:
        	await asyncio.sleep(1)


def main() -> None:
    """
    The main funcion that gives the user a semi-decent text interface
    """

    address = "FD:D3:9D:E7:40:E0"

    print("Select an option:")
    print("(S)can for bluetooth devices")
    print("(M)ap out all services and characteristics of the device")
    print("(R)ead all the characteristic values of a service")
    print("(W)rite a new value to a characteristic")
    print("(N)otify for motion sensing")
    inp = input().strip().lower()

    
    match inp:
        case "s": asyncio.run(scan_ble_devices())
        case "m": asyncio.run(get_all_charcateristics(address))
        case "r": 
        	handle = int(input("which service (input handle number): ").strip())
        	asyncio.run(get_all_characteristic_values(address, handle))
        case "w": write_handler(address)
        case "n": asyncio.run(notify_for_motion(address))
        case _: print("unknown option")
    return

if __name__ == "__main__":
    try:
        main()
    except EOFError:
        print("Device disconnected unexpectedly; ignoring EOFError from dbus-fast.")
    
