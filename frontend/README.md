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

## Production

```powershell
npm.cmd run build
npm.cmd run start
```

## Checks

```powershell
npm.cmd run lint
```
