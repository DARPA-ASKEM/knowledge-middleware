#!/bin/bash

python tests/seed.py
# Check if there are additional arguments
if [ $# -gt 0 ]; then
    # Pass the additional arguments to the report.py script
    python tests/report.py "$@"
else
    python tests/report.py
fi
