FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# uWSGI збирається з вихідного коду, тому потрібен компілятор
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# компілятор після збірки uWSGI не потрібен
RUN apt-get purge -y --auto-remove gcc libc6-dev

COPY . .

# uWSGI слухає порт 8085 за протоколом uwsgi; запити передає nginx
CMD ["uwsgi", "--ini", "bottle.ini"]
