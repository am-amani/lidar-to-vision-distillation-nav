import os
import time

import numpy as np
import torch
from PIL import Image
from torchvision.transforms import Compose, Normalize, Resize, ToTensor

from distillation_CNNs import (
    Actor_model,
    CNN_FeatureExtractor_Camera,
    CNN_FeatureExtractor_Scan,
    Encoder,
)
from velodyne_env import GazeboEnv


# -----------------------------------------------------------------------------
# Controlled LiDAR-to-vision handover evaluation for the latest student model.
#
# Training confirmation from train_student.py:
# - camera/vision actor input used a zero token instead of the robot ID
# - LiDAR/scan actor input used the real robot ID
#
# This script keeps the same evaluation logic as the old handover script, but
# matches that new input contract.
# -----------------------------------------------------------------------------

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
seed = 3407
max_ep = 1500

environment_dim = 20
robot_dim = 4
state_dim = environment_dim + robot_dim
action_dim = 2

OUTPUT_DIM = 5
ACTOR_INPUT_DIM = 4 + OUTPUT_DIM + 32 + 1

NUM_TEST_EPISODES = int(os.environ.get("HANDOVER_EPISODES", 100))
SWITCH_STEP = 20 # either 20 or 30
LIDAR_ROBOT_ID_VALUE = 2.0
VISION_ROBOT_ID_VALUE = 0.0
ROBOT_LABEL = "Waffle"
CHECKPOINT_EPOCH = int(os.environ.get("DISTILLATION_CHECKPOINT_EPOCH", 445))
RUN_LABEL = f"{ROBOT_LABEL}_handover_step_{SWITCH_STEP}_camNoID_lidarWithID_epoch{CHECKPOINT_EPOCH}"

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
# Use the current TD3 directory by default, since files are named like epoch 445datcamera_model
DEFAULT_CHECKPOINT_DIR = SCRIPT_DIR
CHECKPOINT_DIR = os.environ.get("DISTILLATION_CHECKPOINT_DIR", DEFAULT_CHECKPOINT_DIR)
CHECKPOINT_PREFIX = f"epoch {CHECKPOINT_EPOCH}.dat"
LOG_FILE = os.path.join(SCRIPT_DIR, "handover_evaluation_runs.txt")


def _checkpoint_path(suffix):
    return os.path.join(CHECKPOINT_DIR, CHECKPOINT_PREFIX + suffix)


def _load_student_models():
    model_camera = CNN_FeatureExtractor_Camera().to(device)
    model_scan = CNN_FeatureExtractor_Scan().to(device)
    model_encoder = Encoder(OUTPUT_DIM).to(device)
    model_actor = Actor_model(ACTOR_INPUT_DIM, action_dim).to(device)

    model_camera.load_model(_checkpoint_path("camera_model"), map_location=device)
    model_scan.load_model(_checkpoint_path("scan_model"), map_location=device)
    model_encoder.load_model(_checkpoint_path("encoder_model"), map_location=device)
    model_actor.load_model(_checkpoint_path("actor_model"), map_location=device)

    model_camera.eval()
    model_scan.eval()
    model_encoder.eval()
    model_actor.eval()

    return model_camera, model_scan, model_encoder, model_actor


def _robot_state_tensor(current_state):
    state_tensor = torch.as_tensor(
        current_state, dtype=torch.float32, device=device
    ).reshape(1, -1)
    return state_tensor[:, 20:24]


def _action_to_env(action):
    return [(float(action[0]) + 1.0) / 2.0, float(action[1])]


def _student_action_from_lidar(current_state):
    raw_scan = env.get_scan_data()

    num_sections = 20
    section_length = 360 // num_sections
    min_values_per_scan = [[
        min(raw_scan[i * section_length:(i + 1) * section_length])
        for i in range(num_sections)
    ]]
    scan_tensor = torch.tensor(
        min_values_per_scan, dtype=torch.float32, device=device
    ).view(-1, 1, num_sections)

    features = model_scan(scan_tensor)
    encoded_features = model_encoder(features)
    robot_state = _robot_state_tensor(current_state)
    robot_id = torch.tensor(
        [[LIDAR_ROBOT_ID_VALUE]], dtype=torch.float32, device=device
    )

    actor_input = torch.cat(
        (robot_id, features, encoded_features, robot_state), dim=1
    )
    action = model_actor(actor_input).detach().cpu().numpy()[0]
    return _action_to_env(action)


def _student_action_from_vision(current_state):
    raw_camera = env.get_camera_data()
    camera_tensor = torch.stack([
        transform_camera(Image.fromarray(raw_camera.squeeze().astype(np.uint8)))
    ]).to(device)

    features = model_camera(camera_tensor)
    encoded_features = model_encoder(features)
    robot_state = _robot_state_tensor(current_state)
    camera_robot_token = torch.tensor(
        [[VISION_ROBOT_ID_VALUE]], dtype=torch.float32, device=device
    )

    actor_input = torch.cat(
        (camera_robot_token, features, encoded_features, robot_state), dim=1
    )
    action = model_actor(actor_input).detach().cpu().numpy()[0]
    return _action_to_env(action)


