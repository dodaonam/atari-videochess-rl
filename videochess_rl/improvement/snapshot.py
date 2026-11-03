"""Immutable evaluation-only snapshots at the improvement decision boundaries."""
import os
from pathlib import Path
import tempfile
import torch
from videochess_rl.rl.checkpoint import SNAPSHOT_SCHEMA, load_evaluation_snapshot
from .common import sha, write


def save_snapshot(path, model, metadata):
    t=metadata['valid_decisions']
    if type(t) is not int or t not in range(0,250001,25000):raise ValueError('snapshot boundary')
    path=Path(path);side=path.with_suffix(path.suffix+'.manifest.json')
    if path.exists() or side.exists() or path.is_symlink() or side.is_symlink():raise FileExistsError(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    meta={**metadata,'schema':SNAPSHOT_SCHEMA,'resumable':False}
    fd,temp=tempfile.mkstemp(dir=path.parent,suffix='.tmp');os.close(fd)
    try:
        torch.save(dict(schema=SNAPSHOT_SCHEMA,resumable=False,metadata=meta,online={k:v.detach().cpu() for k,v in model.state_dict().items()}),temp)
        with open(temp,'rb') as f:os.fsync(f.fileno())
        os.replace(temp,path)
    finally:
        if Path(temp).exists():Path(temp).unlink()
    write(side,dict(schema=SNAPSHOT_SCHEMA,file=path.name,sha256=sha(path),size_bytes=path.stat().st_size,resumable=False))
    with torch.random.fork_rng(devices=[]):
        load_evaluation_snapshot(path)
