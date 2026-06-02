#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: Siyu
# @Filename: models.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class FocusSession(BaseModel):
    """Model representing a focus session."""

    id: Annotated[
        str,
        Field(description="Unique identifier for the focus session"),
    ] = ""

    focuser_positons: Annotated[
        list[float],
        Field(description="List of focuser positions", default_factory=list),
    ]

    fwhm_metrics: Annotated[
        list[float],
        Field(
            description="List of FWHM values corresponding to the focuser positions",
            default_factory=list,
        ),
    ]

    hfd_metrics: Annotated[
        list[dict[str, float]],
        Field(
            description="List of HFD values corresponding to the focuser positions",
            default_factory=list,
        ),
    ]

    files: Annotated[
        list[str],
        Field(description="List of file paths", default_factory=list),
    ]

    fwhm_fit: Annotated[
        list[float] | None,
        Field(description="Coefficients of the FWHM fit", default=None),
    ] = None

    hfd_fits: Annotated[
        dict[str, list[float]] | None,
        Field(description="Coefficients of the HFD fit for each method", default=None),
    ] = None

    predicted_min_fwhm: Annotated[
        float | None,
        Field(description="Predicted focuser position for minimum FWHM", default=None),
    ] = None

    predicted_min_hfd: Annotated[
        dict[str, float] | None,
        Field(
            description="Predicted focuser position for minimum HFD "
            "for different methods",
        ),
    ] = None