def _log_message(message):
    line = str(message)
    with open(LOG_FILE, "a", encoding="utf-8") as log_handle:
        log_handle.write(line + "\n")


def _print_terminal(message):
    print(message)


def _write_run_header():
    header_lines = [
        "",
        "=" * 72,
        f"RUN TITLE: {RUN_LABEL}",
        f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Script: {os.path.basename(__file__)}",
        f"Seed: {seed}",
        f"Device: {device}",
        f"Checkpoint epoch: {CHECKPOINT_EPOCH}",
        f"Checkpoint directory: {CHECKPOINT_DIR}",
        f"Number of episodes: {NUM_TEST_EPISODES}",
        f"Switch step: {SWITCH_STEP}",
        f"LiDAR robot ID value: {LIDAR_ROBOT_ID_VALUE}",
        f"Vision robot token value: {VISION_ROBOT_ID_VALUE}",
        f"Max episode steps: {max_ep}",
        f"Log file: {LOG_FILE}",
        "=" * 72,
    ]
    with open(LOG_FILE, "a", encoding="utf-8") as log_handle:
        log_handle.write("\n".join(header_lines) + "\n")


def _print_report(label):
    if active_at_switch > 0:
        post_handover_success_rate = success_after_switch / active_at_switch
    else:
        post_handover_success_rate = float("nan")

    if episode_durations:
        average_duration = np.mean(episode_durations)
        min_duration = np.min(episode_durations)
        max_duration = np.max(episode_durations)
    else:
        average_duration = float("nan")
        min_duration = float("nan")
        max_duration = float("nan")

    report_lines = [
        "=" * 72,
        label,
        "Overall results",
        "Success:" + str(success),
        "Failure:" + str(failure),
        "Overall success rate:" + str(success / len(episode_durations) if episode_durations else float("nan")),
        "Episode durations:" + str(episode_durations),
        "Average episode duration:" + str(average_duration),
        "Episode duration min and max:" + str(min_duration) + " " + str(max_duration),
        "=" * 72,
        "Handover-specific results",
        "Switch step:" + str(SWITCH_STEP),
        "Episodes active at switch:" + str(active_at_switch),
        "Success before switch:" + str(success_before_switch),
        "Failure before switch:" + str(failure_before_switch),
        "Goals after switch:" + str(success_after_switch),
        "Collisions/failures after switch:" + str(collision_after_switch),
        "Timeouts after switch:" + str(timeout_after_switch),
        "Post-handover success rate:" + str(post_handover_success_rate),
        "=" * 72,
    ]

    for line in report_lines:
        _log_message(line)
        _print_terminal(line)


torch.manual_seed(seed)
np.random.seed(seed)

env = GazeboEnv("multi_robot_scenario.launch", environment_dim)
time.sleep(5)

transform_camera = Compose([
    Resize((32, 64)),
    ToTensor(),
    Normalize(mean=[0.5], std=[0.5]),
])

model_camera, model_scan, model_encoder, model_actor = _load_student_models()

success = 0
failure = 0
episode_durations = []

active_at_switch = 0
success_after_switch = 0
collision_after_switch = 0
timeout_after_switch = 0

success_before_switch = 0
failure_before_switch = 0

_write_run_header()

with torch.no_grad():
    for episode_index in range(NUM_TEST_EPISODES):
        state = env.reset()
        episode_timesteps = 0
        switched_to_vision = False
        was_active_at_switch = False

        while True:
            if episode_timesteps == SWITCH_STEP:
                switched_to_vision = True
                was_active_at_switch = True
                active_at_switch += 1
                _print_terminal(
                    f"Episode {episode_index + 1}: externally switching "
                    f"LiDAR -> vision at step {SWITCH_STEP}"
                )

            if switched_to_vision:
                _print_terminal("Vision")
                action = _student_action_from_vision(state)
            else:
                _print_terminal("LiDAR")
                action = _student_action_from_lidar(state)

            next_state, reward, env_done, target, x, y = env.step(action)
            episode_timesteps += 1
            reached_time_limit = episode_timesteps >= max_ep
            done = bool(env_done or reached_time_limit)

            if done:
                episode_durations.append(episode_timesteps)

                if target:
                    success += 1
                    if was_active_at_switch:
                        success_after_switch += 1
                    else:
                        success_before_switch += 1
                    _print_terminal("Target reached")
                else:
                    failure += 1
                    if was_active_at_switch:
                        if env_done:
                            collision_after_switch += 1
                            _print_terminal("Collision/failure after handover")
                        else:
                            timeout_after_switch += 1
                            _print_terminal("Timeout after handover")
                    else:
                        failure_before_switch += 1
                        _print_terminal("Target not reached before handover")
                break

            state = next_state

        if (episode_index + 1) % 100 == 0 or episode_index + 1 == NUM_TEST_EPISODES:
            _print_report(f"Progress report after episode {episode_index + 1}")


_print_report("Final report")
