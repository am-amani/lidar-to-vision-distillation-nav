import datetime
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
SWITCH_STEP = 15 #either 10 or 15
LIDAR_ROBOT_ID_VALUE = 1.0
VISION_ROBOT_ID_VALUE = 0.0
ROBOT_LABEL = "Pioneer"
CHECKPOINT_EPOCH = int(os.environ.get("DISTILLATION_CHECKPOINT_EPOCH", 445))
RUN_LABEL = f"{ROBOT_LABEL}_handover_step_{SWITCH_STEP}_camNoID_lidarWithID_epoch{CHECKPOINT_EPOCH}"

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
# Use the current TD3 directory by default, since files are named like epoch 445.datcamera_model
DEFAULT_CHECKPOINT_DIR = SCRIPT_DIR
CHECKPOINT_DIR = os.environ.get("DISTILLATION_CHECKPOINT_DIR", DEFAULT_CHECKPOINT_DIR)
CHECKPOINT_PREFIX = f"epoch {CHECKPOINT_EPOCH}.dat"

TIMESTAMP = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(
    LOG_DIR,
    f"{os.path.splitext(os.path.basename(__file__))[0]}_{TIMESTAMP}.log",
)
log_handle = open(LOG_FILE, "a", encoding="utf-8")


def _append_log(message):
    if not log_handle.closed:
        log_handle.write(message + "\n")


def _write_run_header():
    header_lines = [
        "=" * 72,
        "Controlled handover evaluation log",
        f"Timestamp: {TIMESTAMP}",
        f"Script: {os.path.basename(__file__)}",
        f"Run: {RUN_LABEL}",
        f"Seed: {seed}",
        f"Device: {device}",
        f"Checkpoint directory: {CHECKPOINT_DIR}",
        f"Checkpoint epoch: {CHECKPOINT_EPOCH}",
        f"Checkpoint prefix: {CHECKPOINT_PREFIX}",
        f"Episodes: {NUM_TEST_EPISODES}",
        f"Switch step: {SWITCH_STEP}",
        f"LiDAR robot ID: {LIDAR_ROBOT_ID_VALUE}",
        f"Vision robot token: {VISION_ROBOT_ID_VALUE}",
        f"Maximum episode steps: {max_ep}",
        "=" * 72,
    ]
    header_text = "\n".join(header_lines)
    _append_log(header_text)


def _write_summary_report(label, completed_episodes):
    if completed_episodes > 0:
        overall_success_rate = success / completed_episodes
    else:
        overall_success_rate = float("nan")

    if active_at_switch > 0:
        post_handover_success_rate = success_after_switch / active_at_switch
    else:
        post_handover_success_rate = float("nan")

    report_lines = [
        "=" * 72,
        f"{label}",
        f"Completed episodes: {completed_episodes}/{NUM_TEST_EPISODES}",
        f"Success: {success}",
        f"Failure: {failure}",
        f"Overall success rate: {overall_success_rate}",
        f"Episodes active at switch: {active_at_switch}",
        f"Success before switch: {success_before_switch}",
        f"Failure before switch: {failure_before_switch}",
        f"Goals after switch: {success_after_switch}",
        f"Collisions/failures after switch: {collision_after_switch}",
        f"Timeouts after switch: {timeout_after_switch}",
        f"Post-handover success rate: {post_handover_success_rate}",
        f"Episode duration min/max: {np.min(episode_durations) if episode_durations else 'n/a'} / {np.max(episode_durations) if episode_durations else 'n/a'}",
        "=" * 72,
    ]
    report_text = "\n".join(report_lines)
    print(report_text)
    _append_log(report_text)


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

print("=" * 72)
print("Controlled handover evaluation")
print("Run:", RUN_LABEL)
print("Episodes:", NUM_TEST_EPISODES)
print("Switch step:", SWITCH_STEP)
print("LiDAR robot ID:", LIDAR_ROBOT_ID_VALUE)
print("Vision robot token:", VISION_ROBOT_ID_VALUE)
print("Checkpoint directory:", CHECKPOINT_DIR)
print("Checkpoint epoch:", CHECKPOINT_EPOCH)
print("Device:", device)
print("Maximum episode steps:", max_ep)
print("=" * 72)

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
                print(
                    f"Episode {episode_index + 1}: externally switching "
                    f"LiDAR -> vision at step {SWITCH_STEP}"
                )

            if switched_to_vision:
                print("Vision")
                action = _student_action_from_vision(state)
            else:
                print("LiDAR")
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
                    print("Target reached")
                else:
                    failure += 1
                    if was_active_at_switch:
                        if env_done:
                            collision_after_switch += 1
                            print("Collision/failure after handover")
                        else:
                            timeout_after_switch += 1
                            print("Timeout after handover")
                    else:
                        failure_before_switch += 1
                        print("Target not reached before handover")

                if (episode_index + 1) % 100 == 0 or (episode_index + 1) == NUM_TEST_EPISODES:
                    _write_summary_report("Progress report", episode_index + 1)
                break

            state = next_state


if active_at_switch > 0:
    post_handover_success_rate = success_after_switch / active_at_switch
else:
    post_handover_success_rate = float("nan")

print("=" * 72)
print("Overall results")
print("Success:", success)
print("Failure:", failure)
print("Overall success rate:", success / NUM_TEST_EPISODES)
print("Episode durations:", episode_durations)
print("Average episode duration:", np.mean(episode_durations))
print("Episode duration min and max:", np.min(episode_durations), np.max(episode_durations))
print("=" * 72)
print("Handover-specific results")
print("Switch step:", SWITCH_STEP)
print("Episodes active at switch:", active_at_switch)
print("Success before switch:", success_before_switch)
print("Failure before switch:", failure_before_switch)
print("Goals after switch:", success_after_switch)
print("Collisions/failures after switch:", collision_after_switch)
print("Timeouts after switch:", timeout_after_switch)
print("Post-handover success rate:", post_handover_success_rate)
print("=" * 72)

_write_summary_report("Final report", NUM_TEST_EPISODES)
log_handle.flush()
log_handle.close()