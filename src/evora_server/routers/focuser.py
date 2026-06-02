#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-11
# @Filename: focuser.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from evora_server.tools.focuser import FocuserStatusModel, get_focus, set_focus


router = APIRouter(prefix="/focuser", tags=["focuser"])


@router.get("/status", summary="Gets the current focuser position.")
async def route_get_focus() -> FocuserStatusModel:
    """Gets the current focuser position."""

    try:
        return await get_focus()
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


@router.get("/move", summary="Moves the focuser position.")
async def route_move_focus(
    position: Annotated[
        float,
        Query(description="The position to move the focuser to."),
    ],
    absolute: Annotated[
        bool,
        Query(description="Absolute or relative focuser position."),
    ] = False,
) -> None:
    """Moves the focuser position."""

    try:
        await set_focus(position, absolute)
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err
