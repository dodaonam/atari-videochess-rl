"""Smoke the owner's optional existing GUI without editing or copying its source."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import runpy
import time
import tkinter as tk
import torch
from .common import ROOT, ARTIFACTS, sha, write


def main():
    path=Path('/home/dodaonam/Downloads/atari_videochess_live.py')
    if not path.is_file():raise FileNotFoundError('Optional owner GUI absent: '+str(path))
    original=sha(path)
    module=runpy.run_path(str(path),run_name='improvement_existing_demo')
    torch.set_num_threads(1)
    output=io.StringIO()
    report={}
    with contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):
        root=tk.Tk()
        args=argparse.Namespace(m5_root=str(ROOT/'artifacts/m5'),policy='m5-warm-seed-20261104-post-rl',seed=20261103,every=8,max_seconds=120.)
        app=module['LiveApp'](root,args)
        started=time.monotonic();launched=False
        def check():
            nonlocal launched
            if time.monotonic()-started>150:
                report['error']='GUI smoke timeout';app.exit_requested.set();root.destroy();return
            if app.preloaded is not None and not launched:
                app.preloaded['profile']={**app.preloaded['profile'],'maximum_player_moves':2}
                launched=True;app.start_game()
            elif launched and not app.is_running and app.replay_entries:
                app.step_replay_to(0);first=app.replay_index
                app.step_replay_to(len(app.replay_entries)-1);last=app.replay_index
                report.update(checkpoint_loaded=True,visible_frames=app.visible_frames,verified_half_moves=len(app.verified_history_uci),replay_entries=len(app.replay_entries),replay_first=first,replay_last=last,wall_seconds=time.monotonic()-started,profile='historical ALE v5 extended, shortened to two player moves for smoke')
                app.exit_requested.set();root.destroy();return
            root.after(100,check)
        root.after(100,check)
        root.mainloop()
    directory=ARTIFACTS/'existing-demo';directory.mkdir(exist_ok=True)
    (directory/'private-console.log').write_text(output.getvalue())
    report.update(script_path=str(path),script_sha256=original,script_preserved=sha(path)==original)
    write(directory/'summary.json',report)
    print(json.dumps(report))
    return 0 if report.get('checkpoint_loaded') and report.get('verified_half_moves',0)>=2 and report.get('replay_last',0)>0 and report['script_preserved'] else 2


if __name__=='__main__':raise SystemExit(main())
