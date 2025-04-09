#!/usr/bin/env python3

import time
import logging
import serial
import threading
import queue
import numpy as np
from rplidar import RPLidar, RPLidarException

# BreezySLAM + RPLidar sensor model
from breezyslam.algorithms import RMHC_SLAM
from breezyslam.sensors import RPLidarA1 as LaserModel

# Your map visualizer
from mapgen import MapVisualizer

# HuskyLens
from huskylib import HuskyLensLibrary, Block

# =============================================================================
# =                            CONSTANTS & CONFIG                             =
# =============================================================================

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

# =============================================================================
# =                            HELPER FUNCTIONS                               =
# =============================================================================

def learnObject(hl):
    """Pause and let the user train the HuskyLens for object tracking."""
    input("Press Enter when ready to learn object on HuskyLens...")
    hl.learn(1)
    input("Press Enter to continue...")

def clamp(val, min_val, max_val):
    """Clamp 'val' to the [min_val, max_val] range."""
    return max(min(val, max_val), min_val)

def extract_average_distances_by_sector(distances, angles):
    """
    Given arrays of distances (mm) and angles (deg),
    return average distance in each sector: front, right, back, left.
    """
    sectors = {
        'front': (345, 15),  # Spans around angle 0
        'right': (75, 105),
        'back': (165, 195),
        'left': (255, 285)
    }
    sector_averages = {}

    angles_np = np.array(angles)
    distances_np = np.array(distances)

    for key, (start, end) in sectors.items():
        if start < end:
            # Normal case, e.g. right: 75..105
            mask = (angles_np >= start) & (angles_np <= end)
        else:
            # For front, e.g. 345..360 or 0..15
            mask = (angles_np >= start) | (angles_np <= end)

        sector_distances = distances_np[mask]
        avg = np.mean(sector_distances) if len(sector_distances) > 0 else float('inf')
        sector_averages[key] = avg

    return sector_averages

# =============================================================================
# =                          LIDAR READER (THREAD)                            =
# =============================================================================

class LidarReader(threading.Thread):
    """
    A background thread that continuously reads from the RPLidar
    and puts the scan data into a thread-safe queue.
    """

    def __init__(self, device='/dev/ttyUSB0', min_samples=50):
        super().__init__()
        self.device = device
        self.min_samples = min_samples
        self.lidar = None
        self.iterator = None
        self.scan_queue = queue.Queue()
        self.running = False

    def run(self):
        """Thread entry point: connect to the LiDAR and read scans in a loop."""
        try:
            self.lidar = RPLidar(self.device)
            self.iterator = self.lidar.iter_scans()
            self.running = True
            print(f"[LidarReader] LiDAR connected on {self.device}, thread started.")
        except Exception as e:
            print(f"[LidarReader] Failed to connect to LiDAR: {e}")
            self.running = False
            return

        while self.running:
            try:
                scan = next(self.iterator)  # blocks until a new scan
                # Convert generator to a list of (quality, angle, distance)
                items = list(scan)

                if len(items) >= self.min_samples:
                    # Put the scan data in the queue
                    self.scan_queue.put(items)
                else:
                    # Not enough data; skip or continue reading
                    pass

            except RPLidarException as e:
                print(f"[LidarReader] RPLidarException: {e}")
                self._reconnect()

            except StopIteration:
                print("[LidarReader] StopIteration encountered, stopping thread.")
                self.running = False
            except Exception as e:
                print(f"[LidarReader] Error in LiDAR thread: {e}")
                self._reconnect()

        # Cleanup after exiting the loop
        self._cleanup()

    def _reconnect(self):
        """Attempt to recover from LiDAR errors by stopping/restarting."""
        self._cleanup()
        time.sleep(1.0)
        try:
            print("[LidarReader] Attempting LiDAR reconnection...")
            self.lidar = RPLidar(self.device)
            self.iterator = self.lidar.iter_scans()
            print("[LidarReader] Reconnected successfully.")
        except Exception as e:
            print(f"[LidarReader] Reconnection failed: {e}")
            self.running = False

    def _cleanup(self):
        """Stop and disconnect the LiDAR hardware safely."""
        if self.lidar:
            try:
                self.lidar.stop()
                self.lidar.stop_motor()
                self.lidar.disconnect()
            except Exception as e:
                print(f"[LidarReader] Cleanup error: {e}")
        self.lidar = None
        self.iterator = None

    def stop(self):
        """Signal the thread to stop reading LiDAR data."""
        self.running = False

    def get_scan(self, timeout=0.05):
        """
        Return the latest LiDAR scan from the queue or None if no new scan arrives.
        Each scan is a list of (quality, angle, distance) tuples.
        """
        try:
            return self.scan_queue.get(timeout=timeout)
        except queue.Empty:
            return None

