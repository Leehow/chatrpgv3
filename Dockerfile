FROM python:3.14-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*
COPY . /app
ENV PYTHONPATH=/app/src
RUN python -m pip install --upgrade pip && python -m pip install ".[ingest,observability]"
CMD ["trpg", "version"]
