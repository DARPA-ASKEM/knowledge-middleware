# Terarium TA1 Middleware Service

[![codecov](https://codecov.io/github/DARPA-ASKEM/TA1-Service/branch/main/graph/badge.svg?token=XEARJHESHY)](https://codecov.io/github/DARPA-ASKEM/TA1-Service)

The TA1 Middleware Service is designed to provide an intermediate job queue for management of long running TA1 extraction and profiling tasks. It enables the Terarium HMI to request TA1 tasks to be performed asynchronously, with robust error handling, and with customized ETL of TA1 responses into Terarium specific schemas and specifications. It currently supports the following functions:

1. Equation to AMR: both LaTeX and MathML
2. Code to AMR: code snippets only
3. PDF to text: via Cosmos
4. PDF Extraction: via SKEMA
5. Data Card: via MIT
6. Model Card: via MIT
7. TODO: Model/Paper Linking


## Quickstart

1. Run `make init` which will create a stub `api.env` file. 
2. Ensure that `api.env` contains the correct endpoint and other information 
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

To modify your test configuration, edit the `tests/conftest.py` file. In particular note that setting `LIVE` to `TRUE` and adding the correct endpoints for TA1 will send real payloads to TA1 services and validate the results.

## License

[Apache License 2.0](LICENSE)