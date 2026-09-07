FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY evalguard ./evalguard
COPY examples ./examples

RUN pip install --no-cache-dir .

RUN mkdir -p /app/reports

ENTRYPOINT ["evalguard"]
CMD ["run", "examples/config.yaml"]
