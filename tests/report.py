import json
import csv
import datetime
import os
import re
from collections import defaultdict

import yaml

def report():
    # TODO: Make this into a predefined struct
    report = defaultdict(lambda: {"operations": defaultdict(dict)}) 
    if os.path.exists("tests/output/qual.csv"):
        with open("tests/output/qual.csv", "r", newline="") as file:
            qual = csv.reader(file)
            for scenario, operation, test, result in qual:
                report[scenario]["operations"][operation][test] = result

    with open("tests/output/tests.json", "r") as file:
        raw_tests = json.load(file)["tests"]
        def add_case(testobj):
            full_name = testobj["nodeid"].split("::")[-1]
            # Don't worry we're not actually checking if brackets match
            pattern = r"test_([a-z0-9_]+)\[([a-z0-9_]+)\]"
            match_result = re.match(pattern, full_name, re.IGNORECASE)
            operation, scenario = match_result[1], match_result[2]
            passed = testobj["outcome"] == "passed"
            duration = round(testobj["call"]["duration"],2)
            report[scenario]["operations"][operation]["Integration Status"] = passed
            report[scenario]["operations"][operation]["Execution Time"] = duration
            try:
                logs = testobj["call"]["stderr"]
                report[scenario]["operations"][operation]["Logs"] = logs
            except Exception as e:
                print(f"Unable to obtain logs for {full_name}: {e}")
        for testobj in raw_tests: add_case(testobj)

    for scenario in report:
        with open(f"tests/scenarios/{scenario}/config.yaml") as file:
            spec = yaml.load(file, yaml.CLoader)
            report[scenario]["name"] = spec["name"]
            report[scenario]["description"] = spec["description"]

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"tests/output/report_{timestamp}.json"
    with open(filename, "w") as file:
        json.dump(report, file, indent=2)

if __name__ == "__main__":
    report()