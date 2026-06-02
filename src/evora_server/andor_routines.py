#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-08
# @Filename: andor_routines.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import time

from evora_server import config


def startup(andor_wrapper):
    """Initializes the camera and sets the acquisition mode to single scan.

    Parameters
    ----------
    andor_wrapper
        The Andor wrapper instance.

    Returns
    -------
    dimensions
        Tuple of the image dimensions.
    status
        Status code returned by the Andor camera.

    """

    andor_wrapper.initialize()
    andor_wrapper.setAcquisitionMode(1)
    andor_wrapper.setExposureTime(0.1)

    image_dimensions: tuple[int, int] = andor_wrapper.getDetector()["dimensions"]

    andor_wrapper.setShutter(1, 0, 50, 50)
    andor_wrapper.setImage(1, 1, 1, image_dimensions[0], 1, image_dimensions[1])

    return {"dimensions": image_dimensions, "status": config.DRV_SUCCESS}


def activateCooling(andor_wrapper, target_temperature=-10):
    """Activates the camera cooling system and sets the target temperature.

    Parameters
    ----------
    andor_wrapper
        The Andor wrapper instance.
    target_temperature
        The desired temperature of the camera sensor.

    Returns
    -------
    status
         Status code returned by the Andor camera.

    """

    # andor_wrapper.setFanMode(2)
    andor_wrapper.coolerOn()
    andor_wrapper.setTargetTEC(target_temperature)

    return config.DRV_SUCCESS


def deactivateCooling(andor_wrapper, fan_mode_high=False):
    """Deactivates the camera cooling system.

    Parameters
    ----------
    andor_wrapper
        The Andor wrapper instance.
    fan_mode_high
        Whether the fan mode should be set to high.

    Returns
    -------
    status
        Status code returned by the Andor camera.

    """

    andor_wrapper.coolerOff()
    andor_wrapper.setFanMode(0 if fan_mode_high else 1)

    return config.DRV_SUCCESS


def acquisition(andor_wrapper, dim, exposure_time=0.1):
    """Acquires an image with the given dimensions and exposure time.

    Parameters
    ----------
    dim
        Tuple of the image dimensions.
    exposure_time
        The exposure time for the image acquisition.

    Returns
    -------
    data
        The acquired image data

    """

    andor_wrapper.setExposureTime(exposure_time)
    andor_wrapper.startAcquisition()

    time.sleep(exposure_time + 0.5)

    return {
        "data": andor_wrapper.getAcquiredData(dim)["data"],
        "status": config.DRV_SUCCESS,
    }


def acquireBias(andor_wrapper, dim):
    """Acquires a bias image.

    Parameters
    ----------
    dim
        Tuple of the image dimensions.

    Returns
    -------
    image
        The acquired bias image.

    """

    andor_wrapper.setShutter(1, 2, 50, 50)
    andor_wrapper.setImage(1, 1, 1, dim[0], 1, dim[1])

    image = acquisition(andor_wrapper, dim, exposure_time=0.0)
    andor_wrapper.setShutter(1, 0, 50, 50)

    return image
