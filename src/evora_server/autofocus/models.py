#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-11-19
# @Filename: models.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class AutofocusStatusModel(BaseModel):
    """Status of the focus sweep."""

    state: Annotated[
        Literal["idle", "running", "awaiting_confirm", "aborted", "error", "done"],
        Field(description="Where the sweep is."),
    ]
    message: Annotated[
        str,
        Field(description="What the client should report."),
    ]
    completed: Annotated[
        int,
        Field(description="Frames measured so far."),
    ]
    total: Annotated[
        int,
        Field(description="Frames requested for this sweep."),
    ]
    recommended_position: Annotated[
        int | None,
        Field(description="Optimal focus step, once the sweep has a result."),
    ] = None
