import uvicorn
import sqlite3
from fastapi import FastAPI


app = FastAPI()

def init():
    conn = sqlite3.connect("sensor_data.db")
    return conn