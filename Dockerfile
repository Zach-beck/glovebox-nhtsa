FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

ENV GLOVEBOX_CACHE_DIR=/tmp/glovebox-cache
ENV GLOVEBOX_DATA_DIR=/tmp/glovebox-data
USER nobody
ENTRYPOINT ["glovebox-mcp"]
