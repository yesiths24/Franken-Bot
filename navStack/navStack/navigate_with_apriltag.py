#!/usr/bin/env python3

import matplotlib
matplotlib.use('agg')

MAP_SIZE_PIXELS = 500
MAP_SIZE_METERS = 10
LIDAR_DEVICE = '/dev/ttyUSB0'

MIN_SAMPLES = 50
DISTANCE_THRESHOLD = 200  # in cm

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
import heapq

# UART parameters for map sending
MAP_SERIAL_PORT = '/dev/ttyUSB1'
BAUD_RATE = 115200

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

        with serial.Serial(MAP_SERIAL_PORT, BAUD_RATE, timeout=2) as ser:
            ser.write(b'START\n')
            ser.write(len(jpg_data).to_bytes(4, 'big'))
            ser.write(jpg_data)
            ser.write(b'END\n')
            print(f"Sent {len(jpg_data)} bytes to Pico.")
    except Exception as e:
        print(f"Error sending map to Pico: {e}")


# A* Path Planner

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

class PathPlanner:
    def __init__(self, map_size_pixels):
        self.map_size_pixels = map_size_pixels

    def plan_path(self, start, goal, map_grid):
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        f_score = {start: heuristic(start, goal)}
        closed_set = set()

        while open_set:
            current_f, current = heapq.heappop(open_set)
            if current == goal:
                return self.reconstruct_path(came_from, current)

            closed_set.add(current)

            for neighbor in self.get_neighbors(current):
                if not self.is_valid_move(neighbor, map_grid):
                    continue

                tentative_g = g_score[current] + 1
                if neighbor in closed_set and tentative_g >= g_score.get(neighbor, float('inf')):
                    continue

                if tentative_g < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return []

    def get_neighbors(self, node):
        x, y = node
        return [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]

    def is_valid_move(self, position, map_grid):
        x, y = position
        if 0 <= x < self.map_size_pixels and 0 <= y < self.map_size_pixels:
            return map_grid[y * self.map_size_pixels + x] < 250
        return False

    def reconstruct_path(self, came_from, current):
        path = []
        while current in came_from:
            path.append(current)
            current = came_from[current]
        path.reverse()
        return path

class HuskyLens:
    def __init__(self, port='/dev/ttyUSB2', baud=9600):
        self.ser = serial.Serial(port, baud, timeout=1)
        time.sleep(2)

    def read_tag_height(self):
        try:
            self.ser.write(b'getBlocks\r\n')
            line = self.ser.readline().decode().strip()
            if "height=" in line:
                for part in line.split():
                    if part.startswith("height="):
                        height = int(part.split("=")[1])
                        return height
        except Exception as e:
            print(f"HuskyLens read error: {e}")
        return None

