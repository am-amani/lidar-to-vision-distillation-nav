#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/noetic/setup.bash

cd "$repo_root/catkin_ws"
rosdep install --from-paths src --ignore-src --rosdistro noetic -r -y
catkin_make

echo "Build complete. Run: source $repo_root/catkin_ws/devel/setup.bash"

