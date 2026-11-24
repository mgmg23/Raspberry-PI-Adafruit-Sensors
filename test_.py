import pytest
from sensors import Sensors

@pytest.fixture(scope="session")
def sensors():
    return Sensors()



def test_soilMoisture_valid(sensors):
    voltage1, voltage2, moisture1, moisture2 = sensors.read_soil()
    #Testing that moisture percentage is within valid range of 0-100%
    assert 0 <= moisture1 <= 100, f"Soil Moisture Sensor 1 out of range: {moisture1}%"
    assert 0 <= moisture2 <= 100, f"Soil Moisture Sensor 2 out of range: {moisture2}%"
    
    print(f"Test Soil Moisture Sensor 1: Moisture={moisture1:.2f}%")
    print(f"Test Soil Moisture Sensor 2: Moisture={moisture2:.2f}%")
    
def test_soilMoisture_invalid(sensors):
    voltage1, voltage2, moisture1, moisture2 = 1, 2, -2, -1

    assert 0 <= moisture1 <= 100, f"Soil Moisture Sensor 1 out of range: {moisture1}%"
    assert 0 <= moisture2 <= 100, f"Soil Moisture Sensor 2 out of range: {moisture2}%"

    print(f"Test Soil Moisture Sensor 1: Moisture={moisture1:.2f}%")
    print(f"Test Soil Moisture Sensor 2: Moisture={moisture2:.2f}%")


def test_soilVoltage_valid(sensors):
    voltage1, voltage2, moisture1, moisture2 = sensors.read_soil()

    assert voltage1 != None and voltage1 >= 0, "Soil Moisture Sensor 1 voltage read failed."
    assert voltage2 != None and voltage2 >= 0, "Soil Moisture Sensor 2 voltage read failed."

    print(f"Test Soil Moisture Sensor 1: Voltage={voltage1:.2f}V")
    print(f"Test Soil Moisture Sensor 2: Voltage={voltage2:.2f}V")
    
def test_soilVoltage_invalid(sensors):
    voltage1, voltage2, moisture1, moisture2 = None, None, 50, 50

    assert voltage1 != None and voltage1 >= 0, "Soil Moisture Sensor 1 voltage read failed."
    assert voltage2 != None and voltage2 >= 0, "Soil Moisture Sensor 2 voltage read failed."

    print(f"Test Soil Moisture Sensor 1: Voltage={voltage1}")
    print(f"Test Soil Moisture Sensor 2: Voltage={voltage2}")

def test_bme_valid(sensors):
    bme_data = sensors.read_bme()
    assert bme_data["temperature"] is not None, "Failed to read BME680 sensor data."
    assert bme_data["humidity"] is not None, "Failed to read BME680 sensor data."
    assert bme_data["pressure"] is not None, "Failed to read BME680 sensor data."
    assert bme_data["gas"] is not None, "Failed to read BME680 sensor data."

    print(f"Test BME680: Temperature={bme_data['temperature']:.2f}°C, Humidity={bme_data['humidity']:.2f}%, Pressure={bme_data['pressure']:.2f} hPa, Gas={bme_data['gas']}")
    
def test_bme_invalid(sensors):
    bme_data = {"temperature": -50.0, "humidity": 50.0, "pressure": 1013.25, "gas": 100}

    assert -40 <= bme_data["temperature"] <= 85, f"Temperature out of range: {bme_data['temperature']}°C"
    assert 0 <= bme_data["humidity"] <= 100, f"Humidity out of range: {bme_data['humidity']}%"
    assert 300 <= bme_data["pressure"] <= 1100, f"Pressure out of range: {bme_data['pressure']} hPa"
    assert bme_data["gas"] >= 0, f"Gas reading out of range: {bme_data['gas']}"