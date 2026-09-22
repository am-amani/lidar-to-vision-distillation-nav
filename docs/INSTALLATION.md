# Installation

## Supported reference platform

The code was recovered and checked on Ubuntu 20.04 with ROS Noetic, Gazebo
11.15.1 and Python 3.8.10. ROS Noetic reached end of life, so preserving an
Ubuntu 20.04 machine, VM, or container is recommended for long-term use.

This branch also builds the recovered TurtleBot3 1.2.6 and `slam_gmapping`
1.4.2 packages. The setup script installs their ROS package dependencies.

## Native installation

Install ROS Noetic Desktop Full first. Then clone and build:

```bash
git clone https://github.com/am-amani/lidar-to-vision-distillation-nav.git
cd lidar-to-vision-distillation-nav
./scripts/install_dependencies.sh
./scripts/build_workspace.sh
```

The ROS Python modules must remain visible to the selected Python interpreter.
The simplest supported setup uses Ubuntu's `/usr/bin/python3` and `pip3`.

## Conda alternative

```bash
conda env create -f environment.yml
conda activate drl-navigation
```

Conda can hide ROS packages installed under `/opt/ros/noetic`. If imports such
as `rospy` or `cv_bridge` fail, prefer the system Python setup or add the ROS
Python path only after confirming ABI compatibility.

## Build and environment

```bash
source /opt/ros/noetic/setup.bash
./scripts/build_workspace.sh
source catkin_ws/devel/setup.bash
export GAZEBO_RESOURCE_PATH="$PWD/catkin_ws/src/multi_robot_scenario/launch"
export ROS_HOSTNAME=localhost
export ROS_MASTER_URI=http://localhost:11311
export ROS_PORT_SIM=11311
```

## Common problems

- **A ROS node cannot be imported:** source `/opt/ros/noetic/setup.bash` and
  `catkin_ws/devel/setup.bash` in the same terminal.
- **Gazebo cannot find a world or model:** set `GAZEBO_RESOURCE_PATH` to the
  repository path shown above.
- **CUDA out of memory:** use CPU or reduce the distillation batch size.
- **A replay buffer is not found:** download both buffers (see
  `docs/ARTIFACTS.md`) and set `REPLAY_BUFFER_DIR` to their folder.
- **A model shape does not match:** checkpoints belong to different teacher or
  student architectures. Use the checkpoint set named for the script.
