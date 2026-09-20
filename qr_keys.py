import os
import time
from dotenv import load_dotenv, set_key

load_dotenv()
DEVICE_ID = os.getenv("TUYA_DEVICE_ID")
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

CLIENT_ID = "HA_3y9q4ak7g4ephrvke"
SCHEME = "smartlife"

def main():
    from tuya_sharing import LoginControl, Manager

    print("User Code: Smart Life -> Me -> Settings -> Account and Security -> User Code")
    user_code = input("Enter user code: ").strip()
    if not user_code:
        raise SystemExit("User code is required")

    resp = LoginControl().qr_code(CLIENT_ID, SCHEME, user_code)
    if not resp.get("success"):
        raise SystemExit(f"Could not start QR login: {resp}")
    token = resp["result"]["qrcode"]

    try:
        import qrcode
        qr = qrcode.QRCode(border=2)
        qr.add_data(f"{SCHEME}--qrLogin?token={token}")
        qr.make(fit=True)
        qr.print_ascii(invert=True)
        png = os.path.join(os.path.dirname(__file__), "tuya-login-qr.png")
        qr.make_image().save(png)
        print(f"\nIf the terminal QR does not scan — open {png}")
    except Exception as e:
        print(f"QR lib fail: {e}\nLink: {SCHEME}--qrLogin?token={token}")

    print("\nScan it in Smart Life (+ -> Scan) and tap Confirm login. Waiting ~150s...")
    session = None
    deadline = time.time() + 150
    while time.time() < deadline:
        ok, result = LoginControl().login_result(token, CLIENT_ID, user_code)
        if ok:
            session = {
                "client_id": CLIENT_ID,
                "user_code": user_code,
                "terminal_id": result.get("terminal_id"),
                "endpoint": result.get("endpoint") or result.get("end_point"),
                "token_info": {k: result.get(k) for k in ("t", "uid", "expire_time", "access_token", "refresh_token")},
            }
            break
        print(".", end="", flush=True)
        time.sleep(2)
    print()
    if not session:
        raise SystemExit("Timed out — the QR code expired (1-2 min). Re-run and scan faster.")

    mgr = Manager(
        session["client_id"], session["user_code"], session["terminal_id"],
        session["endpoint"], session["token_info"], None,
    )
    mgr.update_device_cache()
    devices = list(mgr.device_map.values())
    print(f"\nFound {len(devices)} device(s)")
    mine = None
    for d in devices:
        mark = " <-- YOURS" if getattr(d, "id", "") == DEVICE_ID else ""
        print(f" - {getattr(d, 'name', '?')} {getattr(d, 'id', '?')} online={getattr(d, 'online', '?')}{mark}")
        if getattr(d, "id", "") == DEVICE_ID:
            mine = d

    if not mine:
        print(f"\n{DEVICE_ID} is not in this account. Check the lamp is paired in the same Smart Life account.")
        return

    key = getattr(mine, "local_key", "")
    ip = getattr(mine, "ip", "") or ""
    print(f"\nLamp: {mine.name}\nlocal_key=...{key[-4:] if key else 'EMPTY'} len={len(key) if key else 0}\nip={ip or 'no IP reported — find it with a network scan'}")
    print(f"product={getattr(mine, 'product_name', '')} category={getattr(mine, 'category', '')}")
    if hasattr(mine, "status") and mine.status:
        print(f"DPS/status: {dict(mine.status)}")

    if key:
        set_key(ENV_PATH, "TUYA_LOCAL_KEY", key)
        print("-> wrote TUYA_LOCAL_KEY to .env")
    if ip:
        set_key(ENV_PATH, "TUYA_LOCAL_IP", ip)
        print("-> wrote TUYA_LOCAL_IP to .env")
    else:
        print("-> IP is empty. Find it in the router DHCP list, then update .env manually.")

    print("\nNext: ./.venv/bin/python lamp_local.py status")

if __name__ == "__main__":
    main()
