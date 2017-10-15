#!/usr/bin/env python3
import re
import os
import signal
import subprocess
import binascii
import sys
import time
import argparse
from pprint import pprint
from enum import Enum

application_name = 'palmbeach-beacon'

DEVICE="hci1"

if (sys.version_info > (3, 0)):
    DEVNULL = subprocess.DEVNULL
else:
    DEVNULL = open(os.devnull, 'wb')

parser = argparse.ArgumentParser(prog=application_name, description=__doc__)
group = parser.add_mutually_exclusive_group()

#parser.add_argument('-s', '--scan', action='store_true',
#                    help='Scan for beacons.')
parser.add_argument('-m', '--mode', default='range', choices=['range', 'gateway'])
parser.add_argument("-V", "--Verbose", action='store_true',
                    help='Print lots of debug output.')

args = parser.parse_args()

foundPackets = set()

def verboseOutput(text=""):
    """Verbose output logger."""
    if args.Verbose:
        sys.stderr.write(text + "\n")
 
def onPacketFound(packet):
    """Called by the scan function for each beacon packets found."""
    data = bytearray.fromhex(packet)


    # iBeacon
    if len(data) >=20 and data[18] == 0x02 and data[19] == 0x15:
        uuid = binascii.hexlify(data[20:20+16])
        rssi = 256 - int(binascii.hexlify(data[41:42]), 16)
        play('in.wav')

        print("IBEACON %s %d %.02f" % (uuid, rssi, rssiToDistance(rssi)))

    # Eddystone
    elif len(data) >= 20 and data[19] == 0xaa and data[20] == 0xfe:
        serviceDataLength = data[21]
        frameType = data[25]

        # Eddystone-URL
        if frameType == Eddystone.url.value:
            onUrlFound(decodeUrl(data[27:22 + serviceDataLength]))
        elif frameType == Eddystone.uid.value:
            onUidFound(data[27:22 + serviceDataLength])
        elif frameType == Eddystone.tlm.value:
            verboseOutput("Eddystone-TLM")
        else:
            verboseOutput("Unknown Eddystone frame type: {}".format(frameType))

    # UriBeacon
    elif len(data) >= 20 and data[19] == 0xd8 and data[20] == 0xfe:
        serviceDataLength = data[21]
        verboseOutput("UriBeacon")
        onUrlFound(decodeUrl(data[27:22 + serviceDataLength]))

    else:
        verboseOutput("Unknown beacon type")

    verboseOutput(packet)
    verboseOutput()

def rssiToDistance(rssi, txpower=65):
    if rssi == 0:
        raise Exception("Cannot estimate range")

    ratio = rssi * 1./txpower
    if ratio < 1:
        return ratio**10

    accuracy = 0.89976*(ratio**7.7095) + 0.111
    return accuracy

def play(wavfile):
    subprocess.Popen(['aplay', wavfile], stderr=DEVNULL)

def scan():
    print("Mode: %s" % args.mode)

    subprocess.call("hciconfig %s reset" % DEVICE, shell=True, stdout=DEVNULL)

    lescan = subprocess.Popen(
            ["hcitool", "-i", DEVICE, "lescan", "--duplicates"],
            stdout=DEVNULL)

    dump = subprocess.Popen(
            ["hcidump", "-i", DEVICE, "--raw"],
            stdout=subprocess.PIPE)

    packet = None
    try:
        startTime = time.time()
        while True:
            line = dump.stdout.readline().decode()
            if line.startswith("> "):
                if packet:
                    onPacketFound(packet)
                packet = line[2:].strip()
            elif line.startswith("< "):
                if packet:
                    onPacketFound(packet)
                packet = None
            elif "Broken pipe" in line:
                print("Zas to spadlo")
            else:
                if packet:
                    packet += " " + line.strip()

    except Exception as e:
        print(str(e))

    subprocess.call(["kill", str(dump.pid), "-s", "SIGINT"])
    subprocess.call(["kill", str(lescan.pid), "-s", "SIGINT"])

def main():
    scan()

if __name__ == "__main__":
    main()
