# Routerly Local Connector

The connector runs on the user's computer and gives the Routerly web UI a narrowly scoped way to inspect the local default gateway. It binds to loopback only and does not accept arbitrary URLs, credentials, commands, or port ranges.

## Requirements
- Python 3.10+
- Computer connected to the same LAN as the router

## Install and run (Windows PowerShell)
Open PowerShell in this connector folder:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn routerly_connector.main:app --host 127.0.0.1 --port 8765
```

## Install and run (macOS / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn routerly_connector.main:app --host 127.0.0.1 --port 8765
```

Keep the terminal running while using Routerly.

## Verify
Open http://127.0.0.1:8765/health on the same computer. Expected response:

```json
{"ok":true,"service":"routerly-local-connector","version":"0.1.0"}
```

The web UI uses:
- GET /api/v1/gateway — reads the operating system's default route.
- POST /api/v1/discover — probes only the supplied private LAN IP on HTTP/HTTPS ports 80/443.

## Security boundaries
- Binds to 127.0.0.1; do not change this to 0.0.0.0.
- Allows only the Routerly production origins and local development origins configured in the source.
- Rejects non-private, loopback, link-local, multicast, reserved and unspecified target IPs.
- Does not scan subnets, follow redirects, accept arbitrary URLs, or store/send router credentials.
- Uses read-only HTTP GET requests for reachability and best-effort page fingerprinting.
- HTTPS certificate verification is disabled only for the local router probe because some router admin pages use self-signed certificates. No credentials are sent.
- This is an early discovery connector, not yet a router configuration agent. Do not expose its port to the internet.

If your deployed Routerly domain changes, add that exact origin to ALLOWED_ORIGINS in routerly_connector/main.py and restart the connector.
