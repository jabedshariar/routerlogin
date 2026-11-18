# Routerly Cloud-Connected Remote Management Architecture

## Product requirement

Routerly's website and account system must be publicly accessible from any location. A user should be able to manage a router remotely without being on the router's Wi-Fi network.

A browser-only website cannot directly reach a private LAN address such as 192.168.1.1 from the public internet. The router-side network therefore needs one of:

1. A Routerly Network Agent installed on an always-on computer or supported gateway in that LAN; or
2. A vendor-supported cloud management API exposed by the router manufacturer.

The agent is a small background service. It is not the user's browser localhost server and it is not deployed on Vercel.

## Target topology

```text
User browser / mobile
        |
        | HTTPS
        v
Routerly web app (Vercel)
        |
        | authenticated HTTPS API
        v
Routerly cloud control plane
  - accounts and sessions
  - device pairing and revocation
  - authorization and audit log
  - command policy / capability registry
        ^
        | outbound authenticated WSS
        |
Routerly Network Agent (home / office LAN)
        |
        | private LAN only
        v
Supported router management interface
```

The agent initiates the outbound WSS connection. No inbound port forwarding on the user's router is required. The agent must maintain a heartbeat and reconnect with bounded exponential backoff.

## Pairing and trust model

1. User signs in to Routerly over HTTPS.
2. The website requests a short-lived, single-use pairing code from the cloud.
3. The user installs the Network Agent on a computer or supported always-on device in the router's LAN and enters the pairing code locally.
4. The cloud binds the agent public key/device identity to the authenticated account and consumes the pairing code.
5. The agent opens an outbound WSS session and authenticates with a revocable device credential.
6. The dashboard lists the paired network and its online/offline status.
7. Revocation immediately prevents new sessions and commands.

Pairing codes must be short-lived, single-use, rate-limited, and stored hashed. Long-lived agent credentials must be revocable and never exposed to browser JavaScript.

## Command security

- The agent must not be an arbitrary HTTP proxy, SOCKS proxy, shell, or general-purpose LAN scanner.
- Cloud commands use a strict allow-listed schema and capability registry.
- Every command is scoped to one paired agent and one router address.
- Read operations and configuration writes are separate permissions.
- Configuration writes require explicit user confirmation and an audit record.
- Sensitive values are redacted from logs.
- Agent binds no public listener; it only opens outbound TLS connections.
- Router credentials remain on the user's LAN agent and are never sent to Routerly cloud.
- The agent validates destination IPs as private LAN addresses and blocks loopback, link-local, multicast, reserved, and public addresses.
- No firmware flashing, factory reset, firewall exposure, or other destructive action is enabled by default.

## Compatibility model

Manufacturer alone is not sufficient to guarantee compatibility. Capabilities are defined per router model, hardware revision, firmware version, and management protocol. The first release should support discovery and login-page handoff, then add read-only status adapters, then carefully permissioned configuration adapters. Unsupported capabilities must be labelled unsupported rather than simulated.

## Availability requirements

Remote access works only while the Network Agent is running and connected, or when a supported vendor cloud API is available. The user's router and internet connection must also be online. An agent installed on a laptop that is shut down cannot provide remote access; an always-on home device is recommended.

## Deployment boundary

- Vercel hosts the public web application and ordinary HTTPS API routes.
- A persistent cloud relay/control-plane service handles long-lived WSS agent sessions. Do not attempt to host a long-lived WebSocket server inside a Vercel serverless function.
- A managed database stores accounts, pairings, capabilities, and audit metadata.
- A managed pub/sub or message broker coordinates dashboard requests and agent responses across relay instances.
- Secrets are configured in deployment environment variables; never commit them to Git.

## Delivery phases

1. Cloud architecture, threat model, data model, and agent packaging.
2. Account authentication, short-lived pairing, device revocation, and agent heartbeat.
3. Persistent WSS relay and request/response correlation.
4. LAN discovery and router web-interface reachability through the agent.
5. First tested read-only router adapters.
6. Explicitly confirmed configuration writes, audit history, and rollback where supported.
7. Model/firmware compatibility expansion and security review.

This document describes the target architecture, not a claim that remote management is already operational.
