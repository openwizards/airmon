from machine import ADC, Pin
import time

class MQ131:
    incoming_voltage = 3.3
    def __init__(self, pin: Pin):
        self.adc = ADC(pin)
        self.adc.atten(ADC.ATTN_11DB)
        self.adc.width(ADC.WIDTH_12BIT)

    def get_ozone_ppb(self):
        value = self.adc.read()
        voltage = value * self.incoming_voltage / 4095
        ozone_ppb = 200 * voltage * 0.66
        return voltage, ozone_ppb


if __name__ == "__main__":
    sensor_mq131 = MQ131(Pin(34, Pin.IN))
    while True:
        v, ppb = sensor_mq131.get_ozone_ppb()
        print(f"{v:.2f} V → {ppb:.0f} ppb O₃")
        time.sleep(1)