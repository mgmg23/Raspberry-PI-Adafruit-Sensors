import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c, address=0x48)
channel = AnalogIn(ads, ADS.P0)

while True:
    print("Raw:", channel.value, "Voltage:", channel.voltage)
    time.sleep(1)
