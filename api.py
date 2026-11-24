from pathlib import Path
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import pandas as pd
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "sensor_data.db"
CSV_PATH = BASE_DIR / "sensor_data.csv"

app = FastAPI()


def init():
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def export_all_to_single_csv():
    # Update "thpg" if your table in sensor_data.db is named "tempHumidityPressureGas"
    tables = ["soilMoisture", "thpg", "phSensor", "npkSensor"]
    all_dfs = []

    try:
        with init() as conn:
            for table in tables:
                query = f"SELECT *, datetime(timestamp, 'localtime') AS datetime FROM {table}"
                df = pd.read_sql_query(query, conn)
                df["source_table"] = table
                df = df.drop(columns=["timestamp"], errors="ignore")
                all_dfs.append(df)

        combined_df = pd.concat(all_dfs, ignore_index=True)
        combined_df.to_csv(CSV_PATH, index=False)

        return FileResponse(
            path=CSV_PATH,
            filename="sensor_data.csv",
            media_type="text/csv",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)