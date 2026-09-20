import os
import sys
from dotenv import load_dotenv

load_dotenv()
ok = True

print(f"Python: {sys.version.split()[0]} @ {sys.executable}")
try:
    import tinytuya
    print(f"tinytuya: {tinytuya.__version__ if hasattr(tinytuya, '__version__') else 'installed'} OK")
except Exception as e:
    print(f"tinytuya: FAIL ({e})")
    ok = False

for key in ("TUYA_API_REGION", "TUYA_API_KEY", "TUYA_API_SECRET",
            "TUYA_DEVICE_ID", "TUYA_LOCAL_KEY", "TUYA_LOCAL_IP",
            "TUYA_LOCAL_VERSION"):
    v = os.getenv(key, "")
    masked = ("..." + v[-4:] if len(v) > 8 else ("set" if v else "EMPTY"))
    mark = "OK" if v else "--"
    if key in ("TUYA_LOCAL_KEY", "TUYA_LOCAL_IP") and not v:
        mark = ".. (run qr_keys.py)"
    print(f"{mark} {key}={masked if 'SECRET' in key or 'KEY' in key else v or 'EMPTY'}")

print("\nENV OK" if ok else "\nENV FAIL")
