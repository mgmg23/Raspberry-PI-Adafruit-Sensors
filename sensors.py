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
        
        # Initialize Modbus Serial Connection
        self.port = "/dev/ttyUSB0"
        self.baudrate = 9600
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

        print(f"Connected to {self.port} at {self.baudrate} baud.")

        # pH Sensor Configurations & Active Probe Discovery
        self.ph_configs = [
            {"sensor_id": "ph_bed_1", "slave_id": 3, "register": 6},
            {"sensor_id": "ph_bed_2", "slave_id": 4, "register": 6} 
        ]
        
        active_ph_probes = []
        for cfg in self.ph_configs:
            if self._test_probe(cfg["slave_id"], cfg["register"]):
                print(f"pH Sensor '{cfg['sensor_id']}' (Slave ID {cfg['slave_id']}) is connected.")
                active_ph_probes.append(cfg)
            else:
                print(f"WARNING: pH Sensor '{cfg['sensor_id']}' (Slave ID {cfg['slave_id']}) did not respond. Skipping.")
        self.ph_configs = active_ph_probes

        # NPK Sensor Configurations
        self.npk_configs = [
            {"sensor_id": "npk_bed_1", "slave_id": 1, "start_register": 30},
            {"sensor_id": "npk_bed_2", "slave_id": 2, "start_register": 30}
        ]
        
        active_npk_probes = []
        for cfg in self.npk_configs:
            if self._test_probe(cfg["slave_id"], cfg["start_register"]):
                print(f"NPK Sensor '{cfg['sensor_id']}' (Slave ID {cfg['slave_id']}) is connected.")
                active_npk_probes.append(cfg)
            else:
                print(f"WARNING: NPK Sensor '{cfg['sensor_id']}' (Slave ID {cfg['slave_id']}) did not respond. Skipping.")
        self.npk_configs = active_npk_probes


        # ZMQ Setup
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://localhost:{zmq_port}")

    def _test_probe(self, slave_id, register):
        try:
            result = self.client.read_holding_registers(
                address=register,
                count=1,
                device_id=slave_id,
            )
            return not result.isError()
        except Exception:
            return False
        
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
    
    def read_ph(self, slave_id, register):
        try:
            result = self.client.read_holding_registers(
                address=register,
                count=1,
                device_id=slave_id,
            )

            if result.isError():
                print(f"Modbus error (pH Slave {slave_id}):", result)
                return None
            else:
                raw = result.registers[0]
                return raw / 100.0

        except ModbusException as error:
            print(f"Communication error (pH Slave {slave_id}):", error)
        return None
    
    def read_npk(self, slave_id, start_register):
        try:
            # Reads 3 contiguous registers: N (start), P (start+1), K (start+2)
            result = self.client.read_holding_registers(
                address=start_register,
                count=3,
                device_id=slave_id,
            )

            if result.isError():
                print(f"Modbus error (NPK Slave {slave_id}):", result)
                return None
            else:
                return {
                    "nitrogen": float(result.registers[0]),
                    "phosphorus": float(result.registers[1]),
                    "potassium": float(result.registers[2])
                }

        except ModbusException as error:
            print(f"Communication error (NPK Slave {slave_id}):", error)
        return None


def main():
    hub = Sensors()
    print("Running...")

    try:
        while True:
            # 1. Read Soil Moisture safely on the shared bus
            print("\n")
            try:
                voltage, moisture = hub.read_soil()
                soil_payload = {
                    "type": "soil_moisture",
                    "sensor": "soil1",
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
                        "type": "temp_humidity_pressure_gas",
                        "sensor": "bme680_1",
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
            
            # 3. Read pH Sensors
            for cfg in hub.ph_configs:
                try:
                    ph_value = hub.read_ph(cfg["slave_id"], cfg["register"])
                    if ph_value is not None:
                        ph_payload = {
                            "type": "ph_sensor",
                            "sensor": cfg["sensor_id"],
                            "ph_value": round(ph_value, 2)
                        }
                        hub.socket.send_string(json.dumps(ph_payload))
                        print(f"pH ({cfg['sensor_id']}) Sent | ACK: {hub.socket.recv_json().get('status')}")
                except Exception as e:
                    print(f"pH Read Error ({cfg['sensor_id']}): {e}")
                time.sleep(0.5) # Brief pause between polling different Modbus IDs
                
            # 4. Read NPK Sensors (Modbus)
            for cfg in hub.npk_configs:
                try:
                    npk_data = hub.read_npk(cfg["slave_id"], cfg["start_register"])
                    if npk_data is not None:
                        npk_payload = {
                            "type": "soil_npk",
                            "sensor_id": cfg["sensor_id"],
                            "nitrogen": npk_data["nitrogen"],
                            "phosphorus": npk_data["phosphorus"],
                            "potassium": npk_data["potassium"]
                        }
                        hub.socket.send_string(json.dumps(npk_payload))
                        print(f"NPK ({cfg['sensor_id']}) Sent | ACK: {hub.socket.recv_json().get('status')}")
                except Exception as e:
                    print(f"NPK Read Error ({cfg['sensor_id']}): {e}")
                time.sleep(0.5)
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nStopping hub node.")


if __name__ == "__main__":
    main()
