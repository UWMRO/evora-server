#!/bin/bash
source /home/mrouser/anaconda3/etc/profile.d/conda.sh
conda activate uwmro_instruments
gunicorn -w 4 "app:app"