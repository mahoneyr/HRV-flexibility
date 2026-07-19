FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies that might be needed
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY data/ ./data/
COPY templates/ ./templates/

# Create necessary directories with proper permissions
RUN mkdir -p /app/uploads /app/static /app/data && \
    chmod -R 755 /app

# Create a non-root user (optional but recommended)
# Commented out for now since you're using it privately
# RUN useradd -m -u 1000 appuser && \
#     chown -R appuser:appuser /app
# USER appuser

# Expose port
EXPOSE 5000

# Health check hits the lightweight /health probe, not the full history page
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health').read()" || exit 1

# One worker keeps the in-memory history cache and user-profile state coherent;
# threads keep the app responsive while a long analysis runs.
CMD ["gunicorn", "--workers", "1", "--threads", "4", "--timeout", "120", "--bind", "0.0.0.0:5000", "app:app"]
