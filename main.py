from machine import Pin
import time

led = Pin(2, Pin.OUT)  # On-board LED on many ESP32 boards

while True:
    led.value(not led.value())
    time.sleep(4)
