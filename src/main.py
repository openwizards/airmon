from sps30 import SPS30
from machine import I2C, Pin
import time

FREQ = 100_000
I2C_ADDRESS = 0x69

i2c = I2C(1, freq=FREQ, sda=Pin(0), scl=Pin(16))
sensor = SPS30(i2c=i2c, addr=I2C_ADDRESS)

print("Starting SPS30...")
sensor.start_measurement()

try:
    while True:
        if sensor.read_data_ready():
            data = sensor.read_measurement()
            for k, v in data:
                print("output")
                if isinstance(v, float):
                    print(f"{k}: {v:.2f}")
                else:
                    print(f"{k}: {v}")
            print()
        time.sleep(2)
except KeyboardInterrupt:
    print("Stopping...")
    sensor.stop_measurement()
