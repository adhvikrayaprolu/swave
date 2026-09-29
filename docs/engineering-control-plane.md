# Engineering control plane

Discover music, express preferences and save personally relevant playlists.

## Setup and validation
Create .venv, install requirements.txt, npm ci --prefix frontend and copy .env.example. Backend migrate/run and frontend npm run dev are documented separately; backend cannot start until settings syntax is repaired. make check PYTHON=/absolute/path/to/.venv/bin/python deliberately fails at this blocker.

## Verified state
Published main audit SHA: `fff449d9c730a8148113447884f579afb66aa2d8`. No root AGENTS.md, issues or PRs existed at this audit. No existing Actions pipeline or meaningful behavior test suite in published main.

## Unmerged work
Earlier local branch `codex/swave-runtime-security-foundation` at `66cd66ba788ca09b61296003fba83eb1fe3b0921` has tested improvements, but is not hosted or merged. Review/reuse it before reimplementing. Its reported checks are not checks of this control-plane branch.

## Backlog and stop rule
Use GitHub issues after publication; local draft identifiers must never be treated as GitHub issue numbers. Portfolio tracking covers core flows, safe configuration, meaningful tests, green PR CI, reproducible setup and concise demo documentation. Stop after the tracker is complete; no speculative features.

## Queue
`is:issue is:open label:"automation:ready" sort:updated-asc` scoped to this repository. Apply priority and dependency checks from AGENTS.md.
