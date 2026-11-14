"""Render review frames for a rigged asset: the rest pose plus N frames from each action.

Run inside Blender after the asset's .blend is open (the build script leaves it open):
    ARMATURE, ASSET, FRAMES_PER_ACTION, TARGET, DISTANCE = 'AstronautRig', 'astronaut', 4, (0, 0, .9), 4.2
    exec(open(r'<repo>/blender/scripts/preview_animations.py').read())
Writes assets/previews/<asset>_<action>_<i>.png and returns the list.
"""
import sys
from pathlib import Path
import bpy

sys.path.insert(0, str(Path(r'C:\dev\godot\new-game-project\blender\scripts')))
import importlib
import sunline_common as C
importlib.reload(C)

arm = bpy.data.objects[ARMATURE]
arm.animation_data_create()
out = []
arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.location = (0, 0, 0)
    pb.rotation_euler = (0, 0, 0)
out.append(str(C.preview(ASSET, target=TARGET, distance=DISTANCE, suffix='_rest', size=(520, 520))))
for act in [a for a in bpy.data.actions if a.use_fake_user]:
    arm.animation_data.action = act
    if hasattr(arm.animation_data, 'action_slot') and act.slots:
        arm.animation_data.action_slot = act.slots[0]
    a, b = act.frame_range
    for i in range(FRAMES_PER_ACTION):
        f = round(a+(b-a)*i/max(1, FRAMES_PER_ACTION-1)) if FRAMES_PER_ACTION > 1 else round(a)
        bpy.context.scene.frame_set(f)
        out.append(str(C.preview(ASSET, target=TARGET, distance=DISTANCE, suffix=f'_{act.name}_{i}', size=(520, 520), frame=f)))
arm.animation_data.action = None
C.remove_preview_rig()
result = {'frames': out}
