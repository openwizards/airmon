from machine import I2C
import time

# Constants
GM_VERF = 3.3  # Default for most boards; adjust if using 5V
GM_RESOLUTION = 1023

# Commands
GM_102B = 0x01
GM_302B = 0x03
GM_502B = 0x05
GM_702B = 0x07

WARMING_UP = 0xFE
WARMING_DOWN = 0xFF

class GMGSV2:
    is_preheated = False

    def __init__(self, i2c: I2C):
        self.i2c = i2c
        self.address = 0x08
        self.preheated()

    def set_address(self, address: int):
        """Set I2C address after initialization."""
        self.address = address
        self.preheated()
        self.is_preheated = True

    def write_byte(self, cmd: int):
        """Send a single byte command to the sensor."""
        self.i2c.writeto(self.address, bytes([cmd]))
        time.sleep(0.001)

    def read_32(self) -> int:
        """Read 4 bytes from the sensor and return a 32-bit integer."""
        data = self.i2c.readfrom(self.address, 4)
        value = 0
        for i, b in enumerate(data):
            value |= b << (8 * i)
        time.sleep(0.001)
        return value

    def calc_vol(self, adc, verf=GM_VERF, resolution=GM_RESOLUTION):
        """Convert ADC value to voltage."""
        return (adc * verf) / (resolution * 1.0)

    def preheated(self):
        """Enable warming up mode."""
        self.write_byte(WARMING_UP)
        self.is_preheated = True

    def un_preheated(self):
        """Disable warming up mode."""
        self.write_byte(WARMING_DOWN)
        self.is_preheated = False

    def getNO2(self) -> int:
        if not self.is_preheated:
            self.preheated()
        self.write_byte(GM_102B)
        return self.read_32()

    def getC2H5CH(self) -> int:
        if not self.is_preheated:
            self.preheated()
        self.write_byte(GM_302B)
        return self.read_32()

    def getVOC(self) -> int:
        if not self.is_preheated:
            self.preheated()
        self.write_byte(GM_502B)
        return self.read_32()

    def getCO(self) -> int:
        if not self.is_preheated:
            self.preheated()
        self.write_byte(GM_702B)
        return self.read_32()

if __name__ == "__main__":
    from machine import Pin
    print("Starting I2C for GMGSV2...")
    i2c = I2C(0, scl=Pin(0), sda=Pin(16), freq=400000)  # Adjust pins

    gmgsv2 = GMGSV2(i2c, 0x08)

    print("NO2,C2H5CH,VOC,CO")
    while True:
        no2 = gmgsv2.getNO2()
        c2h5ch = gmgsv2.getC2H5CH()
        voc = gmgsv2.getVOC()
        co = gmgsv2.getCO()
        
        # Send as CSV string over USB serial
        print(f"{no2},{c2h5ch},{voc},{co}")
        time.sleep(0.1)
