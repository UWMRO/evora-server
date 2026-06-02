#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2026-05-30
# @Filename: telescope.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from fastapi import APIRouter

from evora_server.tools.tcs import TCSStatusResponse, get_tcs_status


router = APIRouter(prefix="/telescope", tags=["telescope"])


@router.get(
    "/status",
    response_model=TCSStatusResponse,
    description="Returns the current status of the telescope.",
)
async def get_telescope_status():
    """Returns the current status of the telescope."""

    return await get_tcs_status()
