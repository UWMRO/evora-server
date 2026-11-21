#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-11-19
# @Filename: sweep.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import asyncio

from typing import Literal

import numpy as np
from astropy.io import fits
from fastapi import HTTPException

from evora_server import andor_wrapper, logger
from evora_server.autofocus.measure import (
    NO_STAR_IN_IMAGE,
    MeasureError,
    measure_star,
    recommend_focus,
)
from evora_server.autofocus.models import AutofocusStatusModel
from evora_server.routers.expose import (
    ExposurePostParams,
    abort_lock_path,
    take_exposure,
)
from evora_server.tools.camera import check_camera_initialized
from evora_server.tools.focuser import get_focus, set_focus


_session: Sweep | None = None


def current_status() -> AutofocusStatusModel:
    """Returns the sweep status, or idle when none has been started."""

    if _session is None:
        return AutofocusStatusModel(
            state="idle",
            message="",
            completed=0,
            total=0,
        )
    return _session.status()


async def start_sweep(
    f0: int,
    delta: int,
    n_positions: int,
    exposure_time: float,
) -> AutofocusStatusModel:
    """Starts one focus sweep. The focuser is not moved to the result."""

    global _session

    if _session is not None and _session.state in {"running", "awaiting_confirm"}:
        raise HTTPException(
            status_code=409,
            detail="A focus sweep is already in progress.",
        )

    check_camera_initialized()
    positions = [f0 + index * delta for index in range(n_positions)]
    _session = Sweep(positions, exposure_time)
    _session.task = asyncio.create_task(_session.run())
    return _session.status()


async def abort_sweep() -> AutofocusStatusModel:
    """Stops the sweep and leaves the focuser where it is."""

    if _session is None or _session.state not in {"running", "awaiting_confirm"}:
        return current_status()

    _session.abort_requested = True
    abort_lock_path.touch()
    if _session.state == "awaiting_confirm":
        _session.mark_aborted()
    return _session.status()


async def confirm_sweep(move: bool) -> AutofocusStatusModel:
    """Moves to the recommended step, or leaves the focuser at the end of the sweep."""

    if (
        _session is None
        or _session.state != "awaiting_confirm"
        or _session.recommended_position is None
    ):
        raise HTTPException(
            status_code=409,
            detail="There is no focus result waiting for confirmation.",
        )

    position = _session.recommended_position
    if move:
        await set_focus(float(position), absolute=True)
        await _wait_until_idle()
        _session.state = "done"
        _session.message = f"Focuser moved to {position} steps."
    else:
        _session.state = "done"
        _session.message = "Focuser left at its current position."
    return _session.status()


class Sweep:
    """One pass across focus positions."""

    def __init__(self, positions: list[int], exposure_time: float) -> None:
        self.positions = positions
        self.exposure_time = exposure_time
        self.state: Literal[
            "running",
            "awaiting_confirm",
            "aborted",
            "error",
            "done",
        ] = "running"
        self.message = "Focusing."
        self.completed = 0
        self.recommended_position: int | None = None
        self.abort_requested = False
        self.kept_positions: list[float] = []
        self.kept_sigmas: list[float] = []
        self.task: asyncio.Task[None] | None = None

    def status(self) -> AutofocusStatusModel:
        return AutofocusStatusModel(
            state=self.state,
            message=self.message,
            completed=self.completed,
            total=len(self.positions),
            recommended_position=self.recommended_position,
        )

    def mark_aborted(self) -> None:
        self.state = "aborted"
        self.message = "Focusing stopped. The focuser was left where it stopped."

    async def run(self) -> None:
        try:
            await self._sweep()
        except asyncio.CancelledError:
            self.mark_aborted()
            raise
        except Exception as err:
            self.state = "error"
            detail = getattr(err, "detail", None)
            self.message = detail if isinstance(detail, str) else str(err)
            logger.exception("Autofocus sweep failed.")

    async def _sweep(self) -> None:
        previous: tuple[float, float] | None = None
        found_star = False
        for index, position in enumerate(self.positions):
            if self.abort_requested:
                self.mark_aborted()
                return

            await set_focus(float(position), absolute=True)
            await _wait_until_idle()
            if self.abort_requested:
                self.mark_aborted()
                return

            result = await take_exposure(
                ExposurePostParams(
                    exposure_time=self.exposure_time,
                    exposure_type="single",
                    image_type="object",
                    n_frames=1,
                    comment="autofocus",
                ),
                andor_wrapper,
            )
            if result.aborted or self.abort_requested:
                self.mark_aborted()
                return
            if not result.success or result.path is None:
                self.state = "error"
                self.message = "The exposure failed."
                return

            try:
                measurement = await asyncio.to_thread(
                    _measure_path,
                    result.path,
                    previous,
                )
            except MeasureError as err:
                if str(err) == NO_STAR_IN_IMAGE:
                    logger.info(
                        "Autofocus step %s has no star and was left out.",
                        position,
                    )
                    self.completed = index + 1
                    continue
                self.state = "error"
                self.message = str(err)
                return

            found_star = True
            previous = (measurement.x, measurement.y)
            self.completed = index + 1
            if measurement.donut:
                logger.info(
                    "Autofocus step %s is a donut and was left out of the fit.",
                    position,
                )
                continue

            self.kept_positions.append(float(position))
            self.kept_sigmas.append(float(measurement.sigma))
            logger.info(
                "Autofocus step %s sigma %.3f.",
                position,
                measurement.sigma,
            )

        if self.abort_requested:
            self.mark_aborted()
            return
        if not self.kept_positions:
            self.state = "error"
            if found_star:
                self.message = (
                    "Every measured star is a donut. No focus recommendation."
                )
            else:
                self.message = "No star in the images."
            return

        recommendation = recommend_focus(self.kept_positions, self.kept_sigmas)
        self.recommended_position = recommendation.position
        self.state = "awaiting_confirm"
        self.message = (
            f"Focusing is done. Optimal focus is {recommendation.position} steps."
        )
        logger.info(self.message)


async def _wait_until_idle() -> None:
    """Waits until the focuser reports that it has stopped."""

    started = asyncio.get_running_loop().time()
    while True:
        status = await get_focus()
        if not status.moving:
            return
        if asyncio.get_running_loop().time() - started > 120:
            raise RuntimeError("The focuser did not stop moving.")
        await asyncio.sleep(0.2)


def _measure_path(
    path: str,
    previous: tuple[float, float] | None,
):
    with fits.open(path) as hdul:
        image = np.asarray(hdul[0].data)
    return measure_star(image, previous)
