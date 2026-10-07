# Pretrained models and results

Model weights are too large for Git. They are attached to the GitHub release
[`models-v1.0`](https://github.com/am-amani/lidar-to-vision-distillation-nav/releases/tag/models-v1.0).

## Contents

| File | Size | Contents |
|---|---|---|
| `models.tar.gz` | ~320 MB | teachers, student checkpoints, result arrays |
| `SHA256SUMS` | | checksum of `models.tar.gz` |

`models.tar.gz` extracts to:

```text
teacher/pioneer/TD3_velodyne_{actor,critic}.pth
teacher/turtlebot3-waffle/TD3_velodyne_{actor,critic}.pth
student/checkpoint-sweep/epoch N.dat{camera,scan,encoder,actor}_model
    N = 445, 990, 1310, 1680, 1750, 2525, 2880, 4300, 4770
student/joint-robot-id-epoch470/epoch 470.dat{camera,scan,encoder,actor}_model
results/{pioneer,turtlebot3-waffle}/TD3_velodyne.npy
```

A student checkpoint is always the four files with the same epoch prefix.

## Suggested layout

The tutorial and the Docker commands assume the files sit in a `data/` folder
next to the repository checkout:

```bash
mkdir data && cd data
curl -LO https://github.com/am-amani/lidar-to-vision-distillation-nav/releases/download/models-v1.0/models.tar.gz
curl -LO https://github.com/am-amani/lidar-to-vision-distillation-nav/releases/download/models-v1.0/SHA256SUMS
sha256sum -c SHA256SUMS
tar -xzf models.tar.gz
```

```text
data/
  teacher/  student/  results/
```

The files are PyTorch pickles: check the checksum before loading them.

## What each file is used for

- **Teachers**: `TD3/test_velodyne_td3.py` loads `TD3_velodyne_actor.pth` from
  `TD3/pytorch_models`. Each robot branch uses its own teacher.
- **Student checkpoints**: the handover evaluation reads them from
  `DISTILLATION_CHECKPOINT_DIR` and picks the epoch with
  `DISTILLATION_CHECKPOINT_EPOCH`.

## Replay buffers

The teacher replay buffers (about 5.5 GB for the Pioneer and Waffle buffers)
are not distributed with this repository. `TD3/train_student.py` reads both
buffers from `REPLAY_BUFFER_DIR` (default `TD3/pytorch_models`), so student
training cannot be rerun from this release alone. Each transition holds the
24-value robot state, the teacher action, reward, done flag, next state, the
camera image and the LiDAR scan, stored as a pickled
`replay_buffer.ReplayBuffer`. Contact the authors if you need them.

## Known limitations

- Epoch 4770 uses an older architecture (student actor input 61 instead of 42)
  and cannot be loaded by the current `distillation_CNNs.py`. It is kept for
  provenance.
- Older experiment scripts reference further buffers and checkpoint families
  that were not recovered; those scripts are not part of this release.
