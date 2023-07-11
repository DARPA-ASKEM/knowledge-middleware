FROM scratch as tmp

WORKDIR /

COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock
COPY workers workers
COPY README.md README.md

FROM python:3.10

COPY --from=tmp / /

WORKDIR /
RUN pip install --no-cache-dir poetry==1.5.1
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --no-cache

ENV REDIS_HOST redis
ENV REDIS_PORT 6379

WORKDIR /workers
CMD rq worker --url redis://$REDIS_HOST:$REDIS_PORT high default low