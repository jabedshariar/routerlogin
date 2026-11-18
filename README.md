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
