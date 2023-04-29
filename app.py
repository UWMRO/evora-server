from andor_routines import startup, activateCooling, deactivateCooling, acquisition
from flask import Flask, render_template, request, redirect, jsonify, make_response, send_from_directory, current_app, url_for
import asyncio
from astropy.io import fits
import logging
import socket
import os
import numpy as np
from datetime import datetime
import atexit
import json
import time

from debug import DEBUGGING
if (DEBUGGING):
    from evora.dummy import Dummy as andor #andor
else:
    from evora import andor

"""
 dev note: I also ran pip install aioflask and pip install asgiref to try to give flask async abilities.
 this is for handling requests from the filter wheel that may take some time.
"""

logging.getLogger("PIL").setLevel(logging.WARNING)

FITS_PATH = "static/fits_files"


def formatFileName(file):
    """
    Formats the given file name to be valid.
    If the file contains invalid characters or is empty, image.fits will be used.
    if the file already exists, it will be saved as: name(0), name(1), name(2), ..., name(n)
    """

    invalid_characters = [":", "<", ">", "/", "\\", '"', "|", "?", "*", ".."]
    # if invalid filename, use image.fits
    if file == "" or any(c in file for c in invalid_characters):
        file = "image.fits"

    # ensure extension is .fits
    if file[-1] == ".":
        file += "fits"
    if len(file) < 5 or file[-5:] != ".fits":
        file += ".fits"

    # ensure nothing gets overwritten
    num = 0
    length = len(file[0:-5])
    while os.path.isfile(f"{FITS_PATH}/{file}"):
        file = file[0:length] + f"({num})" + file[-5:]
        num += 1
    return file


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    # app.config['UPLOAD_FOLDER'] = 'static/fits_files'

    logging.basicConfig(level=logging.DEBUG)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    status = startup()
    activateCooling()

    app.logger.info(f"Startup Status: {str(status['status'])}")

    @app.route("/getStatus")
    def getStatus():
        return jsonify(andor.getStatus())

    @app.route("/")
    def index():
        tempData = andor.getStatusTEC()["temperature"]
        return render_template("index.html", tempData=tempData)

    # REMEMBER: localhost:5000/temperature
    @app.route("/getTemperature")
    def route_getTemperature():
        # return str(andor.getStatusTEC()['temperature'])
        print(andor.getStatusTEC())
        return jsonify(andor.getStatusTEC())

    @app.route("/setTemperature", methods=["POST"])
    def route_setTemperature():
        if request.method == "POST":
            req = request.get_json(force=True)

            try:
                req_temperature = int(req["temperature"])
                app.logger.info(f"Setting temperature to: {req_temperature:.2f} [C]")
                andor.setTargetTEC(req_temperature)
            except ValueError:
                app.logger.info(
                    "Post request received a parameter of invalid type (must be int)"
                )

        return str(req["temperature"])

    # def route_setTemperature():
    #     """
    #     Sets the temperature of the camera in Celsius. Uses the 'POST' method
    #     to take in form requests from the front end.

    #     Returns the set temperature for display on the front end.
    #     """
    #     if request.method == "POST":
    #         app.logger.info('setting temperature')
    #         req = request.get_json(force=True)

    #         #change_temp = andor.setTemperature(req['temp'])
    #         activateCooling(req['temp'])

    #         curr_temp = andor.getStatusTEC()['temperature']
    #         while curr_temp != req['temp']:
    #             curr_temp = andor.getStatusTEC()['temperature']
    #         deactivateCooling()

    #         app.logger.info(andor.getStatusTEC()['temperature'])

    #         res = req['temp']

    #         return res

    # @app.route('/getStatusTEC')
    # def route_getStatusTEC():
    #     return str(andor.getStatusTEC()['status'])

    @app.route("/get_filter_position")
    def route_get_filter():
        pass

    #    @app.route('/setFilter')
    #    async def route_set_filter():
    #        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #        req = request.get_json(force=True)
    #        s.connect(('127.0.0.1', 5503))
    #        #if req['value']
    #        s.send(b'home\n')
    #        received = await s.recv(1000).decode()
    #        s.close()
    #        return received

    def set_filter(filter):
        res = asyncio.run(set_filter_helper(filter))
        return res

    async def set_filter_helper(filter):
        # these filter positions are placeholders - need to find which filter corresponds
        # to each position on the wheel
        """
        Moves the filter to the given position.
        """

        filter_dict = {"Ha": 1, "B": 2, "V": 3, "g": 4, "r": 5}

        if filter not in filter_dict.keys():
            raise ValueError("Invalid Filter")

        pos_str = f"move {filter_dict[filter]}\n"
        reader, writer = await asyncio.open_connection("127.0.0.1", 5503)
        writer.write(pos_str.encode("utf-8"))
        await writer.drain()
        received = await reader.readline()
        writer.close()
        await writer.wait_closed()
        return {"message": received.decode()}

    def home_filter():
        res = asyncio.run(home_filter_helper())
        return res

    async def home_filter_helper():
        """
        Homes the filter back to its default position.
        """
        reader, writer = await asyncio.open_connection("127.0.0.1", 5503)
        writer.write(b"home\n")
        await writer.drain()
        received = await reader.readline()
        writer.close()
        await writer.wait_closed()
        return {"message": received.decode()}

    @app.route("/testReturnFITS", methods=["GET"])
    def route_testReturnFITS():
        acq = acquisition((1024, 1024), exposure_time=0.1)

        hdu = fits.PrimaryHDU(data=acq["data"])
        filename = f'{datetime.now().strftime("%m-%d-%Y_T%H%M%S")}.fits'
        hdu.writeto("./fits_files/" + filename)

        # np.savetxt('./uploads/' + filename, acq['data'], delimiter=',')
        uploads = os.path.join(current_app.root_path, "./fits_files/")
        return send_from_directory(uploads, filename, as_attachment=True)

    @app.route("/testLongExposure")
    def route_testLongExposure():
        acquisition((1024, 1024), exposure_time=10)
        return str("Finished Acquiring after 10s")

    @app.route("/capture", methods=["POST"])
    def route_capture():
        """
        Attempts to take a picture with the camera. Uses the 'POST' method
        to take in form requests from the front end.

        Returns the url for the fits file generated, which is then used for
        JS9's display.
        Throws an error if status code is not 20002 (success).
        """
        if request.method == "POST":
            req = request.get_json(force=True)
            req = json.loads(req)
            dim = andor.getDetector()["dimensions"]

            # check if acquisition is already in progress
            status = andor.getStatus()
            if status == 20072:
                return {"message": str("Acquisition already in progress.")}

            # handle filter type - untested, uncomment if using filter wheel

            # filter_msg = set_filter(req['fil_type'])
            # if filter_msg['message'].startswith('Error'):
            #     raise Exception(filter_msg)
            # else:
            #     app.logger.info(filter_msg)

            # handle img type
            if req["imgtype"] == "bias":
                andor.setShutter(1, 2, 50, 50)
                andor.setImage(1, 1, 1, dim[0], 1, dim[1])
            else:
                andor.setShutter(1, 0, 50, 50)
                andor.setImage(1, 1, 1, dim[0], 1, dim[1])

            # handle exposure type
            # refer to pg 41 - 45 of sdk for acquisition mode info
            if req["exptype"] == "Single":
                andor.setAcquisitionMode(1)
                andor.setExposureTime(float(req["exptime"]))

            elif req["exptype"] == "Real Time":
                # this uses "run till abort" mode - how do we abort it?
                andor.setAcquisitionMode(5)
                andor.setExposureTime(0.3)
                andor.setKineticCycleTime(0)

            elif req["exptype"] == "Series":
                andor.setAcquisitionMode(3)
                andor.setNumberKinetics(int(req["expnum"]))
                andor.setExposureTime(float(req["exptime"]))

            file_name = f"{req['filename']}.fits"

            andor.startAcquisition()
            status = andor.getStatus()
            # todo: review parallelism, threading behavior is what we want?
            while status == 20072:
                status = andor.getStatus()
                app.logger.info("Acquisition in progress")

            time.sleep(float(req["exptime"]) + 0.5)
            img = andor.getAcquiredData(
                dim
            )  # TODO: throws an error here! gotta wait for acquisition

            if img["status"] == 20002:
                # use astropy here to write a fits file
                andor.setShutter(1, 0, 50, 50)  # closes shutter
                # home_filter() # uncomment if using filter wheel
                hdu = fits.PrimaryHDU(img["data"])
                hdu.header["EXP_TIME"] = (
                    float(req["exptime"]),
                    "Exposure Time (Seconds)",
                )
                hdu.header["EXP_TYPE"] = (
                    str(req["exptype"]),
                    "Exposure Type (Single, Real Time, or Series)",
                )
                hdu.header["IMG_TYPE"] = (
                    str(req["imgtype"]),
                    "Image Type (Bias, Flat, Dark, or Object)",
                )
                hdu.header["FILTER"] = (str(req["filtype"]), "Filter (Ha, B, V, g, r)")

                fname = req["filename"]
                fname = formatFileName(fname)
                hdu.writeto(f"{FITS_PATH}/{fname}", overwrite=True)

                return {
                    "filename": fname,
                    "url": url_for("static", filename=f"fits_files/{fname}"),
                    "message": "Capture Successful",
                }

            else:
                andor.setShutter(1, 0, 50, 50)
                home_filter()  # uncomment if using filter wheel
                return {"message": str("Capture Unsuccessful")}

    # we shouldn't download files locally - instead, lets upload them to server instead
    # def send_file(file_name):
    #   uploads = os.path.join(current_app.root_path, './fits_files/')
    #   return send_from_directory(uploads, file_name, as_attachment=True)

    @app.route("/fw_test")
    def route_fw_test_helper():
        res = asyncio.run(route_fw_test())
        return res

    async def route_fw_test():
        """
        Tests the example server server.py
        """

        reader, writer = await asyncio.open_connection("127.0.0.1", 5503)
        writer.write(b"getFilter\n")
        await writer.drain()
        received = await reader.readline()
        writer.close()
        await writer.wait_closed()

        return {"message": received.decode()}

    return app


def OnExitApp():
    andor.shutdown()


atexit.register(OnExitApp)

app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=3000)
