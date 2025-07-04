FROM python:3.11-slim

WORKDIR /app

# Set Python to run in unbuffered mode for better container logging
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# Install system dependencies required for discord.py and other packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create a volume mount point for persistent data
VOLUME ["/app/config"]

# Verify the installation and show debug info
RUN python -c "import discord; print(f'discord.py version: {discord.__version__}')" && \
    python -c "from discord.ext import commands; print('discord.ext.commands imported successfully')" && \
    ls -la /app/src/

# Run the application
CMD ["python", "bot.py"]
