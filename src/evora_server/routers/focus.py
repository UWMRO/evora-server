#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-11
# @Filename: focus.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query


router = APIRouter(prefix="/focus", tags=["focus"])


@router.get("/", summary="Gets the current focus position.")
async def get_focus() -> float:
    """Gets the current focus position."""

    from evora_server.tools.focus import get_focus

    try:
        return await get_focus()
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


@router.get("/move", summary="Moves the focus position.")
async def move_focus(
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

    from evora_server.tools.focus import set_focus

    try:
        await set_focus(position, absolute)
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err
