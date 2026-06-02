#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2026-06-02
# @Filename: framing.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, Field

from evora_server import config
from evora_server.framing.models import PlateSolvingResult


router = APIRouter(prefix="/framing", tags=["framing"])


class PlateSolvePostPayload(BaseModel):
    """Request model for plate solving."""

    filename: Annotated[
        str | None,
        Field(
            description="Path to the FITS file to be solved. "
            "If not provided, the last exposure will be used."
        ),
    ] = None
    hint_ra_deg: Annotated[
        float,
        Field(description="Estimated Right Ascension in degrees.", default=0.0),
    ]
    hint_dec_deg: Annotated[
        float,
        Field(description="Estimated Declination in degrees.", default=0.0),
    ]
    hint_radius_deg: Annotated[
        float,
        Field(description="Search radius in degrees.", default=5.0),
    ]


@router.post(
    "/plate_solve",
    description="Performs plate solving on the given FITS file.",
)
def route_plate_solve(payload: PlateSolvePostPayload) -> PlateSolvingResult:
    """Endpoint to perform plate solving on a FITS file."""

    from astrometry import PositionHint

    from evora_server.framing.framing_assist import solve_fits

    file_path = str(payload.filename or config.last_exposure_path)
    position_hint = PositionHint(
        ra_deg=float(payload.hint_ra_deg),
        dec_deg=float(payload.hint_dec_deg),
        radius_deg=float(payload.hint_radius_deg),
    )

    res = solve_fits(file_path, position_hint=position_hint)
    return res
