"""
INCLUDED SENSORS
SOIL MOISTURE (ADS1115)
TEMPERATURE, HUMIDITY, PRESSURE, GAS (BME680)
PH SENSOR (MODBUS)
"""

import time
import json
import board
import busio
import zmq
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_bme680

class Sensors:
    def __init__(self, zmq_port=5555):
        # Initialize the shared I2C bus ONCE for the whole process
        self.i2c = busio.I2C(board.SCL, board.SDA)
        
        # Initialize ADS1115 (Soil Moisture)
        self.ads = ADS.ADS1115(self.i2c)
        self.ads.gain = 1
        self.soil_chan = AnalogIn(self.ads, 0)
        self.dry_voltage = 3.27
        self.wet_voltage = 0.50

        # Initialize BME680
        self.bme = adafruit_bme680.Adafruit_BME680_I2C(self.i2c, address=0x77)
        self.bme.sea_level_pressure = 1013.25

        # ZMQ Setup
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://localhost:{zmq_port}")

    def read_soil(self):
        voltage = self.soil_chan.voltage
        moisture = max(0, min(100, (self.dry_voltage - voltage) / (self.dry_voltage - self.wet_voltage) * 100))
        return voltage, moisture

    def read_bme(self):
        if self.bme.get_sensor_data():
            return {
                "temperature": self.bme.temperature,
                "humidity": self.bme.relative_humidity,
                "pressure": self.bme.pressure,
                "gas": self.bme.gas
            }
        return None

def main():
    hub = Sensors()
    print("Agricultural Hub node running...")

    try:
        while True:
            # 1. Read Soil Moisture safely on the shared bus
            try:
                voltage, moisture = hub.read_soil()
                soil_payload = {
                    "type": "soil_moisture",
                    "sensor_id": "soil_bed_1",
                    "voltage": round(voltage, 2),
                    "moisture_percent": round(moisture, 2)
                }
                hub.socket.send_string(json.dumps(soil_payload))
                print(f"Soil Sent | ACK: {hub.socket.recv_json().get('status')}")
            except OSError as e:
                print(f"ADS1115 I/O Error: {e}")

            time.sleep(1.0) # Small pause between different sensor reads

            # 2. Read BME680 safely on the shared bus
            try:
                bme_data = hub.read_bme()
                if bme_data:
                    bme_payload = {
                        "type": "temp_humidity_pressure",
                        "sensor_id": "bme680_bed_1",
                        "temperature": round(bme_data["temperature"], 2),
                        "humidity": round(bme_data["humidity"], 2),
                        "pressure": round(bme_data["pressure"], 2),
                        "gas": round(bme_data["gas"], 2)
                    }
                    hub.socket.send_string(json.dumps(bme_payload))
                    print(f"BME Sent | ACK: {hub.socket.recv_json().get('status')}")
            except OSError as e:
                print(f"BME680 I/O Error: {e}")

            time.sleep(4.0)

    except KeyboardInterrupt:
        print("\nStopping hub node.")

if __name__ == "__main__":
    main()