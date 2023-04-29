import unittest
import sys
  
# setting path
sys.path.append('../evora')
from andor import *


def test_initialize():
   assert initialize() == 20002


def test_setAcquisitionMode():
   assert setAcquisitionMode() == 20002


def test_setExposureTime():
   assert setExposure() == 20002


def test_setShutter():
   assert setShutter() == 20002


def test_setImage():
   assert setImage() == 20002


def test_setFanMode():
   assert setFanMode() == 20002


def test_coolerOn():
   assert coolerOn() == 20002


def test_coolerOff():
   assert coolerOff() == 20002


def test_setTargetTEC():
   assert setTargetTEC() == 20002


def test_startAcquisition():
   assert startAcquisition() == 20002


def test_getStatus():
   assert getStatus() == 20002


def main():
   test_initialize()


if __name__ == '__main__':
   main()
   shutdown()
