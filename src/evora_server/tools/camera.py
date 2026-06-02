#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-11
# @Filename: camera.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import Literal

from fastapi import HTTPException

from evora_server import andor_wrapper, config


__all__ = ["check_camera_initialized"]


def check_camera_initialized(error_type: Literal["runtime", "http"] = "http"):
    """Checks that the camera is initialized."""

    status = andor_wrapper.getStatus()["status"]

    if status == config.DRV_NOT_INITIALIZED:
        if error_type == "runtime":
            raise RuntimeError("Camera is not initialized.")
        else:
            raise HTTPException(status_code=500, detail="Camera is not initialized.")
