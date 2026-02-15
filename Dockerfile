# Use a lightweight Python base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app code
COPY . .

# Create directory for plots (Fixed: used -p instead of -path)
RUN mkdir -p static

# Expose the web port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
