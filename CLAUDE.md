# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Autoplex is a FastAPI-based web application and CLI tool for managing Plex music libraries. It helps users identify and remove duplicate tracks from their Plex music libraries. Users authenticate via Plex OAuth, sync their server/library metadata, and browse duplicate tracks with options to flag them for deletion.

## Architectural Notes (Planned Changes)

This project is mid-transition. Key planned work:

- **Replace Celery + Redis with APScheduler** (in-process, PostgreSQL-backed job store) to match tgfp-web's architecture. This eliminates the need for Redis and a separate Celery worker process.
- **Align architecture with tgfp-web** (`/Users/johnsturgeon/Code/tgfp-web`) as the reference project for patterns, deployment, and structure.
- **Refine deployment** with updated instructions and Docker-based workflow (currently uses bare-metal Debian 12 + systemd).

## Development Environment Setup

1. **Create environment configuration:**
   Copy `app/sample.env` to `app/.env` and fill in values.

2. **Install dependencies:**
   ```bash
   scripts/create_dev_env.sh
   ```
   Uses `uv` for Python package management.

3. **Prerequisites:**
   - Python >= 3.11
   - PostgreSQL
   - Redis (currently required for Celery; will be removed after APScheduler migration)

4. **Run the application:**
   ```bash
   cd app
   uvicorn main:app --port 6701
   ```
   In development (`ENVIRONMENT=development`), auto-reload is enabled.

5. **Start Celery worker** (currently required):
   ```bash
   cd app
   celery --app=main.celery_app worker --concurrency=1
   ```

## Common Commands

### Testing and Linting

```bash
# Run all tests and linters
./test_and_lint.sh

# Individual commands:
pytest
pylint $(git ls-files '*.py')
```

### Deployment (Current - Debian 12)

```bash
scripts/deploy.sh
```

Targets bare Debian 12 LXC environments. Installs to `/opt/autoplex`. Optionally uses Infisical for secrets management.

## Architecture

### Core Components

**FastAPI Application (`app/main.py`):**
- Main entry point with routes and Celery configuration
- Session-based auth via Plex OAuth (Starlette SessionMiddleware)
- Jinja2 template rendering

**Database Layer (`app/db/`):**
- SQLModel ORM over PostgreSQL (`postgresql+psycopg2`)
- `database.py`: Engine creation, table auto-creation via `SQLModel.metadata.create_all()`

**Models (`app/db/models.py`):**
- `PlexUser`: Authenticated user with auth token
- `PlexServer`: User's Plex media servers
- `PlexLibrary`: Music library sections on a server
- `PlexTrack`: Individual tracks with `hash_value` for dedup and `flagged_for_deletion` flag
- `Preference`: Key-value store for user settings and sync status

**Background Tasks (currently Celery + Redis):**
- Single task: `sync_servers_for_user_uuid()` - syncs Plex server/library/track data into PostgreSQL
- Redis as broker and result backend
- systemd services: `autoplex.service` (web) + `celery.service` (worker)

**Plex Integration (`app/plex/api.py`):**
- PIN-based OAuth flow for authentication
- Server/library/track listing via PlexAPI
- Direct Plex server connection for track metadata

**Auth Router (`app/routers/auth.py`):**
- Plex OAuth flow (PIN creation, callback, token exchange)
- Cookie-based session persistence (`saved_user_uuid`)

**CLI Tool (`deduplex.py`):**
- Standalone duplicate finder with interactive TUI (uses `rich`)
- Direct Plex server connection (no web UI needed)
- Dedup via hash: `title-artist-album-duration`

### Key Workflows

**User Syncs Library:**
1. User hits `/sync` endpoint
2. Celery task `sync_servers_for_user_uuid.delay()` fires
3. Worker calls `PlexUser.sync_servers_with_db()` which syncs servers -> libraries -> tracks
4. Progress updates stored in `Preference` table, polled via `/sync_status`

**Duplicate Detection:**
1. Tracks grouped by `hash_value` (composite of title-artist-album-duration)
2. Groups with count > 1 displayed on `/duplicates` page
3. User can flag individual tracks for deletion via `/toggle_select_track/{rating_key}`

## Configuration

All configuration via environment variables (see `app/sample.env`):
- `AUTOPLEX_HOST`, `AUTOPLEX_PORT`: Server binding
- `POSTGRESQL_HOST`, `POSTGRESQL_USERNAME`, `POSTGRESQL_PASSWORD`: Database
- `REDIS_URL`: Celery broker (will be removed post-migration)
- `SESSION_SECRET_KEY`: Session middleware secret
- `ENVIRONMENT`: `production` or `development`
- `APP_CLIENT_ID`, `APP_PRODUCT_NAME`: Plex app identification
- `PLEX_AUTH_URL`, `PLEX_PIN_URL`, `PLEX_USER_URL`: Plex API endpoints

## Important Notes

- **Authentication:** Plex OAuth only. Session stores `user_uuid`.
- **Duplicate hashing:** `hash_value` = `title-artist-album-duration` composite. Stored on `PlexTrack`.
- **Single Celery task:** Only one task exists (`sync_servers_for_user_uuid`), making migration to APScheduler straightforward.
- **Reference project:** tgfp-web at `/Users/johnsturgeon/Code/tgfp-web` is the architectural target for APScheduler patterns, Docker deployment, and project structure.
