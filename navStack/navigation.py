import time
import threading
import heapq
import numpy as np
from lidar import LidarReader  # Integrating LidarReader
from motordriver import MotorController  # Motor control
from breezyslam.algorithms import RMHC_SLAM
from breezyslam.sensors import RPLidar as LaserModel
from mapvisualizer import MapVisualizer  # Assuming this is another module for visualizing the map
from multiprocessing import Process, Queue, Value

MAP_SIZE_PIXELS = 500
MAP_SIZE_METERS = 10

class Robot:
    def __init__(self):
        # Initialize components
        self.lidar = LidarReader('/dev/ttyUSB0')  # Using RPLIDAR for data
        self.mover = MotorController()  # Motor control
        self.slam = RMHC_SLAM(LaserModel(), MAP_SIZE_PIXELS, MAP_SIZE_METERS)
        self.viz = MapVisualizer(MAP_SIZE_PIXELS, MAP_SIZE_METERS, 'SLAM')
        self.mapbytes = bytearray(MAP_SIZE_PIXELS * MAP_SIZE_PIXELS)
        self.navigating = True
        self.visited_positions = set()
        self.path_queue = []

        self.thread = threading.Thread(target=self.navigate, args=())
        self.thread.daemon = True
        self.thread.start()

    def construct_map(self):
        while True:
            time.sleep(0.0001)
            self.slam.update(self.lidar.get_data())  # Get LiDAR data
            x, y, theta = self.slam.getpos()
            self.slam.getmap(self.mapbytes)
            if not self.viz.display(x / 1000., y / 1000., theta, self.mapbytes):
                break

    def navigate(self):
        while self.navigating:
            time.sleep(0.01)
            self.follow_shortest_path()

    def follow_shortest_path(self):
        x, y, _ = self.slam.getpos()
        pos = (int(x), int(y))
        if pos in self.visited_positions:
            return
        self.visited_positions.add(pos)

        neighbors = self.get_possible_moves(x, y)
        for nx, ny in neighbors:
            heapq.heappush(self.path_queue, (self.distance(nx, ny), (nx, ny)))

        if self.path_queue:
            _, next_pos = heapq.heappop(self.path_queue)
            self.move_toward(next_pos)
        else:
            self.avoid_obstacles()

    def get_possible_moves(self, x, y):
        moves = [(x + 10, y), (x - 10, y), (x, y + 10), (x, y - 10)]
        return [(nx, ny) for nx, ny in moves if (0 <= nx < MAP_SIZE_PIXELS and 0 <= ny < MAP_SIZE_PIXELS)]

    def distance(self, x, y):
        return np.linalg.norm(np.array([x, y]))

    def move_toward(self, target):
        x, y, _ = self.slam.getpos()
        tx, ty = target
        if tx > x:
            self.mover.turn_right()
        elif tx < x:
            self.mover.turn_left()
        self.mover.forward()

    def avoid_obstacles(self):
        front_too_close = self.lidar.container[180] < 400  # Example threshold
        left_too_close = min(self.lidar.container[95:175]) < 250
        right_too_close = min(self.lidar.container[185:265]) < 250

        if front_too_close and left_too_close and right_too_close:
            self.mover.backward()
        elif front_too_close:
            if self.lidar.container[270] > self.lidar.container[90]:
                self.mover.turn_left()
            else:
                self.mover.turn_right()
        elif left_too_close:
            self.mover.turn_right()
        elif right_too_close:
            self.mover.turn_left()
        else:
            self.mover.forward()

    def shutdown(self):
        self.navigating = False
        self.thread.join()
        self.mover.shutdown()

if __name__ == "__main__":
    robot = Robot()
    robot.construct_map()  # Start constructing the map
    robot.shutdown()  # Shut down when done
    print("Safely exited.")
