#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: Siyu
# @Filename: models.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from enum import Enum

from typing import Annotated

from pydantic import BaseModel, Field


class PlateSolvingResultStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class PlateSolvingResult(BaseModel):
    status: Annotated[
        PlateSolvingResultStatus,
        Field(description="Status of the plate solving result."),
    ]
    failure_reason: Annotated[
        str | None,
        Field(description="Reason for failure, if applicable."),
    ] = None
    center_ra_deg: Annotated[
        float,
        Field(description="Right ascension of the center of the image in degrees."),
    ] = 0.0
    center_dec_deg: Annotated[
        float,
        Field(description="Declination of the center of the image in degrees."),
    ] = 0.0
    visualization_url: Annotated[
        str | None,
        Field(description="URL for the visualization of the solved image."),
    ] = None
