# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies required for building some python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Create python wheels to avoid recompiling in the final image
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Create a non-root user for security
RUN useradd -m -r appuser

# Copy wheels and requirements from the builder stage
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Install the dependencies from the wheels
RUN pip install --no-cache /wheels/*

# Copy the rest of the application code
COPY . .

# Change ownership to the non-root user
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Default command (Web UI on port 8080 to match docker-compose.yml)
CMD ["python", "main.py", "--web", "8080"]
