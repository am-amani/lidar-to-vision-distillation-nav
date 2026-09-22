# Tutorial: from zero to a trained navigation policy

This walks through the whole pipeline with Docker: check the install, watch a
pretrained LiDAR teacher drive, test the LiDAR-to-camera handover of a
pretrained student, and train your own teacher and student. No ROS
installation is needed. All commands are for a Linux or macOS shell, or Git
Bash / WSL on Windows.

```text
 LiDAR teacher (TD3)  --records-->  replay buffer  --distils-->  student (LiDAR + camera)
 train_velodyne_td3.py                (250k steps)                train_student.py
                                                                  handover test: test_handover.py
```

## 0. What you need

- Docker (Docker Desktop on Windows/macOS) and about 25 GB of free disk
- 8 GB RAM for the simulation, 16 GB for student training
- Optional: an NVIDIA GPU with the NVIDIA Container Toolkit; add `--gpus all`
  to any `docker run` below. Everything also runs on CPU.

## 1. Get the code and build the image

```bash
git clone https://github.com/am-amani/lidar-to-vision-distillation-nav.git
cd lidar-to-vision-distillation-nav
docker build -t drl-nav:pioneer .
```

The first build downloads ROS Noetic and Gazebo 11 and takes 10-20 minutes.
For the TurtleBot3 Waffle, check out the other branch in a second folder and
tag the image `drl-nav:waffle`:

```bash
git clone -b turtlebot3-waffle https://github.com/am-amani/lidar-to-vision-distillation-nav.git waffle
cd waffle && docker build -t drl-nav:waffle .
```

Check the image:

```bash
docker run --rm drl-nav:pioneer scripts/docker_verify.sh
```

Every line should say `PASS`.

## 2. Download the pretrained models and replay buffers

Download the files from the data record linked in [ARTIFACTS.md](ARTIFACTS.md)
into a `data/` folder next to the repository and unpack them as shown there.
Then set two shell variables used in the rest of this tutorial:

```bash
DATA="$PWD/../data"           # the folder with teacher/, student/, replay_buffers/
OUT="$PWD/../output"          # where your own runs are written
mkdir -p "$OUT"
```

On Windows Git Bash, put `MSYS_NO_PATHCONV=1` in front of each `docker run`
so the `-v` paths are not rewritten.

Verify the downloaded models load and run a two-minute simulation:

```bash
docker run --rm \
  -v "$DATA/teacher/pioneer:/workspace/TD3/pytorch_models:ro" \
  -v "$DATA:/artifacts:ro" \
  drl-nav:pioneer scripts/docker_verify.sh
```

## 3. Evaluate the pretrained LiDAR teacher

```bash
docker run --rm \
  -v "$DATA/teacher/pioneer:/workspace/TD3/pytorch_models:ro" \
  drl-nav:pioneer bash -c "cd TD3 && python3 test_velodyne_td3.py"
```

The robot drives to random goals in the Gazebo world; each episode prints
`Target reached` or `Target not reached`. Stop with `Ctrl+C`. For the Waffle,
use `drl-nav:waffle` and `$DATA/teacher/turtlebot3-waffle`.

## 4. Test the LiDAR-to-camera handover of a pretrained student

The student starts each episode with LiDAR and switches to the camera after
15 steps. Epoch 4300 is the best recovered checkpoint:

```bash
docker run --rm \
  -v "$DATA/student/checkpoint-sweep:/checkpoints:ro" \
  -v "$OUT/logs:/workspace/TD3/logs" \
  -e DISTILLATION_CHECKPOINT_DIR=/checkpoints \
  -e DISTILLATION_CHECKPOINT_EPOCH=4300 \
  -e HANDOVER_EPISODES=20 \
  drl-nav:pioneer bash -c "cd TD3 && python3 test_handover.py"
```

The success rate is printed at the end and saved as a log in `$OUT/logs`.

## 5. Train your own LiDAR teacher

```bash
docker run --rm \
  -v "$OUT/teacher:/workspace/TD3/pytorch_models" \
  -v "$OUT/runs:/workspace/TD3/runs" \
  drl-nav:pioneer bash -c "cd TD3 && python3 train_velodyne_td3.py"
```

Weights are saved to `$OUT/teacher` during training. Follow progress with
`tensorboard --logdir "$OUT/runs"` on the host. A useful teacher needs many
hours; the script runs until you stop it.

## 6. Train a student from the replay buffers

Student training does not start Gazebo. It learns from the recorded Pioneer
and Waffle teacher buffers:

```bash
docker run --rm \
  -v "$DATA/replay_buffers:/buffers:ro" \
  -v "$OUT/student_runs:/workspace/TD3/runs" \
  -e REPLAY_BUFFER_DIR=/buffers \
  -e DISTILLATION_EPOCHS=50 \
  drl-nav:pioneer bash -c "cd TD3 && python3 train_student.py"
```

`DISTILLATION_EPOCHS=50` is a quick run; the paper models used several
thousand epochs (default 10000). Checkpoints are written every 10 epochs to
`$OUT/student_runs/new_runs/<experiment>/`.

Test your student with step 4, pointing `/checkpoints` at that experiment
folder and `DISTILLATION_CHECKPOINT_EPOCH` at one of its saved epochs.

## Where to go next

- [DOCKER.md](DOCKER.md): all Docker options and known limitations
- [EXPERIMENTS.md](EXPERIMENTS.md): what the scripts do and their settings
- [INSTALLATION.md](INSTALLATION.md): native Ubuntu 20.04 installation
- [SCRIPTS.md](SCRIPTS.md): status of every script in `TD3/`

If you use this code, models or data, please cite the paper (see the README).
