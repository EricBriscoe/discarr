FROM python:alpine

WORKDIR /app

# Set Python to run in unbuffered mode for better container logging
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create a volume mount point for persistent data
VOLUME ["/app/config"]

# Run the application
CMD ["python", "bot.py"]
