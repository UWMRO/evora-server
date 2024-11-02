import os
import sys
import warnings
from distutils.core import Extension

from setuptools import find_packages, setup


class getPybindInclude(object):
    """Helper class to determine the pybind11 include path
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

if sys.platform == "linux":  # The andor library is only available on Linux
    root_path = os.path.dirname(__file__)
    ANDOR_WRAPPER_PATH = root_path + "/evora/andor_wrapper.cpp"

    ext_modules = [
        Extension(
            "evora.andor_wrapper",
            sources=[ANDOR_WRAPPER_PATH],
            libraries=["andor"],
            include_dirs=includes,
            extra_compile_args=extra_compile_args,
            extra_link_args=extra_link_args,
            optional=True,
        )
    ]

# Works with Python 3.13.0
setup(
    name="evora",
    version="0.2.2a0",
    description="Package containing PyBind11 wrapper code for the Andor SDK.",
    author="Astronomy Undergraduate Engineering Group",
    setup_requires=["pybind11"],
    install_requires=[
        "numpy",
        "astropy>=4.0",
        "pillow",
        "flask[async]",
        "gunicorn>=20.1.0",
        "flask_cors",
        "matplotlib",
        "sep-pjw",
        "photutils",
        "astrometry; platform_system != 'Windows'",
        "ambient_api",
        "python-dotenv"
    ],
    packages=find_packages(exclude=("tests*")),
    ext_modules=ext_modules,
)
