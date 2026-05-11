#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-09
# @Filename: tools.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import pathlib
import re

from typing import Literal

import numpy
from astropy.io import fits
from astropy.time import Time
from fastapi import HTTPException

from evora_server import IS_DEBUG, andor_wrapper, config, logger
from evora_server.filter_wheel import get_filter
from evora_server.focus import get_focus


__all__ = ["create_hdul", "get_exposure_path", "check_camera_initialized"]


def check_camera_initialized(error_type: Literal["runtime", "http"] = "http"):
    """Checks that the camera is initialized."""

    status = andor_wrapper.getStatus()["status"]

    if status == config.DRV_NOT_INITIALIZED:
        if error_type == "runtime":
            raise RuntimeError("Camera is not initialized.")
        else:
            raise HTTPException(status_code=500, detail="Camera is not initialized.")


async def create_hdul(
    data: numpy.ndarray,
    exposure_time: float,
    start_time: float,
    image_path: str | None = None,
    image_type: str | None = None,
    exposure_type: str | None = None,
    comment: str | None = None,
) -> fits.HDUList:
    """Creates an HDUList from the given data and image parameters."""

    # Check that the camera is initialized.
    status = andor_wrapper.getStatus()["status"]
    if status == config.DRV_NOT_INITIALIZED:
        raise RuntimeError("Camera is not initialized.")

    # Get the camera temperature.
    temperature = andor_wrapper.getStatusTEC()["temperature"]

    # Get filter wheel value.
    filter_ = await get_filter()

    # Get focus position.
    try:
        focus = await get_focus()
    except Exception as err:
        focus = None
        logger.warning(f"Failed to get focus position: {err}")

    # Convert start time to ISO format.
    date_obs = Time(start_time, format="unix")
    date_obs_isot = date_obs.isot

    # Create the FITS header.
    header = fits.Header()
    header["DATE-OBS"] = date_obs_isot
    header["COMMENT"] = comment
    header["INSTRUME"] = ("iKon-M 934 CCD DU934P-BEX2-DD", "Camera model")
    header["XBINNING"] = ("1", "X Binning")
    header["YBINNING"] = ("1", "Y Binning")
    header["XPIXSZ"] = ("13", "X Pixel Size")
    header["YPIXSZ"] = ("13", "Y Pixel Size")
    header["FOCALLEN"] = ("5766", "Focal Length")

    header["IMGPATH"] = (image_path, "Path to the image file")
    header["EXPTIME"] = (float(exposure_time), "Exposure Time (Seconds)")
    header["EXP_TYPE"] = (exposure_type, "Exposure Type (Single, Real Time, or Series)")
    header["IMAGETYP"] = (image_type, "Image Type (Bias, Flat, Dark, or Object)")

    header["FILTER"] = (filter_, "Filter name")
    header["CCD-TEMP"] = (round(temperature, 2), "CCD Temperature [C]")
    header["FOCUS"] = (focus, "Relative focus position [microns]")

    header["TESTEXP"] = (IS_DEBUG, "Is this a test exposure taken in debug mode?")

    hdu = fits.PrimaryHDU(data=data, header=header)
    hdul = fits.HDUList([hdu])

    return hdul


def get_exposure_path(filename: str | None = None) -> pathlib.Path:
    """Returns a valid file path for a camera exposure.

    Crestes a sequential path for a new exposure. If ``filename`` is provided, the
    resulting path is of the form ``{DATA_PATH}/{date}/{filename}``. Otherwise,
    the path is of the form ``{DATA_PATH}/{date}/ecam-{seq:04d}.fits``, where
    ``seq`` is the next available sequence number for that date.


    """

    data_path = pathlib.Path(config.DATA_PATH)
    default_image_name = "ecam-{seq:04d}.fits"

    date: str = Time.now().utc.isot.split("T")[0].replace("-", "")
    parent_dir = data_path / date

    invalid_characters = [":", "<", ">", "/", "\\", '"', "|", "?", "*", ".."]

    # If we did not provide a filename or it is invalid, create a sequential filename.
    seq = 1
    if (
        filename is None
        or filename == ""
        or any(c in filename for c in invalid_characters)
    ):
        all_files = list(sorted(parent_dir.glob("ecam-*.fits")))
        if len(all_files) > 0:
            match = re.search(r"ecam\-([0-9]+)", str(all_files[-1]))
            if match:
                seq = int(match.group(1)) + 1

    file_ = default_image_name.format(seq=seq)

    # Ensure extension is .fits
    if file_[-1] == ".":
        file_ += "fits"
    if len(file_) < 5 or file_[-5:] != ".fits":
        file_ += ".fits"

    # Ensure nothing gets overwritten
    while True:
        file_path = parent_dir / file_
        if not file_path.exists():
            break
        seq += 1
        file_ = default_image_name.format(seq=seq)

    return file_path
