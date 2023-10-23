# Testrunner for TA1
`knowledge-middleware` Reporting generates an integration report by
standing up all of the relevant TA3 services with a Docker Compose
and trying to use a few requests through the relevant parts of the stack.

## Usage
- [Log in to GitHub Package Registry](https://github.com/DARPA-ASKEM/orchestration/blob/main/CONTRIBUTING.md#login-to-registry)
- Ensure your current directory is `./reporting`.
- Create `reporting/.env` based off `env.sample` and change variables as needed
  - Set `UPLOAD=TRUE`, `BUCKET`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY` IF you want the report uploaded
- Run `docker compose run --build tests`. Once the `tests` container completes, the report is done.
  - _Note:_ In order to run specific scenarios, you can specify them as follows: `docker compose run tests bash tests/run_tests.sh "<Scenario Directory>"` where the `<Scenario Directory>` the is full name of the directory containing all scenario files. You can specify as many as you would like in one run. _Example:_ `docker compose run tests bash tests/run_tests.sh "SIDARTHE Code" "SIDARTHE Equations" "SIR"`
- View results using `docker compose run --build --service-ports dashboard` (Assuming you haven't deleted any volumes)

Note: The services used in testing are not cleaned up following testing. When done with running tests,
be sure to shut down the services by running `docker compose down` to conserve your resources.

## Adding Scenarios
In the `scenarios` directory, you'll find two example scenarios: `12 Month Eval Scenario 3` and `SIDARTHE`. To add a new scenario, start by creating a directory with the name of your scenario. Within this directory, include a file named description.txt containing a detailed scenario description. Additionally, each scenario must have at least one of the following assets: a `paper.pdf`, the code (which can be specified by providing a GitHub repository URL in a `repo_url.txt` file or included as a `code.zip` file), and/or a `dataset.csv`. You can use the existing scenarios as examples while following these guidelines to prepare your new scenario for inclusion in the system.
