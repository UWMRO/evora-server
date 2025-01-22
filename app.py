import asyncio
import atexit
import json
import logging
import os
import sys
import re
import time
import typing
from datetime import datetime
from glob import glob

import numpy
from astropy.io import fits
from astropy.time import Time
from flask import (
    Flask,
    current_app,
    jsonify,
    render_template,
    request,
    send_from_directory,
)
from flask_cors import CORS
from ambient_api.ambientapi import AmbientAPI

from andor_routines import acquisition, activateCooling, deactivateCooling, startup
from evora.debug import DEBUGGING

if DEBUGGING:
    from evora.dummy import Dummy as andor  # andor
else:
    from evora import andor

'''
 dev note: I also ran pip install aioflask and pip install asgiref to try to give
 flask async abilities.
 this is for handling requests from the filter wheel that may take some time.
'''

# add instructions to create data dir

logging.getLogger('PIL').setLevel(logging.WARNING)

FILTER_DICT = {'Ha': 0, 'B': 1, 'V': 2, 'g': 3, 'r': 4, 'i': 5}
FILTER_DICT_REVERSE = {0: 'Ha', 1: 'B', 2: 'V', 3: 'g', 4: 'r', 5: 'i'}

DEFAULT_PATH = '/data/ecam'

api = AmbientAPI()

# If we're debugging, use a local directory instead - create if doesn't exist
if DEBUGGING:
    DEFAULT_PATH = './' + DEFAULT_PATH
    os.makedirs(os.path.dirname(DEFAULT_PATH), exist_ok=True)

DUMMY_FILTER_POSITION = 0

ABORT_FLAG = False

def getFilePath(file):
    """
    Formats the given file name to be valid.
    If the file contains invalid characters or is empty, image.fits will be used.
    if the file already exists, it will be saved as:
        name(0), name(1), name(2), ..., name(n)
    """

    default_image_name = "ecam-{seq:04d}.fits"

    date = Time.now().utc.isot.split("T")[0].replace("-", "")

    path = os.path.join(DEFAULT_PATH, date)
    os.makedirs(path, exist_ok=True)

    invalid_characters = [":", "<", ">", "/", "\\", '"', "|", "?", "*", ".."]
    # if invalid filename, use image.fits
    if file is None or file == "" or any(c in file for c in invalid_characters):
        all_files = list(sorted(glob(os.path.join(path, "ecam-*.fits"))))
        if len(all_files) == 0:
            seq = 1
        else:
            match = re.search(r"ecam\-([0-9]+)", all_files[-1])
            if match:
                seq = int(match.group(1)) + 1
            else:
                seq = 1
        file = default_image_name.format(seq=seq)

    # ensure extension is .fits
    if file[-1] == ".":
        file += "fits"
    if len(file) < 5 or file[-5:] != ".fits":
        file += ".fits"

    # ensure nothing gets overwritten
    num = 0
    length = len(file[0:-5])
    while os.path.isfile(f"{DEFAULT_PATH}/{file}"):
        file = file[0:length] + f"({num})" + file[-5:]
        num += 1

    return os.path.join(path, file)


