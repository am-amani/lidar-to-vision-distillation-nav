# Validation report

This file is updated after both branches are tested from fresh clones.

## Current recovery audit

- All 25 Pioneer-branch top-level Python files parsed successfully with Python
  3.8.10 before publication cleanup.
- ROS Noetic, Gazebo 11.15.1, PyTorch 2.1.1+cu121 and torchvision 0.16.1+cu121
  were detected on the recovery machine.
- Generated catkin build directories and Python caches are excluded.
- No authentication secrets were found by the initial text scan.
- Several historical training scripts are blocked by replay buffers that were
  referenced but not found in either recovered folder. The two buffers used by
  the latest student training scripts were found later (2026-09-22) and are
  published with the models; see `docs/ARTIFACTS.md`.

## Fresh-clone recovery test (2026-08-11)

- Cloned the new GitHub code repository and the private artifact repository
  into an empty directory.
- Downloaded all three private release archives with the documented
  `download.sh` command. All 46 recovered files passed `MANIFEST.sha256`.
- Loaded both teacher pairs, nine compatible four-part student checkpoints,
  and the joint robot-ID checkpoint. Epoch 4770 also deserialized, but is
  correctly reported as a readable legacy 61-input architecture.
- `validate_repository.sh` passed on both branches.
- A clean catkin build compiled four packages on `main` and nine packages on
  `turtlebot3-waffle`.
- Bounded evaluation from the fresh Pioneer clone spawned the robot, loaded
  the private teacher, consumed live sensor data, and repeatedly reached
  targets.
- Bounded evaluation from the fresh Waffle clone did the same with the Waffle
  teacher, reaching targets and recording collision termination correctly.
- The tests were intentionally stopped after 70 seconds. The resulting
  `ROSInterruptException` is ROS reacting to that controlled shutdown.

These checks validate recovery, model loading, compilation, simulation and
short inference runs. They do not claim completion of a new multi-million-step
training experiment.

## Pioneer native smoke tests

- Catkin configured all four packages and compiled both Velodyne Gazebo plugin
  libraries successfully.
- The recovered Pioneer teacher actor and critic loaded successfully.
- Gazebo started headlessly, spawned `r1`, and published odometry, camera and
  laser data.
- Teacher evaluation completed navigation episodes and reached targets during
  the bounded test.
- TD3 training entered its environment loop and stored multimodal replay
  experiences during the bounded test.
- Two recovered interface mismatches were fixed: callers now unpack the
  environment's camera/scan outputs, and the trainer stores those fields in
  the extended replay buffer.
- The final `ROSInterruptException` visible in bounded test logs is caused by
  the intentional timeout shutting ROS down; it is not a runtime failure.

## TurtleBot3 Waffle native smoke tests

- All recovered package-level `CMakeLists.txt` files are retained; the clean
  branch build uses them rather than the old generated build directory.
- Catkin then configured nine packages and compiled `slam_gmapping`,
  TurtleBot3 diagnostics and both Velodyne plugins successfully.
- The TurtleBot3 Waffle Pi spawned successfully in Gazebo and published scan,
  camera and odometry messages.
- The recovered Waffle teacher pair loaded and ran during a bounded inference
  test without a model or interface exception.
- Waffle training launched, initialized the simulation, reset the environment,
  and entered its first step. Its base trainer received the same six-field
  environment and seven-field replay-buffer compatibility fixes as the
  Pioneer branch.
- The recovered epoch-445 student checkpoint loaded all four networks. A
  bounded handover run completed one LiDAR episode, switched from LiDAR to
  camera control in the next episode, and continued producing vision actions.

## Docker validation (2026-09-22)

Environment: Docker Desktop 29.7.2, Windows 11, WSL 2, CPU only (no GPU, no
display). Image `drl-nav:pioneer` (16.3 GB) built from the `Dockerfile` in this
repository; the artifact repository release was mounted read-only.

- `scripts/docker_verify.sh`: repository validation, ROS package lookup, Python
  imports, loading of all 12 recovered checkpoint sets (two teachers, nine
  compatible students, the joint robot-ID student and the legacy epoch 4770)
  and a headless simulation all passed.
- Pioneer teacher, 150 s headless: 17 targets reached, 1 missed.
- Student handover (`DISTILLATION_CHECKPOINT_EPOCH=1680`, 10 episodes, CPU):
  8 successes, 2 failures (0.80), the same as the recorded 2026-06-29 GPU run
  of the same epoch. Epoch 4300, 20 episodes: 20 successes.
- Teacher training, 7 minutes bounded: six update rounds logged to TensorBoard,
  no errors.
- TurtleBot3 Waffle branch (own image): teacher evaluation, 7 minutes bounded,
  17 targets reached, 0 missed.

Defects found by this run and fixed on `main` and ported to this branch:

1. `test_velodyne_td3.py` and `train_velodyne_td3.py` could not load a
   CUDA-saved checkpoint on a CPU-only machine (`torch.load` without
   `map_location`).
2. `train_velodyne_td3.py` crashed at the end of the first episode when the
   replay buffer held fewer than `batch_size` transitions.
3. Gazebo downloaded `fire_hydrant` and `cardboard_box` from the online model
   database on every start (about 60 s, and the world lost its hydrant
   collision when offline); start-up then raced the first odometry message.
   The Dockerfile now bakes the models in and `GazeboEnv` waits for odometry.
4. Camera sensors need a display: the image now starts Xvfb.
5. Windows checkouts converted shell scripts to CRLF; `.gitattributes` forces LF.
6. The handover script's epoch and episode count were edited in the source; they
   are now `DISTILLATION_CHECKPOINT_EPOCH` and `HANDOVER_EPISODES`.

On this branch the Dockerfile additionally installs the TurtleBot3 ROS
dependencies listed in `scripts/install_dependencies.sh`.
