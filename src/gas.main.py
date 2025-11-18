from machine import I2C, Pin
import time
from gas import GAS_GMXXX as GasSensor

print("Starting I2C...")

i2c = I2C(0, scl=Pin(0), sda=Pin(16), freq=400000)  # Adjust pins

gas = GasSensor()
gas.begin(i2c, 0x08)


print("NO2,C2H5CH,VOC,CO")
while True:
    no2 = gas.getNO2()
    c2h5ch = gas.getC2H5CH()
    voc = gas.getVOC()
    co = gas.getCO()
    
    # Send as CSV string over USB serial
    print(f"{no2},{c2h5ch},{voc},{co}")
    time.sleep(0.1)
