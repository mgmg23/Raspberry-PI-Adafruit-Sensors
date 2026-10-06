import time
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

PORT = "/dev/ttyUSB0"
BAUDRATE = 9600
SLAVE_ID = 1
PH_REGISTER = 6

client = ModbusSerialClient(
    port=PORT,
    baudrate=BAUDRATE,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=2,
    retries=1,
)

if not client.connect():
    raise SystemExit(f"Could not open {PORT}")

print(
    f"Connected to {PORT} at {BAUDRATE} baud, "
    f"slave ID {SLAVE_ID}"
)
print("Press Ctrl+C to stop.")

try:
    while True:
        try:
            result = client.read_holding_registers(
                address=PH_REGISTER,
                count=1,
                device_id=SLAVE_ID,
            )

            if result.isError():
                print("Modbus error:", result)
            else:
                raw = result.registers[0]
                ph = raw / 100.0

                print(f"Raw value: {raw}")
                print(f"Soil pH: {ph:.2f}")
                print("-" * 30)

        except ModbusException as error:
            print("Communication error:", error)

        time.sleep(2)

except KeyboardInterrupt:
    print("\nStopped.")

finally:
    client.close()
