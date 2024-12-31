FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml poetry.lock ./

# Install poetry and dependencies
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root

# Copy environment file
COPY .env .env

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL="postgresql://paperrec:paperrec@db:5432/paperrec"

# Expose port (if needed)
EXPOSE 8000

# Run the application
CMD ["poetry", "run", "python", "main.py"]
