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

    # SET PACKAGE SIZE: 256 bytes
    uart1.write(bytes.fromhex("AA 06 08 00 01 00")) 
    time.sleep(0.1)
    rxData = bytearray()
    while uart1.any() > 0:
        rxData += uart1.read()
    print("Set package size response:", rxData)


def take_image(uart1, filename):

    # GET PICTURE
    uart1.write(bytes.fromhex("AA 04 05 00 00 00"))
    rxData = bytearray()

    while uart1.any()<12:
        time.sleep(0.0001)
    
    while uart1.any() > 0:
        rxData += uart1.read()

    length_bytes = rxData[9],rxData[10],rxData[11]
    length = length_bytes[0] + (length_bytes[1] << 8) + (length_bytes[2] << 16)
    no_packets = math.ceil(length/(250))

    #print(no_packets, " NUMBER OF PACKETS")

    with open(filename, "wb") as img_file:
        for i in range(0, no_packets):
            print(f"Requesting packet {i} ...")
            hex_4 = f"{i:04X}"  
            swapped_str = hex_4[2:] + hex_4[:2]  
            prompt = bytes.fromhex("AA0E0000" + swapped_str)

            uart1.write(prompt)

            if i < no_packets-1:

                while uart1.any() < 256:
                    time.sleep(0.0001)

                packet = uart1.read(256)
                img_file.write(packet[4:254])

            else:

                last_packet = bytes()
                last_packet_header = uart1.read(4)
                data_length = int.from_bytes(last_packet_header[2:4], 'little')

                if uart1.any() < data_length:

                    while uart1.any() < data_length:
                        time.sleep(0.0001)

                    last_packet = uart1.read(data_length)

                else:

                    last_packet = uart1.read(data_length)

                img_file.write(last_packet)

                while uart1.any():
                    uart1.read(1)

                uart1.write(bytes.fromhex("AA 0E 00 00 F0 F0"))
            

def main(frames):

    uart1 = UART(0, baudrate=921600, tx=Pin(0), rx=Pin(1))
    init(uart1)
    start = time.ticks_ms()

    for i in range(frames):
        take_image(uart1, f"frame_{i}_new.jpg")

    return start

        

start = main(20)
end = time.ticks_ms()
elapsed = time.ticks_diff(end, start)
print("Time taken for 20 frames: ", elapsed, "ms")