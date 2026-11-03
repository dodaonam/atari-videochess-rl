"""Identity and retained command evidence for the improvement campaign."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts/improvement/videochess-improvement-20261103-v1"


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    with temp.open('w') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def read_rows(path):
    with Path(path).open() as f:
        return [json.loads(s) for s in f if s.strip()]


def write_rows(path, rows):
    with Path(path).open('x') as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, separators=(',', ':')) + '\n')


def revision():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()


def usage():
    import resource
    memory={line.split(':')[0]:int(line.split()[1])*1024 for line in open('/proc/meminfo')}
    return dict(peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                available_ram_bytes=memory['MemAvailable'],free_disk_bytes=shutil.disk_usage(ROOT).free)


def run_evidence(name, command):
    """Execute without shell interpolation, retaining output and actual provenance."""
    directory = ROOT / '.agents/evidence/improvement'
    directory.mkdir(parents=True, exist_ok=True)
    log = directory / (name + '.log')
    if log.exists():
        raise FileExistsError(log)
    start, tick = utc(), time.monotonic()
    start_revision=revision()
    start_dirty=bool(subprocess.check_output(["git","status","--porcelain"],cwd=ROOT,text=True).strip())
    snapshot=ARTIFACTS/'source-evidence'/name
    files={}
    for path in sorted([*(ROOT/'videochess_rl').rglob('*.py'),*(ROOT/'tests').rglob('*.py'),*(ROOT/'scripts').rglob('*.py'),*(ROOT/'configs/improvement').glob('*')]):
        if not path.is_file():continue
        rel=path.relative_to(ROOT)
        destination=snapshot/rel
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,destination)
        files[rel.as_posix()]=sha(path)
    write(snapshot/'manifest.json',files)
    with log.open('x') as out:
        result = subprocess.run(command, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)
    record = dict(command=command, started_at_utc=start, ended_at_utc=utc(),
                  wall_seconds=time.monotonic()-tick, exit_code=result.returncode,
                  git_revision=start_revision, source_worktree_dirty=start_dirty, end_git_revision=revision(), source_manifest_path=(snapshot/'manifest.json').relative_to(ROOT).as_posix(), source_manifest_sha256=sha(snapshot/'manifest.json'), log_path=log.relative_to(ROOT).as_posix(),
                  log_sha256=sha(log))
    write(directory / (name + '.json'), record)
    print(json.dumps(record), flush=True)
    return result.returncode


if __name__ == '__main__':
    sys.exit(run_evidence(sys.argv[1], sys.argv[2:]))
