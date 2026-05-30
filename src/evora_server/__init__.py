#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-08
# @Filename: __init__.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import logging
import os
import sys
from importlib.metadata import version

from evora_server._config import Config


__all__ = ["IS_DEBUG", "andor_wrapper", "__version__", "config", "logger"]


config = Config()

# Are we in debug mode?
IS_DEBUG = os.getenv("EVORA_SERVER_DEBUG", "0").lower() in ("1", "true", "yes")

# Decide whether to provide the mock Andor module or the real wrapper to the camera API.
if IS_DEBUG:
    from evora_server.mock import AndorWrapperMocker

    andor_wrapper = AndorWrapperMocker()
else:
    if sys.platform == "linux":
        try:
            from evora_server import andor_wrapper
        except Exception as err:
            raise ImportError(
                f"Failed to import andor_wrapper: {err} \n\n"
                "Did you forget to install the package or "
                "mean to use EVORA_SERVER_DEBUG=1?"
            )
    else:
        raise ImportError(
            "Andor wrapper is only supported on Linux. "
            "Please set EVORA_SERVER_DEBUG=1 to use the mock implementation."
        )

logger = logging.getLogger("uvicorn.error")


__version__ = version("evora-server")
