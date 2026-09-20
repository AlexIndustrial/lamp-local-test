import os
import sys
import time
from dotenv import load_dotenv
import tinytuya

load_dotenv()

DEVICE_ID = os.getenv("TUYA_DEVICE_ID")
LOCAL_KEY = os.getenv("TUYA_LOCAL_KEY")
LOCAL_IP = os.getenv("TUYA_LOCAL_IP")
VERSION = float(os.getenv("TUYA_LOCAL_VERSION", "3.3"))

DP_POWER = 20   # switch_led
DP_MODE = 21    # work_mode
DP_BRIGHT = 22  # bright_value_v2 10-1000
DP_TEMP = 23    # temp_value_v2 0-1000

def get_bulb():
    assert DEVICE_ID and "replace" not in DEVICE_ID, "Missing TUYA_DEVICE_ID in .env"
    assert LOCAL_KEY, "Missing TUYA_LOCAL_KEY in .env — run qr_keys.py first"
    assert LOCAL_IP, "Missing TUYA_LOCAL_IP in .env — run qr_keys.py first"
    bulb = tinytuya.BulbDevice(
        dev_id=DEVICE_ID,
        address=LOCAL_IP,
        local_key=LOCAL_KEY,
        version=VERSION,
    )
    bulb.set_version(VERSION)
    return bulb

def cmd_status():
    bulb = get_bulb()
    data = bulb.status()
    print("STATUS:", data)
    dps = data.get("dps", {}) if isinstance(data, dict) else {}
    def g(dp):
        return dps.get(str(dp), dps.get(dp))
    print(f"switch_led (20): {g(20)}  mode (21): {g(21)}  bright_v2 (22): {g(22)}  temp_v2 (23): {g(23)}")

def cmd_on():
    bulb = get_bulb()
    print(">> ON")
    print(bulb.set_value(DP_POWER, True))

def cmd_off():
    bulb = get_bulb()
    print(">> OFF")
    print(bulb.set_value(DP_POWER, False))

def cmd_bright(val: int):
    val = max(10, min(1000, val))
    bulb = get_bulb()
    # power on + white mode first, then brightness
    bulb.set_value(DP_POWER, True)
    time.sleep(0.2)
    bulb.set_value(DP_MODE, "white")
    time.sleep(0.2)
    print(f">> BRIGHT {val}")
    print(bulb.set_value(DP_BRIGHT, val))

def cmd_temp(val: int):
    val = max(0, min(1000, val))
    bulb = get_bulb()
    bulb.set_value(DP_POWER, True)
    time.sleep(0.2)
    bulb.set_value(DP_MODE, "white")
    time.sleep(0.2)
    print(f">> TEMP {val}")
    print(bulb.set_value(DP_TEMP, val))

def cmd_color(h: int, s: int = 1000, v: int = 1000):
    h = max(0, min(360, h)); s = max(0, min(1000, s)); v = max(0, min(1000, v))
    hexv = f"{h:04x}{s:04x}{v:04x}"
    bulb = get_bulb()
    bulb.set_value(DP_POWER, True)
    time.sleep(0.2)
    bulb.set_value(DP_MODE, "colour")
    time.sleep(0.2)
    print(f">> COLOR h={h} s={s} v={v} ({hexv})")
    print(bulb.set_value(24, hexv))

def cmd_demo():
    bulb = get_bulb()
    print(">> DEMO: on -> dim up -> dim down -> off")
    bulb.set_value(DP_POWER, True)
    time.sleep(1)
    for b in (100, 400, 700, 1000):
        bulb.set_value(DP_BRIGHT, b)
        print(f"bright {b}")
        time.sleep(1.2)
    for b in (700, 300, 50):
        bulb.set_value(DP_BRIGHT, b)
        print(f"bright {b}")
        time.sleep(1.2)
    bulb.set_value(DP_POWER, False)
    print("done")

USAGE = "usage: lamp_local.py status|on|off|bright 10-1000|temp 0-1000|color H [S] [V]|demo"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(1)
    cmd = sys.argv[1].lower()
    if cmd == "status":
        cmd_status()
    elif cmd == "on":
        cmd_on()
    elif cmd == "off":
        cmd_off()
    elif cmd == "bright" and len(sys.argv) == 3:
        cmd_bright(int(sys.argv[2]))
    elif cmd == "temp" and len(sys.argv) == 3:
        cmd_temp(int(sys.argv[2]))
    elif cmd == "color" and len(sys.argv) >= 3:
        # color H [S] [V], e.g.: color 0 / color 120 1000 800
        h = int(sys.argv[2]); s = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
        v = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
        cmd_color(h, s, v)
    elif cmd == "demo":
        cmd_demo()
    else:
        print(USAGE)
