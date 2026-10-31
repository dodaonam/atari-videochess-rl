#!/usr/bin/env python3
"""Reconstruct and report M4–M7 evidence from frozen raw records."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from videochess_rl.m6.ledger import sha256_file
from videochess_rl.m7.analysis import AnalysisIntegrityError, analyze_all_tracks


OUTCOME_ORDER = ("wins", "draws", "losses", "terminal_unknown", "truncated", "incomplete", "not_started")
COLORS = {
    "wins": "#2e8b57", "draws": "#4b8b83", "losses": "#bd4b4b",
    "terminal_unknown": "#7851a9", "truncated": "#dd9f25", "incomplete": "#65758b",
    "not_started": "#c5cbd3",
}


def _git_identity() -> dict[str, str]:
    def run(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    return {"commit": run("rev-parse", "HEAD"), "tree": run("rev-parse", "HEAD^{tree}")}


def _format_rate(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "—"
    return f"{100 * value:.2f}%"


def _format_score(value: Any) -> str:
    return "—" if not isinstance(value, (int, float)) else f"{value:.3f}"


def _interval_text(interval: dict[str, Any]) -> str:
    ci = interval.get("ci_95_crossed_cluster") or interval.get("ci_95_seed_cluster")
    if not ci:
        return f"unavailable ({interval.get('status', 'reason not recorded')})"
    return f"[{ci[0]:.3f}, {ci[1]:.3f}]"


def _track_table(name: str, rows: dict[str, dict[str, Any]]) -> list[str]:
    lines = [f"### {name}", "", "| Policy | Scheduled | W / D / L | Unknown | Truncated | Incomplete | Not started | Terminal score (n) |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for policy, row in sorted(rows.items()):
        score = _format_score(row.get("terminal_only_game_score"))
        denom = row.get("terminal_wdl_denominator", row.get("terminal_known_games", 0))
        lines.append(
            f"| `{policy}` | {row.get('scheduled', '—')} | "
            f"{row.get('wins', 0)} / {row.get('draws', 0)} / {row.get('losses', 0)} | "
            f"{row.get('terminal_unknown', 0)} | {row.get('truncated', 0)} | "
            f"{row.get('incomplete', 0)} | {row.get('not_started', 0)} | {score} ({denom}) |"
        )
    return lines


def render_markdown(analysis: dict[str, Any], *, created_at: str, analysis_source: dict[str, str]) -> str:
    tracks = analysis["tracks"]
    m4 = tracks["M4_supervised_imitation"]
    m5 = tracks["M5_simulator_Double_DQN"]
    m6v1 = tracks["M6_stage3_v1_ALE"]
    m6v2 = tracks["M6_stage3_v2_ALE"]
    m7 = tracks["M7_option_B_ALE"]
    m6v2_rows = list(m6v2["policy_summary"]["by_policy"].values())
    m6v2_totals = {
        key: sum(row.get(key, 0) for row in m6v2_rows)
        for key in ("wins", "draws", "losses", "terminal_unknown", "truncated", "incomplete", "not_started",
                    "initiated_moves", "rgb_verified_initiated_moves", "verified_atari_replies", "desynchronizations")
    }
    lines = [
        "# M7 Option B Evaluation Analysis", "",
        f"Generated from raw records at `{created_at}` using analysis source `{analysis_source['commit']}` (tree `{analysis_source['tree']}`).", "",
        f"Protocol: `{analysis['analysis_protocol']}`; scientific basis: `{analysis['scientific_basis']}`.",
        f"M7 run: `{m7['run_id']}`; config SHA-256 `{m7['configuration_sha256']}`; schedule SHA-256 `{m7['schedule_sha256']}`.",
        f"Environment: `{m7['evaluation_identity']['environment_id']}`, White, mode {m7['evaluation_identity']['mode']}, difficulty {m7['evaluation_identity']['difficulty']}, RGB, frameskip {m7['evaluation_identity']['frameskip']}, sticky probability {m7['evaluation_identity']['repeat_action_probability']}; seeds `{m7['evaluation_identity']['ale_evaluation_seeds']}`.",
        f"ALE registered horizon {m7['evaluation_identity']['registered_default_max_num_frames_per_episode']} frames; M7 effective horizon {m7['evaluation_identity']['effective_max_num_frames_per_episode']} frames; runner cap {m7['evaluation_identity']['runner_maximum_post_reset_action_frames']} post-reset frames.",
        f"Raw M7 artifacts are owner-local under `artifacts/m7-option-b/{m7['run_id']}`. They are not included in this report bundle.", "",
        "## Evidence tracks", "",
        "The five tracks below remain separate. M4 imitation accuracy is not game score; M5 simulator results are not ALE results; M6 v1 and v2 retain different configurations; cross-protocol M6/M7 differences are descriptive only.", "",
        "### M4 supervised imitation", "",
        f"Accepted run `{m4['run_id']}`, seed `{m4['training_seed']}`, epoch `{m4['selected_epoch']}`, checkpoint SHA-256 `{m4['checkpoint_sha256']}`.",
        f"Held-out test: {m4['positions']} positions; legal top-1 `{m4['legal_top1_accuracy']:.6f}`; legal top-3 `{m4['legal_top3_accuracy']:.6f}`. These are imitation metrics. The accepted root retains an aggregate evaluation record, not per-position predictions.", "",
        "### M5 simulator Double DQN", "",
        "The accepted raw evaluation was independently read as 1,500 rows (15 policy groups × 100 rows); terminal-only game score uses only known W/D/L outcomes.", "",
    ]
    lines.extend(_track_table("M5 policy outcomes", m5["policy_summary"]["by_policy"]))
    lines.extend(["", "#### Paired M5 comparisons", "", "| Comparison | Matched terminal pairs | Censored pairs | Point difference | 95% interval |", "|---|---:|---:|---:|---|"])
    for comparison in m5["paired_comparisons"]:
        result = comparison["left_minus_right"]
        lines.append(
            f"| `{comparison['comparison']}` | {comparison['matched_terminal_pairs']} | {comparison['censored_pairs']} | "
            f"{_format_score(result.get('point_difference'))} | {_interval_text(result)} |"
        )
    lines.extend([
        "", "M5 bootstrap intervals are withheld when a comparison contains censored pairs. The historical M5 provenance limitation RSK-014 remains in force.", "",
        f"### M6 Stage 3 v1 — `{m6v1['run_id']}`", "",
        f"Configuration SHA-256 `{m6v1['configuration_sha256']}`; root manifest `{m6v1['root_artifact_manifest_sha256']}`; {m6v1['scheduled_attempts']} scheduled attempts.", "",
    ])
    lines.extend(_track_table("M6 v1 outcomes", m6v1["policy_summary"]["by_policy"]))
    lines.extend([
        "", f"### M6 Stage 3 v2 — `{m6v2['run_id']}`", "",
        f"Configuration SHA-256 `{m6v2['configuration_sha256']}`; root manifest `{m6v2['root_artifact_manifest_sha256']}`; {m6v2['scheduled_attempts']} scheduled attempts.", "",
    ])
    lines.extend(_track_table("M6 v2 outcomes", m6v2["policy_summary"]["by_policy"]))
    lines.extend([
        "", f"M6 v2 raw reconstruction totals: {m6v2_totals['losses']} terminal losses; {m6v2_totals['incomplete']} incomplete; {m6v2_totals['wins']} wins, {m6v2_totals['draws']} draws, {m6v2_totals['terminal_unknown']} terminal-unknown, {m6v2_totals['truncated']} truncated; {m6v2_totals['rgb_verified_initiated_moves']}/{m6v2_totals['initiated_moves']} initiated moves RGB-verified; {m6v2_totals['desynchronizations']} board desynchronizations. PM6-F06 remains an immutable metadata erratum.", "",
        f"### M7 Option B ALE — {m7['scheduled_attempt_count']} scheduled cells", "",
        f"Run reconstruction: {m7['attempt_processes_started']} attempt processes, {m7['reset_observed_cells']} reset-observed cells; run resource stop: `{m7['resource_stop_reason'] or 'none'}`.",
        f"Root artifact manifest SHA-256 `{m7['raw_artifact_manifest_sha256']}`; run-manifest SHA-256 `{m7['raw_run_manifest_sha256']}`.", "",
    ])
    lines.extend(_track_table("M7 policy outcomes", m7["policy_summary"]["by_policy"]))
    lines.extend([
        "", "| Policy | RGB-verified moves / initiated | Verified move rate | Legal selections valid / proposals | Desyncs | Cursor corrections | Median process wall s | Median machine CPU % |", "|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for policy, row in sorted(m7["policy_summary"]["by_policy"].items()):
        wall = row["resource_distributions"].get("observed_process_wall_seconds", {}).get("median")
        cpu = row["resource_distributions"].get("process_cpu_utilization_machine_percent", {}).get("median")
        lines.append(
            f"| `{policy}` | {row['rgb_verified_initiated_moves']} / {row['initiated_moves']} | {_format_rate(row['rgb_verified_move_rate'])} | "
            f"{row['legal_action_validation_passed']} / {row['legal_action_proposals']} | {row['desynchronizations']} | {row['cursor_corrections']} | "
            f"{_format_score(wall)} | {_format_score(cpu)} |"
        )
    lines.extend(["", "| Policy | Input-validation latency median s | Choose-move latency median s | Adapter-total latency median s | Stop categories | Uncertainty categories |", "|---|---:|---:|---:|---|---|"])
    for policy, row in sorted(m7["policy_summary"]["by_policy"].items()):
        latency = row["policy_latency_distributions"]
        lines.append(
            f"| `{policy}` | {_format_score(latency['input_validation_latency_seconds']['median'])} | "
            f"{_format_score(latency['policy_choose_move_latency_seconds']['median'])} | "
            f"{_format_score(latency['adapter_total_latency_seconds']['median'])} | "
            f"`{json.dumps(row['stop_category_counts'], sort_keys=True)}` | "
            f"`{json.dumps(row['incomplete_final_move_category_counts'], sort_keys=True)}` |"
        )
    warm_scratch = m7["paired_comparisons"]["warm_vs_scratch_post_rl"]
    interval = warm_scratch["crossed_training_seed_and_ale_seed_bootstrap"]
    lines.extend([
        "", "#### Paired M7 comparisons", "",
        f"Warm-start minus Scratch post-RL: {warm_scratch['matched_terminal_training_seed_by_ale_seed_cells']}/30 matched terminal training-seed × ALE-seed cells; {warm_scratch['censored_or_unknown_cells']} censored/unknown; point difference `{_format_score(interval.get('point_difference'))}`; 95% interval {_interval_text(interval)}.",
        "",
        "| RL policy vs baseline | Training seed | Matched blocks | Censored/unknown | Point difference | 95% interval |",
        "|---|---:|---:|---:|---:|---|",
    ])
    for comparison in m7["paired_comparisons"]["rl_policy_vs_baseline"]:
        result = comparison["paired_cluster_bootstrap"]
        lines.append(
            f"| `{comparison['comparison']}` | {comparison['training_seed']} | {comparison['matched_terminal_seed_blocks']} | "
            f"{comparison['censored_or_unknown_seed_blocks']} | {_format_score(result.get('point_difference'))} | {_interval_text(result)} |"
        )
    shadow_stops = [
        {"policy": policy, **cell, "diagnostic": cell["metrics"]["shadow_terminal_policy_input_diagnostic"]}
        for policy, summary in m7["policy_summary"]["by_policy"].items()
        for cell in summary["per_seed_cells"]
        if cell["metrics"].get("shadow_terminal_policy_input_diagnostic") is not None
    ]
    if shadow_stops:
        lines.extend([
            "", "#### Shadow-terminal policy-input stops", "",
            "These stops came from the frozen adapter validating the replayed python-chess history. They remain incomplete because ALE had not emitted a terminal flag; they are not ALE draws or terminal results.",
            "", "| Policy | ALE seed | Shadow termination | Legal moves available in shadow | ALE terminated/truncated | ALE reward |",
            "|---|---:|---|---|---|---:|",
        ])
        for stop in shadow_stops:
            diagnostic = stop["diagnostic"]
            lines.append(
                f"| `{stop['policy']}` | {stop['ale_seed']} | {diagnostic['shadow_termination']} | "
                f"{diagnostic['shadow_legal_moves_available']} | {diagnostic['ale_terminated']}/{diagnostic['ale_truncated']} | "
                f"{diagnostic['ale_reward_total']} |"
            )
    resources = m7["campaign_resources"]
    pre = resources.get("pre_campaign") or {}
    limits = m7["resource_limits"]
    expected_time = limits["expected_gameplay_time"]
    lines.extend([
        "", "### Resource accounting", "",
        f"Device profile: local CPU; one serialized ALE process. Free disk before campaign: {pre.get('free_disk_bytes')}; after campaign: {resources.get('free_disk_bytes_after')}.",
        f"Artifact-parent bytes after finalization (including preregistration/preflight logs): {resources.get('artifact_parent_total_bytes_after_finalization')}; run-manifest inventory bytes excluding its manifest file: {resources.get('run_manifest_inventory_bytes_excluding_manifest')}; peak process RSS: {resources.get('peak_process_rss_bytes')}.",
        f"Frozen limits: {limits['maximum_wall_seconds_per_attempt']} seconds/attempt; {limits['maximum_campaign_artifact_bytes']} artifact bytes; at least {limits['minimum_free_bytes_before_first_attempt']} free bytes before start; aggregate gameplay cap {limits['maximum_aggregate_gameplay_seconds']} seconds.",
        f"Expected gameplay duration was approximately {expected_time['hours']} hours from {expected_time['historical_basis']}; this is a planning estimate, not a guarantee. The aggregate cap equals 45 hours, plus separately measured setup/recovery.",
        f"Aggregate process CPU seconds: {resources.get('aggregate_process_cpu_seconds')}; observed process wall seconds: {resources.get('aggregate_observed_process_wall_seconds')}; whole campaign session seconds: {resources.get('campaign_observed_session_wall_seconds')}.",
        "Per-policy latency and per-attempt resource distributions are available in `m7-analysis.json`.", "",
        "### Interpretation and limitations", "",
        "- All W/D/L and terminal game-score denominators include only ALE-authoritative known terminal outcomes. Incomplete, truncated, terminal-unknown, and not-started cells are retained separately; no incomplete result is scored as a draw.",
        "- Full-schedule score bounds classify every unresolved cell as a loss or as a win, without imputing an outcome.",
        "- Paired intervals are suppressed when a pair set contains censored/unknown outcomes. Per-policy seed intervals are suppressed unless every scheduled seed has a usable outcome/metric.",
        "- Three M5 training-seed pairs and ten M7 ALE seed blocks provide limited inference. The paired seed blocks are not independent trained policies, and no broad Warm-start superiority or generalization claim follows.",
        "- The M7 campaign uses White only and the built-in Atari opponent. M6/M7 comparisons are across different schedules/runtime profiles and are descriptive.",
        "- The M4 accepted aggregate is imitation agreement, not playing strength. The M5 track is a simulator. M6/M7 are actual ALE but measure the frozen controller-policy system together.",
        "- Elo not reported: calibrated opponent pool/design not approved or unavailable. No rating anchor, diverse calibrated pool, or approved Elo match schedule exists.",
        "- M5 RSK-014 and M6 v2 PM6-F06 remain disclosed historical limitations.",
        "", "### Reproducibility and integrity", "",
        f"Analysis source commit `{analysis_source['commit']}`; analysis source tree `{analysis_source['tree']}`. Raw M5, M6 v1/v2, M7 ledgers, trace files, root manifests, and the accepted M4 aggregate evaluation were verified before summarization.",
        f"Summary reconciliation: `{json.dumps(m7['summary_reconciliation'], sort_keys=True)}`.",
        "The machine-readable JSON retains per-seed cells, status categories, denominators, paired comparisons, bootstrap configuration, and resource observations. Raw traces/checkpoints/ROM/RGB remain local and are excluded from this bundle.", "",
    ])
    return "\n".join(lines)


def _svg_start(title: str, width: int, height: int) -> list[str]:
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
            f'<text x="20" y="28" font-family="sans-serif" font-size="18" font-weight="bold">{html.escape(title)}</text>']


def outcome_svg(rows: dict[str, dict[str, Any]]) -> str:
    width, height = 1050, 410
    svg = _svg_start("M7 Option B — scheduled outcome categories by frozen policy", width, height)
    left, top, bar_h, plot_w = 285, 58, 24, 590
    for i, (policy, row) in enumerate(sorted(rows.items())):
        y = top + i * 35
        svg.append(f'<text x="{left - 10}" y="{y + 17}" text-anchor="end" font-family="sans-serif" font-size="12">{html.escape(policy)}</text>')
        x = left
        for key in OUTCOME_ORDER:
            count = int(row.get(key, 0))
            w = plot_w * count / max(1, row.get("scheduled", 10))
            if count:
                svg.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{bar_h}" fill="{COLORS[key]}"/>')
                if w > 25:
                    svg.append(f'<text x="{x + w / 2:.1f}" y="{y + 16}" text-anchor="middle" fill="#fff" font-family="sans-serif" font-size="11">{count}</text>')
            x += w
        svg.append(f'<text x="{left + plot_w + 12}" y="{y + 17}" font-family="sans-serif" font-size="11">n={row.get("scheduled", 10)}</text>')
    legend_y = top + 9 * 35 + 4
    lx = left
    for key in OUTCOME_ORDER:
        svg.append(f'<rect x="{lx}" y="{legend_y}" width="12" height="12" fill="{COLORS[key]}"/>')
        svg.append(f'<text x="{lx + 17}" y="{legend_y + 11}" font-family="sans-serif" font-size="11">{key.replace("_", " ")}</text>')
        lx += 105
    svg.append('</svg>')
    return "\n".join(svg)


def m7_seed_grid_svg(rows: dict[str, dict[str, Any]]) -> str:
    width, height = 850, 390
    svg = _svg_start("M7 Option B — outcome by policy and shared ALE seed block", width, height)
    left, top, cell_w, cell_h = 275, 65, 47, 30
    labels = {"win": "W", "draw": "D", "loss": "L", "terminal_unknown": "?", "truncated": "T", "incomplete": "I", "not_started": "—"}
    for col, seed in enumerate(range(20261201, 20261211)):
        svg.append(f'<text x="{left + col * cell_w + cell_w / 2}" y="{top - 9}" text-anchor="middle" font-family="sans-serif" font-size="10">{str(seed)[-2:]}</text>')
    for i, (policy, row) in enumerate(sorted(rows.items())):
        y = top + i * cell_h
        svg.append(f'<text x="{left - 8}" y="{y + 19}" text-anchor="end" font-family="sans-serif" font-size="11">{html.escape(policy)}</text>')
        cells = {cell["ale_seed"]: cell for cell in row["per_seed_cells"]}
        for col, seed in enumerate(range(20261201, 20261211)):
            category = cells[seed]["outcome"]
            color_key = {"win": "wins", "draw": "draws", "loss": "losses"}.get(category, category)
            x = left + col * cell_w
            svg.append(f'<rect x="{x}" y="{y}" width="{cell_w - 3}" height="{cell_h - 3}" rx="2" fill="{COLORS[color_key]}"/>')
            svg.append(f'<text x="{x + (cell_w - 3) / 2}" y="{y + 18}" text-anchor="middle" fill="#fff" font-family="sans-serif" font-size="12">{labels[category]}</text>')
    svg.append('<text x="20" y="370" font-family="sans-serif" font-size="11">Each column is a shared seed block (20261201–20261210); cells are not independent training replications.</text>')
    svg.append('</svg>')
    return "\n".join(svg)


def m5_learning_svg(rows: dict[str, dict[str, Any]]) -> str:
    width, height = 1050, 430
    svg = _svg_start("M5 simulator — terminal-only game score before and after Double DQN", width, height)
    left, top, plot_h, plot_w = 250, 65, 270, 550
    for tick in range(6):
        y = top + plot_h - tick * plot_h / 5
        value = tick / 5
        svg.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#d7dce2"/>')
        svg.append(f'<text x="{left - 9}" y="{y + 4:.1f}" text-anchor="end" font-family="sans-serif" font-size="11">{value:.1f}</text>')
    entries = []
    for arm in ("warm", "scratch"):
        for seed in (20261104, 20261105, 20261106):
            row = rows.get(f"{arm}:{seed}:pre_rl")
            post = rows.get(f"{arm}:{seed}:post_rl")
            if row and post:
                entries.append((arm, seed, row, post))
    group_w = plot_w / max(1, len(entries))
    for i, (arm, seed, pre, post) in enumerate(entries):
        cx = left + (i + 0.5) * group_w
        for j, row in enumerate((pre, post)):
            value = row.get("terminal_only_game_score")
            if value is None:
                continue
            h = plot_h * value
            color = "#5679b9" if j == 0 else "#d78a42"
            x = cx + (-13 if j == 0 else 2)
            svg.append(f'<rect x="{x:.1f}" y="{top + plot_h - h:.1f}" width="11" height="{h:.1f}" fill="{color}"/>')
        svg.append(f'<text x="{cx:.1f}" y="{top + plot_h + 18}" text-anchor="middle" font-family="sans-serif" font-size="10">{arm} {str(seed)[-2:]}</text>')
    svg.extend([
        f'<rect x="{left + plot_w + 45}" y="85" width="13" height="13" fill="#5679b9"/>',
        f'<text x="{left + plot_w + 64}" y="96" font-family="sans-serif" font-size="12">pre-RL</text>',
        f'<rect x="{left + plot_w + 45}" y="110" width="13" height="13" fill="#d78a42"/>',
        f'<text x="{left + plot_w + 64}" y="121" font-family="sans-serif" font-size="12">post-RL</text>',
        '<text x="25" y="405" font-family="sans-serif" font-size="11">Bars use terminal-only simulator game score; each comparison is clustered by its paired training seed and evaluation scenarios.</text>',
        '</svg>',
    ])
    return "\n".join(svg)


def write_analysis(output_dir: Path, result: dict[str, Any]) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing M7 analysis bundle: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    source = _git_identity()
    full = {"schema": "videochess-m7-analysis-bundle/1.0", "created_at_utc": created_at,
            "analysis_source": source, "analysis": result}
    outputs = {
        "m7-analysis.json": json.dumps(full, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        "M7_ANALYSIS.md": render_markdown(result, created_at=created_at, analysis_source=source),
        "m7-outcomes.svg": outcome_svg(result["tracks"]["M7_option_B_ALE"]["policy_summary"]["by_policy"]),
        "m7-seed-grid.svg": m7_seed_grid_svg(result["tracks"]["M7_option_B_ALE"]["policy_summary"]["by_policy"]),
        "m5-pre-post.svg": m5_learning_svg(result["tracks"]["M5_simulator_Double_DQN"]["policy_summary"]["by_policy"]),
    }
    with tempfile.TemporaryDirectory(prefix=f".{output_dir.name}.partial-", dir=output_dir.parent) as temporary:
        staging = Path(temporary)
        for name, content in outputs.items():
            (staging / name).write_text(content, encoding="utf-8")
        manifest = {
            "schema": "videochess-m7-analysis-output-manifest/1.0",
            "created_at_utc": created_at,
            "analysis_source": source,
            "files": [{"path": name, "sha256": sha256_file(staging / name), "bytes": (staging / name).stat().st_size}
                      for name in sorted(outputs)],
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        if output_dir.exists() or output_dir.is_symlink():
            raise FileExistsError(f"refusing to overwrite existing M7 analysis bundle: {output_dir}")
        os.replace(staging, output_dir)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--m7-run-dir", type=Path, required=True)
    parser.add_argument("--m4-root", type=Path, required=True)
    parser.add_argument("--m5-root", type=Path, required=True)
    parser.add_argument("--m6-v1-root", type=Path, required=True)
    parser.add_argument("--m6-v2-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = analyze_all_tracks(
            config_path=args.config,
            m7_run_dir=args.m7_run_dir,
            m4_artifact_root=args.m4_root,
            m5_artifact_root=args.m5_root,
            m6_v1_root=args.m6_v1_root,
            m6_v2_root=args.m6_v2_root,
        )
        manifest = write_analysis(args.output_dir, result)
    except (AnalysisIntegrityError, OSError, ValueError) as exc:
        print(f"M7 analysis refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"output_dir": str(args.output_dir), "files": len(manifest["files"]),
                      "manifest_filesha256": sha256_file(args.output_dir / "manifest.json"),
                      "m7_scheduled_cells": result["tracks"]["M7_option_B_ALE"]["scheduled_attempt_count"],
                      "m7_reset_observed_cells": result["tracks"]["M7_option_B_ALE"]["reset_observed_cells"]},
                     sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
