from __future__ import annotations

import ipaddress
import platform
import re
import shlex
import socket
import subprocess
import urllib.error
import urllib.request
import ssl
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

APP_VERSION = "0.1.0"
ALLOWED_ORIGINS = [
    "https://routerlogin.vercel.app",
    "https://routerlogin-r87e.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app = FastAPI(title="Routerly Local Connector", version=APP_VERSION, docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    max_age=300,
)

@app.middleware("http")
async def local_network_preflight(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin and origin not in ALLOWED_ORIGINS:
        from starlette.responses import JSONResponse
        return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
    response = await call_next(request)
    if request.headers.get("access-control-request-private-network") == "true":
        response.headers["Access-Control-Allow-Private-Network"] = "true"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


class DiscoverRequest(BaseModel):
    address: str = Field(min_length=3, max_length=64)


def run_command(args: list[str]) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=2, check=False)
        return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def detect_default_gateway() -> str | None:
    system = platform.system().lower()
    if system == "windows":
        output = run_command(["route", "print", "-4"])
        for line in output.splitlines():
            match = re.match(r"\s*0\.0\.0\.0\s+0\.0\.0\.0\s+(\d{1,3}(?:\.\d{1,3}){3})", line)
            if match:
                return match.group(1)
    elif system == "linux":
        output = run_command(["ip", "-4", "route", "show", "default"])
        for line in output.splitlines():
            parts = shlex.split(line)
            if len(parts) >= 3 and parts[0] == "default" and parts[1] == "via":
                return parts[2]
    elif system == "darwin":
        output = run_command(["route", "-n", "get", "default"])
        match = re.search(r"^\s*gateway:\s*(\S+)", output, re.MULTILINE)
        if match:
            return match.group(1)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("192.0.2.1", 80))
        local_ip = sock.getsockname()[0]
        sock.close()
        octets = local_ip.split(".")
        if len(octets) == 4 and all(part.isdigit() for part in octets):
            return ".".join(octets[:3] + ["1"])
    except OSError:
        pass
    return None


def validate_router_address(raw: str) -> str:
    try:
        address = ipaddress.ip_address(raw.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Enter a valid IP address.") from exc
    if (
        not address.is_private or address.is_loopback or address.is_link_local
        or address.is_multicast or address.is_unspecified or address.is_reserved
    ):
        raise HTTPException(status_code=400, detail="Only private LAN router addresses are allowed.")
    return str(address)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def extract_title(body: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", match.group(1))).strip()[:160]


def probe_url(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "RouterlyLocalConnector/0.1",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Connection": "close",
        },
        method="GET",
    )
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        NoRedirect(),
        urllib.request.HTTPSHandler(context=context),
    )
    try:
        with opener.open(request, timeout=2.5) as response:
            body = response.read(65536).decode("utf-8", errors="ignore")
            return {"reachable": True, "status": response.status, "server": response.headers.get("Server"), "title": extract_title(body), "body": body}
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(65536).decode("utf-8", errors="ignore")
        except OSError:
            body = ""
        return {"reachable": True, "status": exc.code, "server": exc.headers.get("Server") if exc.headers else None, "title": extract_title(body), "body": body}
    except (urllib.error.URLError, TimeoutError, OSError, ssl.SSLError):
        return {"reachable": False, "status": None, "server": None, "title": None, "body": ""}


def identify_vendor(server: str | None, title: str | None, body: str) -> str | None:
    sample = " ".join([server or "", title or "", body[:20000]]).lower()
    signatures = [
        (("netis", "netis systems"), "Netis"),
        (("tp-link", "tplink"), "TP-Link"),
        (("asus", "asuswrt"), "ASUS"),
        (("netgear",), "NETGEAR"),
        (("d-link", "dlink"), "D-Link"),
        (("tenda",), "Tenda"),
        (("huawei",), "Huawei"),
        (("mikrotik", "routeros"), "MikroTik"),
        (("ubiquiti", "unifi"), "Ubiquiti"),
        (("zyxel",), "Zyxel"),
        (("mercusys",), "Mercusys"),
        (("openwrt",), "OpenWrt"),
        (("keenetic",), "Keenetic"),
        (("fritz!box", "avm"), "AVM (FRITZ!)"),
    ]
    for needles, brand in signatures:
        if any(needle in sample for needle in needles):
            return brand
    return None


@app.get("/health")
async def health():
    return {"ok": True, "service": "routerly-local-connector", "version": APP_VERSION}


@app.get("/api/v1/gateway")
async def gateway():
    address = detect_default_gateway()
    if not address:
        raise HTTPException(status_code=404, detail="Could not detect a default gateway. Enter your router IP manually.")
    return {"gateway": address, "source": "system-routing-table"}


@app.post("/api/v1/discover")
async def discover(payload: DiscoverRequest):
    address = validate_router_address(payload.address)
    results = []
    for scheme in ("http", "https"):
        result = probe_url(f"{scheme}://{address}/")
        results.append({"scheme": scheme, **result})
        if result["reachable"]:
            break
    reachable = next((item for item in results if item["reachable"]), None)
    if not reachable:
        return {
            "address": address, "reachable": False, "brand": None, "model": None,
            "login_url": f"http://{address}/",
            "message": "No HTTP login page responded. The router may block web probes or use a different management port.",
        }
    brand = identify_vendor(reachable.get("server"), reachable.get("title"), reachable.get("body", ""))
    scheme = reachable["scheme"]
    return {
        "address": address, "reachable": True, "http_status": reachable["status"],
        "server": reachable.get("server"), "page_title": reachable.get("title"),
        "brand": brand, "model": None, "login_url": f"{scheme}://{address}/",
        "message": "Router web interface responded. Manufacturer identification is best-effort." if brand
        else "Router web interface responded. Manufacturer could not be identified reliably.",
    }
