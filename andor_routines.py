# try:
#     import evora.andor as andor
#     import time
# except:
#     import evora.dummy as andor

# import evora.andor as andor
from evora.dummy import Dummy as andor
import time

# biases: Readout noise from camera (effectively 0 s exposure)
# flats: take an image with even lighting (i.e. the white paint of the dome)
# darks: image while shutter closed

def startup():
    # implement with config values
    andor.initialize()
    andor.setAcquisitionMode(1)
    andor.setExposureTime(0.1)

    image_dimensions = andor.getDetector()['dimensions']

    andor.setShutter(1, 0, 50, 50)
    andor.setImage(1, 1, 1, image_dimensions[0], 1, image_dimensions[1])

    return {
        'dimensions' : image_dimensions,
        'status' : 20002
    }

def activateCooling(target_temperature = -10):
    # andor.setFanMode(2)
    andor.coolerOn()
    andor.setTargetTEC(target_temperature)

    return 20002

def deactivateCooling(fan_mode_high=False):
    andor.coolerOff()
    # andor.setFanMode(0 if fan_mode_high else 1)

    return 20002

def acquisition(dim, exposure_time = 0.1):
    andor.setExposureTime(exposure_time)
    andor.startAcquisition()

    time.sleep(exposure_time + 0.5)
    # while (camera_status == 20072):
    #     camera_status = andor.getStatus()

    return {
        'data' : andor.getAcquiredData(dim)['data'],
        'status' : 20002
    }

def acquireBias(dim):
    andor.setShutter(1, 2, 50, 50)
    andor.setImage(1, 1, 1, dim[0], 1, dim[1])

    image = acquisition(dim, exposure_time=0.0)
    andor.setShutter(1, 0, 50, 50)

    return image
