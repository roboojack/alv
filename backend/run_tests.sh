#!/bin/bash
# Run tests in parallel using pytest-xdist
# Ensure you have the virtual environment activated or dependencies installed

if [ -d "venv" ]; then
    venv/bin/pytest -n auto "$@"
elif [ -d ".venv" ]; then
    .venv/bin/pytest -n auto "$@"
else
    pytest -n auto "$@"
fi
