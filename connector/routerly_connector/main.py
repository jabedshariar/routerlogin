from __future__ import annotations

import hashlib
import ipaddress
import json
import platform
import re
import shlex
import socket
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import ssl
import http.cookiejar
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, SecretStr

APP_VERSION = "0.2.0"
ALLOWED_ORIGINS = [
    "https://routerlogin.vercel.app",
    "https://routerlogin-r87e.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app = FastAPI(title="Routerly Tenda Local Connector", version=APP_VERSION, docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=False,
                   allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"], max_age=300)

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

class TendaRequest(BaseModel):
    address: str = Field(min_length=3, max_length=64)
    password: SecretStr

class BlockRequest(TendaRequest):
    mac: str

class BandwidthRequest(TendaRequest):
    mac: str
    upload_mbps: float = Field(ge=0, le=10000)
    download_mbps: float = Field(ge=0, le=10000)

class WebsiteRuleRequest(TendaRequest):
    mac: str
    device_name: str = Field(default="Device", max_length=20)
    enabled: bool = True
    websites: list[str] = Field(default_factory=list, max_length=10)
    allowed_window: str = "00:00-00:00"
    every_day: bool = True
    days: list[str] = Field(default_factory=list)
    mode: str = "blacklist"

class WifiRequest(TendaRequest):
    ssid_24: str = Field(min_length=1, max_length=32)
    password_24: str = Field(min_length=8, max_length=63)
    ssid_5: str = Field(min_length=1, max_length=32)
    password_5: str = Field(min_length=8, max_length=63)

class RebootScheduleRequest(TendaRequest):
    enabled: bool
    time: str = "04:00"
    delay: bool = True

def run_command(args: list[str]) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=2, check=False)
        return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""

def detect_default_gateway() -> str | None:
    system = platform.system().lower()
    if system == "windows":
        for line in run_command(["route", "print", "-4"]).splitlines():
            match = re.match(r"\\s*0\\.0\\.0\\.0\\s+0\\.0\\.0\\.0\\s+(\\d{1,3}(?:\\.\\d{1,3}){3})", line)
            if match: return match.group(1)
    elif system == "linux":
        for line in run_command(["ip", "-4", "route", "show", "default"]).splitlines():
            parts = shlex.split(line)
            if len(parts) >= 3 and parts[0] == "default" and parts[1] == "via": return parts[2]
    elif system == "darwin":
        match = re.search(r"^\\s*gateway:\\s*(\\S+)", run_command(["route", "-n", "get", "default"]), re.M)
        if match: return match.group(1)
    return None

def validate_router_address(raw: str) -> str:
    try: address = ipaddress.ip_address(raw.strip())
    except ValueError as exc: raise HTTPException(400, "Enter a valid IP address.") from exc
    if not address.is_private or address.is_loopback or address.is_link_local or address.is_multicast or address.is_unspecified or address.is_reserved:
        raise HTTPException(400, "Only private LAN router addresses are allowed.")
    return str(address)

def tenda_session(address: str, password: str):
    address = validate_router_address(address)
    base = "http://" + address
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [("X-Requested-With", "XMLHttpRequest"), ("User-Agent", "Mozilla/5.0 Routerly/0.2")]
    try:
        opener.open(base + "/login.html", timeout=4).read(65536)
        digest = hashlib.md5(password.encode("utf-8")).hexdigest()
        req = urllib.request.Request(base + "/login/Auth", data=urllib.parse.urlencode({"username":"admin","password":digest}).encode(),
                                     headers={"Content-Type":"application/x-www-form-urlencoded"})
        response = opener.open(req, timeout=5)
        body = response.read(8192).decode("utf-8", "ignore").strip()
        if body == "1" or not any(c.name == "password" and c.value for c in jar):
            raise HTTPException(401, "Tenda admin password was rejected.")
    except HTTPException: raise
    except Exception as exc: raise HTTPException(502, "Could not authenticate with the Tenda router. Check LAN connection and model compatibility.") from exc
    return base, opener

def tenda_call(base: str, opener, endpoint: str, form: dict[str, str] | None = None):
    url = base + "/goform/" + endpoint
    data = urllib.parse.urlencode(form).encode() if form is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/x-www-form-urlencoded"} if data else {})
    try:
        raw = opener.open(req, timeout=8).read(1_000_000).decode("utf-8", "replace").strip()
    except Exception as exc: raise HTTPException(502, f"Tenda API request failed: {endpoint}") from exc
    if "login.html" in raw[:500] or raw.lower().startswith("<!doctype"):
        raise HTTPException(401, "Tenda session expired. Please retry.")
    if raw.startswith("<"):
        raise HTTPException(501, f"This Tenda firmware does not expose {endpoint}.")
    try: return json.loads(raw)
    except json.JSONDecodeError: return {"raw": raw}

