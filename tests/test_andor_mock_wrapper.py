#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2026-05-09
# @Filename: test_andor_mock_wrapper.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import pytest

from evora_server.mock import AndorWrapperMocker


@pytest.fixture()
def andor_wrapper():
    """Fixture that returns an instance of the AndorWrapperMocker."""

    andor_wrapper = AndorWrapperMocker()
    andor_wrapper.initialize()

    yield andor_wrapper


def test_initialize():
    andor_wrapper = AndorWrapperMocker()
    assert andor_wrapper.initialize() == 20002


def test_setAcquisitionMode(andor_wrapper: AndorWrapperMocker):
    assert andor_wrapper.setAcquisitionMode(1) == 20002


def test_setExposureTime(andor_wrapper: AndorWrapperMocker):
    assert andor_wrapper.setExposureTime(1.0) == 20002


def test_setShutter(andor_wrapper: AndorWrapperMocker):
    assert andor_wrapper.setShutter(1, 2, 50, 50) == 20002


def test_setImage(andor_wrapper: AndorWrapperMocker):
    assert andor_wrapper.setImage(1, 1, 1, 1, 1, 1) == 20002


def test_setFanMode(andor_wrapper: AndorWrapperMocker):
    assert andor_wrapper.setFanMode(1) == 20002


def test_coolerOn(andor_wrapper: AndorWrapperMocker):
    assert andor_wrapper.coolerOn() == 20002


def test_coolerOff(andor_wrapper: AndorWrapperMocker):
    assert andor_wrapper.coolerOff() == 20002


def test_setTargetTEC(andor_wrapper: AndorWrapperMocker):
    assert andor_wrapper.setTargetTEC(-60) == 20002


def test_startAcquisition(andor_wrapper: AndorWrapperMocker):
    assert andor_wrapper.startAcquisition() == 20002


def test_getStatus(andor_wrapper: AndorWrapperMocker):
    assert andor_wrapper.getStatus() == {"funcstatus": 20002, "status": 20073}
