# Deliberately old: matches the Python 3.8.10 interpreter this app was built against.

# --- Build stage -------------------------------------------------------------
# The full Debian Buster image includes gcc, needed to compile the uvloop and
# httptools source distributions.
FROM python:3.8.10-buster AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# pipenv 2024.4.1 is the last release that supports Python 3.8.
RUN pip install "pipenv==2024.4.1"

WORKDIR /app
COPY Pipfile Pipfile.lock ./

# Install runtime dependencies from the lock file into a standalone venv.
RUN python -m venv /venv \
 && pipenv requirements > requirements.txt \
 && /venv/bin/pip install -r requirements.txt

# --- Runtime stage -----------------------------------------------------------
FROM python:3.8.10-slim-buster

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/venv/bin:$PATH"

COPY --from=build /venv /venv

WORKDIR /app
COPY app ./app

EXPOSE 8000

# --loop asyncio is required: uvloop 0.11.3 crashes on import under Python 3.8.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "asyncio"]
