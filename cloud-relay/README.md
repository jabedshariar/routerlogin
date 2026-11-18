# Routerly Cloud Relay (MVP)

Persistent WebSocket control plane for Routerly's cloud-connected network agent.

## Deploy

Deploy this folder as a Docker web service on a persistent host (Render/Fly.io/container platform), not as a Vercel serverless function. Provision a private Redis instance and configure:

- \`REDIS_URL\`: private Redis connection URL
- \`JWT_SECRET\`: random secret of at least 32 characters
- \`WEB_ORIGIN\`: exact public Routerly origin

The included \`render.yaml\` is a starting blueprint. Redis must be provisioned separately and its private URL supplied during deployment.

## Important integration status

This relay provides one-time pairing-code exchange, agent tokens, device listing/revocation, heartbeat presence, and authenticated WebSocket channels. The initial dashboard command allow-list permits only \`agent_status\`.

**Authentication integration is not complete:** \`POST /v1/pairing\` expects a Routerly user JWT signed with the same \`JWT_SECRET\`, with claims \`sub\`, \`role=user\`, \`account\`, \`iat\`, and \`exp\`. Connect this to a real identity provider before production use. Do not create user tokens from untrusted browser input.

**Router commands are intentionally disabled.** The next milestone is a signed, allow-listed agent protocol plus model/firmware-specific read-only adapters. This relay is an MVP foundation, not a complete production remote router manager.

## Security notes

- Agent credentials are revocable and scoped to one device/account.
- Pairing codes are single-use and expire after five minutes.
- Agent connections are outbound WSS; no inbound router port forwarding is needed.
- No arbitrary URL proxy, shell, subnet scan, or router credential storage is exposed.
- Run behind TLS. Use private Redis networking and rotate secrets.
- Add rate limiting, structured audit logs, monitoring, and a reviewed identity-provider integration before public launch.
