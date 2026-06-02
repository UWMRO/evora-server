#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-09
# @Filename: focuser.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import Annotated

import httpx
from pydantic import BaseModel, Field

from evora_server import IS_DEBUG, AndorWrapperMocker, andor_wrapper, config


__all__ = ["get_focus", "set_focus"]


class FocuserStatusModel(BaseModel):
    """Model for the focuser status."""

    error: Annotated[
        bool,
        Field(description="Whether the status command returned an error."),
    ]
    moving: Annotated[
        bool,
        Field(description="Whether the focuser is currently moving."),
    ]
    step: Annotated[
        int,
        Field(description="The current step position of the focuser."),
    ]
    limit: Annotated[
        bool,
        Field(description="Whether the focuser has reached a limit."),
    ]


class FocuserMoveModel(BaseModel):
    """Model for the focuser move command."""

    error: Annotated[
        bool,
        Field(description="Whether the move command returned an error."),
    ]


async def get_focus() -> FocuserStatusModel:
    """Returns the current focuser position."""

    if IS_DEBUG:
        assert isinstance(andor_wrapper, AndorWrapperMocker)
        state = andor_wrapper.state
        return FocuserStatusModel(
            error=False,
            moving=False,
            step=int(state.focus_position),
            limit=False,
        )

    async with httpx.AsyncClient(base_url=config.focus_api_url) as client:
        response = await client.get("/status")
        response.raise_for_status()
        data = response.json()
        model = FocuserStatusModel(error=False, **data)
        if model.error:
            raise RuntimeError("Error getting focuser status.")
        return model


async def set_focus(position: float, absolute: bool = False) -> None:
    """Sets the focuser position."""

    if IS_DEBUG:
        assert isinstance(andor_wrapper, AndorWrapperMocker)
        state = andor_wrapper.state
        state.focus_position = position
        return

    if absolute:
        current_position = await get_focus()
        position = position - current_position.step

    position = int(position)

    async with httpx.AsyncClient(base_url=config.focus_api_url, timeout=60) as client:
        response = await client.get(f"/move/{position}")
        response.raise_for_status()
        data = response.json()
        model = FocuserMoveModel(**data)
        if model.error:
            raise RuntimeError("Error moving focuser.")

    return
