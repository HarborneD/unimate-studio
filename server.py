"""Same-origin static viewer + bounded single-worker inference API."""
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import argparse
import json
import re
import threading
import time
import traceback
import uuid

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'output'
LOCK = threading.RLock()
POOL = ThreadPoolExecutor(max_workers=1)
STATE = {'status': 'loading', 'message': 'Starting inference host', 'engine': None}
JOBS = {}
JOB_ROUTE = re.compile(r'^/api/jobs/([a-f0-9]{32})(?:/(motion\.(?:json|bvh|npy)))?$')


def load_engine():
    try:
        from engine import Engine
        def report(message):
            with LOCK:
                STATE['message'] = message
            print(message, flush=True)
        engine = Engine(report)
        with LOCK:
            STATE.update(status='ready', message='UniMate v2 ready', engine=engine)
    except Exception as exc:
        traceback.print_exc()
        with LOCK:
            STATE.update(status='error', message=str(exc))


def validate_request(body, rigs):
    if not isinstance(body, dict):
        raise ValueError('Expected a JSON object.')
    prompt = body.get('prompt')
    if not isinstance(prompt, str) or not 3 <= len(prompt.strip()) <= 400:
        raise ValueError('Describe a motion using 3 to 400 characters.')
    rig = body.get('rig')
    if not isinstance(rig, str) or rig not in rigs:
        raise ValueError('Choose an available prepared rig.')
    seed = body.get('seed', 42)
    if type(seed) is not int or not 0 <= seed <= 2147483647:
        raise ValueError('Seed must be an integer from 0 to 2147483647.')
    guidance = body.get('guidance', 3)
    if type(guidance) not in (int, float) or not 1.1 <= guidance <= 8:
        raise ValueError('Guidance must be between 1.1 and 8.')
    quality = body.get('quality', 'preview')
    if quality not in ('preview', 'standard'):
        raise ValueError('Unknown quality mode.')
    return dict(prompt=prompt.strip(), rig=rig, seed=seed, guidance=guidance, quality=quality)


def run_job(job_id):
    def report(message, progress):
        with LOCK:
            JOBS[job_id].update(status='running', message=message, progress=progress)
    try:
        report('Preparing generation', 0)
        result = STATE['engine'].generate(JOBS[job_id]['request'], OUTPUT / job_id, report)
        with LOCK:
            JOBS[job_id].update(status='complete', message='Animation ready', progress=1,
                                seconds=result['seconds'], frames=result['frames'])
            (OUTPUT / job_id / 'job.json').write_text(json.dumps(JOBS[job_id]))
    except Exception as exc:
        traceback.print_exc()
        with LOCK:
            JOBS[job_id].update(status='error', message=str(exc), progress=0)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'build' / 'web'), **kwargs)

    def json_response(self, data, status=200):
        encoded = json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        path = urlsplit(self.path).path
        with LOCK:
            if path == '/api/health':
                engine = STATE['engine']
                return self.json_response({
                    'status': STATE['status'], 'message': STATE['message'],
                    'model': 'UniMate v2', 'device': str(engine.device) if engine else None,
                    'rigs': engine.rigs if engine else [], 'build': 'unimate-studio-0.1.0',
                })
            if path == '/api/jobs':
                return self.json_response(list(JOBS.values())[-50:][::-1])
            match = JOB_ROUTE.fullmatch(path)
            if match:
                job_id, filename = match.groups()
                job = JOBS.get(job_id)
                if not job:
                    return self.json_response({'error': 'Take not found.'}, 404)
                if not filename:
                    return self.json_response(job)
                if job['status'] != 'complete':
                    return self.json_response({'error': 'This animation is not ready.'}, 409)
                data = (OUTPUT / job_id / filename).read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json' if filename.endswith('.json') else 'application/octet-stream')
                self.send_header('Content-Length', str(len(data)))
                if not filename.endswith('.json'):
                    self.send_header('Content-Disposition', f'attachment; filename="unimate-{job_id[:8]}.{filename.split(".")[-1]}"')
                self.end_headers()
                self.wfile.write(data)
                return
        if path.startswith('/api/'):
            return self.json_response({'error': 'Route not found.'}, 404)
        super().do_GET()

    def do_POST(self):
        if self.path != '/api/jobs':
            return self.json_response({'error': 'Route not found.'}, 404)
        # Browser submissions are same-origin JSON; no credentials or CORS.
        origin = self.headers.get('Origin')
        if origin and urlsplit(origin).netloc != self.headers.get('Host'):
            return self.json_response({'error': 'Cross-origin submission refused.'}, 403)
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.json_response({'error': 'Send application/json.'}, 415)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 1 <= size <= 4096:
                return self.json_response({'error': 'Request body too large or empty.'}, 413)
            body = json.loads(self.rfile.read(size))
        except (ValueError, json.JSONDecodeError):
            return self.json_response({'error': 'Invalid JSON.'}, 400)
        with LOCK:
            if STATE['status'] != 'ready':
                return self.json_response({'error': STATE['message']}, 503)
            if any(x['status'] in ('queued', 'running') for x in JOBS.values()):
                return self.json_response({'error': 'A generation is running. Please wait for it to finish.'}, 429)
            try:
                request = validate_request(body, {x['id'] for x in STATE['engine'].rigs})
            except ValueError as exc:
                return self.json_response({'error': str(exc)}, 400)
            job_id = uuid.uuid4().hex
            JOBS[job_id] = {'id': job_id, 'status': 'queued', 'message': 'Queued', 'progress': 0,
                            'request': request, 'created_at': time.time()}
            POOL.submit(run_job, job_id)
            return self.json_response(JOBS[job_id], 202)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8170)
    args = parser.parse_args()
    OUTPUT.mkdir(exist_ok=True)
    for path in sorted(OUTPUT.glob('*/job.json'), key=lambda x: x.stat().st_mtime):
        job = json.loads(path.read_text())
        JOBS[job['id']] = job
    POOL.submit(load_engine)
    print(f'UniMate Studio http://127.0.0.1:{args.port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
