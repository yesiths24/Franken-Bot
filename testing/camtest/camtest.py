from machine import UART, Pin
import time
import math

def sync(uart1):
    # SYNC
    txData = bytes.fromhex("AA 0D 00 00 00 00")
    rxData = bytes()
    wait = 0.005
    for i in range(60):
        uart1.write(txData)
        time.sleep(wait)
        wait = wait+0.001
        if uart1.any()>0:
            break
    
    while uart1.any() > 0:
        rxData += uart1.read(1)
        #print(rxData)
        

    ACK = bytes.fromhex("AA0E0D000000")
    uart1.write(ACK)
    time.sleep(0.1)

def read_exact_bytes_blocking(uart, num_bytes):
    buffer = bytearray()
    while len(buffer) < num_bytes:
        if uart.any():
            chunk = uart.read(num_bytes - len(buffer))
            if chunk:
                buffer.extend(chunk)
    return buffer

def take_image(uart1):
    #INITIAL JPEG
    txData = bytes.fromhex("AA 01 00 07 03 05")
    rxData = bytes()

    uart1.write(txData)

    time.sleep(0.1)
    while uart1.any() > 0:
        rxData += uart1.read(1)
        #print(rxData)

    #SET PACKAGE SIZE 512 Byte
    txData = bytes.fromhex("AA 06 08 00 02 00")
    rxData = bytes()

    uart1.write(txData)
    
    time.sleep(0.1)
    while uart1.any() > 0:
        rxData += uart1.read(1)
        #print(rxData)

    #GET PICTURE
    txData = bytes.fromhex("AA 04 05 00 00 00")
    rxData = bytes()

    uart1.write(txData)

    time.sleep(0.1)

    while uart1.any() > 0:
        rxData += uart1.read(1)
        #print("ACK1", rxData)
    
    image_data = bytearray()

    for i in range(0, 0xF0F0 + 1):
        print("reached: ", i) 
        prompt = bytes.fromhex("AA0E0000{:04X}".format(i))
        uart1.write(prompt)
        time.sleep(0.01)

        #rxData = bytearray()
        while uart1.any()>0:
            image_data += uart1.read(1)
            time.sleep(0.0001)
    
    return image_data

def main():
    uart1 = UART(0, baudrate=921600, tx=Pin(0), rx=Pin(1))
    sync(uart1)
    image_data = take_image(uart1)
    filename = "image_test.jpg"
    with open(filename, "wb") as img_file:
            img_file.write(image_data)
    '''
    while (count<5):
        #print(count)
        image_data = take_image(uart1)
        filename = f"frame_{count}.jpg"
        with open(filename, "wb") as img_file:
            img_file.write(image_data)
        count +=1
        time.sleep(0.5)
    '''
        
main()


