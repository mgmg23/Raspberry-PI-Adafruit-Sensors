import sqlite3
import time
import board
import busio
import zmq
import adafruit_bme680

class BME680Sensor:
    def __init__(self, db_name="plant_monitor.db", zmq_port=5555, i2c_address=0x77):
        self.db_name = db_name
        self.zmq_port = zmq_port
        self.i2c_address = i2c_address
        self.i2c = None
        self.sensor = None
        self._init_sensor()

    def _init_sensor(self):
        """Initializes the I2C bus and the BME680 sensor module."""
        try:
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self.sensor = adafruit_bme680.Adafruit_BME680_I2C(self.i2c, address=self.i2c_address)
            self.sensor.sea_level_pressure = 1013.25
            time.sleep(1)  # Allow sensor to settle
        except Exception as e:
            print(f"Failed to initialize BME680 sensor: {e}")

    def read_and_publish(self):
        if not self.sensor:
            print("Sensor not initialized. Retrying...")
            self._init_sensor()
            if not self.sensor:
                return None

        with zmq.Context() as context:
            with context.socket(zmq.REQ) as socket:
                socket.connect(f"tcp://localhost:{self.zmq_port}")
                
                try:
                    payload = {
                        "sensor": "bme680",
                        "temperature": self.sensor.temperature,
                        "humidity": self.sensor.relative_humidity,
                        "pressure": self.sensor.pressure,
                        "gas": self.sensor.gas,
                        "timestamp": time.time()
                    }

                    # Broadcast over ZMQ
                    socket.send_json(payload)
                    
                    # Wait for reply if using REQ/REP pattern (optional, but good practice for zmq.REQ)
                    # reply = socket.recv_json() 
                    
                    return payload
                except Exception as e:
                    print(f"Error reading BME680 or publishing: {e}")
        
        return None

# --- Main execution loop ---
if __name__ == "__main__":
    node = BME680Sensor()
    
    while True:
        data = node.read_and_publish()
        if data:
            print(f"[Logged & Published] Temp: {data['temperature']:.2f}°C | Hum: {data['humidity']:.2f}% | Press: {data['pressure']:.2f}hPa | Gas: {data['gas']}Ω")
        time.sleep(5.0)