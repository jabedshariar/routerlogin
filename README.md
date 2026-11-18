# Universal Router Manager

A minimal, local-first interface for discovering and managing supported routers across multiple manufacturers.

## Status

This repository contains the initial web application foundation and brand catalogue. Router control requires a separately installed local connector and tested model/firmware-specific adapters. The UI does not claim unsupported integrations are functional.

## Run locally

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Deploy

Import this repository into Vercel. Framework preset: Next.js. Build command: `npm run build`.

## Security

Never enter router credentials into an unverified interface. This initial web frontend does not collect or transmit router passwords. Local connector pairing and vendor-specific authentication adapters are separate implementation milestones.

## Target brands

The initial brand catalogue is currently defined in `app/page.tsx` and can be moved into a dedicated data module as the compatibility database grows.

## Local connector (early discovery release)

The local connector is a separate Python service. It runs on the user's computer, not on Vercel, because a cloud-hosted website cannot directly inspect the user's private LAN.

See [connector installation instructions](connector/README.md). The connector currently:
- detects the computer's default gateway from the operating system routing table;
- checks the router web interface over HTTP/HTTPS on ports 80/443;
- performs best-effort manufacturer fingerprinting from the login page;
- does not request, store, or transmit router credentials.

This is discovery only. Router login automation and configuration changes are not implemented yet. Feature availability will depend on tested router model/firmware adapters.
