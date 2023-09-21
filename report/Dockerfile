FROM scratch as tmp

WORKDIR /

COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock
COPY README.md README.md

FROM python:3.10

COPY --from=tmp / /

WORKDIR /
RUN pip install --no-cache-dir poetry==1.5.1
RUN poetry config virtualenvs.create true && \
    poetry config virtualenvs.in-project true && \
    poetry install --no-root --no-cache

COPY api api
COPY lib lib
COPY worker worker
COPY tests tests
RUN poetry install

EXPOSE 8000
ENV PYTHONPATH=/
CMD [ "poetry", "run", "poe", "report" ]
