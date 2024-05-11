from flask import Response
from flask import Flask, jsonify, make_response, send_file
from datetime import datetime, timedelta
from flask import current_app, flash, jsonify, make_response, redirect, request, url_for

from glob import glob
import logging
logging.basicConfig(level=logging.INFO)

from framing.framing_assist import extract_sources, plot_sources, solve_fits
from framing.models import PlateSolvingResult

from flask import Blueprint

framing_bp = Blueprint('framing', __name__)

@framing_bp.route('/api/plate_solve', methods=['POST'])
def plate_solve():
    payload = request.get_json()
    file_path = payload['filename']

    res = solve_fits(file_path)
    return jsonify(res.__dict__)
