from machine import Pin, I2C
import ssd1306
import time

# ====== CONSTANTS (change these) ======
TEXT = "Frohe Weihnachten mein lieber Papa"
DIRECTION = -1      # 1 = left->right, -1 = right->left
SPEED_MS = 20      # smaller = faster
Y = 28             # vertical position
# ======================================

i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)

CHAR_W = 8
text_w = len(TEXT) * CHAR_W
WIDTH = 128

def start_x(direction: int) -> int:
    # Start fully off-screen depending on direction
    return -text_w if direction == 1 else WIDTH

def wrap_x(x: int, direction: int) -> int:
    # Reset when fully off the opposite edge
    if direction == 1 and x > WIDTH:
        return -text_w
    if direction == -1 and x < -text_w:
        return WIDTH
    return x

x = start_x(DIRECTION)

while True:
    oled.fill(0)
    oled.text(TEXT, x, Y)
    oled.show()

    x += DIRECTION
    x = wrap_x(x, DIRECTION)

    time.sleep_ms(SPEED_MS)
