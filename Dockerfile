# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

# Install the project into `/app`
WORKDIR /app

# Install libusb-1.0-0 for andor drivers
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get -y update
RUN apt-get -y install libusb-1.0-0 libusb-1.0-0-dev


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

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=setup.py,target=setup.py \
    uv sync --frozen --no-install-project --no-dev

# Then, add the rest of the project source code and install it
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

ENV WORKERS=1
ENV PORT=80

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

CMD ["sh", "-c", "fastapi run src/lvmapi/app.py --port $PORT --workers $WORKERS"]
