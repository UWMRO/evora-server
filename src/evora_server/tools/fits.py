#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-09
# @Filename: fits.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import pathlib
import re

import numpy
from astropy.io import fits
from astropy.time import Time

from evora_server import IS_DEBUG, andor_wrapper, config, logger
from evora_server.tools.filter_wheel import get_filter
from evora_server.tools.focus import get_focus
from evora_server.tools.tcs import get_tcs_status


__all__ = ["create_hdul", "get_exposure_path"]


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

    # Get TCS status.
    try:
        tcs_status = await get_tcs_status()
        logger.info(f"TCS status: {tcs_status}")
    except Exception as err:
        logger.warning(f"Failed to get TCS status: {err}")
        tcs_status = None

    # Get focus position.
    try:
        focus_model = await get_focus()
        focus = focus_model.step
    except Exception as err:
        logger.warning(f"Failed to get focus position: {err}")
        focus = None

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
    header["FOCUS"] = (focus, "Relative focus position [steps]")

    if tcs_status:
        ra = round(tcs_status.right_ascension, 6)
        dec = round(tcs_status.declination, 6)
        alt = round(tcs_status.altitude, 6)
        az = round(tcs_status.azimuth, 6)
        airmass = round(tcs_status.air_mass, 3)

        # Adjust JD and LST to the start of the exposure.
        jd = tcs_status.scope_julian_day - float(exposure_time) / 86400.0
        lst = tcs_status.scope_sidereal_time - float(exposure_time) / 3600.0
        lst = round(lst, 6)
    else:
        ra = dec = alt = az = jd = lst = airmass = None

    header["RA"] = (ra, "Telescops Right ascension [hours]")
    header["DEC"] = (dec, "Telescope Declination [degrees]")
    header["ALT"] = (alt, "Telescope Altitude [degrees]")
    header["AZ"] = (az, "Telescope Azimuth [degrees]")
    header["AIRMASS"] = (airmass, "Telescope Airmass")
    header["JD"] = (jd, "Julian day from TCS")
    header["LST"] = (lst, "Local Sidereal Time from TCS [hours]")

    header["TESTEXP"] = (IS_DEBUG, "Is this a test exposure taken in debug mode?")

    hdu = fits.PrimaryHDU(data=data, header=header)
    hdul = fits.HDUList([hdu])

    return hdul


def get_exposure_path(
    filename: str | None = None,
    overwrite: bool = False,
) -> pathlib.Path:
    """Returns a valid file path for a camera exposure.

    Creates a sequential path for a new exposure. If ``filename`` is provided, the
    resulting path is of the form ``{DATA_PATH}/{date}/{filename}``. Otherwise,
    the path is of the form ``{DATA_PATH}/{date}/ecam-{seq:04d}.fits``, where
    ``seq`` is the next available sequence number for that date.


    """

    data_path = pathlib.Path(config.data_path)
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
    else:
        file_ = filename

    # Ensure extension is .fits
    if file_[-1] == ".":
        file_ += "fits"
    if len(file_) < 5 or file_[-5:] != ".fits":
        file_ += ".fits"

    # Ensure nothing gets overwritten
    while True:
        file_path = parent_dir / file_
        if not file_path.exists() or overwrite:
            break
        seq += 1
        file_ = default_image_name.format(seq=seq)

    return file_path
