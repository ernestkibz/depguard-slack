FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

ENV PORT=3000
EXPOSE 3000

CMD ["sh", "-c", "gunicorn slack_bot:flask_app --bind 0.0.0.0:${PORT:-3000} --timeout 180 --workers 1"]
