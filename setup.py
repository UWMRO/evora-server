import os
import sys
import warnings

from setuptools import setup
from setuptools.extension import Extension


class getPybindInclude(object):
    """Helper class to determine the pybind11 include path.

    The purpose of this class is to postpone importing pybind11
    until it is actually installed, so that the ``get_include()``
    method can be invoked.
    https://github.com/pybind/python_example/blob/master/setup.py

    """

    def __init__(self, user=False):
        self.user = user

    def __str__(self):
        import pybind11

        return pybind11.get_include(self.user)


extra_compile_args = ["--std=c++11", "-fPIC", "-v", "-O3", "-shared", "-Landor"]
extra_link_args = ["-Wl,-rpath,."]

includes = [getPybindInclude(), getPybindInclude(user=True)]

ext_modules = []

IS_DEBUG = os.getenv("EVORA_SERVER_DEBUG", "0").lower() in ("1", "true", "yes")

if IS_DEBUG:
    warnings.warn("EVORA_SERVER_DEBUG is set. Not building the wrapper.")

elif sys.platform != "linux":
    warnings.warn(
        "Andor wrapper is only supported on Linux. "
        "Skipping compilation of the Andor wrapper."
    )

else:
    ANDOR_WRAPPER_PATH = "src/evora_server/cpp/andor_wrapper.cpp"

    ext_modules = [
        Extension(
            "evora_server.andor_wrapper",
            sources=[ANDOR_WRAPPER_PATH],
            libraries=["andor"],
            include_dirs=includes,
            extra_compile_args=extra_compile_args,
            extra_link_args=extra_link_args,
            optional=False,
        )
    ]

# Works with Python 3.13.0
setup(ext_modules=ext_modules)
