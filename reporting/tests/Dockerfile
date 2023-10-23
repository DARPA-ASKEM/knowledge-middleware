FROM python:3.10

WORKDIR /km-reporting
COPY tests/requirements.txt ./
RUN pip install -r requirements.txt

COPY scenarios scenarios/
COPY tests tests/

ENTRYPOINT [ "bash", "tests/run_tests.sh" ]
