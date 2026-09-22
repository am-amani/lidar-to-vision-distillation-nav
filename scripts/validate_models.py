#!/usr/bin/env python3
"""Validate recovered model files without launching ROS or Gazebo."""

import argparse
import sys
from pathlib import Path

import torch


REQUIRED_SUFFIXES = (
    "camera_model",
    "scan_model",
    "encoder_model",
    "actor_model",
)


def load_state(path):
    state = torch.load(path, map_location="cpu")
    if not isinstance(state, dict):
        raise TypeError(f"{path} does not contain a state dictionary")
    return state


def validate_teacher(directory):
    actor = load_state(directory / "TD3_velodyne_actor.pth")
    critic = load_state(directory / "TD3_velodyne_critic.pth")
    if tuple(actor["layer_3.weight"].shape) != (2, 600):
        raise ValueError(f"Unexpected teacher actor output in {directory}")
    if "layer_6.weight" not in critic:
        raise ValueError(f"Second TD3 critic is missing in {directory}")
    print(f"PASS teacher {directory}")


def validate_student_set(td3_dir, prefix):
    sys.path.insert(0, str(td3_dir))
    from distillation_CNNs import (  # pylint: disable=import-outside-toplevel
        Actor_model,
        CNN_FeatureExtractor_Camera,
        CNN_FeatureExtractor_Scan,
        Encoder,
    )

    paths = {suffix: Path(str(prefix) + suffix) for suffix in REQUIRED_SUFFIXES}
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)

    actor_state = load_state(paths["actor_model"])
    actor_inputs = actor_state["actor.0.weight"].shape[1]
    if actor_inputs == 61:
        # Epoch 4770 belongs to an unrecovered historical architecture. Its
        # files are readable but cannot be shape-validated against this source.
        for path in paths.values():
            load_state(path)
        print(f"PASS readable legacy student {prefix} (61-input architecture)")
        return
    if actor_inputs != 42:
        raise ValueError(f"Unexpected student actor input {actor_inputs}: {prefix}")

    camera = CNN_FeatureExtractor_Camera()
    scan = CNN_FeatureExtractor_Scan()
    encoder = Encoder(5)
    actor = Actor_model(42, 2)
    camera.load_state_dict(load_state(paths["camera_model"]))
    scan.load_state_dict(load_state(paths["scan_model"]))
    encoder.load_state_dict(load_state(paths["encoder_model"]))
    actor.load_state_dict(actor_state)

    with torch.no_grad():
        camera_features = camera(torch.zeros(1, 1, 32, 64))
        scan_features = scan(torch.zeros(1, 1, 20))
        encoded = encoder(scan_features)
        action = actor(torch.zeros(1, 42))
    assert camera_features.shape == (1, 32)
    assert scan_features.shape == (1, 32)
    assert encoded.shape == (1, 5)
    assert action.shape == (1, 2)
    print(f"PASS compatible student {prefix}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact_root", type=Path)
    parser.add_argument(
        "--td3-dir", type=Path, default=Path(__file__).resolve().parents[1] / "TD3"
    )
    args = parser.parse_args()

    root = args.artifact_root.resolve()
    validate_teacher(root / "teacher" / "pioneer")
    validate_teacher(root / "teacher" / "turtlebot3-waffle")

    sweep = root / "student" / "checkpoint-sweep"
    epochs = sorted(
        {path.name.split(".dat", 1)[0] for path in sweep.glob("epoch *.dat*model")}
    )
    for epoch in epochs:
        validate_student_set(args.td3_dir, sweep / f"{epoch}.dat")
    validate_student_set(
        args.td3_dir, root / "student" / "joint-robot-id-epoch470" / "epoch 470.dat"
    )


if __name__ == "__main__":
    main()

