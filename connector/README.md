# Routerly Tenda Local Connector

This connector runs on a computer inside the same LAN as the Tenda router. It
connects to the router locally; router admin credentials are sent directly from
the browser to this loopback connector and are not sent to Routerly's cloud.

## Run

Python 3.10+:

```bash
cd connector
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn routerly_connector.main:app --host 127.0.0.1 --port 8765
```

Open Routerly in the same computer's browser. The connector binds only to
127.0.0.1 and permits only the configured Routerly origins.

## Tenda API endpoints

The first adapter targets the reverse-engineered Tenda AC10-family web API.
Endpoints currently implemented:

- `POST /api/v1/tenda/status` — status and Wi-Fi settings (password fields redacted)
- `POST /api/v1/tenda/clients` — connected clients and blacklist
- `POST /api/v1/tenda/block`, `/unblock` — immediate client blacklist
- `POST /api/v1/tenda/bandwidth` — per-device upload/download caps (Mbps)
- `POST /api/v1/tenda/website-rule` — per-device parental time and website keywords
- `POST /api/v1/tenda/wifi` — 2.4/5 GHz SSID and password update
- `POST /api/v1/tenda/scheduled-reboot` — scheduled maintenance configuration
- `POST /api/v1/tenda/feature-status` — compatibility/status matrix

Every request requires router address and admin password. The password is
used for a local Tenda login and is not persisted by the connector. This
adapter has not yet been validated against your physical router. Do not use
Wi-Fi, schedule, or other disruptive writes until testing on the exact model
and firmware. Always keep a wired or alternate admin recovery path.

## Not yet supported / verified

Encrypted Private DNS (DoH/DoT), secure modern VPN setup, admin password
rotation, and cumulative total-usage counters are not exposed by the verified
AC10 API reference. Manual WAN DNS, PPTP/L2TP, or instantaneous speed must not
be mislabeled as those features. The AC10 API reference reports PPTP/L2TP
support on some firmware; PPTP is obsolete and should not be recommended.

## Remote access

This connector is LAN-local. Global remote access additionally requires the
cloud relay, authenticated user identity, secure device pairing and a running
LAN agent. Those pieces are not yet integrated into this UI. No router
port-forwarding should be enabled.


## Automatic model and firmware detection

POST /api/v1/tenda/identify accepts only the private router address and
performs read-only inspection of the local web interface. It returns a
compatibility profile, detected model/firmware strings when exposed, and
explicit capability states. Unknown profiles are write-locked.

The initial registry includes a candidate Tenda F3 V12 profile, a narrowly
scoped AC10 RTL V15 reference profile, and a generic Tenda fallback. F3
write operations are intentionally not enabled until verified on the exact
hardware revision and firmware. The connector must not guess endpoint
formats based on brand alone.
