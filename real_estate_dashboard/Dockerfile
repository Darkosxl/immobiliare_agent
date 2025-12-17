# NOTE: Run this build from the REPO ROOT: docker build -f real_estate_dashboard/Dockerfile .
FROM oven/bun:1

# Install Python, Git, and system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    gcc \
    portaudio19-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Setup Backend (VoiceAI) ---
# Create virtual environment OUTSIDE /app so volume mounts don't hide it
RUN python3 -m venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install (ARG busts cache to force fresh install)
ARG CACHEBUST=1
COPY real_estate_voiceai/requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app/real_estate_voiceai

# Copy backend code
COPY real_estate_voiceai/ .

# --- Setup Frontend (Dashboard) ---
WORKDIR /app/real_estate_dashboard

# Copy frontend dependencies
COPY real_estate_dashboard/package.json real_estate_dashboard/bun.lock ./
RUN bun install

# Copy frontend code
COPY real_estate_dashboard/ .

# Expose ports for both services
EXPOSE 5173
EXPOSE 8000

# Start dashboard in production mode
CMD ["bun", "run", "start"]
