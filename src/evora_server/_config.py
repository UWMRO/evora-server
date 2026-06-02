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

from evora_server.focus.models import FocusSession


class Config(SimpleNamespace):
    """Configuration for the Evora server. A singleton class."""

    _instance: Config | None = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, *args, **kwargs):
        from evora_server import IS_DEBUG

        if getattr(self, "_singleton_initialized", False):
            return
        super().__init__(*args, **kwargs)
        self._singleton_initialized = True

        if IS_DEBUG:
            self.FRAMING_CACHE_DIR = "./" + self.FRAMING_CACHE_DIR

        self.focus_session = None

    # Focus API URL.
    focus_api_url: str = os.environ.get("FOCUS_API_URL", "http://127.0.0.1/focus")

    # TCS API URL.
    tcs_api_url: str = os.environ.get("TCS_API_URL", "http://127.0.0.1/tcs")

    # Focus wheel IP and port.
    focus_wheel_ip: str = os.environ.get("FOCUS_WHEEL_IP", "72.233.250.84")
    focus_wheel_port: int = int(os.environ.get("FOCUS_WHEEL_PORT", "9999"))

    # Data path
    data_path: str = "/data/ecam"

    # Status constants, taken from atmcdLXd.h
    DRV_SUCCESS: int = 20002
    DRV_TEMPERATURE_OFF: int = 20034
    DRV_TEMPERATURE_STABILIZED: int = 20036
    DRV_NOT_INITIALIZED: int = 20075
    DRV_ACQUIRING: int = 20072
    DRV_IDLE: int = 20073

    # Temperature limits.
    min_temp: float = -80.0
    max_temp: float = 50.0

    # Filter value to filter wheel position.
    filter_dict: dict[str, int] = {
        "Ha": 0,
        "B": 1,
        "V": 2,
        "g": 3,
        "r": 4,
        "i": 5,
    }

    # Reverse filter dictionary for position to filter name.
    filter_dict_reverse: dict[int, str] = {
        0: "Ha",
        1: "B",
        2: "V",
        3: "g",
        4: "r",
        5: "i",
    }

    # Path to the last exposure taken.
    last_exposure_path: pathlib.Path | None = None

    # Framing options
    FRAMING_MAX_SOURCES = 50
    FRAMING_CACHE_DIR = "/data/astrometry-index"

    # Focusing options
    FOCUS_SEP_MIN_AREA = 40
    FOCUS_APERTURE_R = 10

    focus_session: FocusSession | None = None
