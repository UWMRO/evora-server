#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-05-09
# @Filename: weather.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import asyncio

from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(prefix="/weather", tags=["weather"])


class WeatherDataResponseModel(BaseModel):
    dateutc: Annotated[
        int,
        Field(description="UTC timestamp for the observation."),
    ]
    tempf: Annotated[
        float,
        Field(description="Outdoor temperature in degrees Fahrenheit."),
    ]
    humidity: Annotated[
        int,
        Field(description="Outdoor relative humidity percentage."),
    ]
    windspeedmph: Annotated[
        float,
        Field(description="Current wind speed in miles per hour."),
    ]
    windgustmph: Annotated[
        float,
        Field(description="Current wind gust speed in miles per hour."),
    ]
    maxdailygust: Annotated[
        float,
        Field(description="Maximum wind gust recorded today in miles per hour."),
    ]
    winddir: Annotated[
        int,
        Field(description="Current wind direction in degrees."),
    ]
    winddir_avg10m: Annotated[
        int,
        Field(description="Average wind direction over the last 10 minutes."),
    ]
    hourlyrainin: Annotated[
        float,
        Field(description="Rainfall during the last hour in inches."),
    ]
    eventrainin: Annotated[
        float,
        Field(description="Rainfall for the current rain event in inches."),
    ]
    dailyrainin: Annotated[
        float,
        Field(description="Rainfall accumulated today in inches."),
    ]
    weeklyrainin: Annotated[
        float,
        Field(description="Rainfall accumulated this week in inches."),
    ]
    monthlyrainin: Annotated[
        float,
        Field(description="Rainfall accumulated this month in inches."),
    ]
    yearlyrainin: Annotated[
        float,
        Field(description="Rainfall accumulated this year in inches."),
    ]
    totalrainin: Annotated[
        float,
        Field(description="Total rainfall accumulated by the station in inches."),
    ]
    battout: Annotated[
        int,
        Field(description="Outdoor sensor battery status indicator."),
    ]
    tempinf: Annotated[
        float,
        Field(description="Indoor temperature in degrees Fahrenheit."),
    ]
    humidityin: Annotated[
        int,
        Field(description="Indoor relative humidity percentage."),
    ]
    baromrelin: Annotated[
        float,
        Field(description="Relative barometric pressure in inches of mercury."),
    ]
    baromabsin: Annotated[
        float,
        Field(description="Absolute barometric pressure in inches of mercury."),
    ]
    temp1f: Annotated[
        float,
        Field(description="Temperature from extra sensor 1 in degrees Fahrenheit."),
    ]
    humidity1: Annotated[
        int,
        Field(description="Relative humidity from extra sensor 1 percentage."),
    ]
    batt1: Annotated[
        int,
        Field(description="Battery status indicator for extra sensor 1."),
    ]
    temp2f: Annotated[
        float,
        Field(description="Temperature from extra sensor 2 in degrees Fahrenheit."),
    ]
    humidity2: Annotated[
        int,
        Field(description="Relative humidity from extra sensor 2 percentage."),
    ]
    batt2: Annotated[
        int,
        Field(description="Battery status indicator for extra sensor 2."),
    ]
    feelsLike: Annotated[
        float,
        Field(description="Outdoor feels-like temperature in degrees Fahrenheit."),
    ]
    dewPoint: Annotated[
        float,
        Field(description="Outdoor dew point in degrees Fahrenheit."),
    ]
    feelsLike1: Annotated[
        float,
        Field(description="Feels-like temperature for sensor 1 in degrees Fahrenheit."),
    ]
    dewPoint1: Annotated[
        float,
        Field(description="Dew point for sensor 1 in degrees Fahrenheit."),
    ]
    feelsLike2: Annotated[
        float,
        Field(description="Feels-like temperature for sensor 2 in degrees Fahrenheit."),
    ]
    dewPoint2: Annotated[
        float,
        Field(description="Dew point for sensor 2 in degrees Fahrenheit."),
    ]
    feelsLikein: Annotated[
        float,
        Field(description="Indoor feels-like temperature in degrees Fahrenheit."),
    ]
    dewPointin: Annotated[
        float,
        Field(description="Indoor dew point in degrees Fahrenheit."),
    ]
    lastRain: Annotated[
        str,
        Field(description="Timestamp of the most recent rain event."),
    ]
    tz: Annotated[
        str,
        Field(description="Timezone for the observation."),
    ]
    date: Annotated[
        str,
        Field(description="Formatted local date and time of the observation."),
    ]


@router.get("/status", summary="Returns the current weather data.")
async def get_weather_data() -> WeatherDataResponseModel:
    """Returns the current weather data."""

    from ambient_api.ambientapi import AmbientAPI

    api = AmbientAPI()

    devices = api.get_devices()

    if len(devices) == 0:
        raise HTTPException(status_code=404, detail="No weather station devices found.")

    device = devices[0]

    await asyncio.sleep(1)

    data = device.last_data

    return WeatherDataResponseModel(**data)