def require_tenda(address: str, password: SecretStr):
    base, opener = tenda_session(address, password.get_secret_value())
    try:
        info = tenda_call(base, opener, "GetRouterStatus")
    except HTTPException: raise
    except Exception as exc: raise HTTPException(502, "Tenda router API is unavailable.") from exc
    return base, opener, info

def parse_mac(mac: str) -> str:
    value = mac.strip().upper().replace("-", ":")
    if not re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", value):
        raise HTTPException(400, "Invalid MAC address.")
    return value.lower()

def encode_days(days: list[str], every_day: bool) -> str:
    order = ["sun","mon","tue","wed","thu","fri","sat"]
    return ",".join("1" if every_day or d in days else "0" for d in order)

@app.get("/health")
async def health(): return {"ok": True, "service": "routerly-tenda-local-connector", "version": APP_VERSION}

@app.get("/api/v1/gateway")
async def gateway():
    address = detect_default_gateway()
    if not address: raise HTTPException(404, "Could not detect gateway; enter router IP manually.")
    return {"gateway": address, "source": "system-routing-table"}

@app.post("/api/v1/discover")
async def discover(payload: DiscoverRequest):
    address = validate_router_address(payload.address)
    for scheme in ("http", "https"):
        try:
            context = ssl._create_unverified_context()
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=context))
            response = opener.open(f"{scheme}://{address}/", timeout=2.5)
            body = response.read(65536).decode("utf-8", "ignore")
            title = re.search(r"<title[^>]*>(.*?)</title>", body, re.I|re.S)
            sample = ((title.group(1) if title else "") + body[:20000]).lower()
            tenda = "tenda" in sample
            return {"address":address,"reachable":True,"brand":"Tenda" if tenda else None,"model":None,
                    "login_url":f"{scheme}://{address}/","message":"Tenda web interface detected." if tenda else "Web interface responded; Tenda identity not confirmed."}
        except Exception: pass
    return {"address":address,"reachable":False,"brand":None,"model":None,"login_url":f"http://{address}/","message":"No router web interface responded."}

@app.post("/api/v1/tenda/status")
async def tenda_status(p: TendaRequest):
    base, op, status = require_tenda(p.address,p.password)
    try:
        clients=tenda_call(base,op,"getOnlineList")
        wifi=tenda_call(base,op,"WifiBasicGet")
        wifi_safe = {k:v for k,v in wifi.items() if k not in ("wrlPwd","wrlPwd_5g","password","adminPwd")} if isinstance(wifi,dict) else {}
        return {"vendor":"Tenda","status":status,"clients_raw":clients,"wifi":wifi_safe,
                "model":"Tenda (exact model/firmware must be checked)","compatibility":"API response received; model/firmware not yet positively verified"}
    except HTTPException: raise

@app.post("/api/v1/tenda/clients")
async def tenda_clients(p: TendaRequest):
    base,op,_=require_tenda(p.address,p.password)
    return {"clients_raw":tenda_call(base,op,"getOnlineList"),"blocked_raw":tenda_call(base,op,"getBlackRuleList")}

@app.post("/api/v1/tenda/block")
async def tenda_block(p: BlockRequest):
    base,op,_=require_tenda(p.address,p.password); mac=parse_mac(p.mac)
    clients=tenda_call(base,op,"getOnlineList")
    if isinstance(clients,list) and clients and str(clients[0].get("localhostMac","")).lower()==mac:
        raise HTTPException(400,"Refusing to block the device currently managing the router.")
    result=tenda_call(base,op,"setBlackRule",{"mac":mac})
    return {"ok":True,"result":result}

@app.post("/api/v1/tenda/unblock")
async def tenda_unblock(p: BlockRequest):
    base,op,_=require_tenda(p.address,p.password)
    return {"ok":True,"result":tenda_call(base,op,"delBlackRule",{"mac":parse_mac(p.mac)})}

@app.post("/api/v1/tenda/bandwidth")
async def tenda_bandwidth(p: BandwidthRequest):
    base,op,_=require_tenda(p.address,p.password); mac=parse_mac(p.mac)
    rows=tenda_call(base,op,"GetNetControlList")
    if not isinstance(rows,list) or not rows: raise HTTPException(501,"Bandwidth list format is unsupported on this firmware.")
    head=rows[0]; devices=rows[1:]
    found=False
    for d in devices:
        if str(d.get("mac","")).lower()==mac:
            d["limitUp"]=str(round(p.upload_mbps*128)); d["limitDown"]=str(round(p.download_mbps*128)); found=True
    if not found: raise HTTPException(404,"Device not found in router bandwidth list.")
    encoded="\n".join("\r".join([str(d.get("hostName","")),str(d.get("mac","")),str(d.get("limitUp","0")),str(d.get("limitDown","0"))]) for d in devices)
    result=tenda_call(base,op,"SetNetControlList",{"list":encoded})
    return {"ok":True,"result":result,"unit":"Mbps"}

