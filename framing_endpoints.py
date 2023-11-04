from flask import Response
from flask import Flask, jsonify, make_response, send_file
from datetime import datetime, timedelta
from focus.models import FocusSession
from focus import settings
from flask import current_app, flash, jsonify, make_response, redirect, request, url_for

from focus.focus_assist import find_focus_position, stat_for_image, plot_fit

import random
from glob import glob
import logging
logging.basicConfig(level=logging.INFO)

from app import app
from framing.framing_assist import extract_sources, plot_sources, solve_fits
from framing.models import PlateSolvingResult

@app.route('/api/plate_solve', methods=['POST'])
def plate_solve():
    payload = request.get_json()
    file_path = payload['filename']

    res = solve_fits(file_path)
    return jsonify(res.__dict__)
