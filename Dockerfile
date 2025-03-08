FROM nikolaik/python-nodejs:python3.13-nodejs23

WORKDIR /app

# Copy all code
COPY . .

# Install Python dependencies with Poetry
RUN poetry config virtualenvs.in-project true
RUN poetry install

# Install Node.js dependencies
RUN npm install

# Build frontend assets
RUN npm run build

ENV FLASK_APP=app.py

EXPOSE 5000