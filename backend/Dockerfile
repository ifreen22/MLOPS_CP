FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (Prisma needs Node.js, and some python packages need build-essential)
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libpq-dev \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --upgrade pip
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch
RUN pip install --index-url https://pypi.org/simple -r requirements.txt --no-cache-dir

COPY . .

# Generate Prisma client
RUN prisma generate

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Start the FastAPI application
CMD ["sh", "-c", "prisma db push && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
