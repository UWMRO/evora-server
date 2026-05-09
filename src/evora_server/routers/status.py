#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-08
# @Filename: status.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel

from evora_server.dependencies import AndorWrapper


router = APIRouter(prefix="/status", tags=["status"])


class StatusResponseModel(BaseModel):
    """Model for the status response."""

    status: Annotated[int, "Status code returned by the Andor camera."]
    funcstatus: Annotated[int, "Function status returned by the Andor camera."]


@router.get(
    "/",
    response_model=StatusResponseModel,
    summary="Returns the status of the Andor camera.",
)
async def get_status(andor: AndorWrapper):
    """Returns the status of the Andor camera."""

    return StatusResponseModel(**andor.getStatus())
