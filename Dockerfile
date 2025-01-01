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

# FIXME: Build stuck here.
RUN poetry run prisma generate

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port (if needed)
EXPOSE 8000

# Run the application
CMD ["poetry", "run", "paperrec"]
