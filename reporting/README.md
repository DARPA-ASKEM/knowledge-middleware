# Testrunner for TA1
`knowledge-middleware` Reporting generates an integration report by
standing up all of the relevant TA3 services with a Docker Compose
and trying to use a few requests through the relevant parts of the stack.

## Usage
- Ensure your current directory is `./reporting`.
- Create `reporting/.env` based off `env.sample` and change variables as needed
  - Set `UPLOAD=TRUE`, `BUCKET`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY` IF you want the report uploaded
- Run `docker compose run --build tests`. Once the `tests` container completes, the report is done.
  - View the `tests` container's logs to see the report IF you chose not to upload to S3
    - Use command `docker compose logs -f tests` to view

Note: The services used in testing are not cleaned up following testing. When done with running tests,
be sure to shut down the services by running `docker compose down` to conserve your resources.

## Adding Scenarios
In the `data` dir... **TODO: WE NEED TO FLESH THIS OUT**