@app.post("/api/v1/tenda/website-rule")
async def tenda_website_rule(p: WebsiteRuleRequest):
    base,op,_=require_tenda(p.address,p.password); mac=parse_mac(p.mac)
    if p.mode not in ("blacklist","whitelist"): raise HTTPException(400,"Mode must be blacklist or whitelist.")
    if len(p.websites)>10 or any(not re.fullmatch(r"[-.a-z0-9]{2,31}",x.lower()) for x in p.websites):
        raise HTTPException(400,"Tenda AC10 website rules accept up to 10 keywords (2-31 lowercase letters, digits, dot or hyphen).")
    form={"deviceId":mac,"enable":"1" if p.enabled else "0"}
    if p.enabled:
        if not re.fullmatch(r"\\d{2}:\\d{2}-\\d{2}:\\d{2}",p.allowed_window): raise HTTPException(400,"Use HH:MM-HH:MM time window.")
        form.update({"deviceName":p.device_name,"time":p.allowed_window,"url_enable":"1" if p.websites else "0",
                     "urls":",".join(x.lower() for x in p.websites),"day":encode_days(p.days,p.every_day),
                     "limit_type":"1" if p.mode=="whitelist" else "0"})
    result=tenda_call(base,op,"saveParentControlInfo",form)
    return {"ok":True,"result":result}

@app.post("/api/v1/tenda/wifi")
async def tenda_wifi(p: WifiRequest):
    base,op,_=require_tenda(p.address,p.password)
    # Read existing settings first so radio enable/security flags are preserved.
    old=tenda_call(base,op,"WifiBasicGet")
    form={"wrlEn":str(old.get("wrlEn","1")),"wrlEn_5g":str(old.get("wrlEn_5g","1")),
          "security":str(old.get("security","wpa2psk")),"security_5g":str(old.get("security_5g","wpa2psk")),
          "ssid":p.ssid_24,"ssid_5g":p.ssid_5,"hideSsid":str(old.get("hideSsid","0")),
          "hideSsid_5g":str(old.get("hideSsid_5g","0")),"wrlPwd":p.password_24,"wrlPwd_5g":p.password_5}
    result=tenda_call(base,op,"WifiBasicSet",form)
    return {"ok":True,"result":result,"warning":"Wi-Fi radios may restart; reconnect using the new credentials."}

@app.post("/api/v1/tenda/scheduled-reboot")
async def tenda_scheduled_reboot(p: RebootScheduleRequest):
    base,op,_=require_tenda(p.address,p.password)
    old=tenda_call(base,op,"GetSysAutoRebbotCfg")
    form=dict(old) if isinstance(old,dict) else {}
    form.update({"autoRebootEn":"1" if p.enabled else "0","rebootTime":p.time,"delayRebootEn": "true" if p.delay else "false"})
    result=tenda_call(base,op,"SetSysAutoRebbotCfg",form)
    return {"ok":True,"result":result,"note":"The exact schedule field names are firmware-dependent; verify the router response and admin UI."}

@app.post("/api/v1/tenda/feature-status")
async def tenda_feature_status(p: TendaRequest):
    base,op,status=require_tenda(p.address,p.password)
    return {"features":{
        "device_block":{"status":"api_available","endpoint":"setBlackRule"},
        "speed_limit":{"status":"api_available","endpoint":"SetNetControlList"},
        "website_block":{"status":"api_available","endpoint":"saveParentControlInfo"},
        "wifi_credentials":{"status":"setter_documented_unverified","endpoint":"WifiBasicSet"},
        "scheduled_reboot":{"status":"setter_documented_unverified","endpoint":"SetSysAutoRebbotCfg"},
        "private_dns":{"status":"unsupported_encrypted_dns_not_verified","detail":"Manual WAN DNS is distinct from encrypted Private DNS (DoH/DoT)."},
        "vpn":{"status":"model_firmware_dependent","detail":"AC10 reference exposes PPTP/L2TP only; PPTP is obsolete and not recommended."},
        "admin_password":{"status":"not_implemented","detail":"Native password-change form requires dedicated safety-tested flow."},
        "total_usage":{"status":"unsupported_cumulative_counter_not_verified","detail":"Instantaneous WAN rates are not cumulative usage."}
    },"router_status":status}
