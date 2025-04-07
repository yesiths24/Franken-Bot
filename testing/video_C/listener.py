import serial

PORT = "/dev/tty.usbmodem1201"
BAUD = 115200
START_TEXT = b'---START-IMAGE---'
END_TEXT = b'---END-IMAGE---'

with serial.Serial(PORT, BAUD, timeout=1) as ser:
    print("Listening for START marker...")

    while True:
        line = ser.readline()

        print(f"Line read: {line!r}")
        
        stripped = line.strip()
        
        if START_TEXT in stripped:
            print("Start marker received")
            break
    
    image = bytearray()
    
    while True:
        chunk = ser.read(512)  
        if not chunk:
            continue
        
        end_idx = chunk.find(END_TEXT)
        
        if end_idx != -1:
            image.extend(chunk[:end_idx])
            print("End marker received")
            break
        else:
            image.extend(chunk)


    with open("captured_image.jpg", "wb") as f:
        f.write(image)
    print("Image saved as captured_image.jpg")
