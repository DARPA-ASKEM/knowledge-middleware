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
In the `data` dir... **TODO: WE NEED TO FLESH THIS OUT**