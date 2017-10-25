#!/usr/bin/env python3
import subprocess
import select
import binascii
import sys
import time
import json
import argparse
import requests

application_name = 'palmbeach-beacon'
CALLBACK_TIMEOUT = 1
DEVNULL = subprocess.DEVNULL

parser = argparse.ArgumentParser(prog=application_name, description=__doc__)
parser.add_argument('room', type=str, metavar='ROOM')
#parser.add_argument('-m', '--mode', default='range', choices=['range', 'gateway'])
parser.add_argument('-s', '--sensitivity', type=int, default=100)
parser.add_argument('-tin', '--timeout-in', dest='timeout_in', type=int, default=10)
parser.add_argument('-tout', '--timeout-out', dest='timeout_out', type=int, default=10)
parser.add_argument('-i', '--iface', default='hci0')
#parser.add_argument('-i2', '--iface2', default='hci1')
parser.add_argument('-c', '--callback', metavar='CALLBACK_URL',
                    help='Callback URL for reporting appearance/disappearance of the device')
parser.add_argument("-v", "--verbose", action='store_true',
                    help='Print lots of debug output.')

args = parser.parse_args()

def play(wavfile):
    subprocess.Popen(['aplay', wavfile], stderr=DEVNULL)

def rssi_to_distance(rssi, txpower=65):
    if rssi == 0:
        raise Exception("Cannot estimate range")

    ratio = rssi * 1./txpower
    if ratio < 1:
        return ratio**10

    accuracy = 0.89976*(ratio**7.7095) + 0.111
    return accuracy

def report_ping():
    if not args.callback:
        return

    try:
        requests.get(args.callback,
                    params={'action': 'ping', 'room': args.room},
                    timeout=CALLBACK_TIMEOUT)
    except Exception as e:
        print(str(e))
   
def report_change(b):
    if not args.callback:
        return

    try:
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        requests.post(args.callback,
                    headers=headers,
                    params={'action': 'change', 'room': args.room},
                    data=str(b),
                    timeout=CALLBACK_TIMEOUT)

    except Exception as e:
        print(str(e))

class Beacon(object):
    def __init__(self, uuid):
        self.uuid = uuid
        self.counter = 0
        self.active = False
        self.last_access = 0

    def __repr__(self):
        return json.dumps(self.__dict__)
        #"UUID %s: %s %d %d" % (self.uuid, self.active, self.counter, self.last_access)

class BeaconRegistry(object):
    def __init__(self, timeout_in, timeout_out):
        self.registry = {}
        self.timeout_in = timeout_in
        self.timeout_out = timeout_out
        self.last_cleanup = int(time.time())
        self.last_ping = 0

    def register(self, uuid, rssi):
        b = self.registry.setdefault(uuid, Beacon(uuid))

        if b.last_access > int(time.time() - 1):
            # Ignore packets over >1Hz
            return

        print("beat %s %d %.02f" % (uuid, rssi, rssi_to_distance(rssi)))

        b.last_access = int(time.time())
        b.counter += 1

        if not b.active and b.counter >= self.timeout_in:
            b.active = True
            self.on_appear(b)

        self.registry[uuid] = b

    def cleanup(self):
        # Called in loop even if no beacon is detected
        if self.last_cleanup > time.time() - 1:
            return
        
        self.last_cleanup = time.time()

        for uuid, b in self.registry.items():
            if b.counter > 0 and int(time.time()) - self.timeout_out > b.last_access:
                b.counter = 0
                if b.active:
                    b.active = False
                    self.on_disappear(b)

        if self.last_ping <= time.time() - 60:
            self.last_ping = int(time.time())
            report_ping()

    def on_appear(self, b):
        print("%s is now active" % b)
        report_change(b)

    def on_disappear(self, b):
        print("%s is now away" % b)
        report_change(b)
      
class Scanner(object):
    def __init__(self, device, sensitivity, timeout_in, timeout_out):
        self.sensitivity = sensitivity
        self.registry = BeaconRegistry(timeout_in, timeout_out)

        subprocess.call(["hciconfig", device, "reset"])
        self.lescan = subprocess.Popen(["hcitool", "-i", device, "lescan", "--duplicates"], stdout=DEVNULL)
        self.dump =  subprocess.Popen(["hcidump", "-i", device, "--raw"], stdout=subprocess.PIPE)

    def stop(self):
        subprocess.call(["kill", str(self.dump.pid), "-s", "SIGINT"])
        subprocess.call(["kill", str(self.lescan.pid), "-s", "SIGINT"])

    def decode_packet(self, packet):
        if args.verbose:
            print(packet)

        data = bytearray.fromhex(packet)
        
        if len(data) < 30:
            # Filter out non-interesting data
            return

        # iBeacon
        if len(data) == data[2] + 3 and data[len(data)-24] == 0x02 and data[len(data)-24+1] == 0x15:

            msg = data[len(data)-24:]
            uuid = binascii.hexlify(msg[2:2+16]).decode()
            rssi = 256 - int(binascii.hexlify(msg[23:24]), 16)

            if rssi <= self.sensitivity:
                self.registry.register(uuid, rssi)
            elif args.verbose:
                print("%s is too far: %d" % (uuid, rssi))

        else:
            # print("Unknown beacon type")
            pass

    def scan(self):
        packet = None
        try:
            while True:
                is_data = select.select([self.dump.stdout], [], [], 0.5)[0]
                self.registry.cleanup()
                if is_data:
                    line = self.dump.stdout.readline().decode()
                    if line.startswith("> "):
                        if packet:
                            self.decode_packet(packet)
                        packet = line[2:].strip()
                    elif line.startswith("< "):
                        if packet:
                            self.decode_packet(packet)
                        packet = None
                    else:
                        if packet:
                            packet += " " + line.strip()

        except Exception as e:
            print(str(e))
        
def main():
    #print("Mode: %s" % args.mode)
    print("Interface: %s" % args.iface)
    print("Sensitivity: %d" % args.sensitivity)
    print("Timeout IN: %d" % args.timeout_in)
    print("Timeout OUT: %d" % args.timeout_out)
    print("Room name: %s" % args.room)
    print("Callback URL: %s" % args.callback)

    scanner = Scanner(args.iface, args.sensitivity, args.timeout_in, args.timeout_out)
    scanner.scan() 

if __name__ == "__main__":
    main()
