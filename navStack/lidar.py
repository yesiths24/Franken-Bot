import time
import numpy as np
import threading
from rplidar import RPLidar

class LidarReader:
    def __init__(self, port):
        self.lidar = RPLidar(port)
        self.container = np.zeros(360)
        self.lidar.start_motor()
        time.sleep(2)  # Allow the motor to start up before reading
        self.lidar.start_scan()
        self.thread = threading.Thread(target=self.read, args=())
        self.thread.daemon = True
        self.thread.start()

    def get_data(self):
        return list(self.container)

    def read(self):
        try:
            for scan in self.lidar.iter_scans():
                for (_, angle, distance) in scan:
                    if 0 < distance < 3000:  # Max distance in mm (3 meters)
                        self.container[int(angle) % 360] = distance
        except Exception as e:
            print(f"Error reading LiDAR data: {e}")
            self.lidar.stop_motor()

    def shutdown(self):
        self.lidar.stop_scan()
        self.lidar.stop_motor()
        self.lidar.disconnect()
        print("LiDAR connection closed.")
