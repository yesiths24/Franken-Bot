import numpy as np
import serial
import time
import threading


class RPLidarReader:
    def __init__(self, port, baudrate):
        self.serialport = serial.Serial(port=port, baudrate=baudrate)
        self.serialport.reset_input_buffer()
        self.serialport.reset_output_buffer()
        self.state = 0
        # The container stores the distance for a certain angle
        self.container = np.zeros(360)
        self.right_container = np.empty(80)  # 95-175
        self.left_container = np.empty(80)  # 185-265
        self.right_container.fill(30000)  # The maximum distance the lidar can detect is 3 meters
        self.left_container.fill(30000)  # Fill distance array with the maximum distance  
        self.thread = threading.Thread(target=self.read, args=())
        self.thread.daemon = True
        self.thread.start()
        
    def get_data(self):
        return list(self.container)

    def read(self):
        while True:
            try:
                time.sleep(0.0001)  # Do not hog the processor power
                if self.state == 0:
                    serial_data = ord(self.serialport.read(1))
                    # RPLIDAR start byte (0xA5 is typically the start byte for RPLIDAR)
                    if serial_data == 0xA5:
                        self.state = 1
                    else:
                        self.state = 0
                elif self.state == 1:
                    serial_data = ord(self.serialport.read(1))
                    if serial_data == 0x5A:  # Header byte indicating start of data packet
                        self.state = 2
                    else:
                        self.state = 0
                elif self.state == 2:
                    data = [ord(b) for b in self.serialport.read(9)]  # Read 9 bytes of data
                    if len(data) < 9:
                        continue
                    angle = (data[1] << 8) | data[0]  # Combine first 2 bytes for angle
                    dist = (data[3] << 8) | data[2]  # Combine next 2 bytes for distance
                    quality = data[8]  # Quality of the reading
                    if quality != 0 and dist > 50:  # Ignore invalid or zero-quality readings
                        self.store(angle, dist)
                    self.state = 0
            except Exception as e:
                print(f"Error reading RPLIDAR data: {e}")
                exit(0)

    def store(self, angle, dist_mm):
        # Store data based on angle
        if angle >= 180:
            self.container[angle - 180] = dist_mm
        else:
            self.container[angle + 180] = dist_mm
        
        # Store data in specific containers for right/left angles
        if 95 <= angle < 175:
            self.right_container[angle - 95] = dist_mm
        elif 185 <= angle < 265:
            self.left_container[angle - 186] = dist_mm

    def checksum(self, data):
        # Compute and return the checksum as an int
        chk32 = 0
        for d in data:
            chk32 = (chk32 << 1) + d
        
        checksum = (chk32 & 0x7FFF) + (chk32 >> 15)
        checksum = checksum & 0x7FFF
        return int(checksum)
    
    def compute_speed(self, data):
        speed_rpm = float(data[0] | (data[1] << 8)) / 64.0
        return speed_rpm

        
if __name__ == "__main__":
    reader = RPLidarReader('/dev/ttyUSB0', 115200)  # Replace with your actual port
    while True:
        time.sleep(0.01)
        data = reader.get_data()  # Retrieve current lidar data
        print(data)  # Print or process data as needed

