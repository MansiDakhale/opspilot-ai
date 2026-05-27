FROM python:3.11-slim

# Keep Python output unbuffered (helps with logs)
ENV PYTHONUNBUFFERED=1

# Use a temporary working dir for dependency installation to leverage Docker cache
WORKDIR /app

# Install build deps required by some packages (psycopg, chromadb, etc.).
# Keep image lean by cleaning apt lists after install.
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
	   build-essential \
	   libpq-dev \
	   gcc \
	   git \
	   curl \
	&& rm -rf /var/lib/apt/lists/*

# Upgrade pip tooling before installing requirements
RUN pip install --upgrade pip setuptools wheel

# Copy only requirements first to leverage Docker layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user to run the app
RUN useradd --create-home appuser || true

# Copy application code and set ownership to non-root user
WORKDIR /app
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
