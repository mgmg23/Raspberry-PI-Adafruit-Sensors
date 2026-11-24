import time
import serial

def crc16(data: bytes) -> bytes:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc.to_bytes(2, "little")

ser = serial.Serial("/dev/ttyUSB1", 9600, timeout=0.5)

for reg in range(0x00, 0x30):
    cmd = bytes([0x01, 0x03, reg >> 8, reg & 0xFF, 0x00, 0x01])
    cmd += crc16(cmd)
    ser.reset_input_buffer()
    ser.write(cmd)
    ser.flush()
    time.sleep(0.1)
    resp = ser.read(7)
    if len(resp) == 7 and resp[1] == 0x03:
        print(f"reg 0x{reg:02X}: {(resp[3] << 8) | resp[4]}")
    elif len(resp) == 5 and resp[1] == 0x83:
        pass  # illegal address, register doesn't exist
    else:
        print(f"reg 0x{reg:02X}: odd response {resp.hex(' ')}")
    time.sleep(0.1)