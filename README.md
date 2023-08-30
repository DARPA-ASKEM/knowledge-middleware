# Terarium Knowledge Middleware

[![codecov](https://codecov.io/github/DARPA-ASKEM/knowledge-middleware/branch/main/graph/badge.svg?token=XEARJHESHY)](https://codecov.io/github/DARPA-ASKEM/knowledge-middleware)

The Knowledge Middleware is designed to provide an intermediate job queue for management of long-running extraction and profiling tasks. It enables the Terarium HMI to request large knowledge discovery and curation tasks to be performed asynchronously, with robust error handling, and with customized ETL of backend service responses into Terarium specific schemas and specifications. It currently supports the following functions:

1. Equation to AMR: both LaTeX and MathML
2. Code to AMR: code snippets only
3. PDF to text: via Cosmos
4. PDF Extraction: via SKEMA
5. Data Card: via MIT
6. Model Card: via MIT
7. TODO: Model/Paper Linking


## Quickstart

1. Run `make init` which will create a stub `.env` file. 
2. Ensure that `.env` contains the correct endpoint and other information 
3. Run `make up`


## Testing
You can run the tests by initializing the environment:

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

### Testing Configuration

Set environment variable `MOCK_TA1` to `False` and adding the correct endpoints for TA1 will send real payloads to TA1 services and validate the results.

To add additional scenarios, create a new directory in `tests/scenarios`. The directory must contain a `config.yaml` where each tests you wish to be run
will be specified in `enabled`. 

The `.env` will be used to specify the `MOCK_TA1` setting as well as the appropriate endpoints and can be passed into the test suite with:
```
poetry shell && export $(cat .env | xargs) && pytest -s
```

Run `poetry run poe report`, to generate `tests/output/report.json` which contains the status of each scenario and operation.


## License

[Apache License 2.0](LICENSE)
