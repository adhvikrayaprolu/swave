# Swave
Swipe through music previews, keep the tracks you like and build a playlist from your discovery history.

## Overview
Swave helps listeners explore artists and songs through a like/pass feed rather than reproducing a streaming service. Account data is persisted; the separately labeled demo uses simulated data.

## Project Context
Started as a CS 222 team project at UIUC. The current engineering pass reconciles authentication, persistent interactions, integration boundaries, tests and reproducible setup.

## Key Features
- Email/password registration and JWT login.
- iTunes catalog search, provider-hosted previews and accessible like/pass controls.
- Persisted preferences and deduplicated daily playlists.
- Retryable save/search failures and clear loading/empty states.

## Architecture / Tech Stack
React/TypeScript + Vite + shadcn/Radix + Zustand/TanStack Query → Django REST APIs → SQLite. `account_views.py` handles accounts, `catalog_views.py` catalog APIs and `services.py` transactional swipes/playlists. `spotify_views.py` is an optional experimental integration, not a prerequisite for discovery.

## Quick Start
Python 3.13, Node 22.23+ and npm:
```sh
make setup
make dev
```
Open http://127.0.0.1:8080. The command migrates SQLite, seeds four metadata-only tracks, and starts the backend at 8000 and frontend at 8080. Search imports playable previews when the provider supplies them. Ctrl-C stops both servers. Setup preserves an existing `.env`.

## Validation / Tests
```sh
make check
```
Django system/migration checks and tests; frontend behavior tests, typecheck, lint and build. Tests cover isolation, revoked tokens, provider errors, idempotent imports/playlists and failed-save recovery without Spotify credentials.

## Environment Variables
Copying `.env.example` is handled by setup. Local `DEBUG=True` enables a development-only secret fallback. Production requires `DEBUG=False`, a private `SECRET_KEY` of at least 32 characters and reviewed hosts/CORS/HTTPS. Optional Spotify client credentials stay server-side. `VITE_API_URL` is documented in `frontend/.env.example`. Firebase is not needed for the canonical account workflow.

## Project Structure
`frontend/`: UI and client state; `music/`: models, migrations, services, views and tests; `backend/`: Django configuration; `scripts/dev.py`: paired server lifecycle.

## Current Status / Limitations
Optional Spotify export/OAuth needs credential-backed verification and further service decomposition. Recommendations are heuristic metadata scoring, not a validated machine-learning model. No preview downloads are stored. Rate limits, production deployment and password reset remain explicit follow-up work; no performance gains are claimed.

See [AGENTS.md](AGENTS.md) and the GitHub readiness tracker before starting another improvement.
