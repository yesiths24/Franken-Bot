from machine import UART, Pin
import time
import math

uart1 = UART(1, baudrate=115200, tx=Pin(4), rx=Pin(5))

# SYNC
txData = bytes.fromhex("AA0D00000000")
rxData = bytes()

waitTime = 0.005
for i in range(60):
    uart1.write(txData)
    time.sleep(waitTime)
    waitTime = waitTime+0.001
    if uart1.any() > 0:
        break

time.sleep(0.1)
while uart1.any() > 0:
    rxData += uart1.read(1)

print(rxData.hex(' '))

ACK = bytes.fromhex("AA0E0D000000")
uart1.write(ACK)
time.sleep(0.1)

#INITIAL JPEG, VGA
txData = bytes.fromhex("AA 01 00 07 07 07")
rxData = bytes()

uart1.write(txData)

time.sleep(0.1)
while uart1.any() > 0:
    rxData += uart1.read(1)

print(rxData.hex(' '))

#SET PACKAGE SIZE 256 Bytes
txData = bytes.fromhex("AA 06 08 00 01 00")
rxData = bytes()

uart1.write(txData)

time.sleep(0.1)
while uart1.any() > 0:
    rxData += uart1.read(1)

print(rxData.hex(' '))

#SNAPSHOT
txData = bytes.fromhex("AA 05 00 00 00 00")
rxData = bytes()

uart1.write(txData)

time.sleep(0.1)
while uart1.any() > 0:
    rxData += uart1.read(1)

print(rxData.hex(' '))

#GET PICTURE
txData = bytes.fromhex("AA 04 01 00 00 00")
rxData = bytes()

uart1.write(txData)

time.sleep(0.1)
while uart1.any() > 0:
    rxData += uart1.read(1)
    time.sleep(0.01)

print(rxData.hex(''))


size = rxData[11]*256^2 + rxData[10]*256 + rxData[9]

print("Image Size: {}".format(size))
numPackages = math.ceil(size / (256-6))

with open("testimage.txt", "w") as f:
    for i in range(0, numPackages-1):
        # print("\nPackage Number: {}\n".format(i))
        prompt = bytes.fromhex("AA0E0000{:02x}00".format(i))
        uart1.write(prompt)

        time.sleep(0.01)

        rxData = bytearray();

        count = 0
        while uart1.any() > 0:
            rxData += uart1.read(1)
            time.sleep(0.0001)
            count = count + 1
            # if (rxData != None):
            #     print("0x{}".format(rxData.hex()), end=" ")
            #     count = count + 1
            
        
        for i in range(4, 254):
            
            f.write("0x{}".format(rxData[i:i+1].hex(), end=" "))
        # print("\nPackage Complete - Printed {} bytes\n".format(count))

    prompt = bytes.fromhex("AA0E0000{:02x}00".format(numPackages-1))
    uart1.write(prompt)

    time.sleep(0.1)

    rxData = bytearray();
    count = 0
    while uart1.any() > 0:
        rxData += uart1.read(1)
        time.sleep(0.0001)
        count = count + 1

    for i in range(4, count-2):
        f.write("0x{}".format(rxData[i:i+1].hex(), end=" "))

prompt = bytes.fromhex("AA0E0000F0F0")
uart1.write(prompt)