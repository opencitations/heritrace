FROM nikolaik/python-nodejs:python3.13-nodejs23

WORKDIR /app

# Copia tutto il codice
COPY . .

# Installa le dipendenze Python con Poetry
RUN poetry install

# Installa le dipendenze Node.js
RUN npm install

# Build degli asset frontend
RUN npm run build

ENV FLASK_APP=app.py

EXPOSE 5000