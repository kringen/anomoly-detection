FROM python:3.8-slim-buster

USER 0

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

USER 1001

CMD ["python3", "telemetryreceiver.py"]