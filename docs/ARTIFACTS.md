# Models, replay buffers and results

Model weights and datasets are too large for Git. They are published as a
separate data record:

**Data record:** the download link will be added here as soon as the data
record is online.

## Contents

| File | Size | Contents |
|---|---|---|
| `models.tar.gz` | ~300 MB | teachers, student checkpoints, result arrays |
| `Replay_Buffer_Pioneer_Part1_first250k.pth` | 2.7 GB | Pioneer 3-DX teacher replay buffer, 250,000 transitions |
| `replay_buffer_new_waffel_200_01_Part22_first250k.pth` | 2.8 GB | TurtleBot3 Waffle teacher replay buffer, 250,000 transitions |
| `SHA256SUMS` | | checksums of all files above |

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
# download the four files from the data record into this folder, then:
sha256sum -c SHA256SUMS
tar -xzf models.tar.gz
mkdir replay_buffers && mv *.pth replay_buffers/
```

```text
data/
  teacher/  student/  results/
  replay_buffers/
    Replay_Buffer_Pioneer_Part1_first250k.pth
    replay_buffer_new_waffel_200_01_Part22_first250k.pth
```

## What each file is used for

- **Teachers**: `TD3/test_velodyne_td3.py` loads `TD3_velodyne_actor.pth` from
  `TD3/pytorch_models`. Each robot branch uses its own teacher.
- **Student checkpoints**: the handover evaluation reads them from
  `DISTILLATION_CHECKPOINT_DIR` and picks the epoch with
  `DISTILLATION_CHECKPOINT_EPOCH`.
- **Replay buffers**: `TD3/train_student.py` reads both buffers from
  `REPLAY_BUFFER_DIR` (default `TD3/pytorch_models`). Each transition holds the
  24-value robot state, the teacher action, reward, done flag, next state, the
  camera image and the LiDAR scan. They are pickled `replay_buffer.ReplayBuffer`
  objects, so load them from inside `TD3/` with the pinned `numpy`/`torch`
  versions. Both buffers are held in memory: plan for at least 6 GB of free RAM
  (16 GB recommended).

## Known limitations

- Epoch 4770 uses an older architecture (student actor input 61 instead of 42)
  and cannot be loaded by the current `distillation_CNNs.py`. It is kept for
  provenance.
- Older experiment scripts reference further buffers and checkpoint families
  that were not recovered; those scripts are not part of this release.
