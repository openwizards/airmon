import network
import time
import machine
import ubinascii
import ujson
from umqtt.simple import MQTTClient
import sys
import errno
import _thread

# required structure and keys
REQUIRED_KEYS = [
    ("wifi", "ssid"),
    ("wifi", "password"),
    ("mqtt", "broker"),
    ("mqtt", "port"),
]

def fatal(msg):
    # print error and halt
    print("FATAL CONFIG ERROR:", msg)
    sys.exit()
    # or machine.reset() if you prefer auto-reboot

def load_config(filename="config.json"):
    try:
        with open(filename, "r") as f:
            cfg = ujson.load(f)
    except OSError as e:
        fatal("config file missing or not readable: %s" % e)
    except ValueError as e:
        # ujson parsing error
        fatal("invalid JSON in config file: %s" % e)

    # validate required keys
    for section, key in REQUIRED_KEYS:
        if section not in cfg or key not in cfg[section]:
            fatal("missing key '%s.%s' in config" % (section, key))

    return cfg

# ===== load config (will abort on error) =====
config = load_config()

WIFI_SSID = config["wifi"]["ssid"]
WIFI_PASS = config["wifi"]["password"]

MQTT_BROKER = config["mqtt"]["broker"]
MQTT_PORT   = config["mqtt"]["port"]
MQTT_USER   = config["mqtt"].get("user")
MQTT_PASS   = config["mqtt"].get("password")

DEVICE_ID = b"esp32-" + ubinascii.hexlify(machine.unique_id())
RPC_SUB_TOPIC = DEVICE_ID + b"/rpc"

class RingBuffer:
    def __init__(self, capacity):
        self.buf = [None] * capacity
        self.cap = capacity
        self.head = 0
        self.tail = 0
        self.count = 0

    def push_overwrite_oldest(self, item):
        if self.count == self.cap:
            # overwrite oldest (advance head)
            self.buf[self.tail] = item
            self.tail = (self.tail + 1) % self.cap
            self.head = self.tail
        else:
            self.buf[self.tail] = item
            self.tail = (self.tail + 1) % self.cap
            self.count += 1

    def pop(self):
        if self.count == 0:
            return None
        item = self.buf[self.head]
        self.buf[self.head] = None
        self.head = (self.head + 1) % self.cap
        self.count -= 1
        return item

    def pop_many(self, max_items):
        out = []
        for _ in range(max_items):
            item = self.pop()
            if item is None:
                break
            out.append(item)
        return out

    def __len__(self):
        return self.count


sample_q = RingBuffer(capacity=60)  # e.g. up to 60 samples buffered

# ---------- SENSOR LOGIC ----------

SENSOR_PUB_TOPIC = DEVICE_ID + b"/sensor"
PUBLISH_PERIOD_MS = 1000

_sensor_enabled = False
_sensor_thread_started = False

_mqtt_lock = _thread.allocate_lock()
_queue_lock = _thread.allocate_lock()

from sps30 import SPS30
from mq131 import MQ131
from gmgsv2 import GMGSV2
from machine import I2C, Pin

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

def read_sensor_sample():
    global sensor_sps30, sensor_gmgsv2, sensor_mq131
    print("read_sensor_sample")
    # Read SPS30
    sensor_sps30 = init_sps30()
    sensor_gmgsv2 = init_gmgsv2()
    
    out = {"ts": time.time()}
    # ----- SPS30 -----
    # Only include SPS30 fields if sensor exists and data is ready.
    if isinstance(sensor_sps30, SPS30):
        print("reading SPS30")
        try:
            if sensor_sps30.read_data_ready():
                m = sensor_sps30.read_measurement()

                sps = {"ready": True}
                # Support either dict-like or iterable-of-pairs return types
                if hasattr(m, "items"):
                    it = m.items()
                else:
                    it = m  # assume iterable of (k, v)

                for k, v in it:
                    # Ensure JSON-serializable primitives
                    if isinstance(v, float):
                        sps[k] = round(v, 3)
                    else:
                        sps[k] = v

                out["sps30"] = sps
            else:
                out["sps30"] = {"ready": False}
        except Exception as e:
            out["sps30"] = {"error": str(e)}
    # ----- MQ131 (ozone) -----
    print("reading MQ131 (ozone)")
    try:
        v, ppb = sensor_mq131.get_ozone_ppb()
        out["mq131"] = {
            "v": round(v, 3),
            "o3_ppb": int(ppb) if ppb is not None else None,
        }
    except Exception as e:
        out["mq131"] = {"error": str(e)}
    # ----- GMGSv2 -----
    if sensor_gmgsv2 is not None:
        print("reading GMGSv2")
        try:
            out["gmgsv2"] = {
                "no2": round(sensor_gmgsv2.getNO2(), 3),
                "c2h5ch": round(sensor_gmgsv2.getC2H5CH(), 3),
                "voc": round(sensor_gmgsv2.getVOC(), 3),
                "co": round(sensor_gmgsv2.getCO(), 3),
            }
        except Exception as e:
            out["gmgsv2"] = {"error": str(e)}

    return out


