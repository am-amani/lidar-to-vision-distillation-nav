# Python files in `TD3/`

| File | Purpose |
|---|---|
| `train_velodyne_td3.py` | Train the LiDAR TD3 teacher in Gazebo |
| `test_velodyne_td3.py` | Evaluate a trained teacher |
| `velodyne_env.py` | ROS/Gazebo environment (LiDAR, camera, odometry, reward) |
| `replay_buffer.py` | Replay buffer; also the class stored in the published buffers |
| `distillation_CNNs.py` | Student networks: camera and scan feature extractors, encoder, actor |
| `train_student.py` | Distil the student from the Pioneer and Waffle teacher replay buffers |
| `test_handover.py` | Evaluate a student with a LiDAR-to-camera switch during each episode |

Settings are environment variables; see [EXPERIMENTS.md](EXPERIMENTS.md).
