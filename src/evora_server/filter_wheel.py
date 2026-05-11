#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-09
# @Filename: filter_wheel.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import asyncio

from evora_server import IS_DEBUG, AndorWrapperMocker, andor_wrapper, config


__all__ = ["get_filter", "set_filter", "send_to_wheel", "home_wheel"]


async def send_to_wheel(command: str) -> tuple[bool, str]:
    """Sends a command to the filter wheel and parses the reply.

    Parameters
    ----------
    command
        The string to send to the filter wheel server.

    Returns
    -------
    res
        A tuple of response status as a boolean, and the additional reply
        as a string (the reply string will be empty if no additional reply is
        provided).

    """

    reader, writer = await asyncio.open_connection("72.233.250.84", 9999)
    writer.write((command + "\n").encode())
    await writer.drain()

    received = (await reader.readline()).decode()
    writer.close()
    await writer.wait_closed()

    parts = received.split(",")

    status = parts[0] == "OK"

    if len(parts) > 1:
        reply = parts[1]
    else:
        reply = ""

    return status, reply


async def get_filter() -> str:
    """Returns the current filter in the wheel."""

    if IS_DEBUG:
        assert isinstance(andor_wrapper, AndorWrapperMocker)
        state = andor_wrapper.state
        fw_position = state.filter_position
        return config.FILTER_DICT_REVERSE.get(fw_position, "Unknown")

    status, reply = await send_to_wheel("get")
    if not status:
        raise RuntimeError(f"Failed to get filter wheel position. Error: {reply}")

    fw_position = int(reply)
    return config.FILTER_DICT_REVERSE.get(fw_position, "Unknown")


async def set_filter(filter_name: str) -> None:
    """Sets the filter in the wheel."""

    if filter_name not in config.FILTER_DICT:
        raise ValueError(f"Invalid filter name: {filter_name!r}.")

    if IS_DEBUG:
        assert isinstance(andor_wrapper, AndorWrapperMocker)
        andor_wrapper.state.filter_position = config.FILTER_DICT[filter_name]
        return

    fw_position = config.FILTER_DICT[filter_name]
    status, reply = await send_to_wheel(f"move {fw_position}")

    if not status:
        raise RuntimeError(f"Failed to set filter wheel position. Error: {reply}")


async def home_wheel() -> None:
    """Homes the filter wheel."""

    if IS_DEBUG:
        assert isinstance(andor_wrapper, AndorWrapperMocker)
        andor_wrapper.state.filter_position = 0
        return

    status, reply = await send_to_wheel("home")

    if not status:
        raise RuntimeError(f"Failed to home filter wheel. Error: {reply}")
