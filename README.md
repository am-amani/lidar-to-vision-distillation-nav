# Multi-Sensor DRL Robot Navigation

Research code for mapless mobile-robot navigation with Twin Delayed Deep
Deterministic Policy Gradient (TD3), LiDAR and camera observations, and
teacher-student policy distillation. It accompanies the paper
[*A Unified Conditional Policy for Multi-Robot Navigation via LiDAR-to-Vision
Distillation*](https://doi.org/10.3390/machines14080936) (Machines, 2026); see
[Citation](#citation).

This branch contains the **TurtleBot3 Waffle Pi** simulation. The
[`main`](../../tree/main) branch contains the Pioneer 3-DX version. Both use
ROS Noetic and Gazebo 11 on Ubuntu 20.04.

The project began from Reinis Cimurs' MIT-licensed
[DRL-robot-navigation](https://github.com/reiniscimurs/DRL-robot-navigation)
implementation. The original copyright and license are retained. This
repository adds the thesis experiments for multi-robot, multi-sensor policy
distillation, robot identity conditioning, and LiDAR-to-vision handover.

## What is in this repository?

- `TD3/train_velodyne_td3.py`: train the LiDAR TD3 teacher.
- `TD3/test_velodyne_td3.py`: evaluate a saved LiDAR TD3 teacher.
- `TD3/distillation_CNNs.py`: camera, scan, encoder and student actor models.
- `TD3/train_student.py`: train the multimodal student from the Pioneer and
  Waffle teacher replay buffers (robot ID on LiDAR, no ID on camera).
- `TD3/test_handover.py`: evaluate a student that starts with LiDAR and
  switches to the camera.
- `catkin_ws/src/turtlebot3`: the recovered TurtleBot3 1.2.6 source snapshot.
- `catkin_ws/src/slam_gmapping`: `slam_gmapping` 1.4.2 at recovered commit
  `0835d19` (only executable-bit differences were present locally).
- `catkin_ws/src/multi_robot_scenario`: shared Gazebo world and launch files.
- `catkin_ws/src/velodyne_simulator`: simulated Velodyne sensor integration.
- `docs/SCRIPTS.md`: what each Python file does.
- `docs/TUTORIAL.md`: step-by-step walkthrough with Docker.
- `docs/ARTIFACTS.md`: pretrained models and replay buffers, and where to
  download them.

## Quick start

### Docker (recommended)

No ROS installation is needed; the image contains ROS Noetic, Gazebo 11 and all
Python dependencies and runs headless:

```bash
docker build -t drl-nav:waffle .
docker run --rm drl-nav:waffle scripts/docker_verify.sh
```

**New here? Follow [docs/TUTORIAL.md](docs/TUTORIAL.md)**: it goes from
installation to evaluating the pretrained models and training your own teacher
and student. All Docker options are in [docs/DOCKER.md](docs/DOCKER.md). The
native installation follows.

### 1. System requirements

The validated native environment is:

- Ubuntu 20.04
- ROS Noetic
- Gazebo 11
- Python 3.8
- NVIDIA GPU optional; CPU works for the base TD3 code

Install ROS Noetic using the official ROS instructions, then install the
project dependencies:

```bash
cd lidar-to-vision-distillation-nav
./scripts/install_dependencies.sh
```

The script installs ROS packages with APT and Python packages with `pip3`.
For an isolated Python environment, see [docs/INSTALLATION.md](docs/INSTALLATION.md).

### 2. Build the ROS workspace

```bash
./scripts/build_workspace.sh
source catkin_ws/devel/setup.bash
```

### 3. Configure the shell

Run this in every new terminal:

```bash
source /opt/ros/noetic/setup.bash
source catkin_ws/devel/setup.bash
export ROS_HOSTNAME=localhost
export ROS_MASTER_URI=http://localhost:11311
export ROS_PORT_SIM=11311
export GAZEBO_RESOURCE_PATH="$PWD/catkin_ws/src/multi_robot_scenario/launch"
```

### 4. Train the TurtleBot3 Waffle teacher

```bash
cd TD3
python3 train_velodyne_td3.py
```

Training writes TensorBoard data under `TD3/runs` and teacher weights under
`TD3/pytorch_models`. These generated files are intentionally ignored by Git.

Monitor training from another terminal:

```bash
tensorboard --logdir TD3/runs
```

### 5. Evaluate a teacher

Place the Waffle teacher files in `TD3/pytorch_models` using these canonical
names:

```text
TD3_velodyne_actor.pth
TD3_velodyne_critic.pth
```

Then run:

```bash
cd TD3
python3 test_velodyne_td3.py
```

Pretrained teachers for both robots can be downloaded as described in
[docs/ARTIFACTS.md](docs/ARTIFACTS.md).

### 6. Distillation and handover

Student training uses the published Pioneer and Waffle replay buffers;
handover evaluation uses the pretrained four-part student checkpoints. Both
are in the data record ([docs/ARTIFACTS.md](docs/ARTIFACTS.md)). Read
[docs/EXPERIMENTS.md](docs/EXPERIMENTS.md) for the inputs and environment
variables of these scripts.

## Validation

Run the repository's non-destructive checks with:

```bash
./scripts/validate_repository.sh
```

The validation checks Python syntax, shell syntax, expected ROS packages,
forbidden absolute home paths, and the presence of documented entry points.
Full RL training is intentionally not part of this quick check. The precise
validation performed for the preserved release is recorded in
[docs/VALIDATION_REPORT.md](docs/VALIDATION_REPORT.md).

## Citation

If you use this code, the pretrained models or the replay buffers, please cite:

> A. M. Amani, S. Amani and A. MajidiRad, "A Unified Conditional Policy for
> Multi-Robot Navigation via LiDAR-to-Vision Distillation," *Machines*,
> vol. 14, no. 8, art. 936, 2026. doi:
> [10.3390/machines14080936](https://doi.org/10.3390/machines14080936)

```bibtex
@article{amani2026unified,
  title   = {A Unified Conditional Policy for Multi-Robot Navigation via LiDAR-to-Vision Distillation},
  author  = {Amani, Amir Mahdi and Amani, Sajjad and MajidiRad, AmirHossein},
  journal = {Machines},
  volume  = {14},
  number  = {8},
  pages   = {936},
  year    = {2026},
  doi     = {10.3390/machines14080936}
}
```

GitHub's "Cite this repository" button uses [CITATION.cff](CITATION.cff). The
work started as the master's thesis *Multi-Sensor Robotic Navigation Using
Distillation Policy* (University of Padua, 2024,
<https://hdl.handle.net/20.500.12608/74949>).

## Acknowledgement

The base code of this project comes from
[DRL-robot-navigation](https://github.com/reiniscimurs/DRL-robot-navigation)
by Reinis Cimurs: the TD3 agent, the Gazebo environment wrapper, the training
world and the Pioneer 3-DX simulation setup. This repository extends it with
the camera sensor, the TurtleBot3 Waffle, teacher-student policy distillation,
robot-ID conditioning and LiDAR-to-vision handover. If you use the base TD3
navigation part, please also cite their work:

> R. Cimurs, I. H. Suh and J. H. Lee, "Goal-Driven Autonomous Exploration
> Through Deep Reinforcement Learning," *IEEE Robotics and Automation Letters*,
> vol. 7, no. 2, pp. 730-737, 2022. doi:
> [10.1109/LRA.2021.3133591](https://doi.org/10.1109/LRA.2021.3133591)

```bibtex
@article{cimurs2022goal,
  title   = {Goal-Driven Autonomous Exploration Through Deep Reinforcement Learning},
  author  = {Cimurs, Reinis and Suh, Il Hong and Lee, Jin Han},
  journal = {IEEE Robotics and Automation Letters},
  volume  = {7},
  number  = {2},
  pages   = {730--737},
  year    = {2022},
  doi     = {10.1109/LRA.2021.3133591}
}
```

## License and attribution

The repository is distributed under the included MIT license inherited from
the upstream project. Third-party ROS packages retain their respective
licenses. See [docs/THIRD_PARTY.md](docs/THIRD_PARTY.md).
