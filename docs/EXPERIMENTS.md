# Training and evaluation workflows

## LiDAR TD3 teacher

`TD3/train_velodyne_td3.py` trains a TD3 policy from 20 LiDAR sectors and four
robot-state values. Its two actions are linear and angular velocity commands.
The script is configured internally and originally targeted five million
steps. Check its constants before launching a long run.

```bash
cd TD3
python3 train_velodyne_td3.py
```

The companion evaluator is `TD3/test_velodyne_td3.py`.

## Multimodal student

The student contains separate camera and scan feature extractors, a shared
encoder, and an actor. A complete checkpoint is four files with one common
epoch prefix:

```text
epoch N.datcamera_model
epoch N.datscan_model
epoch N.datencoder_model
epoch N.datactor_model
```

`train_student.py` trains one student for both robots. It learns offline
from the Pioneer and Waffle teacher replay buffers (see
[ARTIFACTS.md](ARTIFACTS.md)); Gazebo is not started. Settings:

```bash
export REPLAY_BUFFER_DIR=/path/to/replay_buffers   # default TD3/pytorch_models
export DISTILLATION_EPOCHS=50                      # default 10000
python3 train_student.py
```

Checkpoints are saved every 10 epochs to `TD3/runs/new_runs/<experiment>/` and
can be passed to the handover evaluation below. A CUDA GPU is used if present.

## Handover evaluation

`test_handover.py` reads its checkpoint directory from
`DISTILLATION_CHECKPOINT_DIR`:

```bash
cd TD3
export DISTILLATION_CHECKPOINT_DIR=/absolute/path/to/a/checkpoint-set
python3 test_handover.py
```

The epoch and the number of test episodes are set by environment variables; the
defaults are epoch 445 and 100 episodes:

```bash
export DISTILLATION_CHECKPOINT_EPOCH=4300   # selects "epoch 4300.dat*_model"
export HANDOVER_EPISODES=20
```

Logs are created under `TD3/logs`.

## Long-running processes

Training and evaluation launch ROS/Gazebo child processes. Stop only the
processes belonging to the current experiment. Avoid indiscriminate `killall`
commands on a shared machine.

