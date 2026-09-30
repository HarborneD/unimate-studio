# UniMate Studio

User request: create an open-source text-to-animation prototype showcasing UniMate.
Execution mode: auto. This is an animation production tool for the workspace,
so it lives in tools/ and deliberately uses a Python inference service and a
Three.js 3D viewer rather than the Godot game template. A 2D game, gamepad-driven
menus, game audio settings and a gameplay pause screen would obstruct this task.
Keyboard/mouse and touch control the viewer. Playback has explicit pause/scrub.

## Workflow

Choose a prepared rig, describe an action in English, set seed and guidance,
generate actual motion with the released v2 EMA model, inspect/scrub the 60
frames at 30 fps, then download the motion. Save generated takes locally on the
host; show provenance and exact input parameters. No simulated AI or keyword
motion presets. Example prompts fill the editor; they do not select animations.

## Scope

MUST: genuine inference, asynchronous job status and errors, orbitable skeleton
viewer, playback and frame scrubber, reusable machine-readable export, attribution.
SHOULD: multiple skeleton topologies, cached takes, Blender-compatible BVH export.
COULD: mesh retargeting, keyframe in-betweening, joint editing, motion expansion.
These advanced research features are documented upstream, not claimed as shipped.

## Presentation

Warm off-white #f5f3ee, ink #252823, moss #64774d, pale sage #e4eadb,
soft stone #e4e1d9. A quiet animation workbench with a large neutral 3D stage.
Primitive joints/bones visualize actual model output without licensing a mesh.
Asset catalog and available Kenney UI pack inspected: game panel textures do not
fit a text editor/production tool, so semantic HTML/CSS provides its UI.
No generated artwork is required. The neutral grid, joints and bones are data
visualization primitives, not placeholder character art.

## Technical constraints

UniMate code/checkpoints MIT; source data retain their source licenses. Do not
check in source Mixamo/Truebones/Objaverse packs. Downloads and prepared features
are host-local. English prompts should start with "An object" as upstream's
training captions do. The v2 limit is 70 joints, fixed two-second clips.
Model remains on host; browser is a thin viewer and same-origin API client.
Inference selects CUDA, then Apple MPS, then CPU. MPS is verified on this Mac;
CPU and CUDA remain supported code paths, without a timing claim.
Public demo permits one queued generation at a time and bounded input sizes.

## Acceptance

Real generation with two different prompts; finite frames; fixed bone lengths
from FK; reproducibility for fixed prompt/seed; exported BVH reconstructs viewer
positions; graceful malformed input and model failure. Browser visual QA on
desktop and phone, functional generate/play/scrub/reset/export/error tests.
