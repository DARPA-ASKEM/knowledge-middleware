# Exctraction service

TA1 repository to interface with Terarium tools to interface with TA1 services.

## Goals

The extraction service will be hosted inside xDD to support extractions over non-open access documents: in this way, Terarium users will be able to work with models from non-public papers.

The extraction service will have several key endpoints:
- summarization/literature review
- extraction of a model
- profiling of a dataset
- model to dataset alignment suggestion

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


## License

[Apache License 2.0](LICENSE)
