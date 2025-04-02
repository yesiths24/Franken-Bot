from machine import UART, Pin
import time
import math

def sync(uart1):
    # Send SYNC
    txData = bytes.fromhex("AA 0D 00 00 00 00")
    wait = 0.005
    for _ in range(60):
        uart1.write(txData)
        time.sleep(wait)
        wait += 0.001
        if uart1.any() > 0:
            break

    rxData = bytearray()
    while uart1.any() > 0:
        rxData += uart1.read()

    print("SYNC response:", rxData)

    # ACK
    ACK = bytes.fromhex("AA0E0D000000")
    uart1.write(ACK)
    time.sleep(0.1)

def init(uart1):
    sync(uart1)
    # INITIAL JPEG
    uart1.write(bytes.fromhex("AA 01 00 07 03 05"))
    time.sleep(0.1)
    rxData = bytearray()
    while uart1.any() > 0:
        rxData += uart1.read()
    print("Init response:", rxData)

    # SET PACKAGE SIZE: 512 Bytes
    uart1.write(bytes.fromhex("AA 06 08 00 01 00")) # Right now is set to 256 bytes
    time.sleep(0.1)
    rxData = bytearray()
    while uart1.any() > 0:
        rxData += uart1.read()
    print("Set package size response:", rxData)

def take_image(uart1, filename):
    '''
    # INITIAL JPEG
    uart1.write(bytes.fromhex("AA 01 00 07 03 05"))
    time.sleep(0.1)
    rxData = bytearray()
    while uart1.any() > 0:
        rxData += uart1.read()
    print("Init response:", rxData)

    # SET PACKAGE SIZE: 512 Bytes
    uart1.write(bytes.fromhex("AA 06 08 00 01 00")) # Right now is set to 256 bytes
    time.sleep(0.1)
    rxData = bytearray()
    while uart1.any() > 0:
        rxData += uart1.read()
    print("Set package size response:", rxData)
    '''
    # GET PICTURE
    uart1.write(bytes.fromhex("AA 04 05 00 00 00"))
    time.sleep(0.1)
    rxData = bytearray()
    while uart1.any() > 0:
        rxData += uart1.read()
    print("Get picture response:", rxData)
    time.sleep(0.1)
    rxData = bytes()
    
    with open(filename, "wb") as img_file:
        for i in range(0, 0xF0F0 + 1): # Replace with 0xF0F0 + 1 if needed
            print(f"Requesting packet {i} ...")
            hex_4 = f"{i:04X}"  
            swapped_str = hex_4[2:] + hex_4[:2]  
            prompt = bytes.fromhex("AA0E0000" + swapped_str)
            print(prompt)

            uart1.write(prompt)

            time.sleep(0.1)
            #discarded = uart1.read(4)
            print(uart1.any())
            packet = uart1.read(256)
            #uart1.read(2)
            if packet is None:
                print("Timed out waiting for packet.")
                break
            #img_file.write(packet)

            img_file.write(packet[4:254])
            #JPEG end marker
            if b'\xFF\xD9' in packet:
                print("End of image detected.")
                break


def main(frames):
    uart1 = UART(0, baudrate=921600, tx=Pin(0), rx=Pin(1))
    init(uart1)
    for i in range(frames):
        take_image(uart1, f"frame_{i}_new.jpg")


main(5)
