#!/bin/bash

# Check if there are additional arguments
if [ $# -gt 0 ]; then
    # Pass the additional arguments to the seed.py script
    python tests/seed.py "$@"
else
    python tests/seed.py
fi

# Check if there are additional arguments
if [ $# -gt 0 ]; then
    # Pass the additional arguments to the report.py script
    python tests/report.py "$@"
else
    python tests/report.py
fi
