from machine import ADC, Pin
import time

adc = ADC(Pin(34, Pin.IN))  # z.B. ESP32
adc.atten(ADC.ATTN_11DB)  # erlaubt Messung bis ~3.6 V
adc.width(ADC.WIDTH_12BIT)  # 0–4095

def get_ozone_ppb():
    value = adc.read()
    voltage = value * 3.3 / 4095
    #voltage = value * (5/1023)
    ozone_ppb = 200 * voltage * 0.66     # 1 V = 200 ppb
    return voltage, ozone_ppb

while True:
    v, ppb = get_ozone_ppb()
    print(f"{v:.2f} V → {ppb:.0f} ppb O₃")
    time.sleep(1)