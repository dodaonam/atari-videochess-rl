"""Fail-fast readiness checks for the local live Atari demonstration."""
from __future__ import annotations

import importlib
import os
import platform
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Callable

from .demo import ROM_SHA256


def run_demo_preflight(*, policy: str, checkpoint: str | Path | None,
                       expected_sha256: str | None, reset_seed: int,
                       output_root: str | Path, require_display: bool = True,
                       env_factory: Callable | None = None,
                       policy_loader: Callable | None = None,
                       environ: dict | None = None,
                       minimum_free_disk_bytes: int = 64 * 1024 * 1024) -> dict:
    """Check the exact runtime inputs without resetting or stepping Atari.

    Stockfish is intentionally not imported or checked: neither demo policy
    uses an engine during inference.
    """
    environ = os.environ if environ is None else environ
    checks: list[dict[str, object]] = []

    def record(name: str, ok: bool, observed: object, expected: object, action: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "observed": observed,
                       "expected": expected, "action": action})

    py_ok = sys.version_info >= (3, 12)
    record("python", py_ok, platform.python_version(), ">=3.12",
           "Activate the repository .venv created from uv.lock.")
    for module_name in ("numpy", "torch", "chess", "gymnasium", "ale_py"):
        try:
            module = importlib.import_module(module_name)
            version = getattr(module, "__version__", "installed")
            record(f"dependency:{module_name}", True, str(version), "importable",
                   "Install the repository's locked project dependencies if missing.")
        except Exception as exc:
            record(f"dependency:{module_name}", False, f"{type(exc).__name__}: {exc}",
                   "importable", "Activate the repository .venv and install its locked dependencies.")

    try:
        available_ram = int(os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE"))
        ram_ok = available_ram >= 128 * 1024 * 1024
        record("available_memory", ram_ok, {"available_bytes": available_ram},
               {"minimum_available_bytes": 128 * 1024 * 1024},
               "Close memory-intensive applications before loading the policy and ALE.")
    except (AttributeError, OSError, ValueError):
        record("available_memory", True, "unavailable on this platform", "optional measurement",
               "Check available system memory manually if startup fails.")

    display = bool(environ.get("DISPLAY") or environ.get("WAYLAND_DISPLAY"))
    if not require_display:
        record("display", True, "not required for preflight unit invocation", "not required", "")
    elif not display:
        record("display", False, "DISPLAY and WAYLAND_DISPLAY are unset", "usable graphical display",
               "Start a desktop session or configure an approved virtual display.")
    else:
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.update_idletasks()
            root.destroy()
            record("tk_display", True, "Tk root created and closed", "usable Tk display", "")
        except Exception as exc:
            record("tk_display", False, f"{type(exc).__name__}: {exc}", "usable Tk display",
                   "Install/enable Tk and verify that the selected display accepts local windows.")

    try:
        from videochess_rl.environment import ALEConfig, VideoChessEnv
        env_factory = env_factory or VideoChessEnv
        env = env_factory(ALEConfig.deterministic_dev(mode=4))
        try:
            runtime = env.runtime_info()
        finally:
            env.close()
        rom = runtime.get("rom_sha256")
        record("videochess_environment", rom == ROM_SHA256, {
            "env_id": runtime.get("config", {}).get("env_id"),
            "rom_sha256": rom,
            "ale_py": runtime.get("ale_py"),
            "gymnasium": runtime.get("gymnasium"),
            "action_count": runtime.get("instance_runtime", {}).get("action_count"),
            "observation_shape": runtime.get("instance_runtime", {}).get("observation_shape"),
            "ale_episode_frame_limit": runtime.get("ale_episode_frame_limit"),
        }, {"env_id": "ALE/VideoChess-v5", "rom_sha256": ROM_SHA256,
            "action_count": 10, "observation_shape": [210, 160, 3]},
           "Install the compatible ALE-Py/Gymnasium environment and the verified VideoChess ROM.")
        instance = runtime.get("instance_runtime", {})
        shape_ok = instance.get("action_count") == 10 and instance.get("observation_shape") == [210, 160, 3]
        record("environment_contract", shape_ok, {
            "action_count": instance.get("action_count"),
            "observation_shape": instance.get("observation_shape"),
        }, {"action_count": 10, "observation_shape": [210, 160, 3]},
           "Use the repository-locked ALE-Py and Gymnasium packages.")
        expected_profile = {
            "mode": 4, "difficulty": 0, "frameskip": 1,
            "repeat_action_probability": 0.0, "obs_type": "rgb",
            "action_count": 10, "observation_shape": [210, 160, 3],
            "action_set": list(range(10)),
        }
        profile_ok = (runtime.get("config") == ALEConfig.deterministic_dev(mode=4).as_dict()
                      and runtime.get("rom_name") == "video_chess.bin"
                      and all(instance.get(key) == value for key, value in expected_profile.items()))
        record("ale_profile", profile_ok, {
            "config": runtime.get("config"), "rom_name": runtime.get("rom_name"),
            "instance_runtime": {key: instance.get(key) for key in expected_profile},
        }, {"config": ALEConfig.deterministic_dev(mode=4).as_dict(),
            "rom_name": "video_chess.bin", "instance_runtime": expected_profile},
           "Use the tested ALE/VideoChess-v5 mode-4 RGB action profile and locked dependencies.")
    except Exception as exc:
        record("videochess_environment", False, f"{type(exc).__name__}: {exc}",
               "constructible ALE/VideoChess-v5", "Verify ALE-Py, Gymnasium registration, ROM availability, and profile support.")

    try:
        if policy_loader is None:
            from .policies import load_demo_policy
            policy_loader = load_demo_policy
        adapter, identity = policy_loader(policy, checkpoint=checkpoint,
            expected_sha256=expected_sha256, policy_rng_seed=reset_seed)
        del adapter
        record("policy_checkpoint", True, {
            "policy_id": identity.policy_id, "policy_type": identity.policy_type,
            "checkpoint_sha256": identity.checkpoint_sha256,
            "training_seed": identity.training_seed,
            "valid_decisions": identity.valid_decisions,
        }, "exact accepted checkpoint and immutable metadata", "")
    except Exception as exc:
        record("policy_checkpoint", False, f"{type(exc).__name__}: {exc}",
               "present, hash-valid, loadable checkpoint with expected run metadata",
               "Supply the accepted local checkpoint and exact SHA-256; restore its official run metadata if absent.")

    out = Path(output_root)
    try:
        if any(parent.is_symlink() for parent in (out, *out.parents)):
            raise ValueError("artifact output path contains a symlink")
        out.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix=".demo-preflight-", dir=out, delete=True):
            pass
        free = shutil.disk_usage(out).free
        disk_ok = free >= minimum_free_disk_bytes
        record("artifact_output", disk_ok, {"directory_writable": True, "free_bytes": free},
               {"writable": True, "minimum_free_bytes": minimum_free_disk_bytes},
               "Choose a writable local artifact directory and free disk space before launching.")
    except Exception as exc:
        record("artifact_output", False, f"{type(exc).__name__}: {exc}",
               {"writable": True, "minimum_free_bytes": minimum_free_disk_bytes},
               "Choose a writable local artifact directory with at least 64 MiB free.")

    return {"ok": all(item["ok"] for item in checks), "policy": policy,
            "atari_reset_seed": reset_seed, "model_training_seed": next(
                (item["observed"].get("training_seed") for item in checks
                 if item["name"] == "policy_checkpoint" and item["ok"]), None),
            "checks": checks}
