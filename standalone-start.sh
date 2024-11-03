#!/bin/bash

# Get the working directory of evora-server and go to it
EVORA_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $EVORA_DIR

# Check for the existence of a virtual environment
if ! [ -d ".venv" ]; then
    # If it doesn't exist - create it
    /usr/bin/python -m venv init .venv

    # ... start the venv
    source .venv/bin/activate

    # ... and install packages within
    pip install -e .
else
    # start the venv
    source .venv/bin/activate

    # refresh + recompile our packages in case of updates
    pip install .
fi

# Runs the camera server as a single worker without threading.
# This allows for concurrency and async - redo to run app.py with port, host, debugger
flask --no-debug run -p 8000 -h 127.0.0.1 --with-threads --no-debugger --no-reload