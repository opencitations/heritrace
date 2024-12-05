FROM nikolaik/python-nodejs:python3.13-nodejs23

WORKDIR /app

COPY . .

RUN python3 -m pip install --user pipx
RUN python3 -m pipx ensurepath
RUN python3 -m pipx install poetry
RUN poetry install

RUN npm install
RUN npm run build

ENV FLASK_APP=app.py

EXPOSE 5000