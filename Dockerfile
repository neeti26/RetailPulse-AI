# RetailPulse AI — Docker Image
# Multi-stage build for a lean production image

FROM python:3.11-slim AS base

# Install Node.js (required for MongoDB MCP Server via npx)
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Pre-install the MongoDB MCP Server globally to avoid npx download at runtime
RUN npm install -g mongodb-mcp-server

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 retailpulse && chown -R retailpulse:retailpulse /app
USER retailpulse

# Expose Gradio port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

# Default: run the web UI
CMD ["python", "app.py"]
