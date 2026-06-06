import time
import board
import busio
import adafruit_bme680

# I2C setup
i2c = busio.I2C(board.SCL, board.SDA)

# Try address 0x76 first
sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=0x77)

# Sea level pressure (adjust if needed)
sensor.sea_level_pressure = 1013.25

while True:
    print(f"Temp: {sensor.temperature:.2f} C")
    print(f"Humidity: {sensor.humidity:.2f} %")
    print(f"Pressure: {sensor.pressure:.2f} hPa")
    print(f"Gas: {sensor.gas} ohms")
    print("-" * 30)
    time.sleep(2)
