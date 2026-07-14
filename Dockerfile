FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=run.py
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /app/instance

RUN printf '#!/bin/sh\nset -e\npython migrate_add_tags.py\npython seed.py\nexec gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 4 run:app\n' > /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 5000

CMD ["/entrypoint.sh"]