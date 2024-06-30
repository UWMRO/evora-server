import asyncio
import atexit
import json
import logging
import os
import sys
import re
import time
import argparse
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

from andor_routines import acquisition, activateCooling, deactivateCooling, startup
from evora.debug import DEBUGGING

'''
 dev note: I also ran pip install aioflask and pip install asgiref to try to give
 flask async abilities.
 this is for handling requests from the filter wheel that may take some time.
'''

logging.getLogger('PIL').setLevel(logging.WARNING)

class EvoraServer:
    """EvoraServer class containing functions to interface with the Evora CCD."""

    def __init__(self, args):
        """This function will run once when EvoraServer is created."""
        # Interpret arguments as globals
        self.DEBUGGING = args.debug
        self.PORT = args.port
        self.DEFAULT_PATH = args.path

        # Constants + globals
        self.ABORT_FLAG = False
        self.DUMMY_FILTER_POSITION = 0
        self.FILTER_DICT = {'Ha': 0, 'B': 1, 'V': 2, 'g': 3, 'r': 4, 'i': 5}
        self.FILTER_DICT_REVERSE = {0: 'Ha', 1: 'B', 2: 'V', 3: 'g', 4: 'r', 5: 'i'}

        # If we're debugging, use a local directory instead - create if doesn't exist
        if self.DEBUGGING:
            self.DEFAULT_PATH = './' + self.DEFAULT_PATH
            os.makedirs(os.path.dirname(self.DEFAULT_PATH), exist_ok=True)

        atexit.register(self.OnExitApp)

    def getFilePath(self, file):
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


    async def send_to_wheel(self, command: str):
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

    def create_app(self, test_config=None):
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
        def getStatus(self):
            return jsonify(andor.getStatus())

        @app.route('/')
        def index(self):
            tempData = andor.getStatusTEC()['temperature']
            return render_template('index.html', tempData=tempData)

        @app.route('/initialize')
        def route_initialize(self):
            status = startup()
            activateCooling()  # make this a part of a separate route later
            return status

        @app.route('/shutdown')
        def route_shutdown(self):
            deactivateCooling()  # same here
            while andor.getStatusTEC()['temperature'] < -10:
                print('waiting to warm: ', andor.getStatusTEC()['temperature'])
                time.sleep(5)
            # We assume the fan should always be on. Testing to turn it off did not work.
            status = andor.shutdown()
            return {'status': status}

        @app.route('/getTemperature')
        def route_getTemperature(self):
            print(andor.getStatusTEC())
            return jsonify(andor.getStatusTEC())

        @app.route('/setTemperature', methods=['POST'])
        def route_setTemperature(self):
            if request.method == 'POST':
                req = request.get_json(force=True)

                try:
                    req_temperature = int(req['temperature'])
                    app.logger.info(f'Setting temperature to: {req_temperature:.2f} [C]')
                    andor.setTargetTEC(req_temperature)
                except ValueError:
                    app.logger.info(
                        'Post request received a parameter of invalid type (must be int)'
                    )

            return str(req['temperature'])

        @app.route('/testLongExposure')
        def route_testLongExposure(self):
            acquisition((1024, 1024), exposure_time=10)
            return str('Finished Acquiring after 10s')

        @app.route("/capture", methods=["POST"])
        async def route_capture(self):
            '''
            Attempts to take a picture with the camera. Uses the 'POST' method
            to take in form requests from the front end.

            Returns the url for the fits file generated, which is then used for
            JS9's display.
            filename, url, message, status
            status: 0 - success, 1 - aborted, 2 - failed
            '''

            self.ABORT_FLAG = False

            if request.method == 'POST':
                req = request.get_json(force=True)
                req = json.loads(req)
                dim = andor.getDetector()['dimensions']

                # check if acquisition is already in progress
                status = andor.getStatus()
                if status['status'] == 20072:
                    return {'message': str('Acquisition already in progress.'), 'status': 2}

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
                    f'{self.DEFAULT_PATH}/temp.fits'
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
        async def route_abort_capture(self):
            '''Abort exposure.'''

            self.ABORT_FLAG = True

            return {'message': 'Aborting exposure'}

        @app.route('/getFilterWheel')
        async def route_get_filter_wheel(self):
            '''Returns the position of the filter wheel.'''
            if self.DEBUGGING:
                return jsonify({'success': True, 'filter': self.FILTER_DICT_REVERSE[self.DUMMY_FILTER_POSITION], 'error': ''})

            status, reply = await send_to_wheel('get')
            filter_name = None
            error = ''

            if status:
                success = True
                filter_pos = int(reply)
                filter_name = self.FILTER_DICT_REVERSE[filter_pos]
            else:
                success = False
                error = reply

            return jsonify({'success': success, 'filter': filter_name, 'error': error})

        @app.route('/setFilterWheel', methods=['POST'])
        async def route_set_filter_wheel(self):
            '''Moves the filter wheel to a given position by filter name.'''

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
            if filter not in self.FILTER_DICT:
                payload['error'] = f'Unknown filter {filter}.'
                return jsonify(payload)

            filter_num = self.FILTER_DICT[filter]

            if self.DEBUGGING:
                await asyncio.sleep(2)
                self.DUMMY_FILTER_POSITION = filter_num
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
        async def route_home_filter_wheel(self):
            '''Homes the filter wheel.'''

            if DEBUGGING:
                await asyncio.sleep(2)
                self.DUMMY_FILTER_POSITION = 0
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

        return app

    def OnExitApp(self):
        andor.shutdown()

if __name__ == '__main__':
    # CLI app setup + argument parser
    parser = argparse.ArgumentParser(
                    prog='Evora Server',
                    description='High-level server to interface with the MRO Evora CCD.')
    parser.add_argument('--debug', 
                    default=False, 
                    action='store_true',
                    help="Run Evora in debug mode (suitable for local development)")
    parser.add_argument('--port', type=int, default=3000, help="Port to run Evora on")
    parser.add_argument('--path', type=str, default='/data/ecam', help='Directory where Evora will store files')
    args = parser.parse_args() # Access arguments with parser.argument (i.e. parser.debug)

    # If we're debugging - import the dummy andor client. Otherwise, normal.
    if args.debug:
        from evora.dummy import Dummy as andor
    else:
        from evora import andor

    # Create EvoraServer and initialize app
    server = EvoraServer(args)
    app = EvoraServer.create_app(EvoraServer)

    # Framing does not work on windows (due to astrometry)
    if sys.platform != 'win32':
        import framing
        framing.register_blueprint(app)

    import focus
    focus.register_blueprint(app)

    # Change to EvoraServer.run() at some point
    app.run(host='127.0.0.1', port=args.port, debug=args.debug, processes=1, threaded=True)

# TODO:
# - Add arg to download astrometry data
# - Put everything into a class to make globals more pythonic to access