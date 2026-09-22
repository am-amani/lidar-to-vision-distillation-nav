#!/usr/bin/env bash
set -euo pipefail

if [[ "$(lsb_release -sc 2>/dev/null || true)" != "focal" ]]; then
  echo "Warning: the validated platform is Ubuntu 20.04 (focal)." >&2
fi

if [[ ! -f /opt/ros/noetic/setup.bash ]]; then
  echo "ROS Noetic is not installed. Install ROS Noetic Desktop Full first." >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install -y \
  python3-pip \
  python3-rosdep \
  python3-catkin-tools \
  ros-noetic-gazebo-ros-pkgs \
  ros-noetic-robot-state-publisher \
  ros-noetic-xacro \
  ros-noetic-cv-bridge \
  ros-noetic-velodyne-msgs

python3 -m pip install --user -r requirements.txt

if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  sudo rosdep init
fi
rosdep update

echo "Dependencies installed. Run ./scripts/build_workspace.sh next."