def _sensor_sampling_worker():
    global _sensor_enabled

    # Sampling interval can be faster than publish; e.g., 200 ms -> 5 samples/sec
    SAMPLE_PERIOD_MS = 200

    while True:
        if not _sensor_enabled:
            time.sleep_ms(100)
            continue

        sample = read_sensor_sample()

        _queue_lock.acquire()
        try:
            sample_q.push_overwrite_oldest(sample)
        finally:
            _queue_lock.release()

        time.sleep_ms(SAMPLE_PERIOD_MS)

def publish_sensor_queue():
    global client

    if client is None:
        return
    if not wlan.isconnected():
        return

    # Pull up to N samples per MQTT message
    MAX_BATCH = 10

    while True:
        _queue_lock.acquire()
        try:
            batch = sample_q.pop_many(MAX_BATCH)
        finally:
            _queue_lock.release()

        if not batch:
            break

        payload = ujson.dumps({
            "device": DEVICE_ID.decode(),
            "count": len(batch),
            "samples": batch,
        })

        _mqtt_lock.acquire()
        try:
            client.publish(SENSOR_PUB_TOPIC, payload)
        finally:
            _mqtt_lock.release()

def handle_sensor_publish():
    global _sensor_enabled, _sensor_thread_started

    if not _sensor_thread_started:
        _sensor_thread_started = True
        _thread.start_new_thread(_sensor_sampling_worker, ())

    # toggle
    _sensor_enabled = not _sensor_enabled

    if not _sensor_enabled:
        # optional: clear buffer when stopping
        _queue_lock.acquire()
        try:
            while len(sample_q) > 0:
                sample_q.pop()
        finally:
            _queue_lock.release()

    return {
        "ok": True,
        "running": _sensor_enabled,
        "topic": SENSOR_PUB_TOPIC.decode(),
        "publish_period_ms": PUBLISH_PERIOD_MS,
    }


# ---------- WIFI WITH RETRY ----------

client = None
wlan = network.WLAN(network.STA_IF)

def ensure_wifi():
    """Ensure WiFi is connected. Retry forever with backoff."""
    global wlan

    if not wlan.active():
        wlan.active(True)

    backoff = 1
    max_backoff = 60

    while not wlan.isconnected():
        print("Connecting to WiFi SSID:", WIFI_SSID)
        try:
            wlan.connect(WIFI_SSID, WIFI_PASS)
        except Exception as e:
            print("WiFi connect error:", e)

        # wait up to a short time for this attempt
        t0 = time.time()
        timeout = 10
        while not wlan.isconnected() and (time.time() - t0) < timeout:
            time.sleep(0.5)

        if wlan.isconnected():
            break

        print("WiFi not connected, retry in", backoff, "seconds")
        time.sleep(backoff)
        backoff = min(backoff * 2, max_backoff)

    print("WiFi connected, ifconfig:", wlan.ifconfig())


# ---------- MQTT WITH RETRY ----------

