from machine import UART, Pin
import time
import math

uart1 = UART(0, baudrate=921600, tx=Pin(0), rx=Pin(1))

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

#SET PACKAGE SIZE 512 Bytes
txData = bytes.fromhex("AA 06 08 00 02 00")
rxData = bytes()

uart1.write(txData)

time.sleep(0.1)
while uart1.any() > 0:
    rxData += uart1.read(1)

print(rxData.hex(' '))

#SNAPSHOT
# txData = bytes.fromhex("AA 05 00 00 00 00")
# rxData = bytes()

# uart1.write(txData)

# time.sleep(0.1)
# while uart1.any() > 0:
#     rxData += uart1.read(1)

# print(rxData.hex(' '))

#GET PICTURE
frame_counter = 0

while frame_counter<20:
    txData = bytes.fromhex("AA 04 05 00 00 00")
    rxData = bytes()

    uart1.write(txData)

    time.sleep(0.1)
    while uart1.any() > 0:
        rxData += uart1.read(1)
        time.sleep(0.01)

    print(rxData.hex(''))


    size = rxData[11]*256^2 + rxData[10]*256 + rxData[9]

    print("Image Size: {}".format(size))
    numPackages = math.ceil(size / (512-6))

    filename = "testimage_{}.jpg".format(frame_counter)

    with open(filename, "wb") as f:
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
                
            

            f.write(rxData[4:510])
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

        #for i in range(4, count-2):
        f.write(rxData[4:count-2])

    frame_counter += 1
    prompt = bytes.fromhex("AA0E0000F0F0")

    uart1.write(prompt)