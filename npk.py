import time
import serial

# Initialize Serial Port for USB-to-RS485 Adapter
# Common device names on Raspberry Pi are '/dev/ttyUSB0' or '/dev/ttyACM0'
# try:
#     ser1 = serial.Serial(
#         port="/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_BH00ZM30-if00-port0", baudrate=9600, timeout=1  # 1-second timeout for reads
#     )
# except serial.SerialException as e:
#     print(f"Error opening serial port: {e}")
#     exit(1)

try:
    ser2 = serial.Serial(
        port="/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_BH00SX15-if00-port0", baudrate=9600, timeout=1  # 1-second timeout for reads
    )
except serial.SerialException as e:
    print(f"Error opening serial port: {e}")
    exit(1)
    
    
    
# Modbus RTU request frames for NPK
nitro = bytes([0x01, 0x03, 0x00, 0x1e, 0x00, 0x01, 0xe4, 0x0c])
phos = bytes([0x01, 0x03, 0x00, 0x1f, 0x00, 0x01, 0xb5, 0xcc])
pota = bytes([0x01, 0x03, 0x00, 0x20, 0x00, 0x01, 0x85, 0xc0])


def read_sensor(port, command):
    """Sends a Modbus command and returns the combined 16-bit NPK value."""
    try:
        port.write(command)
        port.flush()
    except Exception as e:
        print(f"Error writing to serial port: {e}")
        return 0

    time.sleep(0.05)
    response = port.read(7)
    print([hex(b) for b in response])
    # Verify we received the expected 7-byte Modbus packet
    if len(response) == 7:
        # Combine High Byte (index 3) and Low Byte (index 4) into a full 16-bit integer
        value = (response[3] << 8) | response[4]
        return value
        
    return 0


try:
  print("Reading NPK Sensor via USB-RS485...")
  while True:
    # pot1_1 = read_sensor(ser1, nitro)
    # time.sleep(0.25)

    # pot1_2 = read_sensor(ser1, phos)
    # time.sleep(0.25)

    # pot1_3 = read_sensor(ser1, pota)
    # time.sleep(0.25)

    pot2_1 = read_sensor(ser2, nitro)
    time.sleep(0.25)

    pot2_2 = read_sensor(ser2, phos)
    time.sleep(0.25)
    
    pot2_3 = read_sensor(ser2, pota)
    time.sleep(0.25)

    # Print formatted values
    # print(f"Nitrogen: {pot1_1} mg/kg")
    # print(f"Phosphorous: {pot1_2} mg/kg")
    # print(f"Potassium: {pot1_3} mg/kg")
    # print()
    print(f"Nitrogen: {pot2_1} mg/kg")
    print(f"Phosphorous: {pot2_2} mg/kg")
    print(f"Potassium: {pot2_3} mg/kg")
    print("-" * 30)

    time.sleep(2)

except KeyboardInterrupt:
  print("\nStopping program...")
#   ser1.close()
  ser2.close()