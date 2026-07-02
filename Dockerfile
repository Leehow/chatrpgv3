FROM python:3.14-slim

WORKDIR /app
COPY . /app
ENV PYTHONPATH=/app/src
RUN python -m pip install --upgrade pip && python -m pip install ".[ingest,observability]"
CMD ["trpg", "version"]
