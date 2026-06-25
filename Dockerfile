# syntax=docker/dockerfile:1.7

# Global ARG — available in all FROM lines
ARG PYTHON_VERSION=3.14.6

# Stage 1: build Vue frontend
FROM node:26.3.1-trixie-slim AS frontend-builder

WORKDIR /frontend

COPY frontend/package*.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

COPY frontend/ ./
RUN npm run build


# Stage 2: build the Python venv
FROM python:${PYTHON_VERSION}-slim-trixie AS python-builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY requirements.txt requirements-build.txt ./

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-build.txt

# Important: do not copy the whole repo here.
# Frontend changes should not invalidate Python packaging.
COPY pyproject.toml ./
COPY README.md ./
COPY src/ ./src/

ARG SETUPTOOLS_SCM_PRETEND_VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION}

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-deps .


# Stage 3: runtime — no compiler toolchain, smaller attack surface
FROM python:${PYTHON_VERSION}-slim-trixie

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends arp-scan \
    && rm -rf /var/lib/apt/lists/*

COPY --from=python-builder /opt/venv /opt/venv

WORKDIR /app

# Runtime only needs the built frontend assets.
COPY --from=frontend-builder /frontend/dist ./frontend/dist

EXPOSE 8090

CMD ["python", "-m", "home_cinema_control.web.main"]