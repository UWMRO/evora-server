from typing import Dict
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

from flask import Blueprint

blueprint = Blueprint('focus_assist', __name__)


SessionStorage: {str: FocusSession} = {}


def analyze(session):
    fwhm_metrics = session.fwhm_metrics
    focuser_positons = session.focuser_positons

    hfd_curve_dps = {
        "sep": [dp['sep'] for dp in session.hfd_metrics],
        "my": [dp['my'] for dp in session.hfd_metrics],
        "PHD": [dp['PHD'] for dp in session.hfd_metrics]
    }
    fwhm_min, hfd_min, fwhm_fit, hfd_fits = find_focus_position(
        focuser_positons, fwhm_metrics, hfd_curve_dps)
    session.fwhm_fit = fwhm_fit
    session.hfd_fits = hfd_fits
    session.predicted_min_fwhm = fwhm_min
    session.predicted_min_hfd = hfd_min

    return fwhm_min, hfd_min


@blueprint.route('/plot/<sid>')
def retrieve_plot(sid):
    if sid not in SessionStorage:
        return Response(status=404)
    session = SessionStorage[sid]
    fwhm_metrics = session.fwhm_metrics
    focuser_positons = session.focuser_positons
    fwhm_fit = session.fwhm_fit
    hfd_fits = session.hfd_fits
    hfd_curve_dps = {
        "sep": [dp['sep'] for dp in session.hfd_metrics],
        "my": [dp['my'] for dp in session.hfd_metrics],
        "PHD": [dp['PHD'] for dp in session.hfd_metrics]
    }
    image = plot_fit(focuser_positons, fwhm_metrics,
                     hfd_curve_dps, fwhm_fit, hfd_fits)
    return Response(image, mimetype='image/png')


@blueprint.route('/api/reset', methods=['POST'])
def reset():
    payload = request.get_json()
    sid = payload['sid']
    if sid in SessionStorage:
        del SessionStorage[sid]
    return jsonify({
    })


@blueprint.route('/api/add_focus_datapoint', methods=['POST'])
def add_focus_datapoint():
    clean_old_sessions()
    payload = request.get_json()
    sid = payload['sid']
    if sid not in SessionStorage:
        SessionStorage[sid] = FocusSession(id=sid)
    session = SessionStorage[sid]

    filename = payload['filename']
    focuser_position = int(payload['focuserPosition'])
    session.focuser_positons.append(focuser_position)

    logging.info(f"filename: {filename} focuser_position: {focuser_position}")

    fits_file_url = settings.BASEFILE_PATH + filename

    if settings.DEBUG:
        images = glob(
            '/Users/siyu/Proj/evora_autofocus/focus_test/manual/*.fits')
        fits_file_url = random.choice(images)

    median_fwhm, median_sep_hfd, median_my_hfd, median_phd_hfd = stat_for_image(
        fits_file_url)
    session.hfd_metrics.append({
        "sep": median_sep_hfd,
        "my": median_my_hfd,
        "PHD": median_phd_hfd
    })
    session.fwhm_metrics.append(median_fwhm)
    session.files.append(filename)
    logging.info(
        f"median_fwhm: {median_fwhm} median_sep_hfd: {median_sep_hfd} median_my_hfd: {median_my_hfd} median_phd_hfd: {median_phd_hfd}")
    if len(session.focuser_positons) >= 3:
        analyze(session=session)
    return jsonify(session.serialize())


def clean_old_sessions():
    now = datetime.now()

    for sid in list(SessionStorage):
        timestamp = datetime.fromtimestamp(int(sid)/1000)
        if now - timestamp > timedelta(days=30):
            del SessionStorage[sid]

