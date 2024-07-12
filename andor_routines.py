import time

# biases: Readout noise from camera (effectively 0 s exposure)
# flats: take an image with even lighting (i.e. the white paint of the dome)
# darks: image while shutter closed


def startup(andor):
    '''
    Initializes the camera and sets the acquisition mode to single scan.

    Parameters:
    - andor: andor camera instance

    Returns:
    - dimensions: tuple of the image dimensions
    '''
    # implement with config values
    andor.initialize()
    andor.setAcquisitionMode(1)
    andor.setExposureTime(0.1)

    image_dimensions = andor.getDetector()["dimensions"]

    andor.setShutter(1, 0, 50, 50)
    andor.setImage(1, 1, 1, image_dimensions[0], 1, image_dimensions[1])

    return {"dimensions": image_dimensions, "status": 20002}


def activateCooling(andor, target_temperature=-10):
    '''
    Activates the camera cooling system and sets the target temperature.

    Parameters:
    - andor: andor camera instance
    - target_temperature: the desired temperature of the camera sensor

    Returns:
    - 20002: success
    '''
    # andor.setFanMode(2)
    andor.coolerOn()
    andor.setTargetTEC(target_temperature)

    return 20002

def deactivateCooling(andor, fan_mode_high=False):
    '''
    Deactivates the camera cooling system.

    Parameters:
    - andor: andor camera instance
    - fan_mode_high: whether the fan mode should be set to high

    Returns:
    - 20002: success
    '''
    andor.coolerOff()
    # andor.setFanMode(0 if fan_mode_high else 1)

    return 20002


def acquisition(andor, dim, exposure_time=0.1):
    '''
    Acquires an image with the given dimensions and exposure time.

    Parameters:
    - andor: andor camera instance
    - dim: tuple of the image dimensions
    - exposure_time: how long to expose for (sec)

    Returns:
    - data: the acquired image data
    '''
    andor.setExposureTime(exposure_time)
    andor.startAcquisition()

    time.sleep(exposure_time + 0.5)
    # while (camera_status == 20072):
    #     camera_status = andor.getStatus()

    return {"data": andor.getAcquiredData(dim)["data"], "status": 20002}


def acquireBias(andor, dim):
    '''
    Acquires a bias image.

    Parameters:
    - andor: andor camera instance
    - dim: tuple of the image dimensions

    Returns:
    - image: the acquired bias image
    '''
    andor.setShutter(1, 2, 50, 50)
    andor.setImage(1, 1, 1, dim[0], 1, dim[1])

    image = acquisition(dim, exposure_time=0.0)
    andor.setShutter(1, 0, 50, 50)

    return image
