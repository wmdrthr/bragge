FROM python:3.8.5-slim as build

RUN apt-get update && apt-get install -y build-essential libpq-dev

RUN python3 -m venv /venv
COPY requirements.txt ./
RUN /venv/bin/pip install -r requirements.txt

FROM python:3.8.5-slim

RUN apt-get update && apt-get install -y libpq-dev
COPY --from=build /venv /venv

WORKDIR /app
COPY bragge/ ./bragge
COPY runner.py ./
COPY scrapy.cfg ./

CMD ["/venv/bin/python3", "runner.py"]

