main:
	mpremote connect auto cp src/main.py :main.py
	mpremote connect auto cp src/sps30.py :sps30.py
	mpremote connect auto reset
attach: main
	mpremote repl
reset:
	esptool --chip esp32 erase-flash
	esptool --chip esp32 write-flash -z 0x1000 firmware/ESP32_GENERIC-20250911-v1.26.1.bin
