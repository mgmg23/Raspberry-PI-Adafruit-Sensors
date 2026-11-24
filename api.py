import uvicorn
import sqlite3
from fastapi import FastAPI
import pandas as pd


app = FastAPI()

def init():
    conn = sqlite3.connect("sensor_data.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/home")
def home():
    return {"message": "Append the table type you want to the link above: soilMoisture, thpg, phSensor, npkSensor"}

@app.get("/")
def export_all_to_single_csv():
    tables = ["soilMoisture", "thpg", "phSensor", "npkSensor"]
    all_dfs = []
    
    try:
        with init() as conn:
            for table in tables:
                query = f"SELECT *, datetime(timestamp, 'localtime') AS datetime FROM {table}"
                df = pd.read_sql_query(query, conn)
                
                df.drop(columns=["timestamp"], inplace=True)
                all_dfs.append(df)
                
        combined_df = pd.concat(all_dfs, ignore_index=True)        
        combined_df.to_csv("all_sensors_combined.csv", index=False)
        
        return {"status": "success", "message": "Combined all tables into all_sensors_combined.csv"}
    except Exception as e:
        return {"error": str(e)}