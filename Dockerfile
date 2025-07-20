FROM nikolaik/python-nodejs:python3.13-nodejs23-slim

WORKDIR /app

# Install Redis
RUN apt-get update && apt-get install -y redis-server && \
    rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /app/heritrace /app/babel

# Copy necessary files for Poetry to install the package
COPY pyproject.toml poetry.toml poetry.lock README.md ./
COPY heritrace ./heritrace

# Copy configuration files and babel
COPY config.example.py ./config.py
COPY shacl.ttl ./shacl.ttl
COPY display_rules.yaml ./display_rules.yaml
COPY babel ./babel

# Install Python dependencies with Poetry (main dependencies only)
RUN poetry config virtualenvs.in-project true
RUN poetry install --only main

# Install Node.js dependencies
COPY package.json package-lock.json ./
RUN npm install

# Copy webpack config and app entry point
COPY webpack.config.js ./
COPY app.py ./

# Build frontend assets
RUN npm run build

# Create data directory for Redis
RUN mkdir -p /data

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Starting Redis..."\n\
redis-server --daemonize yes --bind 0.0.0.0 --port 6379 --dir /data --save 900 1 --save 300 10 --save 60 10000 --protected-mode no\n\
echo "Waiting for Redis to be ready..."\n\
until redis-cli ping > /dev/null 2>&1; do\n\
  echo "Waiting for Redis..."\n\
  sleep 1\n\
done\n\
echo "Redis is ready"\n\
echo "Starting Flask app..."\n\
\n\
# Trap SIGTERM and SIGINT to save Redis data before shutdown\n\
cleanup() {\n\
  echo "Shutting down gracefully..."\n\
  echo "Saving Redis data..."\n\
  redis-cli BGSAVE\n\
  # Wait for background save to complete\n\
  while [ "$(redis-cli LASTSAVE)" = "$(redis-cli LASTSAVE)" ]; do\n\
    sleep 0.1\n\
  done\n\
  echo "Redis data saved"\n\
  redis-cli SHUTDOWN\n\
  exit 0\n\
}\n\
\n\
trap cleanup SIGTERM SIGINT\n\
\n\
exec "$@" &\n\
wait $!' > /app/start.sh && chmod +x /app/start.sh

ENV FLASK_APP=app.py

EXPOSE 5000

CMD ["/app/start.sh", "/app/.venv/bin/python", "app.py"]