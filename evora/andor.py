# import andor_wrapper as wrapper
import evora.andor_wrapper as wrapper
from evora._error_codes import ERROR_CODES
# from error_codes import ERROR_CODES
# this wrapper layer adds in error cases only

EXCLUDE = [
    '__doc__',
    '__file__',
    '__loader__',
    '__name__',
    '__package__',
    '__spec__',
    'getStatus',
    'getRangeTEC'
]

RETURNS_DICT = [
    'getDetector',
    'getAcquiredData',
    'getStatusTEC',
    'getAcquisitionTimings'
]

class AndorCameraError(Exception):
    def __init__(self, error_code):
        self.error_code = error_code
        super().__init__(ERROR_CODES[self.error_code])

    def __str__(self):
        error_info = ERROR_CODES[self.error_code]
        return f'({self.error_code}) {error_info[0]}. {error_info[1]}'
        
def errorDecorator(pybind11_func):
    def wrapped_function(*args, **kwargs):
        error_code = pybind11_func(*args, **kwargs)
        if error_code != 20002:
            raise AndorCameraError(error_code)
        else:
            return error_code

    return wrapped_function

def errorDecoratorDict(pybind11_func):
    def wrapped_function(*args, **kwargs):
        out = pybind11_func(*args, **kwargs)
        if out['status'] != 20002:
            raise AndorCameraError(out['status'])
        else:
            return out

    return wrapped_function

# iterate through the roster of andor_wrapper
for exposedName in dir(wrapper):
    if exposedName not in EXCLUDE:
        if exposedName in RETURNS_DICT:
            globals()[exposedName] = errorDecoratorDict(getattr(wrapper, exposedName))
        else:
            globals()[exposedName] = errorDecorator(getattr(wrapper, exposedName))

# edge cases
globals()['getStatus'] = getattr(wrapper, 'getStatus')
globals()['getStatusTEC'] = getattr(wrapper, 'getStatusTEC')

