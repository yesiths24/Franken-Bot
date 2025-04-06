from pca9685 import PCA9685
# from picocat import Servos
from machine import I2C, Pin
from servo import Servos

sda = Pin(14)
scl = Pin(15)
id = 1
i2c = I2C(1, sda=sda, scl=scl)

pca = PCA9685(i2c=i2c)
# pca.i2c = i2c
servo = Servos(i2c=i2c)
servo.position(index=0, degrees=360)