FROM scratch as tmp

WORKDIR /

COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock
COPY README.md README.md

FROM python:3.10

COPY --from=tmp / /

WORKDIR /
RUN pip install --no-cache-dir poetry==1.5.1 pytest
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --no-cache --extras api

COPY api extraction-service/api
COPY tests extraction-service/tests
WORKDIR /extraction-service

ENV PYTHONPATH=/extraction-service/api
CMD [ "pytest", "tests/tests.py" ]