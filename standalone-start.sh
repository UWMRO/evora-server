#!/bin/bash

# Runs the camera server as a single worker without threading.
# This allows for concurrency and async - redo to run app.py with port, host, debugger
source .venv/bin/activate
fastapi run src/evora_server/app.py --port 3000 --workers 1

