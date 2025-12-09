from sps30 import SPS30
from mq131 import MQ131
from gmgsv2 import GMGSV2
from machine import I2C, Pin
import time

SPS30_FREQ = 100_000
SPS30_SDA_PIN = Pin(0, Pin.IN)
SPS30_SCL_PIN = Pin(16, Pin.IN)

MQ131_PIN = Pin(34, Pin.IN)

GMGSV2_SDA_PIN = Pin(32, Pin.IN)
GMGSV2_SCL_PIN = Pin(14, Pin.IN)
GMGSV2_FREQ = 400_000

# Initialize SPS30
def init_sps30():
    i2c = I2C(1, freq=SPS30_FREQ, sda=SPS30_SDA_PIN, scl=SPS30_SCL_PIN)
    try:
        sensor_sps30 = SPS30(i2c=i2c)
        sensor_sps30.start_measurement()
    except OSError:
        print("couldn't reach SPS30")
        return None
    return sensor_sps30

def init_gmgsv2():
    i2c = I2C(0, freq=GMGSV2_FREQ, sda=GMGSV2_SDA_PIN, scl=GMGSV2_SCL_PIN)
    try:
        sensor_gmgsv2 = GMGSV2(i2c=i2c)
    except OSError:
        print("couldn't reach GMGSV2")
        return None
    return sensor_gmgsv2

# Initialize MQ131
sensor_mq131 = MQ131(MQ131_PIN)
sensor_sps30 = None
sensor_gmgsv2 = None

try:
    while True:
        # Read SPS30
        sensor_sps30 = init_sps30()
        sensor_gmgsv2 = init_gmgsv2()
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
        if sensor_gmgsv2 is not None:
            no2 = sensor_gmgsv2.getNO2()
            c2h5ch = sensor_gmgsv2.getC2H5CH()
            voc = sensor_gmgsv2.getVOC()
            co = sensor_gmgsv2.getCO()
            
            # Send as CSV string over USB serial
            print(f"{no2},{c2h5ch},{voc},{co}")
        time.sleep(2)
except KeyboardInterrupt:
    print("Stopping...")
    sensor_sps30.stop_measurement()
