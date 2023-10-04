FROM python:3.10

WORKDIR /simulation-integration
COPY tests/requirements.txt ./
RUN pip install -r requirements.txt

COPY scenarios scenarios/
COPY tests tests/
COPY data data/

CMD [ "bash", "tests/run_tests.sh" ]
