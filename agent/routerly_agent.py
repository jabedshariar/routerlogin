from __future__ import annotations

import asyncio
import json
import os
import platform
import socket
import time
import urllib.request
from urllib.parse import urlencode

import websockets

RELAY_URL = os.environ.get("ROUTERLY_RELAY_URL", "").rstrip("/")
AGENT_TOKEN = os.environ.get("ROUTERLY_AGENT_TOKEN", "")
DEVICE_NAME = os.environ.get("ROUTERLY_DEVICE_NAME", socket.gethostname())
VERSION = "0.1.0"


def gateway() -> str | None:
    system = platform.system().lower()
    try:
        if system == "windows":
            import subprocess, re
            output = subprocess.run(["route", "print", "-4"], capture_output=True, text=True, timeout=2).stdout
            match = re.search(r"^\s*0\.0\.0\.0\s+0\.0\.0\.0\s+(\d{1,3}(?:\.\d{1,3}){3})", output, re.M)
            return match.group(1) if match else None
        if system == "linux":
            import subprocess
            output = subprocess.run(["ip", "-4", "route", "show", "default"], capture_output=True, text=True, timeout=2).stdout
            for line in output.splitlines():
                parts = line.split()
                if len(parts) >= 3 and parts[0] == "default" and parts[1] == "via":
                    return parts[2]
        if system == "darwin":
            import subprocess, re
            output = subprocess.run(["route", "-n", "get", "default"], capture_output=True, text=True, timeout=2).stdout
            match = re.search(r"^\s*gateway:\s*(\S+)", output, re.M)
            return match.group(1) if match else None
    except Exception:
        return None
    return None


def local_status() -> dict:
    return {
        "agent_version": VERSION,
        "device_name": DEVICE_NAME,
        "platform": platform.platform(),
        "gateway": gateway(),
        "checked_at": int(time.time()),
    }


async def run() -> None:
    if not RELAY_URL.startswith("wss://"):
        raise SystemExit("ROUTERLY_RELAY_URL must be a wss:// URL.")
    if not AGENT_TOKEN:
        raise SystemExit("Set ROUTERLY_AGENT_TOKEN after pairing.")
    ws_url = RELAY_URL + "/v1/ws/agent?" + urlencode({"token": AGENT_TOKEN})
    delay = 2
    while True:
        try:
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20, max_size=65536) as ws:
                delay = 2
                async def heartbeat():
                    while True:
                        await ws.send(json.dumps({"type": "heartbeat"}))
                        await asyncio.sleep(15)
                task = asyncio.create_task(heartbeat())
                try:
                    async for raw in ws:
                        message = json.loads(raw)
                        if message.get("type") == "command":
                            command = message.get("command", {})
                            if command.get("action") == "agent_status":
                                payload = local_status()
                            else:
                                payload = {"error": "unsupported_action"}
                            await ws.send(json.dumps({
                                "type": "response",
                                "request_id": message.get("request_id"),
                                "payload": payload,
                            }))
                finally:
                    task.cancel()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"Routerly relay disconnected: {type(exc).__name__}; retrying in {delay}s")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)


if __name__ == "__main__":
    asyncio.run(run())
