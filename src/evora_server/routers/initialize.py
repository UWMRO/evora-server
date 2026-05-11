#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-08
# @Filename: initialize.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel

from evora_server.dependencies import AndorWrapper
from evora_server.tools.camera import check_camera_initialized


router = APIRouter(prefix="", tags=["initialize"])


class InitializeResponseModel(BaseModel):
    """Model for the initialize response."""

    dimensions: Annotated[
        tuple[int, int],
        "Tuple of the image dimensions (width, height).",
    ]
    status: Annotated[
        int,
        "Status code returned by the Andor camera.",
    ]


class ShutdownResponseModel(BaseModel):
    """Model for the shutdown response."""

    status: Annotated[
        int,
        "Status code returned by the Andor camera.",
    ]


@router.get("/initialize", summary="Initializes the Andor camera.")
async def get_initialize_camera(andor_wrapper: AndorWrapper) -> InitializeResponseModel:
    """Initializes the Andor camera."""

    from evora_server.andor_routines import activateCooling, startup

    startup_status = startup(andor_wrapper)
    activateCooling(andor_wrapper)

    return startup_status


@router.get("/shutdown", summary="Shuts down the Andor camera.")
async def get_shutdown_camera(andor_wrapper: AndorWrapper) -> ShutdownResponseModel:
    """Shuts down the Andor camera."""

    from evora_server.andor_routines import deactivateCooling

    check_camera_initialized()

    deactivateCooling(andor_wrapper)
    status = andor_wrapper.shutdown()

    return ShutdownResponseModel(**status)
