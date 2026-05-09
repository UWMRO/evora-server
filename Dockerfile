# Use a Python image without uv. We don't need uv in the final image
# so we'll mount it only for syncing.
FROM python:3.14-slim

# Use the system Python across both stages
ENV UV_PYTHON_DOWNLOADS=0

# Install the project into `/app`
WORKDIR /app

# Install libusb-1.0-0 for andor drivers
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get -y update
RUN apt-get -y install libusb-1.0-0 libusb-1.0-0-dev build-essential

# Copy andor drivers
COPY andor /app/andor

# Install andor drivers
RUN cd /app/andor && bash install_andor

# Delete source drivers folder
RUN rm -rf /app/andor

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Then, add the rest of the project source code and install it
ADD ./pyproject.toml /app
ADD ./uv.lock /app
ADD ./setup.py /app
ADD ./src /app/src

RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Remove build tools and clean up apt cache to save space
RUN apt-get purge -y --auto-remove build-essential libusb-1.0-0-dev && \
    rm -rf /var/lib/apt/lists/*

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

ENV WORKERS=1
ENV PORT=80

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

CMD ["sh", "-c", "fastapi run src/evora_server/app.py --port $PORT --workers $WORKERS"]
