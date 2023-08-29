import requests
from jsonschema import validate, ValidationError
from collections import defaultdict
from os import listdir, makedirs, path
import csv

import yaml

def get_parameterizations():
    selections = defaultdict(list)
    for pick in listdir("tests/scenarios"):
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

    def structural_simularity(self, standard):
        return len(self.json_data["model"]["states"])/len(standard["model"]["states"])


def record_qual_result(context_dir, test, error):
    scenario = context_dir.split("/")[-1]
    makedirs("tests/output", exist_ok=True)
    with open(f"tests/output/qual.csv", "a", newline="") as file:
        result = csv.writer(file)
        result.writerow([scenario, test, error])



