from sps30 import SPS30
from mq131 import MQ131
from machine import I2C, Pin
import time

SPS30_FREQ = 100_000
SPS30_I2C_ADDRESS = 0x69
SPS30_SDA_PIN = Pin(0)
SPS30_SCL_PIN = Pin(16)

MQ131_PIN = Pin(34, Pin.IN)

i2c = I2C(1, freq=SPS30_FREQ, sda=SPS30_SDA_PIN, scl=SPS30_SCL_PIN)

# Initialize SPS30
def init_sps30():
    try:
        sensor_sps30 = SPS30(i2c=i2c, addr=SPS30_I2C_ADDRESS)
        sensor_sps30.start_measurement()
    except OSError:
        print("couldn't reach SPS30")
        return None
    return sensor_sps30


# Initialize MQ131
sensor_mq131 = MQ131(MQ131_PIN)

try:
    while True:
        # Read SPS30
        sensor_sps30 = init_sps30()
        if isinstance(sensor_sps30, SPS30) and sensor_sps30.read_data_ready():
            data = sensor_sps30.read_measurement()
            for k, v in data:
                print("output")
                if isinstance(v, float):
                    print(f"{k}: {v:.2f}")
                else:
                    print(f"{k}: {v}")
            print()
        # Read MQ131
        v, ppb = sensor_mq131.get_ozone_ppb()
        print(f"{v:.2f} V → {ppb:.0f} ppb O₃")
        # Read GMGSv2
        time.sleep(2)
except KeyboardInterrupt:
    print("Stopping...")
    sensor_sps30.stop_measurement()
