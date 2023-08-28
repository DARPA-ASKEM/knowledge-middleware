import requests
from jsonschema import validate, ValidationError
from collections import defaultdict
from os import listdir

import yaml

def get_parameterizations():
    selections = defaultdict(list)
    for pick in listdir("tests/scenarios"):
        with open(f"tests/scenarios/{pick}/config.yaml") as file:
            config = yaml.load(file, yaml.CLoader)
            for selection in config["enabled"]:
                selections[selection].append(pick) 
    return selections
        

class AMR:
    def __init__(self, json_data):
        self.json_data = json_data
        self.schema_url = self._transform_url(self.json_data.get("schema", None))
        self.schema = self._fetch_schema()  # Fetch the schema during initialization
        self.validation_error = None  # Store the validation error if any

    def _transform_url(self, url):
        """Transforms a GitHub URL into its raw format."""
        if not url:
            return None

        if "raw.githubusercontent.com" in url:
            return url

        return url.replace("github.com", "raw.githubusercontent.com").replace(
            "/blob", ""
        )

    def _fetch_schema(self):
        """Private method to fetch the JSON schema from the specified URL."""
        if not self.schema_url:
            raise ValueError("No schema URL specified in the input JSON.")

        response = requests.get(self.schema_url)
        response.raise_for_status()
        return response.json()

    def is_valid(self):
        """Validates the original JSON against the fetched JSON schema."""
        if not self.schema:
            raise ValueError(
                "Schema is not available. Fetching might have failed during initialization."
            )

        try:
            validate(instance=self.json_data, schema=self.schema)
            return True
        except ValidationError as e:
            self.validation_error = e
            return False

    def get_validation_error(self):
        """Retrieve the validation error message."""
        if not self.validation_error:
            return None
        return str(self.validation_error)
