#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-08
# @Filename: app.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from fastapi import FastAPI

from evora_server import __version__

from .routers import expose, filter, initialize, status, temperature, weather


app = FastAPI(
    version=__version__,
    title="Evora Server",
    description="API for the Evora camera control server.",
)

app.include_router(status.router)
app.include_router(temperature.router)
app.include_router(initialize.router)
app.include_router(expose.router)
app.include_router(filter.router)
app.include_router(weather.router)


@app.get("/")
def root():
    """Root endpoint."""

    return {"message": "Welcome to the Evora server!"}


@app.get("/version")
def get_version():
    """Returns the version of the server."""

    return {"version": __version__}
