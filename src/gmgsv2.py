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

CHANGE_I2C_ADDR = 0x55
WARMING_UP = 0xFE
WARMING_DOWN = 0xFF

class GMGSV2:
    def __init__(self):
        self.i2c = None
        self.address = None
        self.is_preheated = False

    def begin(self, i2c: I2C, address: int):
        """Initialize I2C bus and sensor address."""
        self.i2c = i2c
        self.address = address
        self.preheated()
        self.is_preheated = True

    def set_address(self, address: int):
        """Set I2C address after initialization."""
        self.address = address
        self.preheated()
        self.is_preheated = True

    def write_byte(self, cmd: int):
        """Send a single byte command to the sensor."""
        try:
            self.i2c.writeto(self.address, bytes([cmd]))
            time.sleep(0.001)
        except Exception as e:
            print("I2C write error:", e)

    def read_32(self) -> int:
        """Read 4 bytes from the sensor and return a 32-bit integer."""
        try:
            data = self.i2c.readfrom(self.address, 4)
            value = 0
            for i, b in enumerate(data):
                value |= b << (8 * i)
            time.sleep(0.001)
            return value
        except Exception as e:
            print("I2C read error:", e)
            return 0

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
