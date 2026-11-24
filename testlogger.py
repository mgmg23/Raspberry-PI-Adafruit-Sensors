# db_writer.py
import sqlite3
import zmq
import json
import time

DB_FILE = "sensor_data.db"
ZMQ_PORT = 5555

def init_db():
    """Initializes database schemas for various sensor streams."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS plants (
        #         sensor_id INTEGER PRIMARY KEY,
        #         timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        #         start_date DATETIME,
        #         end_date DATETIME,
        #     );
        # """)
        # Table for soil moisture sensors
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS soilMoisture (
                id INTEGER PRIMARY KEY,
                sensor TEXT,
                voltage REAL,
                moisturePercent REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tempHumidityPressureGas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor TEXT,
                temperature REAL,
                humidity REAL,
                pressure REAL,
                gas REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS phSensor (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                ph_value REAL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS npkSensor (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                nitrogen REAL,
                phosphorus REAL,
                potassium REAL
            );
        """)


        conn.commit()

def process_payload(cursor, payload: dict):
    sensor_type = payload.get("type")

    match(sensor_type):
        case "soil_moisture":
            cursor.execute("""
                INSERT INTO soilMoisture (sensor, voltage, moisturePercent)
                VALUES (?, ?, ?);
            """, (
                payload.get("sensor"),
                payload.get("voltage"),
                round(payload.get("moisture_percent", 0), 2)
            ))
        case "temp_humidity_pressure_gas":
            cursor.execute("""
                INSERT INTO tempHumidityPressureGas (sensor, temperature, humidity, pressure, gas)
                VALUES (?, ?, ?, ?, ?);
            """, (
                payload.get("sensor"),
                payload.get("temperature"),
                payload.get("humidity"),
                payload.get("pressure"),
                payload.get("gas")
            ))
        case "ph_sensor":
            cursor.execute("""
                INSERT INTO phSensor (sensor, ph_value)
                VALUES (?, ?);
            """, (
                payload.get("sensor"),
                payload.get("ph_value")
            ))
        case "soil_npk":
            cursor.execute("""
                INSERT INTO npkSensor (sensor, nitrogen, phosphorus, potassium)
                VALUES (?, ?, ?, ?);
            """, (
                payload.get("sensor_id"),
                payload.get("nitrogen"),
                payload.get("phosphorus"),
                payload.get("potassium")
            ))
        case _:
            print("Unknown sensor type received.")
            
def main():
    init_db()
    
    # Set up ZeroMQ REP (Reply) Socket
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{ZMQ_PORT}")
    
    print(f"[{time.strftime('%H:%M:%S')}] Database writer service listening on port {ZMQ_PORT}...")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        while True:
            # 1. Wait for incoming sensor message
            message_str = socket.recv_string()
            payload = json.loads(message_str)
            print(f"[{time.strftime('%H:%M:%S')}] Received payload: {payload}")

            # 2. Write payload to SQLite
            process_payload(cursor, payload)
            conn.commit()

            print(f"[{time.strftime('%H:%M:%S')}] Logged '{payload.get('type')}'")

            socket.send_json({"status": "OK"})

    except KeyboardInterrupt:
        print("\nStopping database writer service...")
    finally:
        conn.close()

if __name__ == "__main__":
    main()