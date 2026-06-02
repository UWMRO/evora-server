#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2026-06-02
# @Filename: focus.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Response
from pydantic import BaseModel

from evora_server import config
from evora_server.focus.focus_assist import (
    find_focus_position,
    plot_fit,
    stat_for_image,
)
from evora_server.focus.models import FocusSession


router = APIRouter(prefix="/focus", tags=["focus"])


def analyze(session: FocusSession) -> tuple[float, dict[str, float]]:
    fwhm_metrics = session.fwhm_metrics
    focuser_positons = session.focuser_positons

    hfd_curve_dps: dict[str, list[float]] = {
        "sep": [dp["sep"] for dp in session.hfd_metrics],
        "my": [dp["my"] for dp in session.hfd_metrics],
        "PHD": [dp["PHD"] for dp in session.hfd_metrics],
    }
    fwhm_min, hfd_min, fwhm_fit, hfd_fits = find_focus_position(
        focuser_positons,
        fwhm_metrics,
        hfd_curve_dps,
    )
    session.fwhm_fit = fwhm_fit
    session.hfd_fits = hfd_fits
    session.predicted_min_fwhm = fwhm_min
    session.predicted_min_hfd = hfd_min

    return fwhm_min, hfd_min


@router.get(
    "/plot/{sid}",
    description="Retrieves the focus plot.",
    response_class=Response,
)
def route_retrieve_plot(
    sid: Annotated[
        str,
        Path(description="The session ID for which to retrieve the focus plot."),
    ],
):
    """Retrieves the focus plot for a given session ID."""

    focus_session = config.focus_session

    if focus_session is None or focus_session.id != sid:
        raise HTTPException(status_code=404, detail="Focus session not found.")

    fwhm_metrics = focus_session.fwhm_metrics
    focuser_positons = focus_session.focuser_positons
    fwhm_fit = focus_session.fwhm_fit
    hfd_fits = focus_session.hfd_fits
    hfd_curve_dps = {
        "sep": [dp["sep"] for dp in focus_session.hfd_metrics],
        "my": [dp["my"] for dp in focus_session.hfd_metrics],
        "PHD": [dp["PHD"] for dp in focus_session.hfd_metrics],
    }

    if hfd_fits is None or fwhm_fit is None:
        raise HTTPException(status_code=404, detail="Focus fits not found.")

    image = plot_fit(
        focuser_positons,
        fwhm_metrics,
        hfd_curve_dps,
        fwhm_fit,
        hfd_fits,
    )

    return Response(content=image, media_type="image/png")


@router.get("/reset", description="Resets the focus session for a given session ID.")
def route_reset():
    """Resets the focus session."""
    config.focus_session = None

    return {}


class FocusPointPostModel(BaseModel):
    """Model for the focus point post request."""

    sid: Annotated[
        str,
        "The session ID for which to add the focus datapoint.",
    ]
    filename: Annotated[
        str,
        "The filename of the image to analyze for the focus datapoint.",
    ]
    focuser_position: Annotated[
        int,
        "The focuser position at which the image was taken.",
    ]


@router.post(
    "/add_focus_datapoint",
    description="Adds a focus datapoint to the current session.",
    response_model=FocusSession,
)
def route_add_focus_datapoint(payload: FocusPointPostModel):
    """Adds a focus datapoint to the current session."""

    sid = payload.sid
    filename: str = payload.filename
    focuser_position = int(payload.focuser_position)

    if config.focus_session is None:
        config.focus_session = FocusSession(
            id=sid,
            focuser_positons=[],
            fwhm_metrics=[],
            hfd_metrics=[],
            files=[],
        )

    config.focus_session.focuser_positons.append(focuser_position)
    config.focus_session.files.append(filename)

    (
        median_fwhm,
        median_sep_hfd,
        median_my_hfd,
        median_phd_hfd,
    ) = stat_for_image(filename)

    config.focus_session.hfd_metrics.append(
        {
            "sep": median_sep_hfd,
            "my": median_my_hfd,
            "PHD": median_phd_hfd,
        }
    )
    config.focus_session.fwhm_metrics.append(median_fwhm)

    if len(config.focus_session.focuser_positons) >= 3:
        analyze(config.focus_session)

    return config.focus_session
