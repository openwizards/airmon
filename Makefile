main:
	mpremote connect auto cp main.py :main.py
	mpremote connect auto reset
reset:
	esptool.py --chip esp32 erase_flash
	esptool.py --chip esp32 write_flash -z 0x1000 firmware/ESP32_GENERIC-20250911-v1.26.1.bin
