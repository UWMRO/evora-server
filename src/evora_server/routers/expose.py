#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-08
# @Filename: expose.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import asyncio
import pathlib
import tempfile
import time

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from evora_server import config, logger
from evora_server.dependencies import AndorWrapper
from evora_server.tools import check_camera_initialized, create_hdul, get_exposure_path


router = APIRouter(prefix="/expose", tags=["expose"])


abort_lock_path = pathlib.Path(tempfile.gettempdir()) / "evora_abort.lock"


class ExposurePostParams(BaseModel):
    """Model for the exposure parameters."""

    exposure_time: Annotated[
        float,
        Field(
            description="Exposure time in seconds.",
            ge=0,
            le=3600,
        ),
    ]
    exposure_type: Annotated[
        Literal["single", "real time", "series"],
        Field(description="Type of exposure (single, real time, series)."),
    ]
    image_type: Annotated[
        Literal["object", "dark", "bias", "flat"],
        Field(description="Type of image (object, dark, bias, flat)."),
    ]
    filter_: Annotated[
        str | None,
        Field(
            alias="filter",
            description="Filter to use for the exposure (optional).",
        ),
    ] = None
    n_frames: Annotated[
        int,
        Field(description="Number of frames to take for series exposures (optional)."),
    ] = 1
    comment: Annotated[
        str | None,
        Field(description="Comment to include in the FITS header (optional)."),
    ] = None

    @field_validator("exposure_type", "image_type")
    @classmethod
    def validate_lowercase(cls, value: str) -> str:
        return value.lower()


class ExposureResponseModel(BaseModel):
    """Model for the exposure response."""

    filename: Annotated[
        str | None,
        Field(description="Filename of the saved exposure."),
    ]
    path: Annotated[
        str | None,
        Field(description="Path where the exposure is saved."),
    ]
    success: Annotated[
        bool,
        Field(description="Indicates whether the exposure was successful."),
    ]
    aborted: Annotated[
        bool,
        Field(description="Indicates whether the exposure was aborted."),
    ] = False


@router.post("/", summary="Takes an exposure with the Andor camera.")
async def take_exposure(
    params: ExposurePostParams,
    andor_wrapper: AndorWrapper,
) -> ExposureResponseModel:
    """Takes an exposure with the Andor camera."""

    # Check if the camera is initialized.
    check_camera_initialized()

    # Unpack parameters.
    exposure_time = params.exposure_time
    exposure_type = params.exposure_type
    image_type = params.image_type
    filter_ = params.filter_
    n_frames = params.n_frames
    comment = params.comment

    # Check that the filter is valid if provided
    if filter_ is not None:
        if filter_ not in config.FILTER_DICT:
            raise HTTPException(status_code=400, detail=f"Invalid filter: {filter_!r}.")

    # Clear the abort lock if it exists
    if abort_lock_path.exists():
        logger.debug("Abort lock found, clearing it.")
        abort_lock_path.unlink()

    # Fail if we are already acquiring.
    status = andor_wrapper.getStatus()
    if status["status"] == config.DRV_ACQUIRING:
        raise HTTPException(
            status_code=400,
            detail="Cannot start exposure: camera is already acquiring.",
        )

    # Set shutter and image mode base of the image type.
    dim: tuple[int, int] = andor_wrapper.getDetector()["dimensions"]
    if image_type in ["bias", "dark"]:
        # Keep shutter closed during biases and darks.
        andor_wrapper.setShutter(1, 2, 50, 50)
        andor_wrapper.setImage(1, 1, 1, dim[0], 1, dim[1])
    else:
        andor_wrapper.setShutter(1, 0, 50, 50)
        andor_wrapper.setImage(1, 1, 1, dim[0], 1, dim[1])

    # Handle exposure type.
    # Refer to pages 41-45 of the SDK for acquisition mode info.
    if exposure_type in ["single", "real time"]:
        andor_wrapper.setAcquisitionMode(1)
        andor_wrapper.setExposureTime(float(exposure_time))
    elif exposure_type == "series":
        andor_wrapper.setAcquisitionMode(3)
        andor_wrapper.setNumberKinetics(int(n_frames))
        andor_wrapper.setExposureTime(float(exposure_time))

    start_time = time.time()

    # Start acquisition.
    logger.info(
        f"Starting exposure of type {exposure_type!r} with "
        f"image type {image_type!r} and exposure time {exposure_time:.1f} s."
    )

    andor_wrapper.startAcquisition()

    # Wait for acquisition to finish. Check for abort lock every tenth of a second..
    while True:
        if abort_lock_path.exists():
            logger.warning("Abort lock found, stopping acquisition.")
            andor_wrapper.abortAcquisition()
            return ExposureResponseModel(
                filename=None,
                path=None,
                success=False,
                aborted=True,
            )

        now = time.time()
        elapsed = now - start_time

        # Check that acquisition finished successfully.
        status = andor_wrapper.getStatus()
        idle = status["status"] == config.DRV_IDLE
        if idle:
            break

        # If the status is stuck in acquiring for more than exposure_time + 5 seconds,
        # something likely went wrong, so abort and raise an error.
        if elapsed > exposure_time + 5:
            raise HTTPException(
                status_code=500,
                detail="Timed out waiting for camera to finish acquisition. "
                f"Status: {status}.",
            )

        if idle and elapsed >= exposure_time:
            break

        await asyncio.sleep(0.1)

    # Wait a bit longer for good measure.
    await asyncio.sleep(0.5)

    # Grab the buffer from the camera as a numpy array.
    data = andor_wrapper.getAcquiredData(dim)

    data_status = data["status"]
    if data_status != config.DRV_SUCCESS:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get acquired data from camera. Status: {data_status}.",
        )

    # Get the image path.
    filename = "test.fits" if exposure_type == "real time" else None
    image_path = get_exposure_path(filename=filename)

    # Create the HDUList and save the FITS file.
    hdul = await create_hdul(
        data["data"],
        exposure_time,
        start_time,
        image_path=str(image_path),
        image_type=image_type,
        exposure_type=exposure_type,
        comment=comment,
    )

    image_path.parent.mkdir(parents=True, exist_ok=True)
    hdul.writeto(image_path, overwrite=(exposure_type == "real time"))

    return ExposureResponseModel(
        filename=image_path.name,
        path=str(image_path),
        success=True,
    )


@router.get("/abort", summary="Aborts the current exposure.")
async def abort_exposure() -> None:
    """Aborts the current exposure."""

    # Create the abort lock file.
    abort_lock_path.touch()
