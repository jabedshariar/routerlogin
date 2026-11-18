from __future__ import annotations

import json
import os
import secrets
import time
from typing import Any

import jwt
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from redis.asyncio import Redis

APP_VERSION = "0.1.0"
JWT_SECRET = os.environ.get("JWT_SECRET", "")
REDIS_URL = os.environ.get("REDIS_URL", "")
WEB_ORIGIN = os.environ.get("WEB_ORIGIN", "https://routerlogin.vercel.app")
PAIR_TTL = 300
AGENT_TTL = 45

if not JWT_SECRET or len(JWT_SECRET) < 32:
    raise RuntimeError("Set JWT_SECRET to a random secret of at least 32 characters.")
if not REDIS_URL:
    raise RuntimeError("Set REDIS_URL to a private Redis instance URL.")

app = FastAPI(title="Routerly Cloud Relay", version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[WEB_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
redis: Redis | None = None
agent_sockets: dict[str, WebSocket] = {}
dashboard_sockets: dict[str, set[WebSocket]] = {}


@app.on_event("startup")
async def startup() -> None:
    global redis
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    await redis.ping()


@app.on_event("shutdown")
async def shutdown() -> None:
    if redis:
        await redis.aclose()


def issue_token(subject: str, role: str, account_id: str, expires: int = 3600) -> str:
    return jwt.encode(
        {"sub": subject, "role": role, "account": account_id, "iat": int(time.time()), "exp": int(time.time()) + expires},
        JWT_SECRET,
        algorithm="HS256",
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token.") from exc


def get_redis() -> Redis:
    if redis is None:
        raise HTTPException(status_code=503, detail="Relay is starting.")
    return redis


class PairRequest(BaseModel):
    account_id: str = Field(min_length=8, max_length=100)


class PairExchange(BaseModel):
    code: str = Field(min_length=6, max_length=12)
    device_name: str = Field(min_length=1, max_length=80)


class AgentHeartbeat(BaseModel):
    device_name: str = Field(min_length=1, max_length=80)
    agent_version: str = Field(default="0.1.0", max_length=30)


@app.get("/health")
async def health():
    return {"ok": True, "service": "routerly-cloud-relay", "version": APP_VERSION}


@app.post("/v1/pairing")
async def create_pairing(payload: PairRequest, authorization: str | None = Header(default=None)):
    # The caller must already be authenticated by Routerly's identity provider.
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in to Routerly first.")
    claims = decode_token(authorization[7:])
    if claims.get("role") != "user" or claims.get("sub") != payload.account_id:
        raise HTTPException(status_code=403, detail="Account does not match the signed-in user.")
    store = get_redis()
    code = f"{secrets.randbelow(1_000_000):06d}"
    key = f"pair:{code}"
    for _ in range(5):
        if await store.set(key, payload.account_id, ex=PAIR_TTL, nx=True):
            return {"pairing_code": code, "expires_in": PAIR_TTL}
        code = f"{secrets.randbelow(1_000_000):06d}"
        key = f"pair:{code}"
    raise HTTPException(status_code=503, detail="Could not issue a pairing code. Try again.")


@app.post("/v1/agent/exchange")
async def exchange_pairing(payload: PairExchange):
    store = get_redis()
    account_id = await store.getdel(f"pair:{payload.code}")
    if not account_id:
        raise HTTPException(status_code=400, detail="Pairing code is invalid, expired, or already used.")
    device_id = secrets.token_urlsafe(18)
    await store.set(f"device:{device_id}:account", account_id)
    await store.set(f"device:{device_id}:name", payload.device_name[:80])
    await store.sadd(f"account:{account_id}:devices", device_id)
    token = issue_token(device_id, "agent", account_id, expires=60 * 60 * 24 * 30)
    return {"device_id": device_id, "agent_token": token, "expires_in": 60 * 60 * 24 * 30}


@app.get("/v1/devices")
async def list_devices(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")
    claims = decode_token(authorization[7:])
    if claims.get("role") != "user":
        raise HTTPException(status_code=403, detail="User token required.")
    store = get_redis()
    ids = await store.smembers(f"account:{claims['sub']}:devices")
    result = []
    for device_id in ids:
        account = await store.get(f"device:{device_id}:account")
        if account != claims["sub"]:
            continue
        name = await store.get(f"device:{device_id}:name") or "Network agent"
        online = bool(await store.get(f"device:{device_id}:online"))
        result.append({"device_id": device_id, "name": name, "online": online})
    return {"devices": result}


@app.delete("/v1/devices/{device_id}")
async def revoke_device(device_id: str, authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")
    claims = decode_token(authorization[7:])
    if claims.get("role") != "user":
        raise HTTPException(status_code=403, detail="User token required.")
    store = get_redis()
    account = await store.get(f"device:{device_id}:account")
    if account != claims["sub"]:
        raise HTTPException(status_code=404, detail="Device not found.")
    await store.set(f"device:{device_id}:revoked", "1")
    await store.delete(f"device:{device_id}:online")
    return {"revoked": True}


@app.websocket("/v1/ws/agent")
async def agent_socket(ws: WebSocket):
    token = ws.query_params.get("token", "")
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        if claims.get("role") != "agent":
            raise ValueError("wrong role")
        device_id, account_id = claims["sub"], claims["account"]
        store = get_redis()
        if await store.get(f"device:{device_id}:account") != account_id:
            raise ValueError("unknown device")
        if await store.get(f"device:{device_id}:revoked"):
            raise ValueError("revoked")
    except Exception:
        await ws.close(code=4401)
        return
    await ws.accept()
    agent_sockets[device_id] = ws
    await store.set(f"device:{device_id}:online", "1", ex=AGENT_TTL)
    try:
        while True:
            message = await ws.receive_json()
            if message.get("type") == "heartbeat":
                await store.set(f"device:{device_id}:online", "1", ex=AGENT_TTL)
                continue
            if message.get("type") == "response" and isinstance(message.get("request_id"), str):
                await store.set(
                    f"response:{message['request_id']}",
                    json.dumps({"device_id": device_id, "payload": message.get("payload")}),
                    ex=30,
                )
                for dashboard in dashboard_sockets.get(account_id, set()):
                    await dashboard.send_json({"type": "agent_response", "request_id": message["request_id"], "device_id": device_id, "payload": message.get("payload")})
    except WebSocketDisconnect:
        pass
    finally:
        if agent_sockets.get(device_id) is ws:
            agent_sockets.pop(device_id, None)
            await store.delete(f"device:{device_id}:online")


@app.websocket("/v1/ws/dashboard")
async def dashboard_socket(ws: WebSocket):
    token = ws.query_params.get("token", "")
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        if claims.get("role") != "user":
            raise ValueError("wrong role")
        account_id = claims["sub"]
    except Exception:
        await ws.close(code=4401)
        return
    await ws.accept()
    dashboard_sockets.setdefault(account_id, set()).add(ws)
    try:
        while True:
            message = await ws.receive_json()
            if message.get("type") != "command":
                await ws.send_json({"type": "error", "message": "Unsupported message type."})
                continue
            device_id = message.get("device_id")
            command = message.get("command")
            request_id = secrets.token_urlsafe(16)
            if not isinstance(device_id, str) or not isinstance(command, dict):
                await ws.send_json({"type": "error", "message": "Invalid command envelope."})
                continue
            store = get_redis()
            if await store.get(f"device:{device_id}:account") != account_id or await store.get(f"device:{device_id}:revoked"):
                await ws.send_json({"type": "error", "message": "Device is not paired or has been revoked."})
                continue
            # Strict initial allow-list: only an agent health/read-only discovery ping.
            if command.get("action") != "agent_status":
                await ws.send_json({"type": "error", "message": "This release only permits agent_status. Router commands are not enabled yet."})
                continue
            agent = agent_sockets.get(device_id)
            if not agent:
                await ws.send_json({"type": "error", "message": "Network agent is offline."})
                continue
            await agent.send_json({"type": "command", "request_id": request_id, "command": {"action": "agent_status"}})
            await ws.send_json({"type": "command_accepted", "request_id": request_id, "device_id": device_id})
    except WebSocketDisconnect:
        pass
    finally:
        dashboard_sockets.get(account_id, set()).discard(ws)
