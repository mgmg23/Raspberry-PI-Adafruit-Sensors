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
import adafruit_bme680

from adafruit_ads1x15.analog_in import AnalogIn
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException


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
        
        # Initialize PH Sensor (Modbus)
        self.port = "/dev/ttyUSB0"
        self.baudrate = 9600
        self.slave_id = 1
        self.ph_register = 6
        self.client = ModbusSerialClient(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=2,
            retries=1
        )

        if not self.client.connect():
            raise SystemExit(f"Could not open {self.port}")

        print(
            f"Connected to {self.port} at {self.baudrate} baud, "
            f"slave ID {self.slave_id}"
        )

        # ZMQ Setup
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://localhost:{zmq_port}")

    def read_soil(self):
        voltage = self.soil_chan.voltage
        moisture = max(0, min(100, (self.dry_voltage - voltage) / (self.dry_voltage - self.wet_voltage) * 100))
        return voltage, moisture

    def read_bme(self):
        try:
            return {
                "temperature": self.bme.temperature,
                "humidity": self.bme.relative_humidity,
                "pressure": self.bme.pressure,
                "gas": self.bme.gas
            }
        except Exception as e:
            print(f"Error reading BME680: {e}")
        return None
    
    def read_ph(self):
        try:
            result = self.client.read_holding_registers(
                address=self.ph_register,
                count=1,
                device_id=self.slave_id,
            )

            if result.isError():
                print("Modbus error:", result)
                return None
            else:
                raw = result.registers[0]
                ph = raw / 100.0
                return ph

        except ModbusException as error:
            print("Communication error:", error)
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
                    print(bme_data)
                    bme_payload = {
                        "type": "temp_humidity_pressure_gas",
                        "temperature": round(bme_data["temperature"], 2),
                        "humidity": round(bme_data["humidity"], 2),
                        "pressure": round(bme_data["pressure"], 2),
                        "gas": bme_data["gas"]
                    }
                    hub.socket.send_string(json.dumps(bme_payload))
                    print(f"BME Sent | ACK: {hub.socket.recv_json().get('status')}")
            except OSError as e:
                print(f"BME680 I/O Error: {e}")

            time.sleep(1.0)
            
            # 3. Read pH Sensor
            try:
                ph_value = hub.read_ph()
                if ph_value is not None:
                    print(f"pH Value: {ph_value}")
                    ph_payload = {
                        "type": "ph_sensor",
                        "ph_value": float(ph_value)
                    }
                    hub.socket.send_string(json.dumps(ph_payload))
                    print(f"pH Sent | ACK: {hub.socket.recv_json().get('status')}")
            except Exception as e:
                print(f"pH Read Error: {e}")

            time.sleep(3.0)

    except KeyboardInterrupt:
        print("\nStopping hub node.")

if __name__ == "__main__":
    main()