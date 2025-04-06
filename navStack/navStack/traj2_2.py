#!/usr/bin/env python3

MAP_SIZE_PIXELS = 500
MAP_SIZE_METERS = 10
LIDAR_DEVICE = '/dev/ttyUSB0'

MIN_SAMPLES = 50
DISTANCE_THRESHOLD = 200  # in cm

from breezyslam.algorithms import RMHC_SLAM
from breezyslam.sensors import RPLidarA1 as LaserModel
from rplidar import RPLidar as Lidar, RPLidarException
from roboviz import MapVisualizer
import time
import logging
import serial
import numpy as np
from PIL import Image
import io
import heapq

import matplotlib
matplotlib.use('Agg')  # Use Agg backend for headless environments
import matplotlib.pyplot as plt


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

# Heuristic for A* algorithm (Euclidean distance)
def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

class PathPlanner:
    def __init__(self, map_size_pixels):
        self.map_size_pixels = map_size_pixels
        self.closed_set = set()  # A set to store visited nodes
        self.open_set = []  # Priority queue for nodes to explore
        self.came_from = {}  # Tracks the best path to each node

    def plan_path(self, start, goal, map_grid):
        # A* path planning
        # Initialize the open set with the start position
        heapq.heappush(self.open_set, (0, start))
        g_score = {start: 0}
        f_score = {start: heuristic(start, goal)}

        while self.open_set:
            current_f, current = heapq.heappop(self.open_set)
            if current == goal:
                path = self.reconstruct_path(current)
                return path

            self.closed_set.add(current)

            for neighbor in self.get_neighbors(current):
                if self.is_valid_move(neighbor, map_grid):
                    tentative_g_score = g_score[current] + 1  # assuming uniform cost

                    if neighbor in g_score and tentative_g_score >= g_score[neighbor]:
                        continue

                    if neighbor not in self.closed_set:
                        heapq.heappush(self.open_set, (tentative_g_score + heuristic(neighbor, goal), neighbor))
                        g_score[neighbor] = tentative_g_score
                        f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                        self.came_from[neighbor] = current

        return []

    def get_neighbors(self, node):
        x, y = node
        neighbors = [
            (x+1, y), (x-1, y),  # right, left
            (x, y+1), (x, y-1)   # down, up
        ]
        return neighbors

    def is_valid_move(self, position, map_grid):
        x, y = position
        if 0 <= x < self.map_size_pixels and 0 <= y < self.map_size_pixels:
            return map_grid[y * self.map_size_pixels + x] != 255  # 255 means obstacle
        return False

    def reconstruct_path(self, current):
        path = []
        while current in self.came_from:
            path.append(current)
            current = self.came_from[current]
        path.reverse()
        return path


class Robot:
    def __init__(self):
        self.navigating = True
        self.lidar = Lidar(LIDAR_DEVICE)
        self.mover = Mover()
        self.slam = RMHC_SLAM(LaserModel(), MAP_SIZE_PIXELS, MAP_SIZE_METERS)
        self.viz = MapVisualizer(MAP_SIZE_PIXELS, MAP_SIZE_METERS, 'SLAM')
        self.trajectory = []
        self.path_planner = PathPlanner(MAP_SIZE_PIXELS)

    def navigate(self):
        try:
            while self.navigating:
                for scan in self.lidar.iter_scans():
                    items = [item for item in scan]
                    if len(items) < MIN_SAMPLES:
                        print("Not enough Lidar data, skipping this iteration...")
                        continue

                    distances = [item[2] for item in items]
                    angles = [item[1] for item in items]

                    extracted_distances = extract_distances_at_angles(distances, angles)

                    front_too_close = extracted_distances[2] < DISTANCE_THRESHOLD
                    left_too_close = extracted_distances[3] < DISTANCE_THRESHOLD
                    right_too_close = extracted_distances[1] < DISTANCE_THRESHOLD

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

                    # Frontier exploration (find closest frontier)
                    frontier = self.find_closest_frontier(mapbytes, (x, y))

                    if frontier:
                        print(f"Planning path to frontier at {frontier}")
                        path = self.path_planner.plan_path((x, y), frontier, mapbytes)

                        # Execute the path
                        for step in path:
                            self.move_to(step)

                    if not self.viz.display(x / 1000., y / 1000., theta, mapbytes):
                        self.navigating = False
                        break

                    send_map_to_pico(mapbytes, MAP_SIZE_PIXELS, MAP_SIZE_PIXELS)

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
        # Find the closest unexplored frontier (simple check for free space near explored area)
        frontier = None
        for y in range(MAP_SIZE_PIXELS):
            for x in range(MAP_SIZE_PIXELS):
                if mapbytes[y * MAP_SIZE_PIXELS + x] == 0:  # Free space
                    # Check if the position is a frontier (adjacent to explored area)
                    if self.is_adjacent_to_explored(x, y, mapbytes):
                        frontier = (x, y)
                        break
            if frontier:
                break
        return frontier

    def is_adjacent_to_explored(self, x, y, mapbytes):
        # Check if the current position is adjacent to an explored area
        neighbors = [
            (x + 1, y), (x - 1, y),
            (x, y + 1), (x, y - 1)
        ]
        for nx, ny in neighbors:
            if 0 <= nx < MAP_SIZE_PIXELS and 0 <= ny < MAP_SIZE_PIXELS:
                if mapbytes[ny * MAP_SIZE_PIXELS + nx] == 0:  # Free space adjacent
                    return True
        return False

    def move_to(self, step):
        # Placeholder for moving to a specific position (robot's movement logic)
        print(f"Moving to {step}")


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

