# Swave

Swipe-based music discovery app from **CS 222 (UIUC)**. React + TypeScript frontend, Django REST API backend, iTunes search, optional Spotify connect, JWT auth, demo mode.

**Repo:** https://github.com/adhvikrayaprolu/swave

## Features

- Register / login with JWT
- **Demo mode** — explore without an account
- Swipe feed for music discovery
- User profiles, likes, playlists
- iTunes preview search (no API key required)
- Optional Spotify OAuth for library / playlist export

## Project structure

```text
swave/
├── backend/          # Django project settings & URLs
├── music/            # Main Django app (models, views, Spotify/iTunes)
├── frontend/         # React + Vite + Tailwind UI
├── manage.py
├── requirements.txt
└── .env.example
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- npm

## Setup

```bash
cd swave
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
```

Frontend:

```bash
cd frontend
npm install
```

## Run locally

Backend (port **8000**):

```bash
source .venv/bin/activate
python manage.py runserver 127.0.0.1:8000
```

Frontend (port **8080**):

```bash
cd frontend
npm run dev
```

Open **http://127.0.0.1:8080** — use **Try Demo Mode** or register a new account.

API base URL is `http://localhost:8000` (see `frontend/src/api/client.ts`).

## Environment

Copy `.env.example` to `.env` at the repo root. Spotify and Firebase vars are optional for core swipe + iTunes demo flows.

## Tech stack

- **Frontend:** React 18, TypeScript, Vite, Tailwind, shadcn/ui, Zustand, TanStack Query
- **Backend:** Django 5, DRF, Simple JWT, SQLite (local)
- **Auth:** JWT + optional Firebase Google sign-in

## Original course repo

Forked from CS 222 team project `fa25-fa25-team045` (GitHub Classroom).
