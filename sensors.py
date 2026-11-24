import time
import json
import board
import busio
import serial
import zmq
import adafruit_ads1x15.ads1115 as ADS
import adafruit_bme680

from adafruit_ads1x15.analog_in import AnalogIn
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException


class Sensors:
    # Modbus RTU Commands for Nitrogen, Phosphorus, and Potassium
    nitro = bytes([0x01, 0x03, 0x00, 0x1e, 0x00, 0x01, 0xe4, 0x0c])
    phos  = bytes([0x01, 0x03, 0x00, 0x1f, 0x00, 0x01, 0xb5, 0xcc])
    pota  = bytes([0x01, 0x03, 0x00, 0x20, 0x00, 0x01, 0x85, 0xc0])

    def __init__(self, zmq_port=5555):
        # Initialize the shared I2C bus ONCE for the whole process
        self.i2c = busio.I2C(board.SCL, board.SDA)

        # Initialize ADS1115 (Soil Moisture)
        self.ads = ADS.ADS1115(self.i2c)
        self.ads.gain = 1
        self.soil_chan1 = AnalogIn(self.ads, 0)
        self.soil_chan2 = AnalogIn(self.ads, 1)
        self.dry_voltage = 3.27
        self.wet_voltage = 0.50

        # Initialize BME680
        self.bme = adafruit_bme680.Adafruit_BME680_I2C(self.i2c, address=0x77)
        self.bme.sea_level_pressure = 1013.25

        # pH Sensor (pymodbus on its own USB-RS485 adapter)
        self.ph_port = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_BH00L2OR-if00-port0"
        self.ph_baudrate = 9600
        self.ph_slave_id = 1
        self.ph_register = 0x06
        self.ph_sensor_id = "ph_bed_1"

        self.client = ModbusSerialClient(
            port=self.ph_port,
            baudrate=self.ph_baudrate,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=2,
            retries=1
        )

        if not self.client.connect():
            raise SystemExit(f"Could not open {self.ph_port}")

        print(f"pH Sensor '{self.ph_sensor_id}' connected to {self.ph_port} at {self.ph_baudrate} baud, slave ID {self.ph_slave_id}.")

        # NPK Sensor (raw pyserial on its own USB-RS485 adapter)
        self.npk_port = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_BH00ZM30-if00-port0"
        self.npk_baudrate = 9600
        self.npk_sensor_id = "npk_bed_1"

        try:
            self.ser = serial.Serial(
                port=self.npk_port, baudrate=self.npk_baudrate, timeout=1
            )
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            raise SystemExit(1)

        print(f"NPK Sensor '{self.npk_sensor_id}' connected to {self.npk_port} at {self.npk_baudrate} baud.")

        # ZMQ Setup
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://localhost:{zmq_port}")

    def read_soil(self):
        voltage1 = self.soil_chan1.voltage
        voltage2 = self.soil_chan2.voltage
        moisture1 = max(0, min(100, (self.dry_voltage - voltage1) / (self.dry_voltage - self.wet_voltage) * 100))
        moisture2 = max(0, min(100, (self.dry_voltage - voltage2) / (self.dry_voltage - self.wet_voltage) * 100))
        return voltage1, voltage2, moisture1, moisture2

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
                device_id=self.ph_slave_id,
            )

            if result.isError():
                print("Modbus error (pH):", result)
                return None
            else:
                # (raw reading, true buffer value)
                P1 = (3.74, 4.00)
                P2 = (520, 7.90)   # fill in your pH 7 reading

                SLOPE = (P2[1] - P1[1]) / (P2[0] - P1[0])
                OFFSET = P1[1] - SLOPE * P1[0]


                raw = result.registers[0]
                return SLOPE * raw + OFFSET

        except ModbusException as error:
            print("Communication error (pH):", error)
        return None

    def read_npk_sensor(self, command):
        """Sends a Modbus command and returns the combined 16-bit NPK value."""
        try:
            self.ser.write(command)
            self.ser.flush()
        except Exception as e:
            print(f"Error writing to serial port: {e}")
            return 0

        time.sleep(0.05)
        response = self.ser.read(7)
        print([hex(b) for b in response])

        # Verify we received the expected 7-byte Modbus packet
        if len(response) == 7:
            # Combine High Byte (index 3) and Low Byte (index 4) into a full 16-bit integer
            value = (response[3] << 8) | response[4]
            return value

        return 0

    def read_npk(self):
        nitrogen = self.read_npk_sensor(self.nitro)
        time.sleep(0.25)

        phosphorus = self.read_npk_sensor(self.phos)
        time.sleep(0.25)

        potassium = self.read_npk_sensor(self.pota)
        time.sleep(0.25)

        return {
            "nitrogen": float(nitrogen),
            "phosphorus": float(phosphorus),
            "potassium": float(potassium)
        }

    def close(self):
        if self.client:
            self.client.close()
        if self.ser.is_open:
            self.ser.close()


