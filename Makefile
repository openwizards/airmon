main:
	mpremote connect auto cp src/main.py :main.py
	mpremote connect auto cp src/sps30.py :sps30.py
	mpremote connect auto cp src/mq131.py :mq131.py
	mpremote connect auto cp src/gmgsv2.py :gmgsv2.py
	mpremote connect auto reset
ozon:
	mpremote connect auto cp src/mq131.py :main.py
	mpremote repl
gmgsv2:
	mpremote connect auto cp src/gmgsv2.py :main.py
	mpremote repl	
attach: main
	mpremote repl
reset:
	esptool --chip esp32 erase-flash
	esptool --chip esp32 write-flash -z 0x1000 firmware/ESP32_GENERIC-20250911-v1.26.1.bin
