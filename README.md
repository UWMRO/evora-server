# Evora

Andor wrapper for Evora and Flask server.

## Installation

`evora-server` requires the proprietary Andor libraries to be installed in `/usr/local/lib`. The library can be used for debugging without the Andor libraries, but they are necessary to run the actual camera. To run the server in debug mode, with the dummy module mocking the camera, edit `debug.py` and set `DEBUGGING = True`.

To install `evora-server`, clone the repository and run

```console
pip install .
```

or to install in editable mode

```console
pip install -e .
```

## Running the server

To run the server, from a terminal at the root of the project, execute

```console
python app.py
```

which is equivalent to

```console
flask --debug run --port 3000
```



## Images

`evora-server` will save camera files to `/data/ecam/DATE` where `DATE` is in the format `20230504` and rotates at midnight UTC.

If `/data/ecam` does not exist, create it with `mkdir -p` and make sure it has the right permissions for `evora-server` to write to it.

## Deploying for production

The recommended way to run `evora-server` in production is by running the app with the Flask development server with a single process and threading. This allows for concurrent routes and asyncio to work (which is required for features such as aborting exposures). At this point this is preferred to using a UWSGI layer such as `gunicorn` since the camera has a single connection so we cannot run multiple workers.

To run this command in the background as a systemd service, create a file `/etc/systemd/system/evora-server.service` with the contents

```ini
[Unit]
Description=evora-server

[Service]
WorkingDirectory=/home/mrouser/Github/evora-server
ExecStart=/home/mrouser/Github/evora-server/standalone-start.sh

[Install]
WantedBy=multi-user.target
```

Here we are pointing to the file `standalone-start.sh` in the repo, which loads the conda environment and starts the server in production mode (port 8000, threading, one worker). This may need to be changed for a location other than MRO. Then start the systemd service with

```console
sudo systemctl daemon-reload
sudo systemctl enable --now enable evora-server
sudo systemctl restart evora-server
```

### Configuring nginx

In addition to running the server, a reverse proxy is needed to run the Evora client and server in the same HTTP server. In Ubuntu, install `nginx` (alternatively you can use `Apache`) with

```console
sudo apt update
sudo apt install nginx
```

and adjust the firewall to open the desired ports. Then start `nginx` with

```console
sudo systemctl enable --now nginx
```

We'll now add a new site for Evora. Create a new file `/etc/nginx/sites-enabled/evora.conf` with

```console
sudo vim /etc/nginx/sites-enabled/evora.conf
```

and include the configuration

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name localhost;
    access_log  /usr/local/var/log/nginx/evora.log;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 75s;
        proxy_read_timeout 1800s;
    }

    location /data {
       alias /data;
        autoindex on;
        index index.html index.php;
    }
}
```

This configuration creates a server running on port `80` (the default HTTP) and adds a reverse proxy to where the `evora-server` webapp is running. It also creates a route to expose and browse `/data`.

After this, restart `nginx` with

```console
sudo systemctl restart nginx
```

and test that it works by navigating to [http://localhost/api/getTemperature](http://localhost/api/getTemperature).

## References

- [Andor SDK documentation](https://neurophysics.ucsd.edu/Manuals/Andor%20Technology/Andor_Software_Development_Kit.pdf)
