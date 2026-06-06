import time
import board
import busio
import adafruit_tsl2561

i2c = busio.I2C(board.SCL, board. SDA)
sensor = adafruit_tsl2561.TSL2561(i2c)
sensor.gain=0
sensor.integration_time=1
print("Sensor Running")
while True:
	print(sensor.lux)
	time.sleep(1)

