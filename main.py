# from machine import Pin
#
# pin_0 = Pin(0, Pin.OUT)
# pin_2 = Pin(2, Pin.OUT)
# i = 1
# timeout = 0.1

# while True:
#    pin_0.on()
#    pin_2.on()
#    time.sleep(timeout)
#    pin_0.off()
#    pin_2.off()
#    time.sleep(timeout)
#    i = i + 1
#    print(i)


from machine import UART

baudrate = 115200
uart = UART(1, baudrate)
uart.init(baudrate, bits=8, parity=None, stop=1, tx=2, rx=0)

start = [0x00, 0x00, 0x02, 0x01, 0x03, 0xF9]
start = bytes([0x7E, 0x00, 0x00, 0x02, 0x01, 0x03, 0xF9, 0x7E])
stop = [0x00, 0x01, 0x00, 0x00, 0xFE]
read = [0x00, 0x03, 0x00, 0xFC]
read = bytes([0x7E, 0x00, 0x03, 0x00, 0xFC, 0x7E])
