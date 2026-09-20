import os
from dotenv import load_dotenv
import tinytuya

load_dotenv()

REGION = os.getenv("TUYA_API_REGION", "eu")
API_KEY = os.getenv("TUYA_API_KEY")
API_SECRET = os.getenv("TUYA_API_SECRET")
DEVICE_ID = os.getenv("TUYA_DEVICE_ID")

assert API_KEY and "replace" not in API_KEY, "Fill in TUYA_API_KEY in .env"
assert API_SECRET and "replace" not in API_SECRET, "Fill in TUYA_API_SECRET in .env"
assert DEVICE_ID and "replace" not in DEVICE_ID, "Fill in TUYA_DEVICE_ID in .env"

cloud = tinytuya.Cloud(
    apiRegion=REGION,
    apiKey=API_KEY,
    apiSecret=API_SECRET,
    apiDeviceID=DEVICE_ID,
)

print(">>> Fetching device list (includes local_key)...")
devices = cloud.getdevices()
if isinstance(devices, dict):
    print(devices)
    err = str(devices.get("Err", "")) + str(devices.get("Payload", ""))
    if "28841002" in err or "subscription" in err.lower():
        print(
            "\n[!] IoT Core trial expired (28841002).\n"
            "Option A: iot.tuya.com -> Cloud -> My Services -> IoT Core -> Extend trial / Subscribe.\n"
            "Option B (no cloud): python -m tinytuya wizard — log in with Smart Life / Tuya Smart app credentials,\n"
            "it will fetch the local key and create tinytuya.json. Then copy key/ip into .env.\n"
        )
    raise SystemExit(1)

print(f"Cloud knows {len(devices)} device(s)")
mine = None
for d in devices:
    if d.get("id") == DEVICE_ID:
        mine = d
        break

if not mine:
    print(f"Device {DEVICE_ID} not found in the cloud. Check the App Account link.")
    for d in devices:
        print(f" - {d.get('name')} {d.get('id')}")
    raise SystemExit(1)

local_key = mine.get("key") or mine.get("local_key")
print(f"\nFound: {mine.get('name')}")
print(f"Local Key: ...{local_key[-4:] if local_key else 'EMPTY'}")
print(f"Full record: {mine}")

print("\n>>> Cloud status and functions:")
try:
    print("status:", cloud.getstatus(DEVICE_ID))
except Exception as e:
    print(f"getstatus fail: {e}")
try:
    print("functions:", cloud.getfunctions(DEVICE_ID))
except Exception as e:
    print(f"getfunctions fail: {e}")

found = tinytuya.deviceScan(verbose=False, timeout=20)
for ip, dev in found.items():
    if dev.get("gwId") == DEVICE_ID or dev.get("id") == DEVICE_ID:
        print(f"\nFOUND ON LAN: IP={ip}  version={dev.get('version')}")
        print(f"Add to .env:\nTUYA_LOCAL_KEY={local_key}\nTUYA_LOCAL_IP={ip}")

if not found:
    print("Nothing found on LAN. Make sure the PC and the lamp share the same 2.4GHz Wi-Fi.")
else:
    print(f"\nTotal devices on LAN: {len(found)}")
    for ip, dev in found.items():
        print(f" - {ip}: {dev}")
