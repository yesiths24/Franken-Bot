#!/usr/bin/env python3
from breezyslam.algorithms import RMHC_SLAM
from breezyslam.sensors import RPLidarA1 as LaserModel
from rplidar import RPLidar as Lidar, RPLidarException
from mapgen import MapVisualizer
import time
import logging
import serial
import numpy as np
from PIL import Image
import io

# Husky lens imports
import time
from huskylib import HuskyLensLibrary


MAP_SIZE_PIXELS = 500
MAP_SIZE_METERS = 10
LIDAR_DEVICE = '/dev/ttyUSB0'

MIN_SAMPLES = 50
DISTANCE_THRESHOLD = 400  # in cm

# Husky Lens constants
CENTER_MIN = 140
CENTER_MAX = 180
STOP_HEIGHT = 100 


# UART parameters for map sending
PICO_SERIAL_PORT = '/dev/ttyAMA0'
BAUD_RATE = 115200

#Function for calc motor speeds from hl input
def clamp(val, min_val, max_val):
    return max(min(val, max_val), min_val)


# Function to extract distances at specific angles (0°, 90°, 180°, 270°)
def extract_distances_at_angles(distances, angles):
    target_angles = [0, 90, 180, 270]
    extracted_distances = []

    for target_angle in target_angles:
        closest_angle_idx = min(range(len(angles)), key=lambda i: abs(angles[i] - target_angle))
        extracted_distances.append(distances[closest_angle_idx])

    return extracted_distances

# Function to send map to Pico over UART as JPEG
def send_map_to_pico(mapbytes, width, height):
    try:
        img = Image.frombytes('L', (width, height), bytes(mapbytes))
        img = img.transpose(Image.FLIP_TOP_BOTTOM).convert('L')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=40)
        jpg_data = buffer.getvalue()

        with serial.Serial(PICO_SERIAL_PORT, BAUD_RATE, timeout=2) as ser:
            ser.write(b'IM')
            ser.write(len(jpg_data).to_bytes(4, 'big'))
            ser.write(jpg_data)
            print(f"Sent {len(jpg_data)} bytes to Pico.")
    except Exception as e:
        print(f"Error sending map to Pico: {e}")
        
# Function to send map to Pico over UART as JPEG
def save_map(mapbytes, width, height):
    try:
        img = Image.frombytes('L', (width, height), bytes(mapbytes))
        img = img.transpose(Image.FLIP_TOP_BOTTOM).convert('L')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=40)
        jpg_data = buffer.getvalue()
        img.save('output.jpg', format='JPEG', quality=40)

        
    except Exception as e:
        print(f"Error sending map to Pico: {e}")



