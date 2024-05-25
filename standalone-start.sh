#!/bin/bash

# Runs the camera server as a single worker without threading.
# This allows for concurrency and async.
source /home/mrouser/anaconda3/etc/profile.d/conda.sh
conda activate uwmro_instruments
flask --no-debug run -p 8000 -h 127.0.0.1 --with-threads --no-debugger --no-reload
