# Running in Docker

The image bundles ROS Noetic, Gazebo 11, the built catkin workspace and the
Python 3.8 dependencies, so nothing has to be installed on the host. It runs
without a GPU and without a display (a virtual X server is started inside).

Tested with Docker Desktop 29.7 (Windows 11, WSL 2 backend, Linux containers).

## Requirements

- Docker with Linux containers, about 20 GB free disk (the image is about 16 GB)
- Internet during `docker build` (apt, PyPI and two Gazebo meshes)
- Optional: an NVIDIA GPU and the NVIDIA Container Toolkit for `--gpus all`
  (only PyTorch uses it; Gazebo always renders in software). Verified: with
  `--gpus all` PyTorch sees the GPU inside the image.

## Build

```bash
git clone -b turtlebot3-waffle https://github.com/am-amani/lidar-to-vision-distillation-nav.git
cd lidar-to-vision-distillation-nav
docker build -t drl-nav:waffle .
```

The first build takes 10-20 minutes. This is the `turtlebot3-waffle` branch:
clone with `-b turtlebot3-waffle`. The Pioneer image on `main` is tagged
`drl-nav:pioneer`.

On Windows, `.gitattributes` forces LF line endings so the shell scripts keep
working inside the container. In Git Bash prefix commands that mount paths with
`MSYS_NO_PATHCONV=1`.

## Check the installation

No model files are needed for the first check:

```bash
docker run --rm drl-nav:waffle scripts/docker_verify.sh
```

It validates the repository, finds the ROS packages, imports every Python
dependency and prints `PASS`/`FAIL` per check.

Model files are not part of this repository; download them as described in
[ARTIFACTS.md](ARTIFACTS.md). Mount them to extend the check. `TEACHER_DIR`
must contain `TD3_velodyne_actor.pth`; `ARTIFACTS_DIR` is the extracted data
folder (with `teacher/` and `student/`):

```bash
docker run --rm \
  -v "$TEACHER_DIR:/workspace/TD3/pytorch_models:ro" \
  -v "$ARTIFACTS_DIR:/artifacts:ro" \
  drl-nav:waffle scripts/docker_verify.sh
```

This also loads every recovered checkpoint and runs a 2-minute headless Gazebo
episode loop with the teacher (`SIM_SECONDS=300` for longer).

## Run the experiments

Evaluate the LiDAR teacher (2000 episodes):

```bash
docker run --rm -v "$TEACHER_DIR:/workspace/TD3/pytorch_models:ro" \
  drl-nav:waffle bash -c "cd TD3 && python3 test_velodyne_td3.py"
```

Train a teacher (checkpoints are written to the mounted folder):

```bash
docker run --rm -v "$PWD/weights:/workspace/TD3/pytorch_models" \
  -v "$PWD/runs:/workspace/TD3/runs" \
  drl-nav:waffle bash -c "cd TD3 && python3 train_velodyne_td3.py"
```

LiDAR-to-vision handover evaluation of a student checkpoint. `CHECKPOINTS_DIR`
holds files named like `epoch 1680.datcamera_model`; logs go to `./logs`:

```bash
docker run --rm \
  -v "$CHECKPOINTS_DIR:/checkpoints:ro" -v "$PWD/logs:/workspace/TD3/logs" \
  -e DISTILLATION_CHECKPOINT_DIR=/checkpoints \
  -e DISTILLATION_CHECKPOINT_EPOCH=1680 -e HANDOVER_EPISODES=10 \
  drl-nav:waffle bash -c "cd TD3 && python3 test_handover.py"
```

Train a student from the replay buffers (no Gazebo; `BUFFER_DIR` holds both
buffer files, checkpoints go to `./runs/new_runs/<experiment>`):

```bash
docker run --rm \
  -v "$BUFFER_DIR:/buffers:ro" -v "$PWD/runs:/workspace/TD3/runs" \
  -e REPLAY_BUFFER_DIR=/buffers -e DISTILLATION_EPOCHS=50 \
  drl-nav:waffle bash -c "cd TD3 && python3 train_student.py"
```

Interactive shell: `docker run --rm -it drl-nav:waffle`.

## Known limitations

- Student training holds both replay buffers in memory: give Docker at least
  8 GB of RAM (Docker Desktop: Settings > Resources, or `.wslconfig` on WSL 2).
- `epoch 4770` is a legacy architecture and cannot be loaded by the current
  network definitions.
- The world uses two meshes (`fire_hydrant`, `cardboard_box`) from Gazebo's old
  online model database. The Dockerfile downloads them at build time; if that
  server disappears the build fails and the meshes must be vendored.
- RViz starts in the virtual display and is not visible. Showing it on the host
  (an X server plus `-e DISPLAY=<host>:0`) has not been tested.
- `pip` prints dependency-conflict warnings during the build (TensorFlow versus
  protobuf, typing-extensions and python-dateutil). All imports were verified
  to work; pinning the transitive packages would remove the warnings.
