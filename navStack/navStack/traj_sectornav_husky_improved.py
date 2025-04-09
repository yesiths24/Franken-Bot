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
import png
# --- HUSKYLENS ---
from huskylib import HuskyLensLibrary, Block

# --- Constants ---
MAP_SIZE_PIXELS = 500
MAP_SIZE_METERS = 10
LIDAR_DEVICE = '/dev/ttyUSB0'
PICO_SERIAL_PORT = '/dev/ttyAMA0'
BAUD_RATE = 115200
MIN_SAMPLES = 50
DISTANCE_THRESHOLD = 700  # in mm
CENTER_MIN = 140
CENTER_MAX = 180
STOP_HEIGHT = 100

# --- Helper Functions ---

def learnObject(hl):
    input("Press enter when ready to learn object...")
    hl.learn(1)
    input("Press enter when ready to continue...")

#Function for calc motor speeds from hl input
def clamp(val, min_val, max_val):
    return max(min(val, max_val), min_val)

def extract_average_distances_by_sector(distances, angles):
    sectors = {
        'front': (345, 15),  # Spans around 0
        'right': (75, 105),
        'back': (165, 195),
        'left': (255, 285)
    }

    sector_averages = {}
    angles_np = np.array(angles)
    distances_np = np.array(distances)

    for key, (start, end) in sectors.items():
        if start < end:
            mask = (angles_np >= start) & (angles_np <= end)
        else:
            mask = (angles_np >= start) | (angles_np <= end)

        sector_distances = distances_np[mask]
        avg = np.mean(sector_distances) if len(sector_distances) > 0 else float('inf')
        sector_averages[key] = avg

    return sector_averages

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

def save_map(mapbytes, width, height):
    try:
        img = Image.frombytes('L', (width, height), bytes(mapbytes))
        img = img.transpose(Image.FLIP_TOP_BOTTOM).convert('L')
        img.save('output.jpg', format='JPEG', quality=40)
    except Exception as e:
        print(f"Error saving map: {e}")

    
#hl.algorthim("ALGORITHM_OBJECT_TRACKING") 

# --- Mover Class ---
class Mover:
    def __init__(self):
        self.ser = serial.Serial(PICO_SERIAL_PORT, 115200, timeout=1)
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

    def forward(self): self.send_command("DRF")
    def backward(self): self.send_command("DRB")
    def turn_left(self): self.send_command("DRL")
    def turn_right(self): self.send_command("DRR")
    def halt(self): self.send_command("DRS")
    def set_motor_speed(self, left, right):
        self.send_command(f"MTS{left}{right}")

