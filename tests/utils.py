import requests
from jsonschema import validate, ValidationError
from collections import defaultdict
from os import listdir, path
from lib.settings import settings

import yaml

def get_parameterizations():
    selections = defaultdict(list)
    options = listdir("tests/scenarios") if not settings.MOCK_TA1 else ["basic"]
    for pick in options:
        with open("tests/resources.yaml") as file:
            spec = yaml.load(file, yaml.CLoader)
        dir = f"tests/scenarios/{pick}" 
        with open(f"{dir}/config.yaml") as file:
            config = yaml.load(file, yaml.CLoader)
            for selection in config["enabled"]:
                for resource in spec[selection]:
                    if not path.exists(dir + "/" + resource):
                        raise Exception(f"Cannot test scenario '{pick}': Missing resource '{resource}'")
                selections[selection].append(pick) 
    return selections
        

class AMR:
    def __init__(self, json_data):
        self.json_data = json_data
        self.header = json_data["header"]
        try:
            self.schema_url = self.header["schema"]
        except KeyError:
            raise ValueError("No schema URL specified in the input JSON.")
        if "raw.githubusercontent.com" not in self.schema_url:
            self.schema_url = self.schema_url.replace("github.com", "raw.githubusercontent.com").replace(
                "/blob", ""
        )
        response = requests.get(self.schema_url)
        response.raise_for_status()
        self.schema = response.json()
        self.validation_error = None


    def is_valid(self):
        """Validates the original JSON against the fetched JSON schema."""
        try:
            validate(instance=self.json_data, schema=self.schema)
        except ValidationError as e:
            self.validation_error = str(e)
            return False
        else:
            return True
