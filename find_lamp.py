import socket, concurrent.futures, sys

PORT = 6668

def local_subnet():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ".".join(ip.split(".")[:3])

SUBNET = sys.argv[1] if len(sys.argv) > 1 else local_subnet()

def check(ip):
    s = socket.socket()
    s.settimeout(0.7)
    try:
        s.connect((ip, PORT))
        s.close()
        return ip
    except Exception:
        return None

ips = [f"{SUBNET}.{i}" for i in range(1, 255)]
print(f"Scanning {SUBNET}.0/24 tcp/{PORT} ...")
with concurrent.futures.ThreadPoolExecutor(max_workers=64) as ex:
    for fut in concurrent.futures.as_completed({ex.submit(check, ip): ip for ip in ips}):
        r = fut.result()
        if r:
            print(f"OPEN {r}:{PORT} <- possible Tuya device")
print("done")
