#!/usr/bin/env python3
"""Quick test: load SO-101 in MuJoCo viewer.

Usage:
  pip install mujoco
  python3 view_so101.py
"""
import os
import mujoco
import mujoco.viewer

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')
SCENE_XML = os.path.join(MODEL_DIR, 'scene.xml')

model = mujoco.MjModel.from_xml_path(SCENE_XML)
data = mujoco.MjData(model)

print(f"Loaded SO-101 MuJoCo model: {model.nq} DOF, {model.nu} actuators")
print(f"Joint names: {[model.joint(i).name for i in range(model.njnt)]}")

mujoco.viewer.launch(model, data)