# =============================================================================
# =                               MOVER CLASS                                 =
# =============================================================================

class Mover:
    """
    Handles sending movement commands to your robot's Pico over UART.
    """

    def __init__(self, pico_serial_port=PICO_SERIAL_PORT):
        self.ser = serial.Serial(pico_serial_port, BAUD_RATE, timeout=1)
        time.sleep(2)
        self.state = None

    def send_command(self, cmd):
        if self.state != cmd:
            try:
                self.ser.write(cmd.encode())
                print(f"[Mover] Sent command: {cmd}")
                self.state = cmd
            except serial.SerialException as e:
                print(f"[Mover] Serial error: {e}")

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

    def set_motor_speed(self, left, right):
        """
        left, right should be bytes or integers within some range.
        Example usage: self.set_motor_speed(80, 100)
        """
        self.send_command(f"MTS{left}{right}")

# =============================================================================
# =                              ROBOT CLASS                                  =
# =============================================================================

class Robot:
    """
    The main robot class:
      - Starts a LidarReader thread.
      - Uses BreezySLAM to build a map.
      - Periodically checks HuskyLens for an object.
      - Moves according to LiDAR-based obstacle avoidance, or object tracking.
    """

    def __init__(self, hl):
        self.hl = hl
        self.navigating = True
        self.mover = Mover()

        # Initialize SLAM & Visualizer
        self.slam = RMHC_SLAM(LaserModel(), MAP_SIZE_PIXELS, MAP_SIZE_METERS)
        self.viz = MapVisualizer(MAP_SIZE_PIXELS, MAP_SIZE_METERS, 'SLAM')
        self.trajectory = []

        # Start LiDAR reading in background
        self.lidar_reader = LidarReader(device=LIDAR_DEVICE, min_samples=MIN_SAMPLES)
        self.lidar_reader.start()
        time.sleep(1.0)  # let LiDAR spin up

        # We’ll store “last_action” to reduce flip-flopping.
        self.last_action = None

        # Count for map saving frequency
        self.map_save_counter = 0

    def navigate(self):
        """
        Main control loop: read LiDAR scans, do obstacle avoidance + SLAM,
        then do a short check for object tracking each iteration.
        """
        while self.navigating:
            # 1) Get the latest LiDAR scan (non-blocking)
            scan_items = self.lidar_reader.get_scan(timeout=0.1)
            if scan_items is not None:
                # Process the new LiDAR scan
                distances = [i[2] for i in scan_items]
                angles = [i[1] for i in scan_items]

                if len(distances) >= MIN_SAMPLES:
                    self._do_obstacle_avoidance(distances, angles)
                    self._update_slam(distances, angles)
                    self._maybe_save_map()

            # 2) Check if we need to track an object (non-blocking approach)
            tracking_status = self.track_once()
            if tracking_status == "STOP":
                # Object is close enough to stop everything
                print("[Robot] Object is close! Stopping navigation.")
                self.mover.halt()
                self.navigating = False
                break

            # Sleep a bit so we don’t spin too fast
            time.sleep(0.05)

        # Cleanup LiDAR thread
        self.lidar_reader.stop()
        self.lidar_reader.join()
        print("[Robot] Navigation ended, LiDAR thread stopped.")

    def _do_obstacle_avoidance(self, distances, angles):
        """
        Simple obstacle avoidance logic, same idea as your code:
        - if something is too close in front => turn
        - if something is too close on left => turn right, etc.
        - else => go forward
        """
        sector_dists = extract_average_distances_by_sector(distances, angles)
        front_too_close = sector_dists['front'] < DISTANCE_THRESHOLD
        left_too_close  = sector_dists['left']  < DISTANCE_THRESHOLD
        right_too_close = sector_dists['right'] < DISTANCE_THRESHOLD

        if front_too_close and left_too_close and right_too_close:
            self.mover.backward()
            self.last_action = "backward"
        elif front_too_close:
            if sector_dists['left'] > sector_dists['right']:
                self.mover.turn_left()
                self.last_action = "turn_left"
            else:
                self.mover.turn_right()
                self.last_action = "turn_right"
        elif left_too_close:
            if self.last_action != "turn_right":
                self.mover.turn_right()
                self.last_action = "turn_right"
        elif right_too_close:
            if self.last_action != "turn_left":
                self.mover.turn_left()
                self.last_action = "turn_left"
        else:
            self.mover.forward()
            self.last_action = "forward"

    def _update_slam(self, distances, angles):
        """Run BreezySLAM update and maintain a simple trajectory for drawing."""
        self.slam.update(distances, scan_angles_degrees=angles)
        x, y, theta = self.slam.getpos()
        self.trajectory.append((x, y))

    def _maybe_save_map(self):
        """
        Occasionally save a visualization of the map with the current robot pose.
        """
        self.map_save_counter += 1
        if self.map_save_counter < 20:
            return

        self.map_save_counter = 0
        mapbytes = bytearray(MAP_SIZE_PIXELS * MAP_SIZE_PIXELS)
        self.slam.getmap(mapbytes)

        # Mark the path in black
        for tx, ty in self.trajectory:
            mx = int(tx * MAP_SIZE_PIXELS / (MAP_SIZE_METERS * 1000))
            my = int(ty * MAP_SIZE_PIXELS / (MAP_SIZE_METERS * 1000))
            if 0 <= mx < MAP_SIZE_PIXELS and 0 <= my < MAP_SIZE_PIXELS:
                mapbytes[my * MAP_SIZE_PIXELS + mx] = 0

        # Save a JPEG visual
        x, y, theta = self.slam.getpos()
        img_bytes = self.viz.get_viz_bytes(x / 1000., y / 1000., theta, mapbytes)
        with open("output_viz.jpg", "wb") as f:
            f.write(img_bytes)
        print("[Robot] Saved updated map visualization to output_viz.jpg")

    def track_once(self):
        """
        Poll the HuskyLens for learned blocks (object).
        Returns "STOP" if the object is close enough to halt.
        Returns None otherwise.
        (Non-blocking single call, so LiDAR thread won't overflow.)
        """
        if not self.hl:
            return None

        # Attempt to get blocks from HuskyLens
        try:
            blocks = self.hl.learnedBlocks()
        except IndexError:
            blocks = None

        if not blocks:
            # No object in view => normal navigation continues
            return None

        # If multiple blocks, pick the first or biggest
        # (Below is a naive approach; you can refine this.)
        if isinstance(blocks, list):
            obj = blocks[0]
        else:
            obj = blocks

        # If the object is very close, STOP everything
        if obj.height >= STOP_HEIGHT:
            return "STOP"

        # Otherwise, do a small tracking adjustment
        # (Your offset-based turning logic)
        offset = obj.x - 160  # 160 is center of 320 pixel width
        scale = 0.6
        turn = clamp(int(offset * scale), -100, 100)

        # If basically centered, move forward a bit
        if -10 < offset < 10:
            self.mover.forward()
            print("[Robot] Tracking: object roughly centered, moving forward.")
        else:
            # Turn in place or differential speed
            left_speed = clamp(80 - turn, -100, 100)
            right_speed = clamp(80 + turn, -100, 100)
            left_byte = left_speed.to_bytes(1, byteorder='little', signed=True)
            right_byte = right_speed.to_bytes(1, byteorder='little', signed=True)
            self.mover.set_motor_speed(left_byte, right_byte)
            print(f"[Robot] Tracking: offset={offset}, L={left_speed}, R={right_speed}")

        # Return None if we didn’t tell the robot to STOP
        return None

# =============================================================================
# =                                MAIN CODE                                  =
# =============================================================================

if __name__ == '__main__':
    # 1. Prompt user to start
    input("Press Enter to start navigation...")

    # 2. Attempt to connect to HuskyLens
    attempts = 0
    success = 0
    hl = None
    while attempts < 3 and success == 0:
        try:
            hl = HuskyLensLibrary("SERIAL", "/dev/ttyUSB1", 3000000)
            success = 1
        except IndexError:
            print("HuskyLens connection error, retrying...")
            attempts += 1
            success = 0

    # If successful, set mode
    if hl:
        mode = input("Please enter mode of operation:\n1: tag recognition\n2: object tracking\n> ")
        if mode == "1":
            hl.algorthim("ALGORITHM_TAG_RECOGNITION")
        elif mode == "2":
            hl.algorthim("ALGORITHM_OBJECT_TRACKING")
        else:
            print("Invalid selection; defaulting to object tracking.")
            hl.algorthim("ALGORITHM_OBJECT_TRACKING")
        learnObject(hl)
    else:
        print("Warning: HuskyLens not initialized. Proceeding without HL.")

    # 3. Create Robot and start navigation
    robot = Robot(hl)
    robot.navigate()

    print("Main script complete.")
