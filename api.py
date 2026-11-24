import uvicorn
import sqlite3
from fastapi import FastAPI


app = FastAPI()

def init():
    conn = sqlite3.connect("sensor_data.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def home():
    return [
        {"Append the table type you want to the link above."},
        {"Table types": "soilMoisture, tempHumidityPressureGas, phSensor, npkSensor"}
    ]
    
@app.get("/{table}")
def get(table: str):
    if table.lower() not in ["soilmoisture", "temphumiditypressuregas", "phsensor", "npksensor"]:
        return {"Invalid table."}
    
    cursor = init().cursor()
    try:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        return {"error": str(e)}
    finally:
        cursor.close()