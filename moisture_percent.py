import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

DRY_V = 3.27
WET_V = 0.50

def clamp(x, lo=0, hi =100):
	return max(lo, min(hi,x))

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
ads.gain = 1
chan = AnalogIn(ads, 0)
print("Soil Moisure")
print(f"Calibration: DRY_V={DRY_V}V WET_V={WET_V}V\n")

while True:
	v=chan.voltage
	moisture = (DRY_V-v) / (DRY_V-WET_V) * 100
	moisture = clamp(moisture)
	print(f"Voltage: {v:3f} V Moisture: {moisture:5.1f}%")
time.sleep(1)