async def send_to_wheel(command: str):
    '''Sends a command to the filter wheel and parses the reply.

    Parameters
    ----------
    command
        The string to send to the filter wheel server.

    Returns
    -------
    res
        A tuple of response status as a boolean, and the additional reply
        as a string (the reply string will be empty if no additional reply is
        provided).

    '''

    reader, writer = await asyncio.open_connection('72.233.250.84', 9999)
    writer.write((command + '\n').encode())
    await writer.drain()

    received = (await reader.readline()).decode()
    writer.close()
    await writer.wait_closed()

    parts = received.split(',')

    status = parts[0] == 'OK'

    if len(parts) > 1:
        reply = parts[1]
    else:
        reply = ''

    return status, reply


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    CORS(app)

    logging.basicConfig(level=logging.DEBUG)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    @app.route('/getStatus')
    def getStatus():
        return jsonify(andor.getStatus())

    @app.route('/')
    def index():
        tempData = andor.getStatusTEC()['temperature']
        return render_template('index.html', tempData=tempData)

    @app.route('/initialize')
    def route_initialize():
        status = startup()
        activateCooling()  # make this a part of a separate route later
        return status

    @app.route('/shutdown')
    def route_shutdown():
        deactivateCooling()  # same here
        while not DEBUGGING and andor.getStatusTEC()['temperature'] < -10:
            print('waiting to warm: ', andor.getStatusTEC()['temperature'])
            time.sleep(5)
        # We assume the fan should always be on. Testing to turn it off did not work.
        status = andor.shutdown()
        return {'status': status}

    @app.route('/getTemperature')
    def route_getTemperature():
        print(andor.getStatusTEC())
        return jsonify(andor.getStatusTEC())

    @app.route('/setTemperature', methods=['POST'])
    def route_setTemperature():
        if request.method == 'POST':
            req = request.get_json(force=True)

            try:
                valid_range: dict = andor.getRangeTEC()
                req_temperature = int(req['temperature'])
                if req_temperature < valid_range['min'] or req_temperature > valid_range['max']:
                    app.logger.info(
                        f'Setting temperature to: {req_temperature:.2f} [C] is out of range. Must be between {valid_range["min"]} and {valid_range["max"]}'
                    )
                    return str(-999)  # indicates tempreature was out of range
                app.logger.info(f'Setting temperature to: {req_temperature:.2f} [C]')
                andor.setTargetTEC(req_temperature)
            except ValueError:
                app.logger.info(
                    'Post request received a parameter of invalid type (must be int)'
                )

        return str(req['temperature'])

    @app.route('/testLongExposure')
    def route_testLongExposure():
        acquisition((1024, 1024), exposure_time=10)
        return str('Finished Acquiring after 10s')
    
    @app.route('/getFocus')
    def route_getFocus():
        return jsonify({'message':'Not implemented'})

    @app.route('/setFocus')
    def route_setFocus():
        return jsonify({'message':'Not implemented'})
    
    @app.route("/capture", methods=["POST"])
    async def route_capture():
        '''
        Attempts to take a picture with the camera. Uses the 'POST' method
        to take in form requests from the front end.

        Returns the url for the fits file generated, which is then used for
        JS9's display.
        filename, url, message, status
        status: 0 - success, 1 - aborted, 2 - failed
        '''

        global ABORT_FLAG

        ABORT_FLAG = False

        if request.method == 'POST':
            req = request.get_json(force=True)
            req = json.loads(req)

            # validate parameters
            if 'exptime' not in req or 3600 < float(req['exptime']) <= 0:
                return {'message': 'Invalid or missing exposure time.', 'status': 2}
            if 'exptype' not in req or req['exptype'] not in ['Single', 'Real Time', 'Series']:
                return {'message': 'Invalid or missing exposure type', 'status': 2}
            if 'imgtype' not in req or req['imgtype'] not in ['Bias', 'Dark', 'Flat', 'Object']:
                return {'message': 'Invalid or missing image type.', 'status': 2}
            if 'filtype' not in req or req['filtype'] not in FILTER_DICT:
                return {'message': 'Invalid or missing filter type.', 'status': 2}
            if 'comment' not in req:
                return {'message': 'Missing comment.', 'status': 2}
            

            dim = andor.getDetector()['dimensions']

            # check if acquisition is already in progress
            status = andor.getStatus()
            if status['status'] == 20072:
                return {'message': 'Acquisition already in progress.', 'status': 2}

            # handle img type
            if req['imgtype'] == 'Bias' or req['imgtype'] == 'Dark':
                # Keep shutter closed during biases and darks
                andor.setShutter(1, 2, 50, 50)
                andor.setImage(1, 1, 1, dim[0], 1, dim[1])
            else:
                andor.setShutter(1, 0, 50, 50)
                andor.setImage(1, 1, 1, dim[0], 1, dim[1])

            # handle exposure type
            # refer to pg 41 - 45 of sdk for acquisition mode info
            exptype = req['exptype']
            if exptype == 'Single':
                andor.setAcquisitionMode(1)
                andor.setExposureTime(float(req['exptime']))

            elif exptype == 'Real Time':
                # this uses 'run till abort' mode - how do we abort it?
                andor.setAcquisitionMode(1)
                andor.setExposureTime(1)
                # andor.setKineticCycleTime(0)
                req['exptime'] = 1

            elif exptype == 'Series':
                andor.setAcquisitionMode(3)
                andor.setNumberKinetics(int(req['expnum']))
                andor.setExposureTime(float(req['exptime']))

            file_name = (
                f'{DEFAULT_PATH}/temp.fits'
                if exptype == 'Real Time'
                else getFilePath(None)
            )

            date_obs = Time.now()

            andor.startAcquisition()
            status = andor.getStatus()
            # todo: review parallelism, threading behavior is what we want?
            # while status == 20072:
            #     status = andor.getStatus()
            #     app.logger.info('Acquisition in progress')

            start_time = datetime.now()

            while (datetime.now() - start_time).total_seconds() < float(req["exptime"]):
                if ABORT_FLAG:
                    andor.abortAcquisition()
                    return {'message': str('Capture aborted'), 'status': 1}
                await asyncio.sleep(0.1)

            # An additional delay because the camera may not have totally finished
            # acquiring after exptime.
            await asyncio.sleep(0.5)
            
            img = andor.getAcquiredData(
                dim
            )  # TODO: throws an error here! gotta wait for acquisition

            comment = req['comment']

            focus_match = re.match(r'^focus\s*[:=]\s*(-?[0-9\.]+)$', comment)
            if focus_match is not None:
                focus = float(focus_match.group(1))
            else:
                focus = ''

            if img['status'] == 20002:
                # use astropy here to write a fits file
                andor.setShutter(1, 0, 50, 50)  # closes shutter
                # home_filter() # uncomment if using filter wheel
                hdu = fits.PrimaryHDU(img['data'].astype(numpy.uint16))
                hdu.header['DATE-OBS'] = date_obs.isot
                hdu.header['COMMENT'] = comment
                hdu.header['INSTRUME'] = 'iKon-M 934 CCD DU934P-BEX2-DD'
                hdu.header['XBINNING'] = '1'
                hdu.header['YBINNING'] = '1'
                hdu.header['XPIXSZ'] = '13'
                hdu.header['YPIXSZ'] = '13'
                hdu.header['FOCALLEN'] = '5766'

                hdu.header['EXPTIME'] = (
                    float(req['exptime']),
                    'Exposure Time (Seconds)',
                )
                hdu.header['EXP_TYPE'] = (
                    str(req['exptype']),
                    'Exposure Type (Single, Real Time, or Series)',
                )
                hdu.header['IMAGETYP'] = (
                    str(req['imgtype']),
                    'Image Type (Bias, Flat, Dark, or Object)',
                )
                hdu.header['FILTER'] = (str(req['filtype']), 'Filter (Ha, B, V, g, r)')
                hdu.header['CCD-TEMP'] = (
                    str(f'{andor.getStatusTEC()["temperature"]:.3f}'),
                    'CCD Temperature during Exposure',
                )
                hdu.header['FOCUS'] = (
                    focus,
                    'Relative focus position [microns]'
                )
                try:
                    hdu.writeto(file_name, overwrite=True)
                except:
                    print('Failed to write')

                return {
                    'filename': os.path.basename(file_name),
                    'url': file_name,
                    'message': 'Capture Successful',
                    'status': 0
                }

            else:
                andor.setShutter(1, 0, 50, 50)
                # home_filter()  # uncomment if using filter wheel
                return {'message': str('Capture Unsuccessful'), 'status': 2}

    @app.route('/abort')
    async def route_abort_capture():
        '''Abort exposure.'''

        global ABORT_FLAG

        ABORT_FLAG = True

        return {'message': 'Aborting exposure'}

    @app.route('/getFilterWheel')
    async def route_get_filter_wheel():
        '''Returns the position of the filter wheel.'''
        if DEBUGGING:
            return jsonify({'success': True, 'filter': FILTER_DICT_REVERSE[DUMMY_FILTER_POSITION], 'error': ''})

        status, reply = await send_to_wheel('get')
        filter_name = None
        error = ''

        if status:
            success = True
            filter_pos = int(reply)
            filter_name = FILTER_DICT_REVERSE[filter_pos]
        else:
            success = False
            error = reply

        return jsonify({'success': success, 'filter': filter_name, 'error': error})

    @app.route('/setFilterWheel', methods=['POST'])
    async def route_set_filter_wheel():
        '''Moves the filter wheel to a given position by filter name.'''

        global DUMMY_FILTER_POSITION

        payload = dict(
            message='',
            success=False,
            error='',
        )

        if request.method == 'POST':
            req = request.get_json(force=True)
        else:
            payload['error'] = 'Invalid request method.'
            return jsonify(payload)

        if 'filter' not in req:
            payload['error'] = 'Filter not found in request.'
            return jsonify(payload)

        filter = req['filter']
        if filter not in FILTER_DICT:
            payload['error'] = f'Unknown filter {filter}.'
            return jsonify(payload)

        filter_num = FILTER_DICT[filter]

        if DEBUGGING:
            await asyncio.sleep(2)
            DUMMY_FILTER_POSITION = filter_num
            payload['success'] = True
            return jsonify(payload)

        status, reply = await send_to_wheel(f'move {filter_num}')

        payload['success'] = status
        if status:
            payload['message'] = f'Filter wheel moved to filter {filter}.'
        else:
            payload['error'] = reply

        return jsonify(payload)

    @app.route('/homeFilterWheel')
    async def route_home_filter_wheel():
        '''Homes the filter wheel.'''

        global DUMMY_FILTER_POSITION

        if DEBUGGING:
            await asyncio.sleep(2)
            DUMMY_FILTER_POSITION = 0
            return dict(message='', success=True, error='')

        payload = dict(
            message='',
            success=False,
            error='',
        )

        status, reply = await send_to_wheel('home')
        payload['success'] = status
        if status:
            payload['message'] = 'Filter wheel has been homed.'
        else:
            payload['error'] = reply
        print(payload)
        return jsonify(payload)
    
    @app.route('/getWeatherData')
    def route_get_weather_data():
        devices = api.get_devices()
        device = devices[0]
        time.sleep(1)
        data = device.last_data
        return data

    return app


def OnExitApp():
    andor.shutdown()


atexit.register(OnExitApp)

app = create_app()

# Framing does not work on windows (due to astrometry)
if sys.platform != 'win32':
  import framing
  framing.register_blueprint(app)

import focus
focus.register_blueprint(app)

if __name__ == '__main__':
    # TO RUN IN PRODUCTION, USE:
    # The key here is threaded=True which allows the server to handle multiple
    # requests at once but withing a single process (?), which allows sharing the
    # camera connection.
    # app.run(host='127.0.0.1', port=8000, debug=False, threaded=True, processes=1)

    # FOR DEBUGGING, USE:
    app.run(host='127.0.0.1', port=3000, debug=True, processes=1, threaded=True)
