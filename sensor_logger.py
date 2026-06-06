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
LOG_INTERVAL = 1800

DRY_V = 3.27
WET_V = 0.50
MAX_LIGHT_V = 3.3

MIN_GAS_OHMS = 9000


def clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))


def safe_round(value, digits=2):
    if value is None:
        return ""
    return round(value, digits)


def check_range(value, min_value, max_value):
    if value is None:
        return None
    if value < min_value or value > max_value:
        return None
    return value


def soil_moisture_percent(voltage):
    voltage = check_range(voltage, 0, 4.5)
    if voltage is None:
        return None

    percent = (DRY_V - voltage) / (DRY_V - WET_V) * 100
    return clamp(percent)


def light_percent(voltage):
    voltage = check_range(voltage, 0, 4.5)
    if voltage is None:
        return None

    percent = (voltage / MAX_LIGHT_V) * 100
    return clamp(percent)


def safe_read(read_func):
    try:
        return read_func()
    except Exception as e:
        print("Sensor read error:", e)
        return None


def format_value(value, suffix=""):
    if value is None:
        return "MISSING"
    return f"{value:.2f}{suffix}"


def ensure_csv_exists():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([
                "timestamp",
                "soil_moisture_percent",
                "light_percent",
                "temperature_c",
                "humidity_percent",
                "pressure_hpa",
                "gas_ohms"
            ])


# I2C setup
i2c = busio.I2C(board.SCL, board.SDA)

# ADS1115 setup
ads = ADS.ADS1115(i2c)

# ADS channels
soil_chan = AnalogIn(ads, 0)
light_chan = AnalogIn(ads, 1)

# BME680 setup
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=0x77)
bme680.sea_level_pressure = 1013.25

ensure_csv_exists()

print("Warming up sensors...")
for _ in range(5):
    _ = safe_read(lambda: bme680.temperature)
    _ = safe_read(lambda: bme680.humidity)
    _ = safe_read(lambda: bme680.pressure)
    _ = safe_read(lambda: bme680.gas)
    time.sleep(5)

print("Logging sensor data...")

while True:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    soil_voltage = safe_read(lambda: soil_chan.voltage)
    soil_percent = soil_moisture_percent(soil_voltage)

    light_voltage = safe_read(lambda: light_chan.voltage)
    light_pct = light_percent(light_voltage)

    temperature = check_range(safe_read(lambda: bme680.temperature), -10, 60)
    humidity = check_range(safe_read(lambda: bme680.humidity), 0, 100)
    pressure = check_range(safe_read(lambda: bme680.pressure), 800, 1200)
    gas = check_range(safe_read(lambda: bme680.gas), MIN_GAS_OHMS, 10000000)

    print(f"\n[{timestamp}]")
    print(f"Soil: {format_value(soil_percent, '%')}")
    print(f"Light: {format_value(light_pct, '%')}")
    print(f"Temp: {format_value(temperature, ' C')}")
    print(f"Humidity: {format_value(humidity, '%')}")
    print(f"Pressure: {format_value(pressure, ' hPa')}")
    print(f"Gas: {format_value(gas, ' ohms')}")

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp,
            safe_round(soil_percent, 2),
            safe_round(light_pct, 2),
            safe_round(temperature, 2),
            safe_round(humidity, 2),
            safe_round(pressure, 2),
            safe_round(gas, 2)
        ])

    time.sleep(LOG_INTERVAL)
