import object_tracking

from huskylib import HuskyLensLibrary
import time

# 1 - object tracking mode
# 2 - object search mode
# 3 - autonomous exit mode


def menu():

    user_mode = int(input("Please enter the mode of operation")) 
    hl = HuskyLensLibrary("SERIAL", "/dev/tty.usbserial-120")   

    if user_mode == 1:
        while True:
            try:
                print(object_tracking.track(hl))
            except RuntimeError:
                print("Searching rn")
            time.sleep(0.1)

    elif user_mode == 2:
        while True:
            try:
                print(object_tracking.track(hl))
            except RuntimeError as e:
                print("navigating")
            time.sleep(0.1)

    elif user_mode == 3:
        print("Navigating")

menu()
