#include <pybind11/pybind11.h>
#include <atmcdLXd.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

namespace py = pybind11;

// GetAcquiredData originally modifies an array of long (at_32) to acquire the imaging data.
// helper func. below to convert it into a returned value, in matrix form.
//
std::vector<std::vector<at_32>> reshapeImageData(at_32* imageData, int imageWidth, int imageHeight) {
	auto out = std::vector<std::vector<at_32>>();
	for (auto row = 0; row < imageHeight; row++) {
		out.push_back(std::vector<at_32>(imageWidth));
	}
	for (auto row = 0; row < imageHeight; row++) {
		for (auto col = 0; col < imageWidth; col++) {
			out[row][col] = imageData[row * col];
		}
	}

	return out;
}


unsigned int InitializeWrapper(std::string andor_dir = "/usr/local/etc/andor") {
	char* casted = const_cast<char*>(andor_dir.c_str());
	return Initialize(casted);
}

PYBIND11_MODULE(andor_wrapper, m) {
    m.def("initialize",		&InitializeWrapper,         "Initialize the Andor Camera",
        py::arg("andor_dir") = "/usr/local/etc/andor"
    );

    m.def("setReadMode",	        &SetReadMode,           "Set Read Mode");
    m.def("shutdown",		        &ShutDown,              "Shutdown the Andor Camera");
    m.def("setAcquisitionMode",	    &SetAcquisitionMode,	"Set acquisition mode");
    m.def("setExposureTime",	    &SetExposureTime,	    "Set exposure time of shot");
    m.def("getAcquisitionTimings",  
                                    [](void) {
                                        float exposure, accumulate, kinetic;
                                        exposure = -1;
                                        accumulate = -1;
                                        kinetic = -1;

                                        int status;
                                        status = GetAcquisitionTimings(&exposure, &accumulate, &kinetic);
                                        py::dict out;
                                        out["exposure"] = exposure;
                                        out["accumulate"] = accumulate;
                                        out["kinetic"] = kinetic;
                                        out["status"] = status;

                                        return out;
                                    },                      "Get current camera timing settings");
    m.def("getStatus",		
                                [](void) {
                                    int status;
                                    int funcStatus;
                                    py::dict out;
                                    funcStatus = GetStatus(&status);
                                    out["status"] = status;
                                    out["funcstatus"] = funcStatus;
                                    return out;
                                },	                    "Get camera status");

    m.def("getDetector",	
                                [](void) {
                                    int imageWidth, imageHeight, status;
                                    imageWidth = -1;
                                    imageHeight = -1;

                                    status = GetDetector(&imageWidth, &imageHeight);
                                    py::tuple dim = py::make_tuple(imageWidth, imageHeight);
                                    py::dict out;
                                    out["dimensions"] = dim;
                                    out["status"] = status;
                                    return out;
                                },                      "Get detector dimensions");	// converted into a tuple.

    m.def("setShutter", 		&SetShutter,		    "Initialize camera shutter");
    m.def("setImage",   		&SetImage,		        "Set image dimensions");
    m.def("startAcquisition",	&StartAcquisition,	    "Acquire CCD data");
    m.def("waitForAcquisition",	&WaitForAcquisition,	"Wait until an acquisition event occurs");
    m.def("abortAcquisition",	&AbortAcquisition,	    "Abort current acquisition if there is one");
    m.def("getAcquiredData",	
                                [](py::tuple& dim) {
                                    int imageWidth, imageHeight;
                                    imageWidth = dim[0].cast<int>();
                                    imageHeight = dim[1].cast<int>();
	                                at_32* imageDataArray = new at_32[imageWidth * imageHeight];
                                    int status = GetAcquiredData(imageDataArray, imageWidth * imageHeight);
                                    py::array imageDataMatrix = py::cast(reshapeImageData(
                                                imageDataArray,
                                                imageWidth,
                                                imageHeight
                                    ));

                                    py::dict out;
                                    out["data"] = imageDataMatrix;
                                    out["status"] = status;
                                    
                                    return out;
                                },     					"Return CCD data");		// converted into a NumPy array.

    m.def("coolerOn",		    &CoolerON,	        	"Turn on Thermoelectric Cooler (TEC)");
    m.def("coolerOff",		    &CoolerOFF,	            "Turn off Thermoelectric Cooler (TEC)");
    m.def("setTargetTEC",	    &SetTemperature,    	"Set target TEC temperature");
    m.def("getStatusTEC",	
                                [](void) {
                                    float temperature;
                                    temperature = -999.0;

                                    int status;
                                    status = GetTemperatureF(&temperature);
                                    py::dict out;
                                    out["temperature"]	= temperature;
                                    out["status"]	= status;
                                
                                    return out;
                                },	                    "Get TEC temperature and status");

    m.def("getRangeTEC",	    
                                [](void) {
                                    int min, max;
                                    min = -999;
                                    max = -999;
                                    
                                    int status;
                                    status = GetTemperatureRange(&min, &max);
                                    py::dict out;
                                    out["min"] = min;
                                    out["max"] = max;
                                    out["status"] = status;

                                    return out;
                                },                      "Get valid range of temperatures (C) which TEC can cool to");
    m.def("setFanMode",		    &SetFanMode,		    "Set fan mode");
    m.def("setNumberKinetics",  &SetNumberKinetics,     "Set the number of scans to be taken during a single acquisition sequence");
    m.def("setKineticCycleTime",&SetKineticCycleTime,   "Set the kinetic cycle time");
}
