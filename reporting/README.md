# Testrunner for TA1
`knowledge-middleware` Reporting generates an integration report by
standing up all of the relevant TA3 services with a Docker Compose
and trying to use a few requests through the relevant parts of the stack.

## Usage
Ensure your current directory is `./reporting`.

Run `docker compose run --build tests`. Once the `tests` container completes, the report is done.

If run with UPLOAD=TRUE as an environment variable, the report will be uploaded to S3.
Otherwise, the report is output as part of the `tests` container's logs.

The logs can be viewed by running `docker compose logs -f tests`.

Note: The services used in testing are not cleaned up following testing. When done with running tests,
be sure to shut down the services by running `docker compose down` to conserve your resources.

See `env.sample` to see which environment variables are used by the test/report runner. 
You can create a `.env` envfile based on sample if you want to override the defaults.

## Adding Scenarios
In the `scenarios` directory, you'll find two example scenarios: `12 Month Eval Scenario 3` and `SIDARTHE`. To add a new scenario, start by creating a directory with the name of your scenario. Within this directory, include a file named description.txt containing a detailed scenario description. Additionally, each scenario must have at least one of the following assets: a `paper.pdf`, the code (which can be specified by providing a GitHub repository URL in a `repo_url.txt` file or included as a `code.zip` file), and/or a `dataset.csv`. You can use the existing scenarios as examples while following these guidelines to prepare your new scenario for inclusion in the system.
