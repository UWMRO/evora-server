#!/bin/bash
source /home/mrouser/anaconda3/etc/profile.d/conda.sh
conda activate uwmro_instruments
gunicorn --timeout 1800 -w 1 "app:app"
