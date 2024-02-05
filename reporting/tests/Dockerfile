FROM python:3.10

WORKDIR /km-reporting
COPY reporting/tests/requirements.txt ./
RUN pip install -r requirements.txt

COPY reporting/scenarios scenarios/
COPY reporting/tests tests/
COPY lib tests/lib/

ENTRYPOINT [ "bash", "tests/run_tests.sh" ]
