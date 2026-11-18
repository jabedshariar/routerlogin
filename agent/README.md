# Routerly Network Agent (early MVP)

This agent runs on an always-on computer inside the home/office LAN. It opens an outbound WSS connection to Routerly's relay. It does not open an inbound port.

## Pairing

1. Deploy the cloud relay and configure its Redis and JWT secrets.
2. Complete the Routerly user-authentication integration and create a short-lived pairing code from the signed-in dashboard.
3. Exchange the pairing code at \`POST /v1/agent/exchange\` with JSON:
   \`{"code":"123456","device_name":"Home network agent"}\`
4. Save the returned \`agent_token\` securely on the local computer.

The exchange endpoint is intended to be called by the agent's local setup flow. Do not paste the agent token into a public issue, chat, or website.

## Run

Python 3.10+:

\`\`\`bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ROUTERLY_RELAY_URL="wss://YOUR-RELAY-HOST"
export ROUTERLY_AGENT_TOKEN="YOUR-DEVICE-TOKEN"
python routerly_agent.py
\`\`\`

On Windows PowerShell, activate with \`.venv\\Scripts\\Activate.ps1\` and set environment variables with \`$env:NAME="value"\`.

Keep the host powered on and connected to the same LAN as the router for remote access.

## Current capability

The agent connects, sends heartbeats, and responds to the allow-listed \`agent_status\` request with its hostname, OS and detected default gateway. It does **not** yet log into or configure a router. Do not treat a detected gateway as proof of router identity.
