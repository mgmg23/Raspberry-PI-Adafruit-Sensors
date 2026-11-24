import csv
import os
import time
from datetime import datetime

import board
import busio

import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

import adafruit_bme680


CSV_FILE = "/home/excalibur/pi_projects/sensor_log.csv"
LOG_INTERVAL = 60  # seconds

DRY_V = 3.27
WET_V = 0.50


def clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))


def soil_moisture_percent(voltage):
    percent = (DRY_V - voltage) / (DRY_V - WET_V) * 100
    return clamp(percent)


def ensure_csv_exists():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([
                "timestamp",
                "soil_voltage",
                "soil_moisture_percent",
                "light_voltage",
                "temperature_c",
                "humidity_percent",
                "pressure_hpa",
                "gas_ohms"
            ])


# I2C
i2c = busio.I2C(board.SCL, board.SDA)

# ADS1115 (YOUR VERSION — unchanged)
ads = ADS.ADS1115(i2c)
soil_chan = AnalogIn(ads, 0)
light_chan = AnalogIn(ads, 1)

# BME680
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=0x77)
bme680.sea_level_pressure = 1013.25

ensure_csv_exists()

print("Logging sensor data...")

while True:
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        soil_voltage = soil_chan.voltage
        soil_percent = soil_moisture_percent(soil_voltage)

        light_voltage = light_chan.voltage

        temperature = bme680.temperature
        humidity = bme680.humidity
        pressure = bme680.pressure
        gas = bme680.gas

        print(f"\n[{timestamp}]")
        print(f"Soil: {soil_percent:.1f}% ({soil_voltage:.3f}V)")
        print(f"Light: {light_voltage:.3f}V")
        print(f"Temp: {temperature:.2f}C")
        print(f"Humidity: {humidity:.2f}%")
        print(f"Pressure: {pressure:.2f} hPa")
        print(f"Gas: {gas:.2f} ohms")

        with open(CSV_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                round(soil_voltage, 3),
                round(soil_percent, 1),
                round(light_voltage, 3),
                round(temperature, 2),
                round(humidity, 2),
                round(pressure, 2),
                round(gas, 2)
            ])

        time.sleep(LOG_INTERVAL)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
