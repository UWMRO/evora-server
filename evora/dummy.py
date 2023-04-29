from PIL import Image
from numpy import asarray
from numpy import array
import base64
from io import BytesIO
from random import randint
import threading
import time

# Replacement constants, taken from atmcdLXd.h
DRV_SUCCESS = 20002
DRV_TEMPERATURE_OFF = 20034
DRV_TEMPERATURE_STABILIZED = 20036
DRV_NOT_INITIALIZED = 20075
DRV_ACQUIRING = 20072
DRV_IDLE = 20073

min_temp = -80.0
max_temp = 50.0

class Dummy:
    current_temp = 20.0
    initialized = False
    acquiring = False
    acquisition_mode = 1
    exp_time = 0.1
    dimensions = (1024, 1024)
    __thread_stop  = False

    """
    SWIG notes
    SWIG seems to change the API from the docs in two major ways
    1. Unsigned int functions actually return [status, return_val] e.g. [DRV_SUCCESS, 35]
    2. Pointer arguments are simply omitted e.g. int SomeFunction(long* input) -> def SomeFunction()...
    """

    # todo: execute this in a separate thread to emulate locking during acquisition?
    @classmethod
    def __emulate_acquisition(cls):
        cls.acquiring = True
        elapsed = 0.0
        while (elapsed < cls.exp_time) and not cls.__thread_stop:
            time.sleep(cls.exp_time)
        cls.acquiring = False
        cls.__thread_stop = False

    # Andor SDK replacement functions with return values
    @classmethod
    def getStatus(cls):
        if cls.initialized:
            if not cls.acquiring:
                return {
                    'status' : DRV_IDLE,
                    'funcstatus' : DRV_SUCCESS
                }
            else:
                return {
                    'status' : DRV_ACQUIRING,
                    'funcstatus' : DRV_SUCCESS
                }
        else:
            return {
                'status' : DRV_NOT_INITIALIZED,
                'funcstatus' : DRV_NOT_INITIALIZED
            }
        #return DRV_NOT_INITIALIZED

    @classmethod
    def getStatusTEC(cls):
        if cls.initialized:
            if not cls.acquiring:
                return {
                    'status' : DRV_SUCCESS, 
                    'temperature': cls.current_temp
                }
            else:
                return {
                    'status' : DRV_ACQUIRING, 
                    'temperature': -999.0
                }
        else:
            return {
                'status' : DRV_NOT_INITIALIZED, 
                'temperature': -999.0
            }
        

    @classmethod
    def setTemperature(cls, value):
        cls.current_temp = float(value) 
        return cls.current_temp

    @classmethod
    def setTargetTEC(cls, temperature):
        if cls.initialized:
            if not cls.acquiring:
                cls.current_temp = float(temperature)
                return DRV_SUCCESS
            else:
                return DRV_ACQUIRING
        else:
            return DRV_NOT_INITIALIZED

    # @classmethod
    # def getAvailableCameras():
    #     return 1


    # def getCameraHandle(cameraIndex):
    #     return DRV_SUCCESS

    @classmethod
    def initialize(cls, directory=''):
        cls.initialized = True
        return DRV_SUCCESS


    # def getTemperatureF():
    #     return -999

    # def getTemperatureStatus():
    #     return DRV_SUCCESS

    @classmethod
    def getTemperatureRange(cls):
        if cls.initialized:
            if not cls.acquiring:
                return {
                    'min' : min_temp,
                    'max' : max_temp,
                    'status' : DRV_SUCCESSsetExpo
                }
            else:
                return {
                'min' : -999.0,
                'max' : -999.0,
                'status' : DRV_ACQUIRING
            }
        else:
            return {
                'min' : -999.0,
                'max' : -999.0,
                'status' : DRV_NOT_INITIALIZED
            }


    # Acquisition
    @classmethod
    def startAcquisition(cls):
        # todo: emulate the locking behavior when andor is taking a picture
        # add a boolean called 'acquiring'. if True, then lock the dummy module
        # this function will begin a thread where acquiring is set to True
        # for exp_time amount of time
        # other functions in the module will check if acquiring is False before proceeding
        if cls.initialized:
            # acquiring = True
            if not cls.acquiring:
                thread = threading.Thread(target=cls.__emulate_acquisition)
                thread.start()
                return DRV_SUCCESS
            else:
                return DRV_ACQUIRING
        else:
            return DRV_NOT_INITIALIZED

    def abortAcquisition():
        if cls.initialized:
            cls.acquiring = False
            cls.__thread_stop = True
            return DRV_SUCCESS
        else:
            return DRV_NOT_INITIALIZED

    @classmethod
    def getAcquiredData(cls, dim):
        if cls.initialized:
            if not cls.acquiring:
                img = 'space.txt'
                if randint(0, 1000) >= 999:
                    img = 'server/evora/space0.txt'

                #time_sec = int(exp_time)
                #while time_sec:
                #    mins, secs = divmod(time_sec, 60)
                #    timer = '{:02d}:{:02d}'.format(mins, secs)
                #    print(timer, end="\r")
                #    time.sleep(1)
                #    time_sec -= 1
                
                #import os
                #list = os.listdir('.')

                with open(img) as f:
                    data = asarray(Image.open(BytesIO(base64.b64decode(f.read()))))

                # This might not work, passing by reference is weird in Python
                
                return {
                    'data' : data,
                    'status' : DRV_SUCCESS
                }
            else:
                return {
                    'data' : array([], dtype='uint8'),
                    'status' : DRV_ACQUIRING
                }
        else:
            return {
                    'data' : array([], dtype='uint8'),
                    'status' : DRV_NOT_INITIALIZED
                }


    # These functions do the same thing in this context
    getMostRecentImage16 = getAcquiredData

    @classmethod
    def getAcquisitionTimings(cls):
        if cls.initialized:
            if not cls.acquiring:
                return {
                    'exposure' : cls.exp_time,
                    'accumulate' : -1.0,
                    'kinetic' : -1.0,
                    'status' : DRV_SUCCESS
                }
            else:
                return DRV_ACQUIRING
        else:
            return DRV_NOT_INITIALIZED


    # def getNumberVSSpeeds(speeds):
    #     return 1

    # def getNumberVSAmplitudes(number):
    #     return 1


    # def getVSSpeed(index, speed):
    #     return 1


    # def getFastestRecommendedVSSpeed(index, speeds):
    #     return 1


    # def getNumberHSSpeeds(channel, typ, speeds):
    #     return 1


    # def getHSSpeed(channel, typ, index, speed):
    #     return 1

    @classmethod
    def getDetector(cls):
        if cls.initialized:
            if not cls.acquiring:
                return {
                    'dimensions' : cls.dimensions,
                    'status' : DRV_SUCCESS
                }
            else:
                return {
                    'dimensions' : (-1, -1),
                    'status' : DRV_ACQUIRING
                }
        else:
            return {
                'dimensions' : (-1, -1),
                'status' : DRV_NOT_INITIALIZED
            }


    # def getAcquisitionProgress(acc, series):
    #     return 1


    # Setter functions
    def noop(*args):
        # Takes any number of arguments, does nothing
        pass


    # Set to noop func instead of defining each to save space
    # setCurrentCamera = noop

    @classmethod
    def setAcquisitionMode(cls, mode):
        if cls.initialized:
            if not cls.acquiring:
                cls.acquisition_mode = mode
                return DRV_SUCCESS
            else:
                return DRV_ACQUIRING
        else:
            return DRV_NOT_INITIALIZED

    #setTemperature = noop
    
    @classmethod
    def setShutter(cls, typ, mode, closingtime, openingtime):
        if cls.initialized:
            if not cls.acquiring:
                return DRV_SUCCESS
            else:
                return DRV_ACQUIRING
        else:
            return DRV_NOT_INITIALIZED

    @classmethod
    def setFanMode(cls, mode):
        if cls.initialized:
            if not cls.acquiring:
                return DRV_SUCCESS
            else:
                return DRV_ACQUIRING
        else:
            return DRV_NOT_INITIALIZED

    @classmethod
    def coolerOn(cls):
        if cls.initialized:
            if not cls.acquiring:
                return DRV_SUCCESS
            else:
                return DRV_ACQUIRING
        else:
            return DRV_NOT_INITIALIZED

    @classmethod
    def coolerOff(cls):
        if cls.initialized:
            if not cls.acquiring:
                return DRV_SUCCESS
            else:
                return DRV_ACQUIRING
        else:
            return DRV_NOT_INITIALIZED

    @classmethod
    def shutdown(cls):
        if not cls.acquiring:
            cls.initialized = False
            cls.acquiring = False
            return DRV_SUCCESS
        else:
            return DRV_ACQUIRING
        
    @classmethod
    def setReadMode(cls):
        if cls.initialized:
            if not cls.acquiring:
                return DRV_SUCCESS
            else:
                return DRV_ACQUIRING
        else:
            return DRV_NOT_INITIALIZED

    @classmethod
    def setImage(cls, hbin, vbin, hstart, hend, vstart, vend):
        # determine the specifics of the behavior later lol
        if cls.initialized:
            if not cls.acquiring:
                return DRV_SUCCESS
            else:
                return DRV_ACQUIRING
        else:
            return DRV_NOT_INITIALIZED

    @classmethod
    def setShutter(cls, typ, mode, closing_time, opening_time):
        # determine the specifics of the behavior later lol
        if cls.initialized:
            if not cls.acquiring:
                return DRV_SUCCESS
            else:
                return DRV_ACQUIRING
        else:
            return DRV_NOT_INITIALIZED

    @classmethod
    def setExposureTime(cls, exp_time):
        if cls.initialized:
            if not cls.acquiring:
                cls.exp_time = exp_time
                return DRV_SUCCESS
            else:
                return DRV_ACQUIRING
        else:
            return DRV_NOT_INITIALIZED

    @classmethod
    def setKineticCycleTime(cycle_time):
        if cls.initialized:
            if not cls.acquiring:
                return DRV_SUCCESS
            else:
                return DRV_ACQUIRING
        else:
            return DRV_NOT_INITIALIZED
    # setNumberAccumulations = noop
    # setAccumulationCycleTime = noop
    @classmethod
    def setNumberKinetics(cls, number):
        if cls.initialized:
            if not cls.acquiring:
                return DRV_SUCCESS
            else:
                return DRV_ACQUIRING
        else:
            return DRV_NOT_INITIALIZED
    # setTriggerMode = noop

