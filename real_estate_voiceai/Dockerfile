# NOTE: Run this build from the REPO ROOT: docker build -f real_estate_voiceai/Dockerfile .
# Stage 1: Build Dashboard
FROM oven/bun:1 as frontend-builder
WORKDIR /app/dashboard
# Copy dashboard files relative to the build context (Repo Root)
COPY real_estate_dashboard/package.json real_estate_dashboard/bun.lock ./
RUN bun install
COPY real_estate_dashboard .
RUN bun run build

# Stage 2: Backend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies for PyAudio
RUN apt-get update && apt-get install -y \
    gcc \
    portaudio19-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements relative to the build context (Repo Root)
COPY real_estate_voiceai/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY real_estate_voiceai .

# Copy built frontend assets
COPY --from=frontend-builder /app/dashboard/dist /app/static

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "fastapi_endpoint.py"]
