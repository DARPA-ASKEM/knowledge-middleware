import json

with open("tests/output/report.json", "r") as f:
    data_dict = json.load(f)

tests = set()
operations = set()

for scenario, values in data_dict.items():
    for operation, raw_tests in values['operations'].items():
        operations.add(operation)
        for test in raw_tests:
            tests.add(test)

html = ""

for test in sorted(tests):
    table = f'<h2>{test}</h2>\n'
    table += '<table border="1">\n'

    table += '<tr>\n<th>Scenarios</th>\n'
    for operation in sorted(operations):
        table += f'<th>{operation}</th>\n'
    table += '</tr>\n'

    for scenario in sorted(data_dict.keys()):
        table += f'<tr>\n<td>{scenario}</td>\n'
        for operation in sorted(operations):
            operation_data = data_dict[scenario]['operations'].get(operation, {}).get(test, None)
            if operation_data is not None:
                if isinstance(operation_data, bool):
                    table += f"<td>{'✅' if operation_data else '❌'}</td>\n"
                else:
                    table += f"<td>{operation_data}</td>\n"
            else:
                table += "<td>⚠️</td>\n"  # Indicating not applicable/missing
        table += '</tr>\n'

    table += '</table>\n'

    html += table

with open("tests/output/report.html", "w") as file:
    file.write(html)
