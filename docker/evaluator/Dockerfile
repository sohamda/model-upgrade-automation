FROM python:3.11-slim

WORKDIR /app

COPY docker/evaluator/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY src /app/src
COPY config /app/config
COPY tests/fixtures /app/tests/fixtures
COPY docker/evaluator/entrypoint.py /app/entrypoint.py

ENTRYPOINT ["python", "/app/entrypoint.py"]