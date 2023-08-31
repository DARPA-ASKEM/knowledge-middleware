import json
from functools import reduce
from collections import defaultdict

import streamlit as st
import pandas as pd

with open("tests/output/report.json") as file:
    report = json.load(file)

test_results = defaultdict(lambda: defaultdict())

for scenario, content in report.items():
    for operation, tests in content["operations"].items():
        for name, result in tests.items():
            test_results[name][(content["name"], operation)] = result

scenarios = [report[scenario]["name"] for scenario in report.keys()]
operations = list(reduce(lambda left, right: left.union(right), [set(content["operations"].keys()) for content in report.values()], set()))
tests = list(test_results.keys())


dataframes = {name: pd.DataFrame(index=scenarios, columns=operations) for name in tests}

st.sidebar.markdown("""
# TA1

TA1 correctness and quality checks.
    
The current metrics are
Status of `knowledge-middleware` integration,
F-Score on the conversions to AMR, and the estimated time saved by the modeler. 
""")
for test, results in test_results.items():
    df = dataframes[test]
    for (scenario_name, operation), result in results.items():
        df.at[scenario_name, operation] = result
    st.write(f"### {test}")
    df.replace({False: "❌", True: "✅", None: ""}, inplace=True)
    df
    
