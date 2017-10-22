#!/usr/bin/env python3
import os
import subprocess
import select
import binascii
import sys
import argparse

application_name = 'palmbeach-beacon'

DEVICE="hci1"
BEACONS = {}

if (sys.version_info > (3, 0)):
    DEVNULL = subprocess.DEVNULL
else:
    DEVNULL = open(os.devnull, 'wb')

parser = argparse.ArgumentParser(prog=application_name, description=__doc__)
parser.add_argument('-m', '--mode', default='range', choices=['range', 'gateway'])
parser.add_argument('-i', '--iface', default='hci0')
parser.add_argument('-i2', '--iface2', default='hci1')
parser.add_argument("-V", "--verbose", action='store_true',
                    help='Print lots of debug output.')

args = parser.parse_args()

def play(wavfile):
    subprocess.Popen(['aplay', wavfile], stderr=DEVNULL)

 
class Scanner(object):
    def __init__(self, device):
        subprocess.call(["hciconfig", device, "reset"])
        self.lescan = subprocess.Popen(["hcitool", "-i", device, "lescan", "--duplicates"], stdout=DEVNULL)
        self.dump =  subprocess.Popen(["hcidump", "-i", device, "--raw"], stdout=subprocess.PIPE)

    def stop(self):
        subprocess.call(["kill", str(self.dump.pid), "-s", "SIGINT"])
        subprocess.call(["kill", str(self.lescan.pid), "-s", "SIGINT"])

    def rssi_to_distance(self, rssi, txpower=65):
        if rssi == 0:
            raise Exception("Cannot estimate range")

        ratio = rssi * 1./txpower
        if ratio < 1:
            return ratio**10

        accuracy = 0.89976*(ratio**7.7095) + 0.111
        return accuracy

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
            uuid = binascii.hexlify(msg[2:2+16])
            rssi = 256 - int(binascii.hexlify(msg[23:24]), 16)

            beacon = BEACONS.setdefault(uuid, [])
            beacon.append(rssi)
            if len(beacon) > 2:
                beacon = beacon[-2:]

            BEACONS[uuid] = beacon
            rssi_avg = sum(beacon) / len(beacon)

            print("IBEACON %s %d %d %.02f %.02f" % (uuid, rssi, rssi_avg, self.rssi_to_distance(rssi), self.rssi_to_distance(rssi_avg)))
            #return Beacon(uuid, rssi)

        else:
            # print("Unknown beacon type")
            pass

    def scan(self):
        packet = None
        try:
            while True:
                is_data = select.select([self.dump.stdout], [], [], 0.5)[0]
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
    print("Mode: %s" % args.mode)
    print("Interface: %s" % args.iface)
    scanner = Scanner(args.iface)
    scanner.scan() 

if __name__ == "__main__":
    main()
