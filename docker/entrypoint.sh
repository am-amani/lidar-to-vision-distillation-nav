#!/usr/bin/env bash
# Container entrypoint: source ROS, start a virtual display, then run the command.
set -e

source /opt/ros/noetic/setup.bash
source /workspace/catkin_ws/devel/setup.bash

# Override DISPLAY (e.g. with an X server on the host) to skip the virtual display.
if [[ "${DISPLAY:-}" == ":99" ]] && [[ ! -e /tmp/.X11-unix/X99 ]]; then
  Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp >/dev/null 2>&1 &
  sleep 1
fi

exec "$@"