class Robot:
    def __init__(self):
        self.navigating = True
        self.lidar = Lidar(LIDAR_DEVICE)
        self.mover = Mover()
        self.slam = RMHC_SLAM(LaserModel(), MAP_SIZE_PIXELS, MAP_SIZE_METERS)
        self.viz = MapVisualizer(MAP_SIZE_PIXELS, MAP_SIZE_METERS, 'SLAM')
        self.trajectory = []
        self.iterator = self.lidar.iter_scans()
        self.mapbytes = bytearray(MAP_SIZE_PIXELS * MAP_SIZE_PIXELS)
        self.previous_distances = None
        self.previous_angles = None
        self.mode = "object_tracking"
        self.hl = HuskyLensLibrary("SERIAL", "/dev/ttyUSB1")
        next(self.iterator)

    def track(self,hl,mode):
        try:
            obj = hl.blocks()
        except IndexError:
            obj = None

        if obj:
            if obj.height >= STOP_HEIGHT:
                self.mover.halt()
                return f"Stopping, reached object!"
            
            x = obj.x
            offset = x - 160
            scale = 0.6
            turn = clamp(int(offset * scale), -100, 100)
            if -10 < offset < 10:
                self.mover.forward()
                return "Keep moving forward"
            else:
                left_speed = clamp(80 - turn, -100, 100)
                right_speed = clamp(80 + turn, -100, 100)
                left_byte = left_speed.to_bytes(1, byteorder='little', signed=True)
                right_byte = right_speed.to_bytes(1, byteorder='little', signed=True)
                self.mover.set_motor_speed(left_byte, right_byte)
                #return f"Tracking → x: {x}, L: {left_speed}, R: {right_speed}"
        else:
            raise RuntimeError("Object Not Found")
        
    def navigate(self):
        count = 0
        while self.navigating:
            try:
                items = [item for item in next(self.iterator)]
                if len(items) < MIN_SAMPLES:
                    print("Not enough Lidar data, skipping this iteration...")
                    continue

                distances = [item[2] for item in items]
                angles = [item[1] for item in items]

                extracted_distances = extract_distances_at_angles(distances, angles)

                front_too_close = extracted_distances[0] < DISTANCE_THRESHOLD
                left_too_close = extracted_distances[1] < DISTANCE_THRESHOLD
                right_too_close = extracted_distances[3] < DISTANCE_THRESHOLD

                self.slam.update(distances, scan_angles_degrees=angles)

                x, y, theta = self.slam.getpos()
                self.trajectory.append((x, y))

                mapbytes = bytearray(MAP_SIZE_PIXELS * MAP_SIZE_PIXELS)
                self.slam.getmap(mapbytes)

                for tx, ty in self.trajectory:
                    mx = int(tx * MAP_SIZE_PIXELS / (MAP_SIZE_METERS * 1000))
                    my = int(ty * MAP_SIZE_PIXELS / (MAP_SIZE_METERS * 1000))
                    if 0 <= mx < MAP_SIZE_PIXELS and 0 <= my < MAP_SIZE_PIXELS:
                        mapbytes[my * MAP_SIZE_PIXELS + mx] = 0

                # if not self.viz.display(x / 1000., y / 1000., theta, mapbytes):
                #     self.navigating = False
                #     break
                if count == 20:
                    print("updating map image...")
                    img = self.viz.get_viz_bytes(x / 1000., y / 1000., theta, mapbytes)
                    with open("output_viz.jpg", "wb") as f:
                        f.write(img)
                    count = 0
                else:
                    count = count+1
                #send_map_to_pico(mapbytes, MAP_SIZE_PIXELS, MAP_SIZE_PIXELS)

                try:
                    self.track(self.hl, self.mode)

                except RuntimeError as re:
                    if front_too_close and left_too_close and right_too_close:
                        self.mover.backward()
                    elif front_too_close:
                        if extracted_distances[1] > extracted_distances[3]:
                            self.mover.turn_left()
                        else:
                            self.mover.turn_right()
                    elif left_too_close:
                        self.mover.turn_right()
                    elif right_too_close:
                        self.mover.turn_left()
                    else:
                        self.mover.forward()
                        
                except Exception as e:
                    logging.error(f"Error: {e}")
                    
            except RPLidarException as e:
                logging.error(f"Lidar error: {e}")
                #self.navigating = False
                self.lidar.clean_input()
                
                self.lidar.stop()
                self.lidar.disconnect()
                self.lidar = Lidar(LIDAR_DEVICE)
                self.lidar.start()

            except KeyboardInterrupt:
                print("Keyboard interrupt received. Stopping navigation.")
                self.navigating = False
      
        self.lidar.clean_input()
            
        self.lidar.stop()
        self.lidar.disconnect()
        #self.lidar = Lidar(LIDAR_DEVICE)


class Mover:
    def __init__(self):
        self.ser = serial.Serial('/dev/ttyAMA0', 115200, timeout=1)
        time.sleep(2)
        self.state = None

    def send_command(self, cmd):
        if self.state != cmd:
            try:
                self.ser.write(cmd.encode())
                print(f"Sent command: {cmd}")
                self.state = cmd
            except serial.SerialException as e:
                print(f"Serial error: {e}")
        else:
            print(f"Command '{cmd}' not sent — already in state '{self.state}'")

    def set_motor_speed(self, left, right):
        self.send_command(f"MTS{left}{right}")

    def forward(self):
        self.send_command("DRF")

    def backward(self):
        self.send_command("DRB")

    def turn_left(self):
        self.send_command("DRL")

    def turn_right(self):
        self.send_command("DRR")
    
    def halt(self):
        self.send_command("DRS")

if __name__ == '__main__':
    input("Press Enter to start navigation...")
    robot = Robot()
    robot.navigate()

