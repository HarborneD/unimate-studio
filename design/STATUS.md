# UniMate Studio — prototype status

Delivered 2026-09-30 as an MIT-licensed animation production tool.

- Source: https://github.com/HarborneD/unimate-studio
- Temporary live preview: https://linking-perspectives-cir-lyric.trycloudflare.com
- Local inference host: http://127.0.0.1:8153

The preview uses a detached Python host and Cloudflare quick tunnel on the Mac.
It depends on the Mac remaining awake. It does not update or join the permanent
Windows demo tunnel. The Python API is required alongside the frontend.

## Verification

The released UniMate v2 EMA checkpoint and FLAN-T5 generated six real takes on
Apple M5 Max / MPS: humanoid walking twice, waving and jumping, quadruped walking,
and bird wing flapping. Preview jobs took 3.84–4.34 seconds after warmup; the first
job took 10.76 seconds. The adaptive bird job took 22.60 seconds. These are observed
local timings, not a guarantee on other hardware or prompts.

All six passed finite `(60, J, 12)` feature output, FK bone-length constancy and
BVH reimport position checks. The repeated walking request produced identical
features for the same seed. Four request-validation tests passed, including
bounded inputs and invalid skeleton identifiers. TypeScript checking and the
production build passed. Package audit reported no vulnerabilities at setup.

Browser checks ran against the real public URL. Generation completed through
the UI; saved takes, pause, single-frame keyboard scrubbing, speed selection,
BVH download and the credits dialog worked. Desktop, 844×390 landscape and
390×844 portrait were visually inspected; phone widths had no horizontal
overflow. The public screenshot is in `docs/preview.png`; its console log had
no messages. Public frontend asset hashes matched the local production build.

Motion remains experimental, particularly on the original unseen bird and
quadruped rigs. Sliding, twisting or imperfect prompt adherence are model-output
limitations. The viewer and exports show the actual generated motion.

## Workspace handover

Port 8153 is registered in the parent workspace. An unrelated service already
used 8152 and was left running. Source assets, checkpoints, runtime environments
and generated takes are excluded from the public repository.

ClickUp hub-list creation was attempted but refused with `HLIMIT_005`: the
workspace has reached its plan list limit. No unrelated list was changed or
deleted. The demo and source links are recorded here and in the README.
