# soil_sensor.py
import time
import zmq
import json
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

class MoisturePercent:
    def __init__(self, database, zmq_port):
        self.dry_voltage = 3.27
        self.wet_voltage = 0.50
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.ads = ADS.ADS1115(self.i2c)
        self.ads.gain = 1
        self.chan = AnalogIn(self.ads, 0)

    def clamp(self, x, lo=0, hi=100):
        return max(lo, min(hi, x))

    def read_moisture(self):
        voltage = self.chan.voltage
        moisture = (self.dry_voltage - voltage) / (self.dry_voltage - self.wet_voltage) * 100
        return voltage, self.clamp(moisture)

def main():
    # Setup ZMQ REQ (Request) Socket to transmit data
    with zmq.Context() as context:
        with context.socket(zmq.REQ) as socket:
            socket.connect("tcp://localhost:5555")

            sensor = MoisturePercent(database="sensor_data.db", zmq_port=5555)
            INTERVAL = 5

            print("Soil Moisture sensor node running...")

            try:
                while True:
                    voltage, moisture = sensor.read_moisture()

                    # Prepare structured dictionary payload
                    payload = {
                        "type": "soil_moisture",
                        "sensor_id": "soil_bed_1",
                        "voltage": round(voltage, 2),
                        "moisture_percent": round(moisture, 2)
                    }

                    # Send payload to db_writer service
                    socket.send_string(json.dumps(payload))
                    response = socket.recv_json()  # Wait for confirmation response

                    print(f"Sent: {voltage:.3f}V, {moisture:.1f}% | ACK: {response.get('status')}")
                    time.sleep(INTERVAL)
            except KeyboardInterrupt:
                print("\nStopping soil moisture node.")

if __name__ == "__main__":
    main()