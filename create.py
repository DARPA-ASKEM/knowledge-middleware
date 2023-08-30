import json

with open("tests/output/report.json", "r") as f:
    data_dict = json.load(f)

unique_tests = set()
unique_operations = set()

for scenario, values in data_dict.items():
    for operation, tests in values['operations'].items():
        unique_operations.add(operation)
        for test in tests:
            unique_tests.add(test)

for test in sorted(unique_tests):
    html = f'<h2>{test}</h2>\n'
    html += '<table border="1">\n'

    html += '<tr>\n<th>Scenarios</th>\n'
    for operation in sorted(unique_operations):
        html += f'<th>{operation}</th>\n'
    html += '</tr>\n'

    for scenario in sorted(data_dict.keys()):
        html += f'<tr>\n<td>{scenario}</td>\n'
        for operation in sorted(unique_operations):
            operation_data = data_dict[scenario]['operations'].get(operation, {}).get(test, None)
            if operation_data is not None:
                html += f"<td>{'✅' if operation_data else '❌'}</td>\n"
            else:
                html += "<td>⚠️</td>\n"  # Indicating not applicable/missing
        html += '</tr>\n'

    html += '</table>\n'

    print(html)
