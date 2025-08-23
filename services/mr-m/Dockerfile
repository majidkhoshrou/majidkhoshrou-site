# services/mr-m/Dockerfile
FROM python:3.12-slim

# Quality-of-life defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# For docker-compose healthcheck (curl)
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better caching
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r /app/requirements.txt

# Now copy the service code (context must be ./services/mr-m)
COPY . /app

EXPOSE 5000

# Local dev entrypoint
CMD ["python", "app.py"]
