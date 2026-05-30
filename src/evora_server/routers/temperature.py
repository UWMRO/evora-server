#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-08
# @Filename: temperature.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from evora_server import logger
from evora_server.dependencies import AndorWrapper
from evora_server.tools.camera import check_camera_initialized


router = APIRouter(prefix="/temperature", tags=["temperature"])


class TemperatureRangeResponseModel(BaseModel):
    """Model for the temperature range response."""

    min: Annotated[
        float,
        "Minimum valid temperature for the camera.",
    ]
    max: Annotated[
        float,
        "Maximum valid temperature for the camera.",
    ]
    status: Annotated[
        int,
        "Status code returned by the Andor camera.",
    ]


class TemperatureResponseModel(BaseModel):
    """Model for the current temperature response."""

    temperature: Annotated[
        float,
        "Current temperature of the camera.",
    ]


class SetTemperatureResponseModel(BaseModel):
    """Model for the set temperature response."""

    temperature: Annotated[
        float,
        "Target temperature that was set for the camera.",
    ]


@router.get("/", summary="Returns the current temperature of the camera.")
async def get_temperature(andor_wrapper: AndorWrapper) -> TemperatureResponseModel:
    """Returns the current temperature of the camera."""

    check_camera_initialized()

    return TemperatureResponseModel(
        temperature=andor_wrapper.getStatusTEC()["temperature"]
    )


@router.get("/range", summary="Returns the valid temperature range of the camera.")
async def get_temperature_range(
    andor_wrapper: AndorWrapper,
) -> TemperatureRangeResponseModel:
    """Returns the valid temperature range of the camera."""

    return TemperatureRangeResponseModel(**andor_wrapper.getRangeTEC())


@router.get("/set", summary="Sets the target temperature of the camera.")
async def set_temperature(
    andor_wrapper: AndorWrapper,
    temperature: Annotated[float, Query(description="Target temperature")],
) -> SetTemperatureResponseModel:
    """Sets the target temperature of the camera."""

    check_camera_initialized()

    temp_range = andor_wrapper.getRangeTEC()
    min_temp = temp_range["min"]
    max_temp = temp_range["max"]

    if temperature < min_temp or temperature > max_temp:
        error = (
            f"Temperature {temperature:.2f} C is out of range. "
            f"Temperature must be between {min_temp} and {max_temp}."
        )

        logger.error(error)
        raise HTTPException(status_code=400, detail=(error))

    temperature = int(temperature)
    logger.info(f"Setting target temperature to: {temperature} C")

    andor_wrapper.setTargetTEC(temperature)

    return SetTemperatureResponseModel(temperature=temperature)
