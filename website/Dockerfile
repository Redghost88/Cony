FROM python:3.12-slim

RUN pip install --upgrade pip

RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://get.docker.com -o get-docker.sh \
    && sh get-docker.sh \
    && rm get-docker.sh \
    && apt-get remove -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r groupDjango && useradd -r -g groupDjango userDjango
ARG DOCKER_GID=999
RUN if getent group ${DOCKER_GID} >/dev/null 2>&1; then \
      usermod -aG ${DOCKER_GID} userDjango; \
    else \
      groupadd -g ${DOCKER_GID} dockerhost && usermod -aG ${DOCKER_GID} userDjango; \
    fi

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R userDjango:groupDjango /app

USER userDjango