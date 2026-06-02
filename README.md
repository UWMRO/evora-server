# evora-server

`evora-server` contains the backend code to communicate with the MRO Andor "Evora" camera, as well as the HTTP API to control the camera, expose, and retrieve images. It also manages the focuser, filter wheel, and weather station. See [evora-client](https://github.com/uwmro/evora-client) for the frontend code.

## Installation

It is recommended to install `evora-server` in a virtual environment using [uv](https://astral.sh/uv/). To do so, run the following commands:

```bash
uv venv
source .venv/bin/activate
uv sync
```

Alternatively you can install the software in editable mode with `pip install -e .` (note that this won't install the development dependencies).

For the installation script to build the shared library around the Andor SDK, the Andor libraries must be installed and available in the system The libraries are not publicly released, so please contact the maintainers if you need access to them. The Andor SDK is only available for Linux machines.

## Running the server

### For development

To run the server in development mode, you need to set the environment variable `$EVORA_SERVER_DEBUG=1` and then run

```bash
fastapi dev --host 0.0.0.0 --port 8888 --reload src/evora_server/app.py
```

Alternatively you can just use the included [poe](https://poethepoet.natn.io/index.html) task:

```bash
poe dev
```

Note that if you are running the server on a non-Linux machine, or if the `andor_wrapper` shared library has not been build, the server will always start in debug mode. You can check the logs to see if the server is running in debug mode or not.

```plaintext
      INFO   Started reloader process [80418] using WatchFiles
      INFO   Started server process [80422]
      INFO   Waiting for application startup.
   WARNING   Using the **mock** Andor wrapper.
      INFO   Application startup complete.
```
