# Swave
Discover music previews, save the songs you like, and build a persistent daily playlist.

## What it does
Register or sign in with email, search for an artist or song, preview music, swipe like/pass, and generate a playlist from today's likes. Accounts have separate histories; failed saves keep the card available for retry. A clearly labeled demo uses simulated data without an account.

## Architecture and tech stack
React/TypeScript, Vite, shadcn/Radix components, Zustand and TanStack Query sit above Django REST Framework and SQLite. JWT authenticates account APIs. `music/account_views.py` handles accounts, `catalog_views.py` handles catalog APIs, `services.py` owns transactional swipes and playlist creation, and `spotify_views.py` contains the optional Spotify integration. Spotify recommendations are exploratory metadata scoring, not a trained recommendation model.

## Quick start
Requires Python 3.13, Node 22.23+ and npm. From the repository root:

```sh
make setup
make dev
```
Open http://127.0.0.1:8080. Startup applies migrations and seeds four metadata-only sample tracks. Use Search to import actual iTunes previews; availability depends on the provider. SQLite persists locally in ignored `db.sqlite3`. Ctrl-C stops both servers. `make setup` creates `.env` from `.env.example` without overwriting an existing file.

## Configuration
The local `.env` explicitly enables DEBUG. Deployment requires DEBUG=False and a private SECRET_KEY of at least 32 characters, plus appropriate hosts, HTTPS, secure cookies and CORS origins. Never deploy the local fallback key. The frontend defaults to http://127.0.0.1:8000; override VITE_API_URL using `frontend/.env.example` when needed.

Spotify client ID/secret/redirect URI are optional, server-side settings. OAuth state is checked and consumed once; external failures return safe errors. The Spotify screen remains an experimental integration requiring a configured provider app and approved scopes. Firebase is not required for the canonical account workflow.

## Testing
```sh
make check
```
Backend tests cover account isolation, authentication, revoked refresh tokens, validation, idempotent playlists/search import, catalog exhaustion and provider failures. Frontend tests cover failed-save retries, refill failures and registration feedback. CI runs tests, type checking, lint and production build, without live provider credentials.

## API and data model
`User` → `SwipeEvent` → `Track`; `User` → dated `Playlist` → ordered items. Playlist rebuilding is transactional and deduplicates repeated likes.

- `/auth/register/`, `/auth/login/`, `/auth/refresh/`, `/auth/logout/`
- `/auth/profile/`, `/api/feed/next`, `/catalog/search/`
- `/api/event/swipe/`, `/likes/`, `/playlist/daily/build/`, `/playlist/daily/`

Private endpoints require a Bearer token. Provider search is bounded to 100 characters and ten results, with a ten-second timeout.

## Design decisions and limitations
SQLite and a single Django service keep local setup small. Music previews stay on provider servers; there is no audio download/storage. Local JWTs use browser storage, so an HTTPS deployment also needs a threat review and XSS defenses. The Spotify module still needs further decomposition and credential-backed end-to-end verification. Rate limits, production deployment, password reset and cross-timezone playlist semantics remain follow-up work. No claims are made about recommendation quality or performance gains.
