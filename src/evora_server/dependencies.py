#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-08
# @Filename: dependencies.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends

from evora_server import andor_wrapper


def get_andor_wrapper():
    """Andor wrapper dependency."""

    return andor_wrapper


AndorWrapper = Annotated[Any, Depends(get_andor_wrapper)]
