# Global ARG — available in all FROM lines
ARG PYTHON_VERSION=3.14.5

# Stage 1: build Vue frontend
FROM node:26-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: build the Python venv (compiler toolchain stays in this stage only)
FROM python:${PYTHON_VERSION}-slim AS python-builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY requirements.txt requirements-build.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-build.txt

COPY . .
ARG SETUPTOOLS_SCM_PRETEND_VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION}
RUN pip install --no-cache-dir --no-deps .

# Stage 3: runtime — no compiler toolchain, smaller attack surface
FROM python:${PYTHON_VERSION}-slim

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends arp-scan \
    && rm -rf /var/lib/apt/lists/*

COPY --from=python-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY . .
COPY --from=frontend-builder /frontend/dist ./frontend/dist

EXPOSE 8090

CMD ["python", "-m", "home_cinema_control.web.main"]
