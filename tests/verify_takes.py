"""Integration verification of actual model outputs and independent BVH reload."""
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.runtime' / 'UniMate'))
import BVH
from Animation import positions_global

paths = list((ROOT / 'output').glob('*/motion.json'))
assert paths, 'Generate a take before running the integration checks.'
seen = {}
for path in paths:
    data = json.loads(path.read_text())
    positions = np.array(data['positions'])
    features = np.load(path.with_name('motion.npy'))
    parents = data['parents']
    assert features.shape == (60, len(parents), 12)
    assert positions.shape == (60, len(parents), 3)
    assert np.isfinite(features).all() and np.isfinite(positions).all()
    for j, p in enumerate(parents):
        if p >= 0:
            length = np.linalg.norm(positions[:,j]-positions[:,p],axis=-1)
            assert np.ptp(length) < 5e-6, (path.name, j, np.ptp(length))
    loaded, names, dt = BVH.load(str(path.with_name('motion.bvh')))
    assert loaded.shape[0] == 60 and abs(dt - 1/30) < 1e-6
    # The serializer walks depth-first, while JSON retains the BFS model order.
    order = []
    def visit(i):
        order.append(i)
        for j,p in enumerate(parents):
            if p==i and j!=i:
                visit(j)
    visit(0)
    assert np.max(np.abs(positions_global(loaded)-positions[:,order])) < 1e-4
    request_key = json.dumps(data['request'],sort_keys=True)
    if request_key in seen:
        assert np.max(np.abs(seen[request_key]-features)) < 1e-5, 'Fixed-seed output changed.'
    seen[request_key] = features
    assert data['provenance']['checkpoint_step']==100000
    print('PASS', path.parent.name, data['request']['rig'], data['request']['prompt'],
          data['seconds'], 'seconds', data['provenance']['device'])
print(f'Verified {len(paths)} real generated takes.')
