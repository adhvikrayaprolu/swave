# Project
Discover music, express preferences and save personally relevant playlists.

# Architecture
frontend/src: React/Vite/shadcn, Zustand and API client; music: Django models and currently monolithic views; backend: settings/URLs; SQLite and iTunes/optional Spotify/Firebase integrations.

# Local Development
Create .venv, install requirements.txt, npm ci --prefix frontend and copy .env.example. Backend migrate/run and frontend npm run dev are documented separately; backend cannot start until settings syntax is repaired. make check PYTHON=/absolute/path/to/.venv/bin/python deliberately fails at this blocker.

# Validation
Canonical command: `make check`. See docs/engineering-control-plane.md for prerequisites and known gaps. A build with zero tests is not behavioral validation. Do not skip a failing check or claim hosted CI passed before a run exists.

# Frontend Rules
Reuse existing React design-system components and shadcn/ui where appropriate; use Figma MCP before substantial redesign. Preserve keyboard access and responsive layouts; test loading/error/empty states.

# Backend Rules
Preserve existing API behavior unless the selected issue explicitly changes it. Validate ownership, inputs and provider failures. Add rollback/permission tests before splitting responsibilities. Never print credentials or use real paid/cloud integrations in tests without explicit authorization.

# Testing Rules
Add meaningful regression tests for the selected workflow, including failure/authorization paths. Use fakes or local emulators; document remaining test gaps. Measure a baseline before any performance claim.

# GitHub Workflow
Read open GitHub issues as the work source. Branch from current main as codex/<issue>-<scope>; link the real issue in a draft PR, record validation and verification limits. Use Closes #N only when all criteria are met; issue closes on human merge, not when the draft opens. Never merge or push directly to main.

# Do Not
Do not commit secrets, migrate frameworks, change unrelated features, deploy, rotate credentials or mutate live cloud data. Do not treat unmerged local sprint branches as main. Before implementing overlapping work inspect the existing local branch listed in docs/engineering-control-plane.md and avoid duplicate PRs.

# Issue Selection Rules
1. Read the Portfolio readiness tracking meta issue; stop if complete.
2. Search open issues labelled automation:ready; exclude any blocked/human-review/do-not-touch issue.
3. Select P0, then P1, then P2; confirm all dependencies are closed and accepted. Within a priority choose foundations first, then oldest issue.
4. Choose one coherent issue; skip work already covered by an open PR.
5. If credentials/decisions/failed baseline block it, document the blocker and remove ready eligibility.
6. Implement, run canonical checks and issue-specific tests, open a linked draft PR. Never merge.
