SHELL = /bin/sh

andor_wrapper: andor_wrapper.cpp
	g++ -O3 -Wall -Werror -shared -std=c++11 -fPIC $$(python3 -m pybind11 --includes) andor_wrapper.cpp -o libandor_wrapper.so
	g++ -O3 -Wall -Werror -shared -std=c++11 -fPIC `python3 -m pybind11 --includes` -I python3 -I . andor_wrapper.cpp -o andor_wrapper`python3-config --extension-suffix` -L. -landor_wrapper -landor -Wl,-rpath,.

clean:
	rm -rf *.so

