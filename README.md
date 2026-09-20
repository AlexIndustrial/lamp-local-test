# smarthome — local Tuya lamp control

Local-only control of a Tuya LED bulb (tested on **LED BULB W509Z2**),
without cloud calls at runtime. Two parts: a Python prototype on
`tinytuya` and a Rust console (`axum` + `rustuya`) with an HTML UI.

## Device

| Param | Value |
|---|---|
| Model | LED BULB W509Z2, category `dj` |
| LAN IP | `192.168.50.5` (see `.env`) |
| Protocol | **3.5** (3.3 times out, 3.4 reports key error) |
| DPS | 20 power · 21 mode (`white`/`colour`) · 22 white brightness 10–1000 · 23 white temperature 0–1000 · 24 colour `HHHHSSSSVVVV` (h 0–360, s/v 0–1000) |

Firmware quirks discovered on the device:

- Writing DP22 while in `colour` mode pushes the lamp back to `white`.
  The Rust `/api/bright` therefore reads the current mode first: in
  `colour` it adjusts brightness via the V-component of DP24, keeping hue.
- `colour` mode with low saturation does not look white. Real white comes
  only from `white` mode + DP23. The UI hue ring is saturation-fixed at 1000.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in values, see below
python check_env.py
```

Config lives in `.env` (never committed, see `.gitignore`):

```
TUYA_DEVICE_ID=...
TUYA_LOCAL_KEY=...     # 16 chars, via qr_keys.py
TUYA_LOCAL_IP=192.168.50.5
TUYA_LOCAL_VERSION=3.5
```

## Getting the local key without an IoT subscription

The Tuya IoT Core trial expires (`28841002`), and both the IoT API and
`tinytuya wizard` stop returning keys. Use QR login via the Smart Life app
account instead — no developer project needed:

```bash
python qr_keys.py
```

1. Smart Life app → Me → Settings → Account and Security → User Code.
2. Enter the code, scan the printed QR in the app (`+` → Scan) → Confirm login.
3. The script finds the lamp by `TUYA_DEVICE_ID` and writes
   `TUYA_LOCAL_KEY` / `TUYA_LOCAL_IP` into `.env`.

Note: the IP reported by the sharing SDK is a public egress address and is
useless for LAN. Find the real one in the router DHCP list (`lwip0` host)
or with `python find_lamp.py` (TCP 6668 sweep of `192.168.50.0/24`).

`fetch_keys.py` is the legacy IoT-API path (needs a valid subscription).

## Python prototype

```bash
python lamp_local.py status
python lamp_local.py on
python lamp_local.py bright 500   # 10–1000
python lamp_local.py temp 300     # 0–1000
python lamp_local.py color 240    # hue, [sat] [val]
python lamp_local.py off
python lamp_local.py demo
```

## Rust console

`lamp-console/` — `axum` HTTP server + `rustuya` 0.3 (native protocol 3.5)
+ Tailwind HTML UI (English, fullscreen, two tabs: White / Color, shared
brightness slider, hue ring, presets, live state).

```bash
cargo run --manifest-path lamp-console/Cargo.toml
# open http://127.0.0.1:8080
```

API:

| Method | Endpoint | Body | Effect |
|---|---|---|---|
| GET | `/api/status` | — | full DPS state |
| POST | `/api/power` | `{"on": true}` | DP20 |
| POST | `/api/bright` | `{"value": 500}` | DP22 in white, DP24-V in colour |
| POST | `/api/temp` | `{"value": 300}` | DP23 (+ white mode) |
| POST | `/api/mode` | `{"mode": "white"}` | DP21 |
| POST | `/api/color` | `{"h": 240, "s": 1000, "v": 1000}` | DP24 (+ colour mode) |

## Files

```
.env.example        config template (no secrets)
check_env.py        venv + config sanity check
qr_keys.py          local-key retrieval via Smart Life QR login
fetch_keys.py       legacy local-key retrieval via IoT Cloud API
lamp_local.py       local control prototype (white + color)
find_lamp.py        TCP-6668 sweep to find the lamp IP
lamp-console/       Rust backend + HTML console
```

## Troubleshooting

- `Err 902 / Timeout` — wrong IP or protocol version; confirm the lamp IP
  in the router and that `TUYA_LOCAL_VERSION=3.5`.
- `Found 0 devices` on UDP scan — PC and lamp must share the same 2.4 GHz
  LAN; VPNs and guest networks break broadcast discovery.
- Key stops working — Tuya rotates the local key on re-pairing; re-run
  `qr_keys.py`.
