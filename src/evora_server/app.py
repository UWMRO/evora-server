#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-08
# @Filename: app.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from contextlib import asynccontextmanager

from typing import AsyncIterator

from fastapi import FastAPI

from evora_server import IS_DEBUG, __version__, logger

from .routers import expose, filter, focus, initialize, status, temperature, weather


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Lifespan function for the FastAPI app."""

    if not IS_DEBUG:
        logger.warning("Using the real Andor camera.")
    else:
        logger.warning("Using the **mock** Andor wrapper.")

    yield


app = FastAPI(
    version=__version__,
    title="Evora Server",
    description="API for the Evora camera control server.",
    lifespan=lifespan,
)

app.include_router(status.router)
app.include_router(temperature.router)
app.include_router(initialize.router)
app.include_router(expose.router)
app.include_router(filter.router)
app.include_router(weather.router)
app.include_router(focus.router)


@app.get("/")
def root():
    """Root endpoint."""

    return {"message": "Welcome to the Evora server!"}


@app.get("/version")
def get_version():
    """Returns the version of the server."""

    return {"version": __version__}
