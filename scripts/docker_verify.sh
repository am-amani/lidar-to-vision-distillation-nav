#!/usr/bin/env bash
# Self-check for the Docker image; see docs/DOCKER.md.
#   docker run --rm drl-nav:pioneer scripts/docker_verify.sh
#   docker run --rm -v <teacher_dir>:/workspace/TD3/pytorch_models:ro drl-nav:pioneer scripts/docker_verify.sh
#   docker run --rm -v <local_artifacts>:/artifacts:ro ... scripts/docker_verify.sh
# The simulation test runs only when a teacher checkpoint is mounted; SIM_SECONDS sets its length.
set -uo pipefail
cd /workspace
fail=0

check() {
  local name=$1; shift
  if "$@" >/tmp/check.log 2>&1; then
    echo "PASS  $name"
  else
    echo "FAIL  $name"; tail -5 /tmp/check.log; fail=1
  fi
}

check "repository validation" ./scripts/validate_repository.sh
check "ROS packages found" bash -c 'for p in multi_robot_scenario velodyne_gazebo_plugins velodyne_description; do rospack find "$p" >/dev/null || exit 1; done'
check "python imports" python3 -c "import numpy, torch, torchvision, cv2, pandas, squaternion, rospy, cv_bridge; from torch.utils.tensorboard import SummaryWriter"

if [[ -d /artifacts ]]; then
  check "all mounted checkpoints load" python3 scripts/validate_models.py /artifacts
fi

if [[ -f TD3/pytorch_models/TD3_velodyne_actor.pth ]]; then
  (cd TD3 && timeout "${SIM_SECONDS:-120}" python3 test_velodyne_td3.py >/tmp/sim.log 2>&1)
  reached=$(grep -c "Target reached" /tmp/sim.log)
  missed=$(grep -c "Target not reached" /tmp/sim.log)
  if (( reached > 0 )); then
    echo "PASS  simulation: $reached targets reached, $missed missed in ${SIM_SECONDS:-120}s"
  else
    echo "FAIL  simulation: no target reached"; tail -8 /tmp/sim.log; fail=1
  fi
fi

exit $fail
