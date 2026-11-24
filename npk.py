import time
import serial

class NPK:
    # Modbus RTU Commands for Nitrogen, Phosphorus, and Potassium
    nitro = bytes([0x01, 0x03, 0x00, 0x1e, 0x00, 0x01, 0xe4, 0x0c])
    phos  = bytes([0x01, 0x03, 0x00, 0x1f, 0x00, 0x01, 0xb5, 0xcc])
    pota  = bytes([0x01, 0x03, 0x00, 0x20, 0x00, 0x01, 0x85, 0xc0])
    
    def __init__(self, port, baudrate=9600, timeout=1):
        try:
            self.ser = serial.Serial(
                port=port, baudrate=baudrate, timeout=timeout
            )
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            exit(1)       
            
    def read_sensor(self, command):
        """Sends a Modbus command and returns the combined 16-bit NPK value."""
        try:
            self.ser.write(command)
            self.ser.flush()
        except Exception as e:
            print(f"Error writing to serial port: {e}")
            return 0

        time.sleep(0.05)
        response = self.ser.read(7)
        print([hex(b) for b in response])
        
        # Verify we received the expected 7-byte Modbus packet
        if len(response) == 7:
            # Combine High Byte (index 3) and Low Byte (index 4) into a full 16-bit integer
            value = (response[3] << 8) | response[4]
            return value
            
        return 0
    
    def print_npk_values(self):
        try:
            print("Reading NPK Sensor via USB-RS485...")
            while True:
                nitrogen = self.read_sensor(self.nitro)
                time.sleep(0.25)

                phosphorus = self.read_sensor(self.phos)
                time.sleep(0.25)
                
                potassium = self.read_sensor(self.pota)
                time.sleep(0.25)

                # Print formatted values
                print(f"Nitrogen: {nitrogen} mg/kg")
                print(f"Phosphorous: {phosphorus} mg/kg")
                print(f"Potassium: {potassium} mg/kg")
                print("-" * 30)

                time.sleep(2)
        except KeyboardInterrupt:
            print("\nStopping program...")
        finally:
            if self.ser.is_open:
                self.ser.close()

if __name__ == "__main__":
    # Initialize sensor reader with your serial port
    sensor = NPK("/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_BH00ZM30-if00-port0")
    sensor.print_npk_values()