def main():
    hub = Sensors()
    print("Running...")

    try:
        while True:
            # 1. Read Soil Moisture safely on the shared bus
            print("\n")
            try:
                voltage1, voltage2, moisture1, moisture2 = None, None, None, None #hub.read_soil()
                if voltage1 and moisture1:
                    soil_payload1 = {
                        "type": "soil_moisture",
                        "sensor": "soil1",
                        "voltage": round(voltage1, 2),
                        "moisture_percent": round(moisture1, 2)
                    }
                    hub.socket.send_string(json.dumps(soil_payload1))
                    print(f"Soil Sent | ACK: {hub.socket.recv_json().get('status')}")
                    time.sleep(0.2)
                else:
                    print("Soil Moisture Sensor 1 read failed.")
                if voltage2 and moisture2:
                    soil_payload2 = {
                        "type": "soil_moisture",
                        "sensor": "soil2",
                        "voltage": round(voltage2, 2),
                        "moisture_percent": round(moisture2, 2)
                    }
                    hub.socket.send_string(json.dumps(soil_payload2))
                    print(f"Soil Sent | ACK: {hub.socket.recv_json().get('status')}")
                else:
                    print("Soil Moisture Sensor 2 read failed.")
            except OSError as e:
                print(f"ADS1115 I/O Error: {e}")

            time.sleep(1.0) # Small pause between different sensor reads

            # 2. Read BME680 safely on the shared bus
            try:
                bme_data = None #hub.read_bme()
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

            # 3. Read pH Sensor
            try:
                ph_value = hub.read_ph()
                if ph_value is not None:
                    ph_payload = {
                        "type": "ph_sensor",
                        "sensor": hub.ph_sensor_id,
                        "ph_value": round(ph_value, 2)
                    }
                    hub.socket.send_string(json.dumps(ph_payload))
                    print(f"pH ({hub.ph_sensor_id}) Sent | ACK: {hub.socket.recv_json().get('status')}")
            except Exception as e:
                print(f"pH Read Error ({hub.ph_sensor_id}): {e}")
            time.sleep(0.5)

            # 4. Read NPK Sensor (Modbus)
            try:
                # npk_data = hub.read_npk()
                if npk_data is not None:
                    npk_payload = {
                        "type": "soil_npk",
                        "sensor_id": hub.npk_sensor_id,
                        "nitrogen": npk_data["nitrogen"],
                        "phosphorus": npk_data["phosphorus"],
                        "potassium": npk_data["potassium"]
                    }
                    hub.socket.send_string(json.dumps(npk_payload))
                    print(f"NPK ({hub.npk_sensor_id}) Sent | ACK: {hub.socket.recv_json().get('status')}")
            except Exception as e:
                print(f"NPK Read Error ({hub.npk_sensor_id}): {e}")
            time.sleep(0.5)

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nStopping hub node.")
    finally:
        hub.close()


if __name__ == "__main__":
    main()