# NEPSE Insight frontend

The frontend is a Next.js App Router application.

## Requirements

- Node.js 20.9 or newer
- npm

## Configure

Copy `.env.example` to `.env.local` and set the Django API and WebSocket URLs if
they differ from the local defaults.

## Run

```powershell
npm.cmd install
npm.cmd run dev
```

Open <http://localhost:3000>.

The Market Analysis page uses the authenticated Django
`/api/market-data/analysis/` endpoint. It displays collected NEPSE index and
sector history, daily market summaries, company quotes, and freshness where
those records are available. Empty source data is shown as unavailable; the
frontend does not supply or estimate market prices.

## Production

```powershell
npm.cmd run build
npm.cmd run start
```

## Checks

```powershell
npm.cmd run lint
```
