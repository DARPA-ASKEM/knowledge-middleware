import json
import csv
import re
from collections import defaultdict

import yaml

def report():
    # TODO: Make this into a predefined struct
    report = defaultdict(lambda: {"operations": defaultdict(dict)}) 
    with open("tests/output/qual.csv", "r", newline="") as file:
        qual = csv.reader(file)
        for scenario, operation, test, passed in qual:
            report[scenario]["operations"][operation][test] = bool(passed)

    with open("tests/output/tests.json", "r") as file:
        raw_tests = json.load(file)["tests"]
        def get_case(testobj):
            full_name = testobj["nodeid"].split("::")[-1]
            # Don't worry we're not actually checking if brackets match
            match_result = re.match(re.compile(r"test_([a-z|_]+)\[([a-z|_]+)\]"), full_name)
            operation, scenario = match_result[1], match_result[2]
            passed = testobj["outcome"] == "passed"
            return (scenario, operation, "Integration", passed)
        for scenario, operation, test, passed in map(get_case, raw_tests):
            report[scenario]["operations"][operation][test] = passed

    for scenario in report:
        with open(f"tests/scenarios/{scenario}/config.yaml") as file:
            spec = yaml.load(file, yaml.CLoader)
            report[scenario]["name"] = spec["name"]
            report[scenario]["description"] = spec["description"]

    with open("tests/output/report.json", "w") as file:
        json.dump(report, file, indent=2)
