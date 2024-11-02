# Evora

Andor wrapper for Evora and Flask server.

## Installation

`evora-server` requires the proprietary Andor libraries to be installed in `/usr/local/lib`. The library can be used for debugging without the Andor libraries, but they are necessary to run the actual camera. 

To install `evora-server`, clone the repository and run

```console
pip install .
```

or to install in editable mode

```console
pip install -e .
```

### Debug mode

To run the server in debug mode, with the dummy module mocking the camera, edit `evora/debug.py` and set `DEBUGGING = True`. This will create a folder in the `evora-server` root that acts as the `/data` folder.

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

**Note**: Mac OSx doesn't allow the creation of folders in the root `/` directory, since [OSx makes the root directory read-only by default](https://apple.stackexchange.com/questions/388236/unable-to-create-folder-in-root-of-macintosh-hd).

## Deploying for production

The recommended way to run `evora-server` in production is by running the app with the Flask development server with a single process and threading. This allows for concurrent routes and asyncio to work (which is required for features such as aborting exposures). At this point this is preferred to using a UWSGI layer such as `gunicorn` since the camera has a single connection so we cannot run multiple workers.

First, make sure the `/data/ecam` directory exists with the proper user permissions

```console
sudo mkdir -p /data/ecam && sudo chown -R $USER /data
```

and that the Andor SDK is installed with

```console
ls /usr/local/lib/libandor.so
```

Try to run `standalone-start.sh` in the `evora-server` now. It should start downloading around ~20 GB of data for astrometry. Once this is done, you should see the server spin up (ignore the "This is a development server" warning). Test it with `curl localhost:8000/getStatus`.

To run this command in the background as a user `systemd` service, create a file `/usr/lib/systemd/user/evora-server.service` with the contents

```ini
[Unit]
Description=evora-server

[Service]
WorkingDirectory=/home/mrouser/Github/evora-server
ExecStart=/home/mrouser/Github/evora-server/standalone-start.sh

[Install]
WantedBy=default.target
```

Change `WorkingDirectory` and `ExecStart` to the download location of `evora-server`, then run the following commands to get it to run at system start.

```console
systemctl --user daemon-reload
systemctl --user enable --now enable evora-server
systemctl --user status evora-server
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
