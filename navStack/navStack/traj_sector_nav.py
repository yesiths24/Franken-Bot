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

MAP_SIZE_PIXELS = 500
MAP_SIZE_METERS = 10
LIDAR_DEVICE = '/dev/ttyUSB0'

MIN_SAMPLES = 50
DISTANCE_THRESHOLD = 40000  # in mm

PICO_SERIAL_PORT = '/dev/ttyAMA0'
BAUD_RATE = 115200

def extract_average_distances_by_sector(distances, angles):
    sectors = {
        'front': (345, 15),
        'left': (75, 105),
        'back': (165, 195),
        'right': (255, 285)
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
        next(self.iterator)

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

                sector_dists = extract_average_distances_by_sector(distances, angles)
                front_too_close = sector_dists['front'] < DISTANCE_THRESHOLD
                left_too_close = sector_dists['left'] < DISTANCE_THRESHOLD
                right_too_close = sector_dists['right'] < DISTANCE_THRESHOLD

                if front_too_close and left_too_close and right_too_close:
                    self.mover.backward()
                elif front_too_close:
                    if sector_dists['left'] > sector_dists['right']:
                        self.mover.turn_left()
                    else:
                        self.mover.turn_right()
                elif left_too_close:
                    self.mover.turn_right()
                elif right_too_close:
                    self.mover.turn_left()
                else:
                    self.mover.forward()

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

            except RPLidarException as e:
                logging.error(f"Lidar error: {e}")
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
