FROM scratch as tmp

WORKDIR /

COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock
COPY api api
COPY README.md README.md

FROM python:3.10

COPY --from=tmp / /

WORKDIR /
RUN pip install --no-cache-dir poetry==1.5.1
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --no-cache

WORKDIR /api

EXPOSE 8000
CMD [ "uvicorn", "server:app", "--reload", "--host", "0.0.0.0", "--port", "8000" ]
