#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-09
# @Filename: focus.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import Annotated

import httpx
from pydantic import BaseModel, Field

from evora_server import IS_DEBUG, AndorWrapperMocker, andor_wrapper
from evora_server.config import FOCUS_API_URL


__all__ = ["get_focus", "set_focus"]


class FocusStatusModel(BaseModel):
    """Model for the focus status."""

    error: Annotated[
        bool,
        Field(description="Whether the status command returned an error."),
    ]
    moving: Annotated[
        bool,
        Field(description="Whether the focus is currently moving."),
    ]
    step: Annotated[
        int,
        Field(description="The current step position of the focus."),
    ]
    limit: Annotated[
        bool,
        Field(description="Whether the focus has reached a limit."),
    ]


class FocusMoveModel(BaseModel):
    """Model for the focus move command."""

    error: Annotated[
        bool,
        Field(description="Whether the move command returned an error."),
    ]


async def get_focus() -> float:
    """Returns the current focus position."""

    if IS_DEBUG:
        assert isinstance(andor_wrapper, AndorWrapperMocker)
        state = andor_wrapper.state
        return state.focus_position

    async with httpx.AsyncClient(base_url=FOCUS_API_URL) as client:
        response = await client.get("/status")
        response.raise_for_status()
        data = response.json()
        model = FocusStatusModel(**data)
        if model.error:
            raise RuntimeError("Error getting focus status.")
        return float(model.step)


async def set_focus(position: float, absolute: bool = False) -> None:
    """Sets the focus position."""

    if IS_DEBUG:
        assert isinstance(andor_wrapper, AndorWrapperMocker)
        state = andor_wrapper.state
        state.focus_position = position
        return

    if absolute:
        current_position = await get_focus()
        position = position - current_position

    position = int(position)

    async with httpx.AsyncClient(base_url=FOCUS_API_URL, timeout=60) as client:
        response = await client.get(f"/move/{position}")
        response.raise_for_status()
        data = response.json()
        model = FocusMoveModel(**data)
        if model.error:
            raise RuntimeError("Error moving focus")

    return
