#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-09
# @Filename: focus.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from evora_server import IS_DEBUG, AndorWrapperMocker, andor_wrapper


__all__ = ["get_focus", "set_focus"]


async def get_focus() -> float:
    """Returns the current focus position."""

    if IS_DEBUG:
        assert isinstance(andor_wrapper, AndorWrapperMocker)
        state = andor_wrapper.state
        return state.focus_position

    raise NotImplementedError("Focus control is not implemented in the non-debug mode.")


async def set_focus(position: float) -> None:
    """Sets the focus position."""

    if IS_DEBUG:
        assert isinstance(andor_wrapper, AndorWrapperMocker)
        state = andor_wrapper.state
        state.focus_position = position
        return

    raise NotImplementedError("Focus control is not implemented in the non-debug mode.")
