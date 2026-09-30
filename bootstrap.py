"""Fetch a pinned upstream, MIT model, and one locally prepared starter rig.

Source animation data stays in .runtime and is never redistributed by this repo.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / '.runtime'
UPSTREAM = RUNTIME / 'UniMate'
CODE_REV = '5d6aabedd947297b5ba6706d8e9113e68c0c3e4f'
DATA_REV = 'faaa81773b315247b03f183548e3898dbec2ce80'
MODEL = 'unimate_uniml3d_f60_v2'
MODEL_REV = '387a344c3031299bc25fcbef35d36bd186d5afe7'


def fetch(url, path, sha256=None):
    path = Path(path)
    if path.exists() and (not sha256 or hashlib.sha256(path.read_bytes()).hexdigest() == sha256):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    print('Downloading', path.name, flush=True)
    tmp = path.with_suffix(path.suffix + '.part')
    urllib.request.urlretrieve(url, tmp)
    if sha256 and hashlib.sha256(tmp.read_bytes()).hexdigest() != sha256:
        tmp.unlink()
        raise RuntimeError('Checksum mismatch: ' + path.name)
    tmp.replace(path)


def main():
    RUNTIME.mkdir(exist_ok=True)
    if not UPSTREAM.exists():
        subprocess.run(['git', 'clone', 'https://github.com/Friedrich-M/UniMate.git', str(UPSTREAM)], check=True)
        subprocess.run(['git', '-C', str(UPSTREAM), 'checkout', CODE_REV], check=True)
    if subprocess.check_output(['git', '-C', str(UPSTREAM), 'rev-parse', 'HEAD'], text=True).strip() != CODE_REV:
        raise RuntimeError('Unexpected upstream revision; preserve local changes and use the pinned revision.')
    exp = RUNTIME / 'model'
    for name in ['config.json', 'dataset_stats.npy', 'checkpoints/checkpoint_step_100000.pt']:
        # The checkpoint includes optimizer state; use the published SHA-256.
        info = json.load(urllib.request.urlopen(
            f'https://huggingface.co/api/models/Linzhan/UniMate/tree/{MODEL_REV}/{MODEL}/' + ('checkpoints' if '/' in name else '')
        ))
        row = next(x for x in info if x['path'] == f'{MODEL}/{name}')
        fetch(f'https://huggingface.co/Linzhan/UniMate/resolve/{MODEL_REV}/{MODEL}/{name}', exp / name,
              row.get('lfs', {}).get('oid'))
    data = RUNTIME / 'export' / 'mixamo'
    for name in ['motions/Walking.npz', 'joint_names.json',
                 'clean_joint_names.json', 'face_joint_names.json', 'motion_captions.json', 'category_groups.json']:
        fetch(f'https://huggingface.co/datasets/Linzhan/UniML3D/resolve/{DATA_REV}/export/mixamo/{name}', data / name)
    features = RUNTIME / 'features' / 'mixamo'
    if not (features / 'cond.npy').exists():
        subprocess.run([sys.executable, '-m', 'data_process.feature_extraction.extract_features',
                        '--dataset_type', 'mixamo', '--data_dir', str(data),
                        '--save_dir', str(features), '--no-vis'], cwd=UPSTREAM, check=True)
    from rigs import build_rigs
    custom_data = RUNTIME / 'export' / 'studio'
    custom_features = RUNTIME / 'features' / 'studio'
    build_rigs(custom_data)
    for cached in (custom_features / 'cond_parts').glob('*.npy'):
        cached.unlink()  # Rebuild our regenerable original rig conditioning.
    subprocess.run([sys.executable, '-m', 'data_process.feature_extraction.extract_features',
                    '--dataset_type', 'objaverse', '--data_dir', str(custom_data),
                    '--save_dir', str(custom_features), '--no-vis', '--activity_threshold', '0',
                    '--static_threshold', '0'],
                   cwd=UPSTREAM, check=True)
    config = json.loads((exp / 'config.json').read_text())
    config['dataset']['dataset_list'] = ['mixamo', 'objaverse']
    config['mixamo']['path'] = str(features)
    config['objaverse']['path'] = str(custom_features)
    config['sampling']['device'] = 'cpu'
    (RUNTIME / 'config.local.json').write_text(json.dumps(config, indent=2))
    print('Ready. Run .venv/bin/python server.py', flush=True)


if __name__ == '__main__':
    main()
