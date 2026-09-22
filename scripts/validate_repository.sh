#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

echo "Checking Python syntax..."
python3 -m compileall -q TD3

echo "Checking shell syntax..."
for script in scripts/*.sh; do
  bash -n "$script"
done

echo "Checking validation helper syntax..."
python3 -m py_compile scripts/validate_models.py

echo "Checking required source files..."
required=(
  TD3/train_velodyne_td3.py
  TD3/test_velodyne_td3.py
  TD3/velodyne_env.py
  TD3/replay_buffer.py
  TD3/distillation_CNNs.py
  TD3/train_student.py
  TD3/test_handover.py
  TD3/assets/multi_robot_scenario.launch
  catkin_ws/src/multi_robot_scenario/package.xml
)
for path in "${required[@]}"; do
  [[ -f "$path" ]] || { echo "Missing required file: $path" >&2; exit 1; }
done

echo "Checking the maintained entry points for private absolute paths..."
if grep -nE '/home/[^/]+/' \
  TD3/train_velodyne_td3.py \
  TD3/test_velodyne_td3.py \
  TD3/velodyne_env.py \
  TD3/test_handover.py; then
  echo "A maintained entry point contains a machine-specific home path." >&2
  exit 1
fi

echo "Checking ROS installation..."
if [[ -f /opt/ros/noetic/setup.bash ]]; then
  source /opt/ros/noetic/setup.bash
  rosversion -d
else
  echo "ROS Noetic not installed; ROS checks skipped."
fi

echo "Repository validation passed."
