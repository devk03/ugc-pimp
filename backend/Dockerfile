# --- Base Image Stage ---
# Specify the base image for this Docker build.
# We're using the official Python image, specifically version 3.13,
# based on the Debian "Bookworm" release, in its "slim" variant.
# The 'slim' variant is smaller than the full version, containing only the minimal packages needed to run Python.
# Using a specific version tag (3.13-slim-bookworm) ensures reproducibility.
FROM python:3.13-slim-bookworm

# --- System Dependencies Installation ---
# The `RUN` instruction executes commands in a new layer on top of the current image.
# First, `apt-get update` resynchronizes the package index files from their sources (essential before installing).
# Then, `apt-get install -y --no-install-recommends curl ca-certificates` installs necessary system packages:
#   `curl`: A command-line tool for transferring data with URLs, needed by the uv installer script.
#   `ca-certificates`: Provides system CAs (Certificate Authorities) to allow secure HTTPS connections (like downloading the installer).
#   `-y`: Automatically answers "yes" to prompts during installation.
#   `--no-install-recommends`: Prevents installing recommended (but often unnecessary) packages, keeping the image smaller.
# Note: It's good practice to chain `apt-get update` and `install` in one RUN command and potentially add `&& apt-get clean && rm -rf /var/lib/apt/lists/*` at the end
#       to reduce layer size by cleaning up the apt cache after installation, though omitted here for simplicity based on the original file.
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

# --- uv Installation ---
# The `ADD` instruction copies files, directories, or remote file URLs into the filesystem of the image.
# Here, it downloads the official uv installer script from the Astral website
# and places it inside the container at the path `/uv-installer.sh`.
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Execute the downloaded uv installer script using the shell (`sh`).
# This script installs the `uv` binary (a fast Python package installer and resolver).
# After successful installation (`&&`), the installer script itself is removed (`rm /uv-installer.sh`)
# to keep the final image clean and slightly smaller.
RUN sh /uv-installer.sh && rm /uv-installer.sh

# --- Environment Configuration ---
# The `ENV` instruction sets environment variables within the image.
# Here, we modify the system's `PATH` variable.
# We prepend `/root/.local/bin/` (the default installation location for `uv` when installed as root)
# to the existing `$PATH`. This ensures that the `uv` command can be found and executed directly
# from anywhere within the container without specifying its full path.
ENV PATH="/root/.local/bin/:$PATH"

# --- Application Setup ---
# The `WORKDIR` instruction sets the working directory for subsequent instructions (`RUN`, `CMD`, `ENTRYPOINT`, `COPY`, `ADD`).
# Any commands will be run from `/app`, and relative paths will be based on this directory.
# If the directory doesn't exist, `WORKDIR` will create it.
WORKDIR /app

# Copy the `pyproject.toml` file from the build context (your local machine's directory where you run `docker build`)
# into the current working directory (`/app`) inside the container.
# This file defines the project metadata and its dependencies.
# We copy this *before* the rest of the source code to leverage Docker's layer caching.
# If `pyproject.toml` doesn't change, Docker can reuse the layer created by the next `RUN` instruction.
COPY pyproject.toml .

# Use `uv` to install the Python dependencies defined in `pyproject.toml`.
# `uv pip install`: Command to install packages.
# `--system`: Installs packages into the main Python environment of the container (system-wide) rather than creating a virtual environment.
#           This is often preferred in containers as the container itself provides isolation.
# `.`: Specifies that `uv` should install the project defined in the `pyproject.toml` file located in the current directory (`/app`).
#      This includes installing all dependencies listed in `[project.dependencies]`.
RUN uv pip install --system .

# Copy the rest of the application source code from the build context (your local directory)
# into the current working directory (`/app`) inside the container.
# The first `.` represents the source directory on your host machine (the build context).
# The second `.` represents the destination directory inside the container (the current `WORKDIR`, which is `/app`).
# This is done *after* installing dependencies so that changes to your source code don't invalidate the dependency installation layer cache.
COPY . .

# --- Runtime Configuration ---
# The `EXPOSE` instruction informs Docker that the container listens on the specified network port(s) at runtime.
# This is primarily documentation and doesn't actually publish the port.
# It signals that the application inside the container is intended to serve traffic on port 8000.
# You still need to use the `-p` flag (e.g., `-p 8080:8000`) with `docker run` to map a host port to this container port.
EXPOSE 8000

# The `CMD` instruction specifies the default command to execute when a container is started from this image.
# There can only be one `CMD` instruction in a Dockerfile. If you list more than one `CMD`, only the last `CMD` will take effect.
# This uses the "exec form" (a JSON array), which is generally preferred as it doesn't invoke a shell.
# It runs the `uvicorn` web server:
#   `uv run`: Executes the following command within the environment managed by uv (though less critical here as we used `--system`).
#   `uvicorn`: The ASGI server used to run applications like FastAPI/Starlette.
#   `main:app`: Tells uvicorn to find the ASGI application instance named `app` inside the Python module `main.py`.
#   `--host 0.0.0.0`: Makes the server listen on all available network interfaces inside the container. This is crucial for accessing the server from outside the container (via the mapped port).
#   `--port 8000`: Specifies that the uvicorn server should listen on port 8000 inside the container (matching the `EXPOSE` instruction).
CMD ["uv", "run", "uvicorn", "router.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]