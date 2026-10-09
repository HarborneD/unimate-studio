"""Detached host lifecycle, leaving existing processes and tunnels untouched."""
from pathlib import Path
import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
PID = ROOT / '.runtime' / 'server.pid'


def health(port):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=2) as response:
            data = json.load(response)
        if data.get('build') == 'unimate-studio-0.1.0':
            return data
    except (OSError, ValueError):
        pass
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['start', 'stop', 'status'])
    parser.add_argument('--port', type=int, default=8170)
    args = parser.parse_args()
    current = health(args.port)
    if args.command == 'status':
        print(json.dumps(current) if current else 'Not running')
        return
    if args.command == 'start':
        if current:
            print(f'Already running at http://127.0.0.1:{args.port}: {current["status"]}')
            return
        if not (ROOT / 'build/web/index.html').exists():
            raise SystemExit('Run npm run build first.')
        if not (ROOT / '.runtime/config.local.json').exists():
            raise SystemExit('Run bootstrap.py first.')
        PID.parent.mkdir(exist_ok=True)
        kwargs = {'creationflags': 0x00000008 | 0x00000200} if os.name == 'nt' else {'start_new_session': True}
        with open(ROOT / 'server.log', 'a') as log:
            proc = subprocess.Popen([sys.executable, str(ROOT / 'server.py'), '--port', str(args.port)],
                                    cwd=ROOT, stdout=log, stderr=log, stdin=subprocess.DEVNULL, **kwargs)
        time.sleep(.5)
        if proc.poll() is not None:
            raise SystemExit('Host failed to start; inspect server.log. The port may be occupied.')
        PID.write_text(str(proc.pid))
        print(f'Started host PID {proc.pid}: http://127.0.0.1:{args.port}')
    else:
        if not current or not PID.exists():
            raise SystemExit('No managed host is running on this port.')
        pid = int(PID.read_text())
        # Validate the recorded PID rather than killing whatever owns a port.
        if os.name != 'nt':
            command = subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True)
            if str(ROOT / 'server.py') not in command:
                raise SystemExit('Recorded PID belongs to a different process; leaving it untouched.')
            os.kill(pid, signal.SIGTERM)
        else:
            # Windows hosts started by this script always carry the full path.
            check = subprocess.run(['powershell','-NoProfile','-Command',
                                    f'(Get-CimInstance Win32_Process -Filter "ProcessId={pid}").CommandLine'],
                                   capture_output=True,text=True,check=True).stdout
            if str(ROOT / 'server.py') not in check:
                raise SystemExit('Recorded PID does not match this host; leaving it untouched.')
            subprocess.run(['taskkill','/PID',str(pid),'/F'],check=True)
        PID.unlink()
        print('Stopped this UniMate Studio host.')


if __name__ == '__main__':
    main()
