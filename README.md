# agent-testing

This repository is deliberately old. It contains a working web API built on the oldest Python,
framework and library versions that can still be installed and run on a current machine, along
with tests that confirm it works. It is a realistic target for upgrade testing of various sorts:
agent-driven dependency upgrades, Python version migrations, framework API migrations, and
tooling modernization.

The app is a small FastAPI book-catalog API pinned to the **first FastAPI release ever published
(0.1.0, December 8, 2018)**, running on **Python 3.8.10**, with every other dependency pinned to
its December 2018 version.

## Why Python 3.8

FastAPI 0.1.0 required Python 3.6 or newer. Of the interpreters available (3.8 and 3.9), 3.8 is
the oldest, so it was used. Everything works on 3.8, though a few pieces only just get by (see
[Known problems](#known-problems)). Python 3.8 reached end of life in October 2024.

## Stack

| Package | Pinned | Notes |
|---|---|---|
| Python | 3.8.10 | Oldest interpreter available here |
| fastapi | 0.1.0 | First public release; no top-level exports (`from fastapi.applications import FastAPI`) |
| starlette | 0.9.7 | |
| pydantic | 0.16 | Pre-1.0 API: `Schema`, `constr`, `Config.ignore_extra`, `@validator(whole=True)` |
| uvicorn | 0.3.22 | Requires uvloop, httptools, websockets |
| uvloop | 0.11.3 | Crashes on import under 3.8 (see below) |
| httptools | 0.0.11 | |
| h11 | 0.8.1 | |
| websockets | 7.0 | |
| click | 7.0 | |
| pytest | 4.0.2 | Needs `attrs==18.2.0` and `setuptools==40.6.3` to load |
| requests | 2.21.0 | Required by Starlette's `TestClient` |

Dev-only pins also include pluggy 0.8.0, py 1.7.0, more-itertools 4.3.0, six 1.12.0,
atomicwrites 1.2.1, urllib3 1.24.1, idna 2.8, chardet 3.0.4 and certifi 2018.11.29. See
`Pipfile` for the full list; `Pipfile.lock` records the exact resolved versions.

## What's in the repo

- `app/main.py` — a book-catalog API with create, read, update and delete endpoints, author
  filtering, pagination via a `Depends` class, validation and a startup hook. It deliberately uses
  APIs that later changed, which gives the upgrade something to work on:
  - FastAPI is imported from `fastapi.applications`, because 0.1.0 exported nothing at the top level.
  - `Depends`, `Path` and `Query` are imported from `fastapi.params`.
  - `HTTPException` comes from Starlette.
  - It uses pydantic's pre-1.0 `Schema`, `constr`, `Config.ignore_extra`,
    `@validator(whole=True)` and `.dict()`.
  - Startup uses `@app.on_event("startup")` (later deprecated in favor of lifespan handlers).
- `tests/test_main.py` — 9 pytest tests, which give developers a way to check that each upgrade
  step still works.
- `Pipfile` / `Pipfile.lock` — every version pinned exactly.
- `Dockerfile` / `.dockerignore` — container build for the app (see [Docker](#docker)).

## Setup

Current pipenv (2025.1 and later) cannot manage a Python 3.8 environment: it refuses to lock, and
its bundled pip requires Python 3.10+. The last pipenv release that supports 3.8 is **2024.4.1**.
Install it alongside your regular pipenv, for example:

```sh
pipx install --suffix @2024 "pipenv==2024.4.1"   # or: pip install "pipenv==2024.4.1" into any Python 3.8 venv
pipenv@2024 install --dev --python 3.8
```

## Run

```sh
pipenv@2024 run uvicorn app.main:app --loop asyncio   # --loop asyncio is required on 3.8
pipenv@2024 run pytest
```

Interactive docs: http://127.0.0.1:8000/docs

## Docker

```sh
docker build -t agent-testing:old .
docker run --rm -p 8000:8000 agent-testing:old
```

Then open http://127.0.0.1:8000/docs.

The Dockerfile is a two-stage build:

1. **Build stage** (`python:3.8.10-buster`): the full image includes gcc, which is needed to
   compile uvloop and httptools from source. It installs pipenv 2024.4.1, exports the runtime
   packages from `Pipfile.lock`, and installs them into a standalone venv at `/venv`.
2. **Runtime stage** (`python:3.8.10-slim-buster`): copies in only `/venv` and `app/`, then starts
   uvicorn with `--loop asyncio`.

The final image is about 220 MB and contains only the runtime packages: no pipenv, compiler, test
packages or tests. Debian Buster has been end of life since June 2024.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Service name and book count |
| GET | `/books?author=&skip=&limit=` | List books, optionally filtered by author, paginated |
| GET | `/books/{id}` | Get one book (404 if missing) |
| POST | `/books` | Create a book (rejects unknown fields; normalizes tags) |
| PUT | `/books/{id}` | Replace a book |
| DELETE | `/books/{id}` | Delete a book |

## Known problems

These came up while building the environment and are useful material for the upgrade demo.

1. **Modern pipenv can't handle Python 3.8.** pipenv 2026.x refuses to lock or install for a 3.8
   environment ("requires Python 3.11 or newer in the project virtualenv"). Use pipenv 2024.4.1,
   as described in [Setup](#setup).
2. **uvloop 0.11.3 crashes on Python 3.8.** It calls `sys.set_coroutine_wrapper`, which 3.8
   removed. uvicorn 0.3.22 still requires uvloop to be installed, so the server must be run with
   `--loop asyncio` to avoid importing it.
3. **pytest 4.0.2 needs old helpers.** It only loads with `attrs==18.2.0` (newer attrs dropped the
   `convert` argument) and with `setuptools==40.6.3` pinned in the environment. Newer setuptools
   vendors typeguard, which registers a pytest plugin that pytest 4.0 can't load.
4. **pydantic 0.16 ignores `Config.anystr_strip_whitespace` for fields declared with
   `Schema(min_length=...)`**, because the constraint creates a constrained string type that
   overrides the config. The app uses `constr(strip_whitespace=True, ...)` instead.
5. **FastAPI 0.1.0 does not pin its dependencies** (`starlette>=0.9.7`, `pydantic>=0.16`). An
   unpinned install pulls in current Starlette and pydantic v2, which break it immediately. Every
   transitive dependency is therefore pinned in the `Pipfile`.

## Upgrade path notes

Upgrading to pydantic v2 and FastAPI 0.100+ also requires moving off Python 3.8, since current
FastAPI no longer supports it. Expected migration points include:

- `from fastapi.applications import FastAPI` → `from fastapi import FastAPI`
- `Schema` → `Field`; `constr(...)` → `Annotated[str, StringConstraints(...)]`
- `Config.ignore_extra = False` → `model_config = ConfigDict(extra="forbid")`
- `@validator(whole=True)` → `@field_validator`
- `.dict()` → `.model_dump()`
- `@app.on_event("startup")` → lifespan context manager
- Starlette `TestClient` moves from requests to httpx
