#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-09
# @Filename: filter.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query


router = APIRouter(prefix="/filter", tags=["filter"])


@router.get("/", summary="Gets the current filter in the wheel.")
async def get_filter() -> str:
    """Gets the current filter in the wheel."""

    from evora_server.tools.filter_wheel import get_filter

    try:
        return await get_filter()
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


@router.get("/set", summary="Sets the filter in the wheel.")
async def set_filter(
    filter_name: Annotated[str, Query(description="The name of the filter to set.")],
) -> None:
    """Sets the filter in the wheel."""

    from evora_server.tools.filter_wheel import set_filter

    try:
        await set_filter(filter_name)
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


@router.get("/home", summary="Homes the filter wheel.")
async def home_filter() -> None:
    """Homes the filter wheel."""

    from evora_server.tools.filter_wheel import home_wheel

    try:
        await home_wheel()
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err
