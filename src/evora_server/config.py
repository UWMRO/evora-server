#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-08
# @Filename: config.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import os
import pathlib
from types import SimpleNamespace


class Config(SimpleNamespace):
    """Configuration for the Evora server."""

    # Focus API URL.
    FOCUS_API_URL = os.environ.get("FOCUS_API_URL", "http://127.0.0.1/focus")

    # TCS API URL.
    TCS_API_URL = os.environ.get("TCS_API_URL", "http://127.0.0.1/tcs")

    # Data path
    DATA_PATH = "/data/ecam"

    # Status constants, taken from atmcdLXd.h
    DRV_SUCCESS = 20002
    DRV_TEMPERATURE_OFF = 20034
    DRV_TEMPERATURE_STABILIZED = 20036
    DRV_NOT_INITIALIZED = 20075
    DRV_ACQUIRING = 20072
    DRV_IDLE = 20073

    # Temperature limits.
    min_temp = -80.0
    max_temp = 50.0

    # Filter value to filter wheel position.
    FILTER_DICT = {
        "Ha": 0,
        "B": 1,
        "V": 2,
        "g": 3,
        "r": 4,
        "i": 5,
    }

    # Reverse filter dictionary for position to filter name.
    FILTER_DICT_REVERSE = {
        0: "Ha",
        1: "B",
        2: "V",
        3: "g",
        4: "r",
        5: "i",
    }

    # Path to the last exposure taken.
    last_exposure_path: pathlib.Path | None = None
