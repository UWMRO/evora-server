#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-11
# @Filename: tcs.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import Annotated

import httpx
from pydantic import BaseModel, Field

from evora_server import config


__all__ = ["StatusResponse", "get_tcs_status"]


class StatusResponse(BaseModel):
    """Response model for the status endpoint."""

    bool_params: Annotated[
        int,
        Field(description="Bitmask indicating the status of the telescope."),
    ]
    bool_params_labels: Annotated[
        list[str],
        Field(description="Labels for the boolean parameters in the status bitmask."),
    ]
    right_ascension: Annotated[
        float,
        Field(description="Right ascension of the telescope [hours]."),
    ]
    declination: Annotated[
        float,
        Field(description="Declination of the telescope [degrees]."),
    ]
    altitude: Annotated[
        float,
        Field(description="Altitude of the telescope [degrees]."),
    ]
    azimuth: Annotated[
        float,
        Field(description="Azimuth of the telescope [degrees]."),
    ]
    secondary_axis_angle: Annotated[
        float,
        Field(description="Secondary axis angle of the telescope [degrees]."),
    ]
    primary_axis_angle: Annotated[
        float,
        Field(description="Primary axis angle of the telescope [degrees]."),
    ]
    scope_sidereal_time: Annotated[
        float,
        Field(description="Scope sidereal time."),
    ]
    scope_julian_day: Annotated[
        float,
        Field(description="Scope Julian day."),
    ]
    scope_time: Annotated[
        float,
        Field(description="Scope time."),
    ]
    air_mass: Annotated[
        float,
        Field(description="Airmass."),
    ]


async def get_tcs_status() -> StatusResponse:
    """Gets the current status of the telescope."""

    async with httpx.AsyncClient() as client:
        response = await client.get(config.tcs_api_url + "/ascii/status")
        response.raise_for_status()
        data = response.json()

    return StatusResponse(**data)