class Robot:
    def __init__(self):
        self.navigating = True
        self.lidar = Lidar(LIDAR_DEVICE)
        self.mover = Mover()
        self.slam = RMHC_SLAM(LaserModel(), MAP_SIZE_PIXELS, MAP_SIZE_METERS)
        self.viz = MapVisualizer(MAP_SIZE_PIXELS, MAP_SIZE_METERS, 'SLAM')
        self.trajectory = []
        self.path_planner = PathPlanner(MAP_SIZE_PIXELS)
        self.huskylens = HuskyLens()
        self.max_tag_height = 180

    def navigate(self):
        try:
            while self.navigating:
                print("Scanning...")  # Debug log
                for scan in self.lidar.iter_scans():
                    print(f"Scan: {len(scan)} points detected.")  # Debug log
                    items = [item for item in scan if item[2] > 0]
                    if len(items) < MIN_SAMPLES:
                        print("Not enough samples, continuing scan...")  # Debug log
                        continue

                    distances = [item[2] for item in items]
                    angles = [item[1] for item in items]

                    extracted_distances = extract_distances_at_angles(distances, angles)

                    # Debug output for obstacle avoidance
                    print(f"Front: {extracted_distances[0]}, Right: {extracted_distances[1]}, Back: {extracted_distances[2]}, Left: {extracted_distances[3]}")

                    # Corrected obstacle avoidance logic
                    front_too_close = extracted_distances[0] < DISTANCE_THRESHOLD
                    right_too_close = extracted_distances[1] < DISTANCE_THRESHOLD
                    back_too_close  = extracted_distances[2] < DISTANCE_THRESHOLD
                    left_too_close  = extracted_distances[3] < DISTANCE_THRESHOLD

                    if front_too_close and left_too_close and right_too_close:
                        self.mover.backward()
                    elif front_too_close:
                        if extracted_distances[3] > extracted_distances[1]:
                            self.mover.turn_left()
                        else:
                            self.mover.turn_right()
                    elif left_too_close:
                        self.mover.turn_right()
                    elif right_too_close:
                        self.mover.turn_left()
                    else:
                        self.mover.forward()

                    # Update SLAM
                    self.slam.update(distances, scan_angles_degrees=angles)
                    x, y, theta = self.slam.getpos()
                    self.trajectory.append((x, y))

                    mapbytes = bytearray(MAP_SIZE_PIXELS * MAP_SIZE_PIXELS)
                    self.slam.getmap(mapbytes)

                    # Debug log for map data
                    print(f"Map data generated, size: {len(mapbytes)} bytes.")
                    send_map_to_pico(mapbytes, MAP_SIZE_PIXELS, MAP_SIZE_PIXELS)

                    # Frontier finding and path planning
                    frontier = self.find_closest_frontier(mapbytes, (x, y))
                    if frontier:
                        print(f"Frontier found at {frontier}. Planning path...")  # Debug log
                        start_px = (int(x * MAP_SIZE_PIXELS / (MAP_SIZE_METERS * 1000)),
                                    int(y * MAP_SIZE_PIXELS / (MAP_SIZE_METERS * 1000)))
                        path = self.path_planner.plan_path(start_px, frontier, mapbytes)
                        print(f"Planned path: {path}")  # Debug log
                        for step in path:
                            self.move_to(step)

                    if not self.viz.display(x / 1000., y / 1000., theta, mapbytes):
                        self.navigating = False
                        break

                    tag_height = self.huskylens.read_tag_height()
                    if tag_height is not None:
                        print(f"AprilTag detected with height: {tag_height}")
                        if tag_height >= self.max_tag_height:
                            print("Max tag height reached. Stopping navigation.")
                            self.mover.halt()
                            self.navigating = False
                            break

        except RPLidarException as e:
            logging.error(f"Lidar error: {e}")
            self.navigating = False
        except KeyboardInterrupt:
            print("Keyboard interrupt received. Stopping navigation.")
            self.navigating = False
        finally:
            self.lidar.clean_input()
            self.lidar.stop()
            self.lidar.disconnect()

    def find_closest_frontier(self, mapbytes, current_position):
        for y in range(MAP_SIZE_PIXELS):
            for x in range(MAP_SIZE_PIXELS):
                idx = y * MAP_SIZE_PIXELS + x
                if mapbytes[idx] == 255 and self.is_adjacent_to_explored(x, y, mapbytes):
                    return (x, y)
        return None

    def is_adjacent_to_explored(self, x, y, mapbytes):
        neighbors = [(x+1,y), (x-1,y), (x,y+1), (x,y-1)]
        for nx, ny in neighbors:
            if 0 <= nx < MAP_SIZE_PIXELS and 0 <= ny < MAP_SIZE_PIXELS:
                if mapbytes[ny * MAP_SIZE_PIXELS + nx] < 250:
                    return True
        return False

    def move_to(self, step):
        print(f"Moving to {step}")
        if not hasattr(self, 'last_step'):
            self.last_step = step
            return

        dx = step[0] - self.last_step[0]
        dy = step[1] - self.last_step[1]

        if dx == 1 and dy == 0:
            self.mover.turn_right()
            self.mover.forward()
        elif dx == -1 and dy == 0:
            self.mover.turn_left()
            self.mover.forward()
        elif dx == 0 and dy == 1:
            self.mover.forward()
        elif dx == 0 and dy == -1:
            self.mover.backward()
        else:
            print("Unknown step direction or non-adjacent step")

        time.sleep(0.1)
        self.last_step = step

class Mover:
    def __init__(self):
        self.ser = serial.Serial('/dev/ttyAMA0', 115200, timeout=1)
        time.sleep(2)

    def send_command(self, cmd):
        try:
            self.ser.write((cmd).encode())
            print(f"Sent command: {cmd}")
        except serial.SerialException as e:
            print(f"Serial error: {e}")

    def forward(self): self.send_command("DRF")
    def backward(self): self.send_command("DRB")
    def turn_left(self): self.send_command("DRL")
    def turn_right(self): self.send_command("DRR")
    def halt(self): self.send_command("DRS")

if __name__ == '__main__':
    input("Press Enter to start navigation...")
    robot = Robot()
    robot.navigate()
