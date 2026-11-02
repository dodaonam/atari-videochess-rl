"""Bounded real-ALE smoke using the historical frozen M4 and RGB adapter."""
import json
import torch
from videochess_rl.episode import run_episode
from videochess_rl.environment import ALEConfig
from videochess_rl.m6.adapter import load_m4_policy, M6PolicyAdapter
from .common import ARTIFACTS, ROOT, write


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live",action="store_true",help="Display local live ALE RGB in a Tk window")
    args=parser.parse_args()
    torch.set_num_threads(1)
    policy,identity = load_m4_policy(ROOT/'artifacts/m4/m4-behavior-20261027-r4')
    adapter = M6PolicyAdapter(policy,identity,rng_seed=20261103)
    def selector(context):
        selected=adapter(context)
        print('VERIFIED move history:',list(context.history_uci) if hasattr(context,'history_uci') else str(context),flush=True)
        print('M4 decision:',selected,flush=True)
        return selected
    extra={}
    if args.live:
        from .live import LiveEnvironment
        extra['env_factory']=LiveEnvironment
    result = run_episode(config=ALEConfig.deterministic_dev(mode=4),seed=20261103,
        expected_rom_sha256='d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7',
        decision_selector=selector,max_player_moves=2,max_opponent_wait_frames=30000,
        max_episode_seconds=180,max_episode_frames=150000,
        artifact_dir=str(ARTIFACTS/('demo-live/frames' if args.live else 'demo/frames')),**extra)
    write(ARTIFACTS/('demo-live/trace.json' if args.live else 'demo/trace.json'),result)
    print(json.dumps(result.get('terminal',{})),flush=True)
    terminal = result.get('terminal',{})
    return 0 if terminal.get('verified_player_moves',0)>=1 and terminal.get('verified_atari_replies',0)>=1 else 2


if __name__=='__main__':
    raise SystemExit(main())
