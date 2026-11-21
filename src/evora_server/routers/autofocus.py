#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-11-19
# @Filename: autofocus.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from evora_server.autofocus.models import AutofocusStatusModel
from evora_server.autofocus.sweep import (
    abort_sweep,
    confirm_sweep,
    current_status,
    start_sweep,
)


router = APIRouter(prefix="/autofocus", tags=["autofocus"])


class AutofocusStartModel(BaseModel):
    """Request to run one focus sweep."""

    f0: Annotated[
        int,
        Field(description="Absolute focuser step for the first frame."),
    ]
    delta: Annotated[
        int,
        Field(description="Step added for each later frame. May be negative."),
    ]
    n_positions: Annotated[
        int,
        Field(
            ge=3,
            le=25,
            description="Number of frames, including the frame at f0.",
        ),
    ]
    exposure_time: Annotated[
        float,
        Field(
            gt=0,
            le=3600,
            description="Exposure time in seconds.",
        ),
    ]


class AutofocusConfirmModel(BaseModel):
    """Whether to move the focuser to the recommended step."""

    move: Annotated[
        bool,
        Field(description="True moves to the recommended step."),
    ]


@router.post("/start", summary="Starts a focus sweep.")
async def route_start(body: AutofocusStartModel) -> AutofocusStatusModel:
    """Moves through the requested steps, measures each frame, and stops to ask."""

    if not 10 <= abs(body.delta) <= 10000:
        raise HTTPException(
            status_code=400,
            detail="Delta must be from 10 to 10000 steps.",
        )
    return await start_sweep(
        body.f0,
        body.delta,
        body.n_positions,
        body.exposure_time,
    )


@router.get("/status", summary="Returns the focus sweep status.")
async def route_status() -> AutofocusStatusModel:
    """Returns the focus sweep status."""

    return current_status()


@router.post("/abort", summary="Stops the focus sweep.")
async def route_abort() -> AutofocusStatusModel:
    """Stops the focus sweep and leaves the focuser where it is."""

    return await abort_sweep()


@router.post("/confirm", summary="Accepts or declines the recommended focus.")
async def route_confirm(body: AutofocusConfirmModel) -> AutofocusStatusModel:
    """Moves to the recommended step, or leaves the focuser alone."""

    return await confirm_sweep(body.move)
