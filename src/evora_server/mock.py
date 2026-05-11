import threading
import time
from types import SimpleNamespace

from numpy import array
from numpy.random import randint

from evora_server import config


__all__ = ["AndorWrapperMocker"]


class EvoraState(SimpleNamespace):
    """Class to hold the state of the mock Evora camera system."""

    # Camera params.
    current_temp: float = 20.0
    initialized: bool = False
    acquiring: bool = False
    acquisition_mode: int = 1
    exposure_time: float = 0.1
    dimensions: tuple = (1024, 1024)

    # Filter wheel state.
    filter_position: int = 0

    # Focus position.
    focus_position: float = 0


class AndorWrapperMocker:
    """Mocker for the Andor wrapper to be used in testing."""

    def __init__(self, state: EvoraState | None = None):
        self.state = state or EvoraState()
        self.__thread_stop = False

    # Andor SDK replacement functions with return values
    def getStatus(self):
        if self.state.initialized:
            if not self.state.acquiring:
                return {
                    "status": config.DRV_IDLE,
                    "funcstatus": config.DRV_SUCCESS,
                }
            else:
                return {
                    "status": config.DRV_ACQUIRING,
                    "funcstatus": config.DRV_SUCCESS,
                }
        else:
            return {
                "status": config.DRV_NOT_INITIALIZED,
                "funcstatus": config.DRV_NOT_INITIALIZED,
            }

    def getStatusTEC(self):
        if self.state.initialized:
            if not self.state.acquiring:
                return {
                    "status": config.DRV_SUCCESS,
                    "temperature": self.state.current_temp,
                }
            else:
                return {"status": config.DRV_ACQUIRING, "temperature": -999.0}
        else:
            return {"status": config.DRV_NOT_INITIALIZED, "temperature": -999.0}

    def setTemperature(self, value: float):
        self.state.current_temp = float(value)
        return self.state.current_temp

    def setTargetTEC(self, temperature: float):
        if self.state.initialized:
            if not self.state.acquiring:
                self.state.current_temp = float(temperature)
                return config.DRV_SUCCESS
            else:
                return config.DRV_ACQUIRING
        else:
            return config.DRV_NOT_INITIALIZED

    def initialize(self):
        self.state.initialized = True
        return config.DRV_SUCCESS

    def getTemperatureRange(self):
        if self.state.initialized:
            if not self.state.acquiring:
                return {
                    "min": config.min_temp,
                    "max": config.max_temp,
                    "status": config.DRV_SUCCESS,
                }
            else:
                return {
                    "min": -999.0,
                    "max": -999.0,
                    "status": config.DRV_ACQUIRING,
                }
        else:
            return {
                "min": -999.0,
                "max": -999.0,
                "status": config.DRV_NOT_INITIALIZED,
            }

    def getRangeTEC(self):
        return self.getTemperatureRange()

    def startAcquisition(self):
        if self.state.initialized:
            if not self.state.acquiring:
                thread = threading.Thread(target=self._emulate_acquisition)
                thread.start()
                return config.DRV_SUCCESS
            else:
                return config.DRV_ACQUIRING
        else:
            return config.DRV_NOT_INITIALIZED

    def _emulate_acquisition(self):
        self.state.acquiring = True

        elapsed = 0.0
        while (elapsed < self.state.exp_time) and not self.__thread_stop:
            time.sleep(self.state.exp_time)
            elapsed += self.state.exp_time

        self.state.acquiring = False

        self.__thread_stop = False

    def abortAcquisition(self):
        if self.state.initialized:
            self.state.acquiring = False
            self.__thread_stop = True
            return config.DRV_SUCCESS
        else:
            return config.DRV_NOT_INITIALIZED

    def getAcquiredData(self, dim: tuple[int, int]):
        if self.state.initialized:
            if not self.state.acquiring:
                data = randint(65535, size=dim)
                return {"data": data, "status": config.DRV_SUCCESS}
            else:
                return {
                    "data": array([], dtype="uint8"),
                    "status": config.DRV_ACQUIRING,
                }
        else:
            return {
                "data": array([], dtype="uint8"),
                "status": config.DRV_NOT_INITIALIZED,
            }

    # These functions do the same thing in this context
    getMostRecentImage16 = getAcquiredData

    def getAcquisitionTimings(self):
        if self.state.initialized:
            if not self.state.acquiring:
                return {
                    "exposure": self.state.exposure_time,
                    "accumulate": -1.0,
                    "kinetic": -1.0,
                    "status": config.DRV_SUCCESS,
                }
            else:
                return config.DRV_ACQUIRING
        else:
            return config.DRV_NOT_INITIALIZED

    def getDetector(self):
        if self.state.initialized:
            if not self.state.acquiring:
                return {
                    "dimensions": self.state.dimensions,
                    "status": config.DRV_SUCCESS,
                }
            else:
                return {"dimensions": (-1, -1), "status": config.DRV_ACQUIRING}
        else:
            return {"dimensions": (-1, -1), "status": config.DRV_NOT_INITIALIZED}

    def setAcquisitionMode(self, mode):
        if self.state.initialized:
            if not self.state.acquiring:
                self.state.acquisition_mode = mode
                return config.DRV_SUCCESS
            else:
                return config.DRV_ACQUIRING
        else:
            return config.DRV_NOT_INITIALIZED

    def setShutter(self, typ, mode, closingtime, openingtime):
        if self.state.initialized:
            if not self.state.acquiring:
                return config.DRV_SUCCESS
            else:
                return config.DRV_ACQUIRING
        else:
            return config.DRV_NOT_INITIALIZED

    def setFanMode(self, mode):
        if self.state.initialized:
            if not self.state.acquiring:
                return config.DRV_SUCCESS
            else:
                return config.DRV_ACQUIRING
        else:
            return config.DRV_NOT_INITIALIZED

    def coolerOn(self):
        if self.state.initialized:
            if not self.state.acquiring:
                return config.DRV_SUCCESS
            else:
                return config.DRV_ACQUIRING
        else:
            return config.DRV_NOT_INITIALIZED

    def coolerOff(self):
        if self.state.initialized:
            if not self.state.acquiring:
                return config.DRV_SUCCESS
            else:
                return config.DRV_ACQUIRING
        else:
            return config.DRV_NOT_INITIALIZED

    def shutdown(self):
        if not self.state.acquiring:
            time.sleep(1)
            self.state.initialized = False
            self.state.acquiring = False
            return config.DRV_SUCCESS
        else:
            return config.DRV_ACQUIRING

    def setReadMode(self):
        if self.state.initialized:
            if not self.state.acquiring:
                return config.DRV_SUCCESS
            else:
                return config.DRV_ACQUIRING
        else:
            return config.DRV_NOT_INITIALIZED

    def setImage(self, hbin, vbin, hstart, hend, vstart, vend):
        # determine the specifics of the behavior later lol
        if self.state.initialized:
            if not self.state.acquiring:
                return config.DRV_SUCCESS
            else:
                return config.DRV_ACQUIRING
        else:
            return config.DRV_NOT_INITIALIZED

    def setExposureTime(self, exp_time):
        if self.state.initialized:
            if not self.state.acquiring:
                self.state.exp_time = exp_time
                return config.DRV_SUCCESS
            else:
                return config.DRV_ACQUIRING
        else:
            return config.DRV_NOT_INITIALIZED

    def setKineticCycleTime(self, cycle_time):
        if self.state.initialized:
            if not self.state.acquiring:
                return config.DRV_SUCCESS
            else:
                return config.DRV_ACQUIRING
        else:
            return config.DRV_NOT_INITIALIZED

    def setNumberKinetics(self, number):
        if self.state.initialized:
            if not self.state.acquiring:
                return config.DRV_SUCCESS
            else:
                return config.DRV_ACQUIRING
        else:
            return config.DRV_NOT_INITIALIZED