# --- Main Robot Class ---
class Robot:
    def __init__(self, hl):
        self.hl = hl
        self.navigating = True
        # lidar reconnect attempt
        attempts_lidar = 0
        success_lidar = 0
        while attempts_lidar < 3 and success_lidar == 0:
            try:
                success_lidar = 1
                self.lidar = Lidar(LIDAR_DEVICE)
                break
            except ValueError:
                print("Lidar Connectoin error, retrying...")
                attempts_lidar = attempts_lidar + 1
                success_lidar = 0
                time.sleep(0.1)
        #self.lidar = Lidar(LIDAR_DEVICE)
        self.mover = Mover()
        self.slam = RMHC_SLAM(LaserModel(), MAP_SIZE_PIXELS, MAP_SIZE_METERS)
        self.viz = MapVisualizer(MAP_SIZE_PIXELS, MAP_SIZE_METERS, 'SLAM')
        self.trajectory = []
        self.iterator = self.lidar.iter_scans()
        self.mapbytes = bytearray(MAP_SIZE_PIXELS * MAP_SIZE_PIXELS)
        while attempts_lidar < 3 and success_lidar == 0:
            try:
                self.iterator = self.lidar.iter_scans()
                next(self.iterator)
                success_lidar = 1
                break
            except ValueError:
                print("Lidar Connectoin error, retrying...")
                attempts_lidar = attempts_lidar + 1
                success_lidar = 0
                time.sleep(0.5)

        if success_lidar == 0:
            raise ValueError
        #next(self.iterator)

        while attempts_lidar < 3 and success_lidar == 0:
            try:
                self.iterator = self.lidar.iter_scans()
                next(self.iterator)
                success_lidar = 1
                break
            except ValueError:
                print("Lidar Connectoin error, retrying...")
                attempts_lidar = attempts_lidar + 1
                success_lidar = 0
                time.sleep(0.5)

        if success_lidar == 0:
            raise ValueError

    def navigate(self):
        count = 0
        last_action = None
        while self.navigating:
            try:
                items = [item for item in next(self.iterator)]
                if len(items) < MIN_SAMPLES:
                    print("Not enough Lidar data, skipping this iteration...")
                    continue

                distances = [item[2] for item in items]
                angles = [item[1] for item in items]

                sector_dists = extract_average_distances_by_sector(distances, angles)
                front_too_close = sector_dists['front'] < DISTANCE_THRESHOLD
                left_too_close = sector_dists['left'] < DISTANCE_THRESHOLD
                right_too_close = sector_dists['right'] < DISTANCE_THRESHOLD

                # Weighted decision to reduce flip-flopping
                if front_too_close and left_too_close and right_too_close:
                    self.mover.backward()
                    last_action = "backward"
                elif front_too_close:
                    if (sector_dists['left'] > sector_dists['right']): #and #(abs(sector_dists['left'] - sector_dists['right'])<100):
                        self.mover.turn_left()
                        last_action = "turn_left"
                    else:
                        self.mover.turn_right()
                        last_action = "turn_right"
                elif left_too_close:
                    if last_action != "turn_right":
                        self.mover.turn_right()
                        last_action = "turn_right"
                elif right_too_close:
                    if last_action != "turn_left":
                        self.mover.turn_left()
                        last_action = "turn_left"
                else:
                    self.mover.forward()
                    last_action = "forward"

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

                if count == 20:
                    print("updating map image...")
                    img = self.viz.get_viz_bytes(x / 1000., y / 1000., theta, mapbytes)
                    with open("output_viz.jpg", "wb") as f:
                        f.write(img)
                    count = 0
                else:
                    count += 1

                if self.hl:
                    tracking_status = self.track(self.hl)
                    if tracking_status == "STOP":
                        print("Object detected nearby. Stopping robot.")
                        self.mover.halt()
                        self.navigating = False
                        break

            except RPLidarException as e:
                logging.error(f"Lidar error: {e}")
                try:
                    self.lidar.clean_input()
                    self.lidar.stop()
                    self.lidar.disconnect()
                    
                except Exception:
                    pass

                try:
                    self.lidar = Lidar(LIDAR_DEVICE)
                    self.lidar.clean_input()
                    self.iterator = self.lidar.iterscans()
                    next(self.iterator)
                    print("Lidar re-connected Succesfully")
                except Exception as e:
                    print("reconnection failed: {e}")
                    self.navigate = False

            except KeyboardInterrupt:
                print("Keyboard interrupt received. Stopping navigation.")
                self.navigating = False

        self.lidar.clean_input()
        self.lidar.stop()
        self.lidar.disconnect()

    def track(self,hl):
        try:
            obj = hl.learnedBlocks()
        except IndexError:
            obj = None

        while obj:
            print("following ")
            if not isinstance(obj, Block):
                obj = obj[0]
            if obj.height >= STOP_HEIGHT:
                self.mover.halt()
                print("Stopping, reached object!")
                return "STOP"
            
            x = obj.x
            offset = x - 160
            scale = 0.6
            turn = clamp(int(offset * scale), -100, 100)
            if -10 < offset < 10:
                self.mover.forward()
                print("Keep moving forward")
            else:
                left_speed = clamp(80 - turn, -100, 100)
                right_speed = clamp(80 + turn, -100, 100)
                left_byte = left_speed.to_bytes(1, byteorder='little', signed=True)
                right_byte = right_speed.to_bytes(1, byteorder='little', signed=True)
                self.mover.set_motor_speed(left_byte, right_byte)
                #return f"Tracking → x: {x}, L: {left_speed}, R: {right_speed}"
            try:
                obj = hl.learnedBlocks()
            except IndexError:
                obj = None

    
    # blocks = hl.learnedBlocks()
    # #print("Blocks return type:")
    # #print(type(blocks))
    # # if not blocks:
    #     #print("No Object Detected, retrying....")
    # if blocks:
    #     try:
    #         for block in blocks:
    #             #print(f"Detected Block ID: {block.ID}, Height: {block.height}")
    #             if block.height > STOP_HEIGHT:
    #                 return "STOP"
    #             else:
    #                 return "NOT FOUND"
    #     except TypeError:
    #         block = blocks
    #         #print(f"Detected Block ID: {block.ID}, Height: {block.height}")
    #         if block.height > STOP_HEIGHT:
    #             return "STOP"
    #         else:
    #             return "NOT FOUND"


# --- Main Program ---
if __name__ == '__main__':
    input("Press Enter to start navigation...")
    # HuskyLens setup
    attempts = 0
    success = 0
    while attempts < 3 and success == 0:
        try:
            success = 1
            hl = HuskyLensLibrary("SERIAL", "/dev/ttyUSB1", 3000000)
        except IndexError:
            print("Connectoin error, retrying...")
            attempts = attempts + 1
            success = 0
    #hl = HuskyLensLibrary("I2C","", address = 0x32) # Replace with correct port
    hl.algorthim("ALGORITHM_OBJECT_TRACKING") 
    learnObject(hl)
    robot = Robot(hl)
    robot.navigate()


