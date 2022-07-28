#!/usr/bin/env python3

from pydbus import SystemBus
from gi.repository import GLib
from enum import IntEnum
import time

class RootRobot:
    ROOT_UUID = '48c5d828-ac2a-442d-97a3-0c9822b04979'
    ROOT_RX_UUID = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'
    ROOT_TX_UUID = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'

    class Device(IntEnum):
        GENERAL = 0
        MOTORS = 1
        MARKER = 2
        LIGHTS = 3
        COLOR_SENSOR = 4
        SOUND = 5
        BUMPERS = 12
        LIGHT_SENSOR = 13
        BATTERY = 14
        ACCELEROMETER = 16
        TOUCH_SENSOR = 17
        CLIFF_SENSOR = 20

    def __init__(self):
        self.message_handlers = {}
        self.system_bus = SystemBus()
        self.bluez = self.system_bus.get('org.bluez', '/')
        root_dev = self.bt_autodiscover()
        self.bt_connect(root_dev)

    def bt_autodiscover(self):
        print('Starting autodiscovery')
    
        # find bt adapter
        print('Searching Bluetooth adapter')
        adapters = self.bt_find_by_interface('org.bluez.Adapter1')
        if not adapters:
            print('no bluetooth device found')
            return
        print('... found ' + adapters[0][0])
        
        # start discovery on adapter
        bt_adapter = self.system_bus.get('org.bluez', adapters[0][0])
        bt_adapter.SetDiscoveryFilter({'UUIDs': GLib.Variant('as', [self.ROOT_UUID])})
        bt_adapter.StartDiscovery()
        print('Starting ROOT device discovery')
        
        #try to detect the robot by name
        root_dev = None
        for i in range(1,10):
            for (obj, interfaces) in self.bt_find_by_interface('org.bluez.Device1'):
                if interfaces['org.bluez.Device1']['Name'] == 'ROOT':
                    print('... found ' + obj)
                    root_dev = obj
                    break
            else:
                time.sleep(1)
                print('trying again')
                continue
            break
        
        bt_adapter.StopDiscovery()
        
        if not root_dev:
            print('could not find ROOT robot')
            return

        print('Autodiscovery finished')        
        return root_dev
    
    def bt_connect(self, root_dev):
        print('Connecting to ' + root_dev)
        self.root = self.system_bus.get('org.bluez', root_dev)
        self.root.Connect()
        print('... success')
        self.connect_robot_uart()
        self.register_receive_callback(self.on_message_received)
    
    def connect_robot_uart(self):
        print('Open communication with ROOT')
        self.tx = None
        self.rx = None
        while not self.tx or not self.rx:
            for (obj, interfaces) in self.bt_find_by_interface('org.bluez.GattCharacteristic1'):
                if interfaces['org.bluez.GattCharacteristic1']['UUID'] == self.ROOT_RX_UUID:
                    self.tx = self.system_bus.get('org.bluez', obj)
                if interfaces['org.bluez.GattCharacteristic1']['UUID'] == self.ROOT_TX_UUID:
                    self.rx = self.system_bus.get('org.bluez', obj)
            if not self.tx or not self.rx:
                time.sleep(1)
                print('trying again')
        print('... success')

    def register_receive_callback(self, cb):
        def prop_cb(interface, changed_properties, invalidated_properties):
            if 'Value' in changed_properties.keys():
                cb(changed_properties['Value'])

        print('Register message handler')
        self.rx.PropertiesChanged.connect(prop_cb)
        self.rx.StartNotify()
        print('... success')
    
    def bt_find_by_interface(self, interface):
        result = []
        for (obj, interfaces) in self.bluez.GetManagedObjects().items():
            if interface in interfaces:
                result.append((obj, interfaces))
        return result

    def msg_crc8(self, data):
        crc = 0
        data_len = len(data)
        pos = 0

        while data_len > 0:
            data_len = data_len - 1
            c = data[pos]
            pos = pos+1
            i = 0x80
            while i > 0:
                bit = bool(crc & 0x80)
                if (c & i) > 0:
                    bit = not bit
                crc = crc * 2
                if bit:
                    crc = crc ^ 0x07
                i = int(i / 2)
            crc = crc & 0xff
        data.append(crc & 0xff)
        return data
        
    def send_message(self, device, cmd, payload):
        while len(payload) < 16:
            payload.append(0)
    
        data = bytes(self.msg_crc8([int(device), cmd, 0x00] + payload))
        self.tx.WriteValue(data, {'type': GLib.Variant('s','command')})

    def on_message_received(self, msg):
        if msg[0] in self.message_handlers:
            self.message_handlers[msg[0]](msg)
        else:
            print(msg)

    def register_message_handler(self, device, cb):
        self.message_handlers[device] = cb
    

if __name__ == 'main':
    def enable_lights(root):
        root.send_message(RootRobot.Device.LIGHTS, 2, [0x03, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    root = RootRobot()
    enable_lights(root)

    loop = GLib.MainLoop()
    loop.run()
