FROM nikolaik/python-nodejs:python3.13-nodejs23-slim

WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/heritrace /app/resources /app/babel

# Copy necessary files for Poetry to install the package
COPY pyproject.toml poetry.toml poetry.lock README.md ./
COPY heritrace ./heritrace

# Copy configuration files and resources
COPY config.example.py ./config.py
COPY resources ./resources
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
# We'll run this at runtime via the command

ENV FLASK_APP=app.py

EXPOSE 5000