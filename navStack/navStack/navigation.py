#!/usr/bin/env python3

MAP_SIZE_PIXELS = 500
MAP_SIZE_METERS = 10
LIDAR_DEVICE = '/dev/ttyUSB0'

# Ideally we could use all 250 or so samples that the RPLidar delivers in one 
# scan, but on slower computers you'll get an empty map and unchanging position
# at that rate.
MIN_SAMPLES = 50

# Distance threshold (in cm) to consider an obstacle in the navigation logic
DISTANCE_THRESHOLD = 200

from breezyslam.algorithms import RMHC_SLAM
from breezyslam.sensors import RPLidarA1 as LaserModel
from rplidar import RPLidar as Lidar, RPLidarException
from roboviz import MapVisualizer
import time
import logging
import serial
import numpy as np

# Function to extract distances at specific angles (0°, 90°, 180°, 270°)
def extract_distances_at_angles(distances, angles):
    target_angles = [0, 90, 180, 270]
    extracted_distances = []
    
    for target_angle in target_angles:
        closest_angle_idx = min(range(len(angles)), key=lambda i: abs(angles[i] - target_angle))
        extracted_distances.append(distances[closest_angle_idx])
    
    return extracted_distances

class Robot:
    def __init__(self):
        self.navigating = True
        self.lidar = Lidar(LIDAR_DEVICE)
        self.mover = Mover()  # Replace with your actual robot control class
        self.slam = RMHC_SLAM(LaserModel(), MAP_SIZE_PIXELS, MAP_SIZE_METERS)
        self.viz = MapVisualizer(MAP_SIZE_PIXELS, MAP_SIZE_METERS, 'SLAM')

    def navigate(self):
        while self.navigating:  # Ensure that the navigation continues until manually stopped
            try:
                for scan in self.lidar.iter_scans():
                    items = [item for item in scan]
                    if len(items) < MIN_SAMPLES:
                        print("Not enough Lidar data, skipping this iteration...")
                        continue

                    distances = [item[2] for item in items]
                    angles = [item[1] for item in items]

                    print("Lidar Inputs:")
                    print("Angles:", angles)
                    print("Distances:", distances)

                    extracted_distances = extract_distances_at_angles(distances, angles)
                    print("Extracted Distances:", extracted_distances)

                    front_too_close = extracted_distances[2] < DISTANCE_THRESHOLD  # 180° (front)
                    left_too_close = extracted_distances[3] < DISTANCE_THRESHOLD   # 270° (left)
                    right_too_close = extracted_distances[1] < DISTANCE_THRESHOLD  # 90° (right)

                    if front_too_close and left_too_close and right_too_close:
                        print("All directions blocked, moving backward...")
                        self.mover.backward()
                    elif front_too_close:
                        if extracted_distances[3] > extracted_distances[1]:  
                            print("Obstacle ahead, turning left...")
                            self.mover.turn_left()
                        else:
                            print("Obstacle ahead, turning right...")
                            self.mover.turn_right()
                    elif left_too_close:
                        print(f"Obstacle on the left, turning right at angle {extracted_distances[3]}")
                        self.mover.turn_right()
                    elif right_too_close:
                        print(f"Obstacle on the right, turning left at angle {extracted_distances[1]}")
                        self.mover.turn_left()
                    else:
                        print("Path clear, moving forward...")
                        self.mover.forward()

                    self.slam.update(distances, scan_angles_degrees=angles)

                    x, y, theta = self.slam.getpos()
                    mapbytes = bytearray(MAP_SIZE_PIXELS * MAP_SIZE_PIXELS)
                    self.slam.getmap(mapbytes)

                    if not self.viz.display(x / 1000., y / 1000., theta, mapbytes):
                        break  # Stop navigation if visualization window is closed
            except RPLidarException as e:
                logging.error(f"Lidar error: {e}")
                self.navigating = False
        
        # Correcting the use of self.lidar for cleanup
        self.lidar.clean_input()
        self.lidar.stop()
        self.lidar.disconnect()
        self.lidar = Lidar(LIDAR_DEVICE)

class Mover:
    def forward(self):
        print("Moving forward")

    def backward(self):
        print("Moving backward")

    def turn_left(self):
        print("Turning left")

    def turn_right(self):
        print("Turning right")

if __name__ == '__main__':
    robot = Robot()
    robot.navigate()

