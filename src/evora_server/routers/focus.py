#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-11
# @Filename: focus.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from evora_server.tools.focus import FocusStatusModel, get_focus, set_focus


router = APIRouter(prefix="/focus", tags=["focus"])


@router.get("/", summary="Gets the current focus position.")
async def route_get_focus() -> FocusStatusModel:
    """Gets the current focus position."""

    try:
        return await get_focus()
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


@router.get("/move", summary="Moves the focus position.")
async def route_move_focus(
    position: Annotated[
        float,
        Query(description="The position to move the focus to."),
    ],
    absolute: Annotated[
        bool,
        Query(description="Absolute or relative focus position."),
    ] = False,
) -> None:
    """Moves the focus position."""

    try:
        await set_focus(position, absolute)
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err
