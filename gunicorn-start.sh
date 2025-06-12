#!/bin/bash

source .venv/bin/activate
gunicorn --timeout 1800 -w 1 "app:app"
