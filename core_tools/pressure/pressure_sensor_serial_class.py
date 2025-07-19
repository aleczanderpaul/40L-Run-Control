import serial
import time

'''Class to handle serial communication with a pressure sensor (specifically the MKS PDR 2000)'''

class PressureSensorSerial:
    def __init__(self, port_name):
        # Initialize the serial connection with specified parameters:
        # port_name: the serial port to connect to (e.g., 'COM4' on Windows)
        # baudrate: 9600 bits per second (communication speed)
        # bytesize: 8 bits per byte
        # parity: no parity bit
        # stopbits: 1 stop bit
        # timeout: 1 second timeout for read operations
        self.ser = serial.Serial(
            port=port_name,
            baudrate=9600,      
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )  # These settings are specific to the MKS PDR 2000 pressure sensor

        time.sleep(1)  # Wait 1 second for the serial port and device to initialize

    def read_pressure(self):
        # Send the 'p' command to the sensor to request pressure readings
        # ASCII 'p' corresponds to byte 112, sent as b'p'
        self.ser.write(b'p')
        time.sleep(0.1)  # Short delay to allow sensor to process and respond
        
        # Read one line from the serial port, decode from bytes to string
        response = self.ser.readline().decode('utf-8').strip()
        
        # Split the response into two values (assuming the sensor returns
        # two pressure gauge readings separated by spaces)
        gauge1, gauge2 = response.split()
        
        # Return the two pressure readings as strings
        return gauge1, gauge2

    def read_units(self):
        # Send the 'u' command to request the units of pressure (e.g., "Torr", "mbar", "Pascal")
        self.ser.write(b'u')
        time.sleep(0.1)  # Wait for response
        
        # Read one line from the serial port, decode from bytes to string
        units = self.ser.readline().decode('utf-8').strip()
        
        # Return the units string
        return units

    def read_full_scale(self):
        # Send the 'f' command to get the full scale range of the sensor
        self.ser.write(b'f')
        time.sleep(0.1)  # Wait for sensor response
        
        # Read one line from the serial port, decode from bytes to string
        response = self.ser.readline().decode('utf-8').strip()
        
        # Split the response into low and high range values
        low_range, high_range = response.split()
        
        # Return the full scale range as strings
        return low_range, high_range

    def close_port(self):
        # Close the serial port connection cleanly
        self.ser.close()

# Example usage
if __name__ == "__main__":
    # Create an instance of the PressureSensorSerial class
    pressureSensor = PressureSensorSerial('COM4')
    
    # Print pressure readings from both gauges
    print(pressureSensor.read_pressure())
    
    # Print the units of the pressure readings
    print(pressureSensor.read_units())
    
    # Print the full scale low and high range values
    print(pressureSensor.read_full_scale())
    
    # Close the serial port when done
    pressureSensor.close_port()