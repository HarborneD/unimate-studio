"""Small, genuine UniMate inference adapter. No procedural motion fallback."""
from pathlib import Path
import json
import os
import sys
import time

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / '.runtime'
sys.path.insert(0, str(RUNTIME / 'UniMate'))


class Engine:
    def __init__(self, report):
        import torch
        from unimate.configs.schema import MainConfig
        from unimate.dataset.factory import create_dataset
        from unimate.models.factory import create_model
        from unimate.inference.sample import _build_diffusion, _load_checkpoint, _make_text_encoder

        self.torch = torch
        torch.set_num_threads(min(8, os.cpu_count() or 4))
        device_name = os.environ.get('UNIMATE_DEVICE') or (
            'cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu')
        self.device = torch.device(device_name)
        self.config = MainConfig.from_json(str(RUNTIME / 'config.local.json'))
        report('Preparing skeleton conditioning')
        self.dataset = create_dataset(self.config.dataset, self.config.model, inference=True,
                                      stats_path=str(RUNTIME / 'model' / 'dataset_stats.npy'))
        report('Loading UniMate v2 EMA weights')
        self.model = create_model(self.config.dataset, self.config.model)
        _load_checkpoint(self.model, str(RUNTIME / 'model' / 'checkpoints' / 'checkpoint_step_100000.pt'), self.config)
        self.model.to(self.device).eval()
        self.diffusion, self.sampler = _build_diffusion(self.config)
        report('Loading text encoder')
        self.encoder = _make_text_encoder(self.config, self.device).eval()
        self.rigs = []
        md = self.dataset.motion_dataset
        for key, cond in md.cond_dict.items():
            if not (md.train_object_motions_map.get(key) or md.eval_object_motions_map.get(key)):
                continue
            self.rigs.append({
                'id': key, 'name': {'mixamo': 'Humanoid', 'quadruped': 'Quadruped', 'avian': 'Bird'}.get(key, key),
                'joints': len(cond['parents']), 'parents': list(map(int, cond['parents'])),
                'rest': cond['tpos_first_frame'].tolist(),
                'description': '22-joint Mixamo core' if key == 'mixamo' else 'Original demonstration rig',
            })
        if not self.rigs:
            raise RuntimeError('No prepared rigs. Run bootstrap.py first.')

    def generate(self, request, out_dir, report):
        import numpy as np
        import BVH
        from unimate.dataset.conditioning import create_sample_condition
        from unimate.inference.sample import _encode_prompt
        from unimate.inference.generate import ClassifierFreeSampleModel
        from unimate.utils.motion_utils import recover_unimate_anim_from_rot
        from Animation import positions_global

        torch = self.torch
        started = time.monotonic()
        torch.manual_seed(request['seed'])
        if self.device.type == 'mps':
            torch.mps.manual_seed(request['seed'])
        report('Encoding your prompt', 0.05)
        with torch.no_grad():
            encoded = _encode_prompt(self.encoder, request['prompt'])
            _, cond = create_sample_condition(self.config, self.dataset,
                                              test_case_captions=[(request['rig'], request['prompt'], encoded)],
                                              gt_start_frame=0)
            cond = {k: v.to(self.device) if torch.is_tensor(v) else v for k, v in cond.items()}
            shape = (1, self.config.dataset.max_joints, 12, 60)
            # Noise on CPU gives stable initial noise on every supported device.
            noise = torch.randn(shape, device='cpu').to(self.device)
            guided = ClassifierFreeSampleModel(self.model, cfg_scale=request['guidance'])
            calls = 0

            def model_fn(x, t, **kw):
                nonlocal calls
                calls += 1
                report('Generating motion', min(0.9, 0.1 + 0.8 * float(t[0].item())))
                return guided(x, t, **kw)

            method = 'euler' if request['quality'] == 'preview' else 'dopri5'
            if method == 'dopri5' and self.device.type == 'mps':
                # torchdiffeq defaults adaptive time arithmetic to float64,
                # unsupported by Apple MPS. Keep the upstream drift, interval,
                # tolerances and solver, with supported float32 time arithmetic.
                from torchdiffeq import odeint
                transport = self.sampler.transport
                t0, t1 = transport.check_interval(transport.train_eps, transport.sample_eps,
                                                  sde=False, eval=True, reverse=False, last_step_size=0.0)
                times = torch.linspace(t0, t1, 50, device=self.device)
                def drift(t, x):
                    return self.sampler.drift(x, t.expand(x.shape[0]), model_fn, cond=cond)
                samples = odeint(drift, noise, times, method='dopri5', atol=1e-6, rtol=1e-3,
                                 options={'dtype': torch.float32})[-1]
            else:
                sampler_fn = self.sampler.sample_ode(sampling_method=method, num_steps=31 if method == 'euler' else 50)
                samples = sampler_fn(noise, model_fn, cond=cond)[-1]
            n = int(cond['n_joints'][0].item())
            motion = samples[0, :n].cpu().permute(2, 0, 1).numpy().copy()
            mean = cond['mean'][0, :n].cpu().numpy()
            std = cond['std'][0, :n].cpu().numpy()
            motion = motion * std[None] + mean[None]
            parents = np.asarray(cond['parents'][0][:n], dtype=int)
            offsets = cond['offsets'][0, :n].cpu().numpy()
            anim = recover_unimate_anim_from_rot(motion, parents, offsets)
            positions = positions_global(anim)
        if not np.isfinite(motion).all() or not np.isfinite(positions).all():
            raise RuntimeError('The model produced non-finite motion. Try another seed or quality mode.')
        report('Exporting animation', 0.95)
        out_dir.mkdir(parents=True, exist_ok=True)
        md_cond = self.dataset.motion_dataset.cond_dict[request['rig']]
        names = md_cond.get('joint_names', md_cond.get('names'))
        if names is None:
            names = ['joint_' + str(i) for i in range(n)]
        names = [str(x).replace(' ', '_').replace(':', '_') for x in names]
        np.save(out_dir / 'motion.npy', motion)
        # BVH writes channels in depth-first hierarchy order. Upstream Motion's
        # writer iterates original indices, so first reorder its BFS skeleton.
        children = [[j for j, p in enumerate(parents) if p == i and j != i] for i in range(n)]
        order = []

        def visit(i):
            order.append(i)
            for child in children[i]:
                visit(child)
        visit(0)
        from Animation import Animation
        from Quaternions import Quaternions
        inverse = {old: new for new, old in enumerate(order)}
        reordered = Animation(anim.rotations[:, order], anim.positions[:, order],
                              Quaternions.id(n), offsets[order],
                              np.array([-1 if parents[i] < 0 else inverse[int(parents[i])] for i in order]))
        BVH.save(str(out_dir / 'motion.bvh'), reordered, [names[i] for i in order], frametime=1 / 30)
        result = {
            'schema': 'unimate-studio.motion.v1', 'fps': 30, 'frames': 60,
            'parents': parents.tolist(), 'joint_names': names, 'offsets': offsets.tolist(),
            'positions': np.round(positions, 6).tolist(),
            'rotations': np.round(anim.rotations.qs, 7).tolist(),
            'request': request, 'seconds': round(time.monotonic() - started, 2),
            'provenance': {'model': 'Linzhan/UniMate/unimate_uniml3d_f60_v2',
                           'checkpoint_step': 100000, 'weights': 'EMA', 'device': str(self.device),
                           'solver': method, 'model_evaluations': calls,
                           'adaptive_time_dtype': 'float32' if self.device.type == 'mps' else 'float64',
                           'upstream_revision': '5d6aabedd947297b5ba6706d8e9113e68c0c3e4f'},
        }
        (out_dir / 'motion.json').write_text(json.dumps(result, allow_nan=False))
        return result
