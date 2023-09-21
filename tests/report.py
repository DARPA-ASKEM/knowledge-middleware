import json
import csv
import datetime
import os
import re
from collections import defaultdict

import yaml
import pytest
import boto3

from lib.settings import settings

def test(output_file="tests/output/tests.json"):
    pytest.main(["--json-report", f"--json-report-file={output_file}"])


def gen_report():
    # TODO: Make this into a predefined struct
    scenarios = defaultdict(lambda: {"operations": defaultdict(dict)}) 
    if os.path.exists("tests/output/qual.csv"):
        with open("tests/output/qual.csv", "r", newline="") as file:
            qual = csv.reader(file)
            for scenario, operation, test, result in qual:
                scenarios[scenario]["operations"][operation][test] = result

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
            scenarios[scenario]["operations"][operation]["Integration Status"] = passed
            scenarios[scenario]["operations"][operation]["Execution Time"] = duration
            try:
                logs = testobj["call"]["stderr"]
                scenarios[scenario]["operations"][operation]["Logs"] = logs
            except Exception as e:
                print(f"Unable to obtain logs for {full_name}: {e}")
        for testobj in raw_tests: add_case(testobj)

    for scenario in scenarios:
        with open(f"tests/scenarios/{scenario}/config.yaml") as file:
            spec = yaml.load(file, yaml.CLoader)
            scenarios[scenario]["name"] = spec["name"]
            scenarios[scenario]["description"] = spec["description"]

    report = {
        "scenarios": scenarios,
        # TODO: Grab version
        # NOTE: This is broken up currently because we expect different version calls
        "services": {
            "TA1_UNIFIED_URL":{
              "source": settings.TA1_UNIFIED_URL,  
              "version": "UNAVAILABLE"
            },
            "SKEMA_RS_URL":{
              "source": settings.SKEMA_RS_URL,  
              "version": "UNAVAILABLE"
            },
            "MIT_TR_URL":{
              "source": settings.MIT_TR_URL,  
              "version": "UNAVAILABLE"
            },
            "COSMOS_URL":{
              "source": settings.COSMOS_URL,  
              "version": "UNAVAILABLE"
            },
        }
    }

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"report_{timestamp}.json"
    fullpath = os.path.join("tests/output", filename)
    with open(fullpath, "w") as file:
        json.dump(report, file, indent=2)

    s3 = boto3.client("s3")
    full_handle = os.path.join("ta1", filename)
    s3.upload_file(fullpath, settings.BUCKET, full_handle)

if __name__ == "__main__":
    gen_report()