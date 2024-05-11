from flask import Response
from flask import Flask, jsonify, make_response, send_file
from datetime import datetime, timedelta
from flask import current_app, flash, jsonify, make_response, redirect, request, url_for

from glob import glob
import logging
logging.basicConfig(level=logging.INFO)

from framing.framing_assist import extract_sources, plot_sources, solve_fits
from framing.models import PlateSolvingResult
from astrometry import PositionHint

from flask import Blueprint

blueprint = Blueprint('framing', __name__)

@blueprint.route('/api/plate_solve', methods=['POST'])
def plate_solve():
    payload = request.get_json()
    file_path = payload['filename']
    position_hint = PositionHint(
        ra_deg=payload.get('hint_ra_deg', 0),
        dec_deg=payload.get('hint_dec_deg', 0),
        radius_deg=payload.get('hint_radius_deg', 360)
    ) 
    res = solve_fits(file_path, position_hint=position_hint)
    return jsonify(res.__dict__)
