## LLM GENERATED
import json

data_dict = json.load(open("tests/output/report.json"))

html = '<table border="1">\n'

html += '<tr>\n<th>Tests/Operations</th>\n'
unique_operations = set()

for scenario, values in data_dict.items():
    for operation in values["operations"]:
        unique_operations.add(operation)

for operation in sorted(unique_operations):
    html += f'<th>{operation}</th>\n'
html += '</tr>\n'

unique_tests = set()
for scenario, values in data_dict.items():
    for operation, tests in values["operations"].items():
        for test in tests:
            unique_tests.add(test)

for test in sorted(unique_tests):
    html += f'<tr>\n<td>{test}</td>\n'
    for operation in sorted(unique_operations):
        html += '<td>'
        for scenario, values in data_dict.items():
            if operation in values["operations"] and test in values["operations"][operation]:
                html += f"{values['name']} ({'✅' if values['operations'][operation][test] else '❌'})<br>"
        html += '</td>\n'
    html += '</tr>\n'

html += '</table>\n'

print(html)