def connect_mqtt():
    """Create and connect MQTT client (no retry here)."""
    global client
    print("Connecting to MQTT as:", DEVICE_ID)
    c = MQTTClient(
        client_id=DEVICE_ID,
        server=MQTT_BROKER,
        port=MQTT_PORT,
        user=MQTT_USER,
        password=MQTT_PASS,
        keepalive=60,
    )
    c.set_callback(on_mqtt_message)
    c.connect()
    c.subscribe(RPC_SUB_TOPIC)
    print("Connected to MQTT broker:", MQTT_BROKER)
    print("Subscribed to RPC topic:", RPC_SUB_TOPIC)
    client = c


def ensure_mqtt():
    """Ensure MQTT is connected. Retry forever with backoff."""
    global client
    if client is not None:
        return

    backoff = 1
    max_backoff = 60

    while client is None:
        try:
            # make sure WiFi is up before trying MQTT
            if not wlan.isconnected():
                ensure_wifi()
            connect_mqtt()
        except Exception as e:
            print("MQTT error during check_msg:", e, type(e), repr(e))
            try:
                client.disconnect()
            except Exception as e2:
                print("Error on client.disconnect():", e2)
            client = None
            print("Retry MQTT in", backoff, "seconds")
            time.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)


# ---------- RPC HANDLERS ----------

def handle_wifi_get_status():
    info = {"connected": wlan.isconnected()}
    if wlan.isconnected():
        ip, netmask, gateway, dns = wlan.ifconfig()
        info.update({
            "ip": ip,
            "netmask": netmask,
            "gateway": gateway,
            "dns": dns,
        })
    return info

def on_mqtt_message(topic, msg):
    global client
    print("MQTT message on", topic, ":", msg)

    if topic != RPC_SUB_TOPIC:
        return

    try:
        req = ujson.loads(msg)
    except ValueError as e:
        print("Invalid RPC JSON:", e)
        return

    req_id = req.get("id")
    src = req.get("src") or ""
    method = req.get("method")

    resp = {
        "id": req_id,
        "src": DEVICE_ID.decode(),
    }

    if method == "Wifi.GetStatus":
        resp["result"] = handle_wifi_get_status()
    elif method == "Sensor.Publish":
        resp["result"] = handle_sensor_publish()
    else:
        resp["error"] = {
            "code": -32601,
            "message": "Method not found: {}".format(method),
        }

    if src:
        resp_topic = src.encode() + b"/rpc"
    else:
        resp_topic = RPC_SUB_TOPIC

    try:
        payload = ujson.dumps(resp)
        print("Publishing RPC response to", resp_topic, ":", payload)
        client.publish(resp_topic, payload)
    except Exception as e:
        print("Failed to publish RPC response:", e)


# ---------- MAIN LOOP ----------

def main():
    global client

    ensure_wifi()
    ensure_mqtt()

    next_pub = time.ticks_add(time.ticks_ms(), PUBLISH_PERIOD_MS)

    while True:
        # If WiFi dropped, force reconnects
        if not wlan.isconnected():
            print("WiFi lost, reconnecting...")
            client = None  # drop MQTT client; it will be recreated
            ensure_wifi()
            ensure_mqtt()

        try:
            _mqtt_lock.acquire()
            try:
                client.check_msg()
            finally:
                _mqtt_lock.release()

        except OSError as e:
            code = e.args[0] if e.args else None
            EAGAIN = getattr(errno, "EAGAIN", -99999)
            EWOULDBLOCK = getattr(errno, "EWOULDBLOCK", -99998)

            if code in (-1, EAGAIN, EWOULDBLOCK):
                pass
            else:
                print("MQTT socket error:", e)
                try:
                    client.disconnect()
                except:
                    pass
                client = None
                ensure_mqtt()

        except Exception as e:
            print("MQTT error:", e)
            try:
                client.disconnect()
            except:
                pass
            client = None
            ensure_mqtt()


        # 1-second publish tick (drain queue)
        now = time.ticks_ms()
        if time.ticks_diff(now, next_pub) >= 0:
            next_pub = time.ticks_add(next_pub, PUBLISH_PERIOD_MS)
            if _sensor_enabled:
                publish_sensor_queue()

        time.sleep_ms(10)

if __name__ == "__main__":
    main()
