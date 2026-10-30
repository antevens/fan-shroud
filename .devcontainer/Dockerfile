FROM mcr.microsoft.com/devcontainers/base:3.0.10-noble@sha256:21e9e3275736cb3bc33a2904b279a2ab292c51fedd53c2963463627d4586c3e6

ARG ELEGOOSLICER_VERSION=1.5.3.5
ARG ELEGOOSLICER_SHA256=7b3b3f08e0d0d51bb472c85865d1be9b0c28385423daba1cb0c3b225d0101afc

# python3-venv: project venv.
# libgl1, libx11-6: OpenCascade (build123d's OCP wheel).
# libopengl0 to libgstreamer-plugins-base1.0-0: ElegooSlicer AppImage host libraries.
# xvfb, xauth, libgl1-mesa-dri: headless X and software OpenGL for the slicer and scratch/render_views.py.
# shellcheck: lint for the shell scripts.
RUN apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3-venv \
    libgl1 \
    libx11-6 \
    libopengl0 \
    libglu1-mesa \
    libegl1 \
    libgtk-3-0t64 \
    libwebkit2gtk-4.1-0 \
    libsecret-1-0 \
    libgstreamer-plugins-base1.0-0 \
    xvfb \
    xauth \
    libgl1-mesa-dri \
    shellcheck \
  && rm -rf /var/lib/apt/lists/*

# Verified AppImage extracted to /opt/elegooslicer (no FUSE needed).
RUN curl -fsSL -o /tmp/ElegooSlicer.AppImage \
    "https://github.com/elegooofficial/ElegooSlicer/releases/download/v${ELEGOOSLICER_VERSION}/ElegooSlicer_Linux_V${ELEGOOSLICER_VERSION}.AppImage" \
  && echo "${ELEGOOSLICER_SHA256}  /tmp/ElegooSlicer.AppImage" | sha256sum -c - \
  && chmod +x /tmp/ElegooSlicer.AppImage \
  && cd /tmp \
  && ./ElegooSlicer.AppImage --appimage-extract >/dev/null \
  && mv /tmp/squashfs-root /opt/elegooslicer \
  && chmod -R a+rX /opt/elegooslicer \
  && rm /tmp/ElegooSlicer.AppImage

COPY elegooslicer /usr/local/bin/elegooslicer

ENV ELEGOOSLICER_DIR=/opt/elegooslicer
