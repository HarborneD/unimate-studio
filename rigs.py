"""Original primitive skeletons, MIT. Builds conditioning, not generated takes.

UniMate's feature pipeline requires a reference clip as well as a rest pose.
These rigs have a small head-hinge calibration clip solely to prepare
topology and text conditioning. All viewer takes are sampled by UniMate.
"""
from pathlib import Path
import json
import numpy as np


def build_rigs(destination: Path):
    skeletons = {
        'quadruped': [
            ('Hips', -1, (0,.7,-.4)), ('Spine',0,(0,.74,0)),
            ('Chest',1,(0,.77,.4)), ('Neck',2,(0,.88,.6)),
            ('Head',3,(0,1.0,.8)), ('Nose',4,(0,.94,1.0)),
            ('Left Ear',4,(-.11,1.14,.72)), ('Right Ear',4,(.11,1.14,.72)),
            ('Tail',0,(0,.8,-.7)), ('Tail End',8,(0,.92,-1.0)),
            ('Left Thigh',0,(-.21,.61,-.4)), ('Left Shin',10,(-.21,.35,-.27)),
            ('Left Foot',11,(-.21,.06,-.4)), ('Left Toe',12,(-.21,.06,-.23)),
            ('Right Thigh',0,(.21,.61,-.4)), ('Right Shin',14,(.21,.35,-.27)),
            ('Right Foot',15,(.21,.06,-.4)), ('Right Toe',16,(.21,.06,-.23)),
            ('Left Shoulder',2,(-.21,.68,.4)), ('Left Forearm',18,(-.21,.34,.4)),
            ('Left Hand',19,(-.21,.06,.4)), ('Left Finger',20,(-.21,.06,.57)),
            ('Right Shoulder',2,(.21,.68,.4)), ('Right Forearm',22,(.21,.34,.4)),
            ('Right Hand',23,(.21,.06,.4)), ('Right Finger',24,(.21,.06,.57)),
        ],
        'avian': [
            ('Hips',-1,(0,.6,0)), ('Spine',0,(0,.78,.08)),
            ('Chest',1,(0,.91,.13)), ('Neck',2,(0,1.11,.2)),
            ('Head',3,(0,1.29,.26)), ('Beak',4,(0,1.25,.48)),
            ('Tail',0,(0,.64,-.28)), ('Tail End',6,(0,.62,-.56)),
            ('Left Shoulder',2,(-.12,.91,.1)), ('Left Upper Arm',8,(-.36,.91,.1)),
            ('Left Forearm',9,(-.66,.91,.14)), ('Left Hand',10,(-.92,.91,.17)),
            ('Left Wing Tip',11,(-1.14,.91,.2)),
            ('Right Shoulder',2,(.12,.91,.1)), ('Right Upper Arm',13,(.36,.91,.1)),
            ('Right Forearm',14,(.66,.91,.14)), ('Right Hand',15,(.92,.91,.17)),
            ('Right Wing Tip',16,(1.14,.91,.2)),
            ('Left Thigh',0,(-.1,.45,0)), ('Left Shin',18,(-.1,.22,-.07)),
            ('Left Foot',19,(-.1,.04,.01)), ('Left Toe',20,(-.1,.04,.2)),
            ('Right Thigh',0,(.1,.45,0)), ('Right Shin',22,(.1,.22,-.07)),
            ('Right Foot',23,(.1,.04,.01)), ('Right Toe',24,(.1,.04,.2)),
        ],
    }
    metadata = {name: {} for name in ['joint_names', 'clean_joint_names', 'face_joint_names', 'motion_captions']}
    (destination / 'motions').mkdir(parents=True, exist_ok=True)
    for key, rows in skeletons.items():
        names = [r[0] for r in rows]
        parents = np.array([r[1] for r in rows], dtype=np.int32)
        world = np.array([r[2] for r in rows], dtype=np.float64)
        # UniMate's facing convention: Y-up cross (right hip - left hip)
        # points along +Z. Character-left therefore lies on positive X.
        world[:, 0] *= -1
        offsets = world.copy()
        for j, p in enumerate(parents):
            if p >= 0:
                offsets[j] -= world[p]
        rot = np.zeros((len(rows), 4)); rot[:, 0] = 1
        pos = np.repeat(offsets[None], 90, axis=0)
        pos[:, 0, 2] += np.linspace(0, 1, 90)
        rotations = np.repeat(rot[None], 90, axis=0)
        angle = .08 * np.sin(np.linspace(0, 4 * np.pi, 90))
        rotations[:, 4, 0] = np.cos(angle / 2)
        rotations[:, 4, 2] = np.sin(angle / 2)
        np.savez(destination / 'motions' / f'{key}-calibration.npz',
                 rest_local_pos=offsets, rest_local_rot=rot,
                 anim_local_pos=pos, anim_local_rot=rotations,
                 offsets=offsets, names=np.array(names), parents=parents, fps=30)
        metadata['joint_names'][key] = names
        metadata['clean_joint_names'][key] = names
        metadata['face_joint_names'][key] = {
            'r_hip': {'raw': 'Right Thigh', 'clean': 'Right Thigh'},
            'l_hip': {'raw': 'Left Thigh', 'clean': 'Left Thigh'},
        }
        metadata['motion_captions'][f'{key}-calibration'] = 'An object moves forward.'
    for name, content in metadata.items():
        (destination / f'{name}.json').write_text(json.dumps(content))
