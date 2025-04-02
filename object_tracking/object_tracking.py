#from huskylib import HuskyLensLibrary
import time

#hl = HuskyLensLibrary("SERIAL", "/dev/tty.usbserial-120")

CENTER_MIN = 140
CENTER_MAX = 180
STOP_HEIGHT = 100 

def clamp(val, min_val, max_val):
    return max(min(val, max_val), min_val)

# Tracks object by object ID
# hl - Husky lens object
def track(hl):
    try:
        obj = hl.blocks()
    except IndexError:
        obj = None

    if obj:
        if obj.height >= STOP_HEIGHT:
            # Object is close enough — stop
            # move.set_motors(0, 0)
            return f"Stopping, reached object!"
        
        x = obj.x
        offset = x - 160
        scale = 0.6
        turn = clamp(int(offset * scale), -100, 100)
        if -10 < offset < 10:
            return "Keep moving forward"
        else:
            left_speed = clamp(80 - turn, -100, 100)
            right_speed = clamp(80 + turn, -100, 100)
            return f"Tracking → x: {x}, L: {left_speed}, R: {right_speed}"
    else:
        #move.set_motors(-30, 30)  # turn left in place
        raise RuntimeError("Object Not Found")
        
        


