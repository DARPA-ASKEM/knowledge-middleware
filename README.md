# Terarium Knowledge Middleware

[![codecov](https://codecov.io/github/DARPA-ASKEM/knowledge-middleware/branch/main/graph/badge.svg?token=XEARJHESHY)](https://codecov.io/github/DARPA-ASKEM/knowledge-middleware)

The Knowledge Middleware (`KM`) is designed to provide an intermediate job queue for management of long-running extraction and profiling tasks. It enables the Terarium HMI to request large knowledge discovery and curation tasks to be performed asynchronously, with robust error handling, and with customized ETL of backend service responses into Terarium specific schemas and specifications. It currently supports the following functions:

1. Equation to AMR: both LaTeX and MathML
2. Code to AMR: code snippets only
3. PDF Extraction: via Cosmos
4. Variable Extraction: via SKEMA
5. Data Card: via MIT
6. Model Card: via MIT
7. Model/Paper Linking: via SKEMA

## Contents

1. [Quickstart](#quickstart)
2. [Integration Testing](#integration-testing)
    - [Adding Test Scenarios](#adding-test-scenarios)
3. [Unit Testing](#unit-testing)
    - [Unit Testing Configuration](#unit-testing-configuration)

## Quickstart

1. Run `make init` which will create a stub `.env` file. 
2. Ensure that `.env` contains the correct endpoint and other information 
3. You can now run the tests or reports using the information below.
4. You can also run `KM` with `make up`

## Integration Testing
`KM` provides a TA1 integration test harness that powers the [ASKEM Integration Dashboard](https://integration-dashboard.terarium.ai). It makes it easy to add new test cases and scenarios which will automatically be evaluated and surfaced in the dashboard. Additionally, the `KM` test harness can be run offline for development purposes. Running the `KM`` test harness requires docker compose. Please see [reporting/README.md](./reporting/README.md) for more information on how to run the test harness locally.

### Adding Test Scenarios
Scenarios should be added in the `reporting/scenarios` directory. When you create a new directory in `reporting/scenarios` the directory name constitutes the new scenario's name.

In the `scenarios` directory, you'll find multiple example scenarios. To add a new scenario, start by creating a directory with the name of your scenario. Within this directory, include a file named `description.txt` containing a detailed scenario description. Additionally, each scenario must have at least one of the following assets: 

* `paper.pdf`: the paper to extract 
* `code.zip`: the zipfile of a code repo
* `dyanmics.*`: a file that contains only code representing the core dynamics of the model. The file should have the correct programming language extension; e.g. `dynamics.py`
* `equations.latex.txt`: a set of equations representing the model dynamics
* `dataset.csv`: a dataset to profile

> **Note**: each scenario should ONLY have one of `[code.zip, dynamics.*, equations.latex.txt]`. This is what will be used to generate a model.

You can use the existing scenarios as examples while following these guidelines to prepare your new scenario for inclusion in the system.


## Unit Testing
`KM` also has an extensive unit testing suite. You can run the tests by initializing the environment:

```
poetry install
poetry shell
```

Then from the top of the repo run:

```
pytest tests
```

You can generate a coverage report with:

```
pytest --cov . tests
```

> You can add the flag ` --cov-report html` to generate an HTML report

### Unit Testing Configuration
*note: the live option will be removed soon*

Set environment variable `MOCK_TA1` to `False` and adding the correct endpoints for TA1 will send real payloads to TA1 services and validate the results.

To add additional scenarios, create a new directory in `tests/scenarios`. The directory must contain a `config.yaml` where each tests you wish to be run
will be specified in `enabled`. 

The `.env` will be used to specify the `MOCK_TA1` setting as well as the appropriate endpoints and can be passed into the test suite with:
```
poetry shell && export $(cat .env | xargs) && pytest -s
```

Run `poetry run poe report`, to generate `tests/output/report.json` which contains the status of each scenario and operation.

Once the report has been generated, run `poetry run streamlit run tests/Home.py` to run the web interface into the test suite, which will be available at `http://localhost:8501`.

> Note: if the tests fail, `poetry poe` will exit and not generate a report. To work around this, run `pytest --json-report --json-report-file=tests/output/tests.json` then `python tests/report.py` manually.

### Adding Test Scenarios

Test scenarious can be added to `tests/scenarios`. Each `scenario` should have it's own directory and must contain a `config.yaml` file which provides a name for the scenario and indicates which test(s) should be run. See `scenarios/basic` for a boilerplate that runs all test cases.

The files required to run each scenario are defined in `tests/resources.yaml`. Note that some files are considered `optional`: e.g. `ground_truth_model_card`.


## License

[Apache License 2.0](LICENSE)
