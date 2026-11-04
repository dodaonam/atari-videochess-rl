"""Resizable local Tk viewer for real ALE frames and RGB-verified chess moves."""
from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk
from pathlib import Path

import numpy as np

from videochess_rl.environment import ALEConfig, VideoChessEnv


@dataclass
class DemoSessionState:
    """Independent episode, trace-persistence, and worker lifecycle state."""
    required_player_moves: int | None = None
    episode_status: str | None = None
    episode_terminal: dict | None = None
    terminal_category: str | None = None
    primary_reason: str | None = None
    trace_status: str = "not saved"
    trace_path: str | None = None
    worker_status: str = "running"
    worker_error_type: str | None = None
    worker_error: str | None = None
    replay_available: bool = False
    verified_pairs_displayed: int = 0
    verified_player_moves_displayed: int = 0
    verified_atari_replies_displayed: int = 0
    terminal_ram_verified_player_moves_displayed: int = 0
    terminal_ram_verified_atari_replies_displayed: int = 0
    terminal_sequence_verification: dict | None = None
    live_summary: dict | None = None
    replay_diagnostics: list[dict] | None = None

    def apply(self, event: dict) -> None:
        kind = event.get("event")
        if kind == "episode_finished":
            self.episode_status = str(event.get("status") or "unknown")
            terminal = event.get("terminal") or {}
            self.episode_terminal = dict(terminal) if isinstance(terminal, dict) else None
            self.terminal_category = terminal.get("runner_stop_category") if isinstance(terminal, dict) else None
            terminal_reason = terminal.get("runner_stop_reason") if isinstance(terminal, dict) else None
            self.primary_reason = (event.get("failure") or terminal_reason
                                   or self.episode_status)
            terminal_sequence = event.get("terminal_sequence_verification")
            if isinstance(terminal_sequence, dict):
                self.terminal_sequence_verification = dict(terminal_sequence)
                if terminal_sequence.get("verified") is True:
                    self.terminal_ram_verified_player_moves_displayed = int(
                        terminal_sequence.get("terminal_ram_player_move_count", 0)
                    )
                    self.terminal_ram_verified_atari_replies_displayed = int(
                        terminal_sequence.get("terminal_ram_atari_reply_count", 0)
                    )
        elif kind == "verified_turn":
            self.verified_pairs_displayed += 1
            if event.get("player_move_verified_earlier") is not True:
                self.verified_player_moves_displayed += 1
            self.verified_atari_replies_displayed += 1
        elif kind == "player_move_verified":
            self.verified_player_moves_displayed += 1
        elif kind == "trace_saved":
            self.trace_status = "saved"
            self.trace_path = event.get("path")
        elif kind == "trace_save_error":
            self.trace_status = "failed"
            self.worker_error_type = event.get("error_type", "TracePersistenceError")
            self.worker_error = event.get("error", "trace could not be saved")
        elif kind == "worker_error":
            self.worker_status = "failed"
            self.worker_error_type = event.get("error_type", "Exception")
            self.worker_error = event.get("error", "worker failed")
        elif kind == "worker_finished":
            self.worker_status = str(event.get("status") or "failed")
            self.replay_available = bool(event.get("replay_available"))
        elif kind == "session_summary":
            summary = event.get("summary")
            if isinstance(summary, dict):
                self.live_summary = dict(summary)
                diagnostics = summary.get("replay_diagnostics")
                self.replay_diagnostics = (
                    [dict(item) for item in diagnostics if isinstance(item, dict)]
                    if isinstance(diagnostics, list) else []
                )

    @property
    def display_status(self) -> str:
        if self.worker_error:
            episode = self.episode_status or "status unavailable"
            if self.terminal_category:
                episode = f"{episode} [{self.terminal_category}]"
            if self.primary_reason:
                episode = f"{episode} — {self.primary_reason}"
            return (f"Worker/runtime failure ({self.worker_error_type}): {self.worker_error}. "
                    f"Episode: {episode}")
        terminal = self.episode_terminal or {}
        category = self.terminal_category
        if terminal.get("ale_terminated") is True:
            result = terminal.get("white_result_from_reward")
            result_text = {
                "white_win": "White win",
                "white_loss": "White loss",
                "draw": "draw",
            }.get(result, "result unavailable")
            if isinstance(self.terminal_sequence_verification, dict) and self.terminal_sequence_verification.get("verified") is True:
                outcome = f"ALE game ended · {result_text}; terminal checkmate verified from ALE RAM"
            else:
                outcome = f"ALE chess game terminated · {result_text} from ALE reward"
        elif terminal.get("ale_truncated") is True:
            outcome = "ALE episode truncated; chess result is incomplete"
        elif category == "RUNNER_USER_CANCEL":
            outcome = "Session cancelled by user"
        elif category and (category.startswith("RUNNER_MAX_") or category in {
                "RUNNER_ARTIFACT_LIMIT", "RUNNER_RESOURCE_LIMIT"}):
            outcome = "Expected runner limit reached"
        elif category and category.startswith("CONTROLLER_"):
            outcome = "Controller stopped safely on uncertain state"
        elif category == "OPPONENT_RESPONSE_TIMEOUT":
            outcome = "Atari reply timeout; game state is incomplete"
        elif category:
            outcome = "Session stopped before a verified game result"
        else:
            outcome = self.episode_status or "Episode status unavailable"
        suffix = f" [{category}]" if category else ""
        reason = f" — {self.primary_reason}" if self.primary_reason else ""
        diagnostics = self.replay_diagnostics or []
        errors = sum(item.get("severity") == "ERROR" for item in diagnostics)
        warnings = sum(item.get("severity") == "WARNING" for item in diagnostics)
        replay = f" • replay evidence: {errors} errors, {warnings} warnings" if self.live_summary else ""
        return f"{outcome}{suffix}{reason}{replay} • trace {self.trace_status}"

    @property
    def smoke_ok(self) -> bool:
        terminal = self.episode_terminal
        required = self.required_player_moves
        if (required is None or terminal is None or self.worker_status != "completed"
                or self.episode_status != "runner_stopped" or self.trace_status != "saved"
                or self.worker_error is not None):
            return False
        return (
            terminal.get("runner_stop_category") == "RUNNER_MAX_PLAYER_MOVES"
            and terminal.get("runner_stopped") is True
            and terminal.get("observed") is False
            and terminal.get("terminated") is False
            and terminal.get("truncated") is False
            and terminal.get("ale_terminated") is False
            and terminal.get("ale_truncated") is False
            and terminal.get("runner_stop_reason") ==
                f"runner stopped after the configured {required} player-move limit"
            and terminal.get("player_moves_attempted") == required
            and terminal.get("verified_player_moves") == required
            and terminal.get("verified_atari_replies") == required
            and terminal.get("incomplete_final_move_count") == 0
            and self.verified_pairs_displayed == required
            and self.verified_player_moves_displayed == required
            and self.verified_atari_replies_displayed == required
        )


def demo_footer_text(demo_seed: int, training_seed: int | None, max_player_moves: int) -> str:
    """Label the ALE reset RNG independently from the model's training seed."""
    model_seed = str(training_seed) if training_seed is not None else "not recorded"
    return (f"Atari reset seed: {demo_seed} • model training seed: {model_seed} "
            f"• move cap {max_player_moves}")


class LiveEnvironment(VideoChessEnv):
    """Publish actual emulator frames to a thread-safe queue, never touching Tk."""
    def __init__(self, config: ALEConfig, *, frame_callback):
        self.frame_callback = frame_callback
        super().__init__(config)

    def _frame(self, rgb, reward, terminated, truncated, info):
        frame = super()._frame(rgb, reward, terminated, truncated, info)
        self.frame_callback(frame)
        return frame


class LiveDemoWindow:
    def __init__(self, *, policy_name: str, identity, artifact_dir: Path, max_player_moves: int,
                 run_worker, demo_seed: int = 20261103, auto_smoke: bool = False,
                 session_limits: dict | None = None, close_on_finish: bool = False):
        self.root = tk.Tk()
        self.root.title("Atari VideoChess — live policy demonstration")
        self.root.geometry("1120x700")
        self.root.minsize(760, 480)
        self.events: queue.Queue = queue.Queue()
        self.frame_lock = threading.Lock()
        self.latest_frame_event = None
        self.stop_event = threading.Event()
        self.worker = None
        self.run_worker = run_worker
        self.policy_name = policy_name
        self.identity = identity
        self.artifact_dir = artifact_dir
        self.max_player_moves = max_player_moves
        self.demo_seed = demo_seed
        self.auto_smoke = auto_smoke
        self.close_on_finish = close_on_finish
        self.session_limits = dict(session_limits or {})
        self.frames: list[dict] = []
        self.move_rows: dict[int, dict[str, object]] = {}
        self.verified_turns = 0
        self.replay_test = None
        self.gui_checks_ok = False
        self.trace_path = None
        self.finished_status = None
        self.session_state = DemoSessionState(required_player_moves=max_player_moves if auto_smoke else None)
        self.exit_code = 1 if auto_smoke else 0
        self._smoke_started = False
        self._worker_terminal_seen = False
        self._worker_exit_grace = False
        self.smoke_resize_checked = False
        self.layout_check = None
        self.replay_index = 0
        self.latest_rgb = None
        self.latest_frame_no = None
        self.latest_photo = None
        self.finished = False
        self.root.protocol("WM_DELETE_WINDOW", self.request_close)
        self.root.bind_all("<Left>", self.replay_back)
        self.root.bind_all("<Right>", self.replay_forward)
        self._layout()
        self.root.after(40, self.poll)

    def _layout(self):
        self.root.configure(background="#101723")
        self.root.geometry("1300x850")
        self.root.minsize(980, 640)
        header = ttk.Frame(self.root, padding=(16, 10, 16, 4))
        header.pack(fill=tk.X)
        header.grid_columnconfigure(0, weight=1)
        ttk.Label(header, text="ATARI VIDEOCHESS  |  LIVE POLICY", font=("TkDefaultFont", 13, "bold")).grid(
            row=0, column=0, sticky="w")
        ttk.Label(header, text="Actual ALE RGB · moves shown after verification").grid(
            row=1, column=0, sticky="w")
        ttk.Button(header, text="Model / session details", command=self.show_details).grid(
            row=0, column=1, rowspan=2, sticky="e", padx=(8, 0))

        body = ttk.Frame(self.root, padding=(12, 4, 12, 6))
        body.pack(fill=tk.BOTH, expand=True)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, minsize=430, weight=0)
        body.grid_rowconfigure(0, weight=1)
        video = ttk.Frame(body, padding=4)
        panel = ttk.Frame(body, padding=12, width=430)
        self.side_panel = panel
        panel.grid_propagate(False)
        video.grid(row=0, column=0, sticky="nsew")
        panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        panel.grid_columnconfigure(0, weight=1, minsize=400)
        panel.grid_rowconfigure(6, weight=1)
        self.canvas = tk.Canvas(video, background="#111111", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda _event: self.render_frame())
        self.canvas.bind("<Left>", self.replay_back)
        self.canvas.bind("<Right>", self.replay_forward)

        family_label = ("Double DQN · Q-only" if self.identity.policy_type == "double_dqn_q_only"
                        else "M4-A · behavior cloning" if self.identity.policy_type == "behavior_cloning"
                        else self.identity.policy_type)
        policy_display = "Double DQN · Q-only" if self.identity.policy_type == "double_dqn_q_only" else family_label
        self.policy_label = ttk.Label(panel, text=policy_display,
                                      justify=tk.LEFT, wraplength=390, font=("TkDefaultFont", 8))
        self.policy_label.grid(row=0, column=0, sticky="ew", pady=1)
        checkpoint_sha = self.identity.checkpoint_sha256 or "not recorded"
        display_sha = (f"{checkpoint_sha[:12]}…{checkpoint_sha[-8:]}" if len(checkpoint_sha) == 64
                       else checkpoint_sha)
        self.checkpoint_label = ttk.Label(panel,
            text=f"SHA {display_sha} · seed {self.identity.training_seed if self.identity.training_seed is not None else '—'} · "
                 f"{self.identity.valid_decisions if self.identity.valid_decisions is not None else '—'} decisions",
            justify=tk.LEFT, wraplength=390, font=("TkDefaultFont", 8))
        self.checkpoint_label.grid(row=1, column=0, sticky="ew", pady=1)
        self.turn_label = ttk.Label(panel, text="White · awaiting verified reset", wraplength=390,
                                    font=("TkDefaultFont", 8))
        self.turn_label.grid(row=2, column=0, sticky="ew", pady=1)
        self.status = ttk.Label(panel, text="Starting ALE…", wraplength=390,
                                justify=tk.LEFT, font=("TkDefaultFont", 9))
        self.status.grid(row=3, column=0, sticky="ew", pady=2)
        if self.session_limits:
            limit_text = (f"Cap {self.session_limits.get('max_player_moves')} moves · "
                f"{self.session_limits.get('max_wall_seconds')} s · ALE {self.session_limits.get('ale_episode_frame_cap')} frames · "
                "truncation incomplete")
            self.limits_label = ttk.Label(panel, text=limit_text, wraplength=390, justify=tk.LEFT,
                                          font=("TkDefaultFont", 8))
            self.limits_label.grid(row=4, column=0, sticky="ew", pady=2)
        ttk.Label(panel, text="VERIFIED MOVE HISTORY", font=("TkDefaultFont", 9, "bold")).grid(
            row=5, column=0, sticky="w", pady=(3, 1))
        scorecard = ttk.Frame(panel)
        scorecard.grid(row=6, column=0, sticky="nsew")
        scorecard.grid_columnconfigure(0, weight=1)
        scorecard.grid_rowconfigure(0, weight=1)
        self.move_table = ttk.Treeview(scorecard, columns=("number", "white", "black"), show="headings",
                                       selectmode="none", height=7)
        self.move_table.bind("<Left>", self.replay_back)
        self.move_table.bind("<Right>", self.replay_forward)
        for column, title, width, stretch in (("number", "#", 45, False),
                ("white", "WHITE · AGENT", 145, True), ("black", "BLACK · ATARI", 145, True)):
            self.move_table.heading(column, text=title)
            self.move_table.column(column, width=width, minwidth=width, stretch=stretch, anchor=tk.CENTER)
        self.move_table.tag_configure("even", background="#e9eef5")
        self.move_table.tag_configure("odd", background="#f7f9fc")
        self.move_table.tag_configure("pending", background="#fff0c2")
        self.move_table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(scorecard, orient=tk.VERTICAL, command=self.move_table.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.move_table.configure(yscrollcommand=scrollbar.set)
        self.replay_label = ttk.Label(panel, text="Replay after stop · ←/→ or buttons", wraplength=200,
                                      font=("TkDefaultFont", 8))
        self.replay_label.grid(row=7, column=0, sticky="w", pady=(1, 2))
        self.trace_status = ttk.Label(panel, text="Trace: pending", wraplength=200,
                                      justify=tk.LEFT, font=("TkDefaultFont", 8))
        self.trace_status.grid(row=7, column=0, sticky="e", pady=(1, 2))
        buttons = ttk.Frame(panel)
        buttons.grid(row=8, column=0, sticky="ew", pady=2)
        self.back_button = ttk.Button(buttons, text="← Previous", command=self.step_back, state=tk.DISABLED)
        self.forward_button = ttk.Button(buttons, text="Next →", command=self.step_forward, state=tk.DISABLED)
        self.back_button.pack(side=tk.LEFT, padx=(0, 5))
        self.forward_button.pack(side=tk.LEFT)
        self.footer = ttk.Label(self.root,
            text=demo_footer_text(self.demo_seed, self.identity.training_seed, self.max_player_moves),
            anchor="w")
        self.footer.pack(fill=tk.X, padx=14, pady=(0, 8))
        self.root.bind_all("<F11>", self.toggle_fullscreen)
        self.root.bind_all("<Escape>", self.leave_fullscreen)

    def publish(self, event):
        if event.get("event") == "frame":
            # Coalesce high-rate emulator frames; the GUI renders only the newest.
            with self.frame_lock:
                self.latest_frame_event = event
        else:
            self.events.put(event)

    def refresh_move_table(self):
        for item in self.move_table.get_children():
            self.move_table.delete(item)
        for number in sorted(self.move_rows):
            row = self.move_rows[number]
            white_pending = bool(row.get("white_pending", row.get("pending", False)))
            black_pending = bool(row.get("black_pending", False))
            white = str(row.get("white") or "—") + (" ?" if white_pending else "")
            black = str(row.get("black") or "—")
            pending = (white_pending or black_pending or bool(row.get("white_unverified"))
                       or bool(row.get("black_unverified")))
            self.move_table.insert("", tk.END, values=(f"{number}.", white, black),
                                   tags=("pending" if pending else ("even" if number % 2 == 0 else "odd"),))
        children = self.move_table.get_children()
        if children:
            self.move_table.see(children[-1])

    def show_details(self):
        details = (
            f"Policy: {self.policy_name}\n"
            f"Family: {self.identity.policy_type}\n"
            f"Checkpoint SHA-256: {self.identity.checkpoint_sha256}\n"
            f"Model training seed: {self.identity.training_seed}\n"
            f"Training decisions: {self.identity.valid_decisions}\n"
            f"Atari reset seed: {self.demo_seed}\n\n"
            f"Session limits: {self.session_limits}\n"
            "ALE truncation is incomplete and is not a chess result."
        )
        dialog = tk.Toplevel(self.root)
        dialog.title("Model and session identity")
        dialog.geometry("620x360")
        dialog.minsize(480, 280)
        content = ttk.Frame(dialog, padding=12)
        content.pack(fill=tk.BOTH, expand=True)
        view = tk.Text(content, wrap=tk.WORD, height=14, state=tk.NORMAL)
        view.insert(tk.END, details)
        view.configure(state=tk.DISABLED)
        scroll = ttk.Scrollbar(content, orient=tk.VERTICAL, command=view.yview)
        view.configure(yscrollcommand=scroll.set)
        view.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(anchor="e", padx=12, pady=(0, 10))
        return "break"

    def toggle_fullscreen(self, _event=None):
        self.root.attributes("-fullscreen", not bool(self.root.attributes("-fullscreen")))
        return "break"

    def leave_fullscreen(self, _event=None):
        self.root.attributes("-fullscreen", False)
        return "break"

    def record_replay(self, event):
        rgb = event.get("rgb")
        if rgb is None:
            return
        frame_no = event.get("frame_number")
        kind = event.get("event")
        if kind == "reset_verified":
            label = "Reset verified"
        elif kind == "player_move_verified":
            label = f"White {event.get('player_san', 'move')} verified"
        elif kind == "player_candidate_verified":
            label = f"White {event.get('player_san', 'move')} candidate · transition verified"
        elif kind == "verified_turn":
            label = f"Atari {event.get('opponent_san', 'reply')} verified"
        elif kind == "ale_terminal":
            terminal = event.get("terminal_sequence_verification")
            if isinstance(terminal, dict) and terminal.get("verified") is True:
                label = f"ALE terminal · {terminal.get('ale_reward', 'result')} · no board snapshot"
            else:
                label = "ALE terminal · no board snapshot"
        else:
            label = str(kind or "verified state")
        if self.frames and self.frames[-1]["frame_number"] == frame_no:
            self.frames[-1] = {"frame_number": frame_no, "rgb": np.array(rgb, copy=True),
                               "fen": event.get("fen"), "label": label}
        else:
            self.frames.append({"frame_number": frame_no, "rgb": np.array(rgb, copy=True),
                                "fen": event.get("fen"), "label": label})
        self.replay_index = len(self.frames) - 1

    def finalize_pending_rows(self):
        """Label actions that never received RGB confirmation before session end."""
        rows = getattr(self, "move_rows", None)
        if not isinstance(rows, dict):
            return
        changed = False
        for row in rows.values():
            if row.get("white_pending", row.get("pending", False)):
                row["white"] = f"{row.get('white') or 'Move'} (unverified)"
                row["white_pending"] = False
                row["white_unverified"] = True
                row["pending"] = False
                changed = True
            if row.get("black_pending"):
                row["black"] = "unverified"
                row["black_pending"] = False
                row["black_unverified"] = True
                changed = True
        if changed and hasattr(self, "move_table"):
            self.refresh_move_table()

    def handle_event(self, event):
        kind = event.get("event")
        if kind == "frame":
            self.latest_rgb = event["rgb"]
            self.latest_frame_no = event["frame_number"]
            self.render_frame()
        elif kind == "reset_verified":
            self.record_replay(event)
            self.turn_label.configure(text="Turn: White · reset RGB verified")
            self.status.configure(text=f"Ready · ALE frame {event['frame_number']}")
            self.render_frame(event["rgb"], event["frame_number"])
        elif kind == "move_selected":
            self.turn_label.configure(text="Turn: White · action pending RGB confirmation")
            self.status.configure(text=f"Agent selected {event['san']} ({event['uci']}); Atari confirmation pending.")
            self.move_rows[int(event["turn"])] = {
                "white": event["san"], "black": "—", "white_pending": True,
                "black_pending": False, "white_verified": False,
            }
            self.refresh_move_table()
        elif kind == "player_move_verified":
            self.record_replay(event)
            turn = int(event["turn"])
            row = self.move_rows.setdefault(turn, {"white": event["player_san"], "black": "—"})
            row.update({"white": f"{event['player_san']} ✓", "black": "Atari thinking…",
                        "white_pending": False, "black_pending": True, "white_verified": True,
                        "pending": False})
            self.refresh_move_table()
            self.turn_label.configure(text=f"Turn {turn} · White move verified; Atari reply pending")
            self.status.configure(text=f"White {event['player_san']} verified from RGB; waiting for Atari.")
        elif kind == "verified_turn":
            self.session_state.apply(event)
            if (not event.get("player_move_verified_earlier")
                    and event.get("player_candidate_rgb") is not None):
                self.record_replay({
                    "event": "player_candidate_verified",
                    "player_san": event.get("player_san"),
                    "frame_number": event.get("player_candidate_frame_number"),
                    "fen": event.get("player_candidate_fen"),
                    "rgb": event.get("player_candidate_rgb"),
                })
            self.record_replay(event)
            self.verified_turns += 1
            self.move_rows[int(event["turn"])] = {
                "white": f"{event['player_san']} ✓", "black": f"{event['opponent_san']} ✓",
                "white_pending": False, "black_pending": False, "white_verified": True,
                "black_verified": True, "pending": False,
            }
            self.refresh_move_table()
            self.turn_label.configure(text="Turn: White · Atari reply verified")
            self.status.configure(text=f"Turn {event['turn']} · both moves RGB verified")
            self.render_frame(event["rgb"], event["frame_number"])
        elif kind == "episode_finished":
            self.session_state.apply(event)
            terminal_sequence = event.get("terminal_sequence_verification")
            if isinstance(terminal_sequence, dict) and terminal_sequence.get("verified") is True:
                turn = terminal_sequence.get("turn")
                if isinstance(turn, int):
                    row = dict(self.move_rows.get(turn, {}))
                    player_ram_verified = int(terminal_sequence.get("terminal_ram_player_move_count", 0)) > 0
                    reply_ram_verified = int(terminal_sequence.get("terminal_ram_atari_reply_count", 0)) > 0
                    player_san = terminal_sequence.get("player_move_san", "Move")
                    reply_san = terminal_sequence.get("atari_reply_san", "Reply")
                    row.update({
                        "white": (
                            f"{player_san} ✓ · ALE terminal RAM"
                            if player_ram_verified
                            else row.get("white") or f"{player_san} ✓ · RGB"
                        ),
                        "black": (
                            f"{reply_san} ✓ · ALE terminal RAM"
                            if reply_ram_verified
                            else row.get("black") or f"{reply_san} ✓ · RGB"
                        ),
                        "white_pending": False,
                        "black_pending": False,
                        "white_verified": not player_ram_verified,
                        "black_verified": not reply_ram_verified,
                        "white_terminal_ram_verified": player_ram_verified,
                        "black_terminal_ram_verified": reply_ram_verified,
                        "pending": False,
                    })
                    self.move_rows[turn] = row
                    self.refresh_move_table()
                if event.get("rgb") is not None:
                    self.record_replay({
                        "event": "ale_terminal",
                        "frame_number": event.get("frame_number"),
                        "rgb": event.get("rgb"),
                        "terminal_sequence_verification": terminal_sequence,
                    })
            self.finalize_pending_rows()
            self.finished = True
            self.finished_status = event.get("status")
            term = event.get("terminal")
            term = term if isinstance(term, dict) else {}
            if term.get("ale_terminated"):
                white_result = term.get("white_result_from_reward")
                result = f"ALE result: {white_result or 'reward unavailable'}"
                if isinstance(terminal_sequence, dict) and terminal_sequence.get("verified") is True:
                    result += " · checkmate verified from terminal ALE RAM"
            elif term.get("ale_truncated"):
                result = "ALE episode truncated; chess result is incomplete"
            else:
                result = "Session incomplete; no ALE game result observed"
            self.status.configure(text=f"{result}. {self.session_state.display_status}")
            self.turn_label.configure(text=f"Session status: {event.get('status')} • frame {event.get('frame_number', 'unknown')}")
            self.back_button.configure(state=tk.NORMAL if len(self.frames) > 1 else tk.DISABLED)
            self.forward_button.configure(state=tk.NORMAL if len(self.frames) > 1 else tk.DISABLED)
            self.replay_label.configure(text=f"Replay {len(self.frames)} ALE states · ←/→ or buttons")
            if event.get("rgb") is not None:
                self.render_frame(event["rgb"], event.get("frame_number"))
        elif kind == "trace_saved":
            self.session_state.apply(event)
            self.trace_path = event["path"]
            self.trace_status.configure(text="Trace: saved")
            self._maybe_start_smoke_replay()
        elif kind == "session_summary":
            self.session_state.apply(event)
            self.status.configure(text=self.session_state.display_status)
        elif kind == "session_summary_error":
            self.trace_status.configure(text="Summary: write failed")
            self.status.configure(
                text=f"{self.session_state.display_status} • summary write failed ({event.get('error_type')})"
            )
        elif kind == "trace_save_error":
            self.session_state.apply(event)
            self.trace_status.configure(text="Trace: write failed")
            self.status.configure(text=self.session_state.display_status)
        elif kind == "worker_error":
            self.session_state.apply(event)
            self.finalize_pending_rows()
            self.finished = True
            self.finished_status = "worker_failed"
            self.exit_code = 1
            self.status.configure(text=self.session_state.display_status)
            self.back_button.configure(state=tk.NORMAL if len(self.frames) > 1 else tk.DISABLED)
            self.forward_button.configure(state=tk.NORMAL if len(self.frames) > 1 else tk.DISABLED)
            if self.auto_smoke:
                self.closing = True
        elif kind == "worker_finished":
            self._worker_terminal_seen = True
            self.session_state.apply(event)
            if event.get("status") != "completed":
                self.exit_code = 1
                if not self.session_state.worker_error:
                    self.session_state.worker_error_type = "WorkerLifecycleError"
                    self.session_state.worker_error = event.get("reason") or (
                        "worker execution did not complete"
                    )
                self.finished = True
                self.status.configure(text=self.session_state.display_status)
                if getattr(self, "close_on_finish", False):
                    self.closing = True
            elif self.auto_smoke and not self.session_state.smoke_ok:
                # The worker can finish and persist a truthful incomplete trace.
                # Keep episode status separate from worker lifecycle and still
                # allow captured verified states to be replayed.
                self.exit_code = 1
                self.finished = True
                self.status.configure(text=self.session_state.display_status)
            elif getattr(self, "close_on_finish", False) and not self.auto_smoke:
                self.closing = True
            self._maybe_start_smoke_replay()

    def _maybe_start_smoke_replay(self):
        if not self.auto_smoke or self._smoke_started or not self._worker_terminal_seen:
            return
        self._smoke_started = True
        if len(self.frames) > 1:
            self.closing = False
            self.root.geometry("1100x680")
            self.root.after(150, self._smoke_left)
        else:
            self.exit_code = 1
            self.closing = True

    def render_frame(self, rgb=None, frame_no=None):
        if rgb is not None:
            self.latest_rgb, self.latest_frame_no = rgb, frame_no
        if self.latest_rgb is None or not self.canvas.winfo_exists():
            return
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if width < 10 or height < 10:
            return
        src = self.latest_rgb
        scale = min(width / src.shape[1], height / src.shape[0])
        out_w, out_h = max(1, int(src.shape[1] * scale)), max(1, int(src.shape[0] * scale))
        xs = np.minimum((np.arange(out_w) / scale).astype(int), src.shape[1] - 1)
        ys = np.minimum((np.arange(out_h) / scale).astype(int), src.shape[0] - 1)
        resized = np.ascontiguousarray(src[ys][:, xs, :3])
        payload = f"P6\n{out_w} {out_h}\n255\n".encode("ascii") + resized.tobytes()
        self.latest_photo = tk.PhotoImage(data=payload, format="PPM")
        self.canvas.delete("all")
        x, y = (width - out_w) // 2, (height - out_h) // 2
        self.canvas.create_image(x, y, anchor=tk.NW, image=self.latest_photo)
        self.canvas.create_text(8, 8, anchor=tk.NW, fill="white", text=f"ALE frame {self.latest_frame_no}",
                                font=("TkDefaultFont", 10, "bold"))

    def poll(self):
        try:
            while True:
                self.handle_event(self.events.get_nowait())
        except queue.Empty:
            pass
        with self.frame_lock:
            latest_frame, self.latest_frame_event = self.latest_frame_event, None
        if latest_frame is not None:
            self.handle_event(latest_frame)
        if self.worker and not self.worker.is_alive() and not self._worker_terminal_seen:
            if not self._worker_exit_grace:
                # A worker may publish its final lifecycle events just after
                # this poll drained the queue. Give that queue one final pass
                # before classifying a silent thread exit as unexpected.
                self._worker_exit_grace = True
                self.root.after(10, self.poll)
                return
            self._worker_terminal_seen = True
            self.finished = True
            self.session_state.worker_status = "failed"
            self.session_state.worker_error_type = "UnexpectedWorkerExit"
            self.session_state.worker_error = "worker exited without a terminal lifecycle event"
            self.finished_status = "worker_failed"
            self.exit_code = 1
            self.status.configure(text=self.session_state.display_status)
            if self.auto_smoke:
                self.closing = True
        if getattr(self, "closing", False) and (self.worker is None or not self.worker.is_alive()):
            if self.auto_smoke:
                from .common import write
                record = {
                    "window_created": True, "policy_name": self.policy_name,
                    "policy_type": self.identity.policy_type,
                    "demo_seed": self.demo_seed,
                    "model_training_seed": self.identity.training_seed,
                    "footer_text": demo_footer_text(self.demo_seed, self.identity.training_seed,
                                                     self.max_player_moves),
                    "checkpoint_sha256": self.identity.checkpoint_sha256,
                    "captured_verified_state_count": len(self.frames),
                    "verified_atari_turns_displayed": self.verified_turns,
                    "verified_player_moves_displayed": self.session_state.verified_player_moves_displayed,
                    "verified_atari_replies_displayed": self.session_state.verified_atari_replies_displayed,
                    "terminal_ram_verified_player_moves_displayed": self.session_state.terminal_ram_verified_player_moves_displayed,
                    "terminal_ram_verified_atari_replies_displayed": self.session_state.terminal_ram_verified_atari_replies_displayed,
                    "pending_player_actions": sum(
                        bool(row.get("white_pending", row.get("pending", False))
                             or row.get("white_unverified"))
                        for row in getattr(self, "move_rows", {}).values()),
                    "requested_player_moves": self.max_player_moves,
                    "episode_status": self.session_state.episode_status,
                    "episode_terminal": self.session_state.episode_terminal,
                    "replay_test": self.replay_test, "resized_1100x680": self.smoke_resize_checked,
                    "layout_check": self.layout_check,
                    "gui_checks_ok": getattr(self, "gui_checks_ok", False),
                    "finished_status": self.finished_status, "trace_path": self.trace_path,
                    "replay_available": self.session_state.replay_available and len(self.frames) > 1,
                    "session_state": vars(self.session_state), "exit_code": self.exit_code,
                    "session_limits": self.session_limits,
                }
                try:
                    write(self.artifact_dir / "demo-verification.json", record)
                except Exception as exc:
                    self.exit_code = 1
                    print(f"Could not persist smoke verification: {type(exc).__name__}: {exc}")
            self.root.destroy()
            return
        self.root.after(40, self.poll)

    def step_back(self):
        if self.finished and self.frames:
            self.replay_index = max(0, self.replay_index - 1)
            self.show_replay()

    def step_forward(self):
        if self.finished and self.frames:
            self.replay_index = min(len(self.frames) - 1, self.replay_index + 1)
            self.show_replay()

    def show_replay(self):
        item = self.frames[self.replay_index]
        self.render_frame(item["rgb"], item["frame_number"])
        self.replay_label.configure(text=f"Replay {self.replay_index + 1}/{len(self.frames)} • {item['label']} • frame {item['frame_number']}")
        if item.get("fen"):
            self.turn_label.configure(text=f"Replay RGB-verified state · {item['label']} · {item['fen']}")

    def replay_back(self, _event=None):
        self.step_back(); return "break"

    def replay_forward(self, _event=None):
        self.step_forward(); return "break"

    def request_close(self):
        if self.worker is not None and self.worker.is_alive():
            self.closing = True
            self.stop_event.set()
            self.status.configure(text="Stopping at the next bounded ALE step…")
        else:
            self.root.destroy()

    def _smoke_left(self):
        before = self.replay_index
        self.canvas.focus_force()
        self.root.update_idletasks()
        self.canvas.event_generate("<Left>", when="tail")
        self.root.after(100, lambda: self._smoke_right(before))

    def _smoke_right(self, before):
        left = self.replay_index
        self.canvas.event_generate("<Right>", when="tail")
        self.root.after(100, lambda: self._smoke_finish(before, left))

    def _smoke_finish(self, before, left):
        self.replay_test = {"start_index": before, "after_left": left,
                            "after_right": self.replay_index,
                            "left_moved_backward": left < before,
                            "right_moved_forward": self.replay_index > left}
        self.root.update_idletasks()
        label_widgets = [self.policy_label, self.checkpoint_label, self.turn_label, self.status,
                         self.replay_label, self.trace_status]
        if hasattr(self, "limits_label"):
            label_widgets.append(self.limits_label)
        clipped = [widget.winfo_class() for widget in label_widgets
                   if widget.winfo_height() + 1 < widget.winfo_reqheight()]
        board_right = self.canvas.winfo_rootx() + self.canvas.winfo_width()
        panel_left = self.side_panel.winfo_rootx()
        table_clipped = self.move_table.winfo_width() + 1 < self.move_table.winfo_reqwidth()
        self.layout_check = {"window_width": self.root.winfo_width(),
            "window_height": self.root.winfo_height(), "board_area_width": self.canvas.winfo_width(),
            "side_panel_width": self.side_panel.winfo_width(), "move_table_width": self.move_table.winfo_width(),
            "side_panel_does_not_overlap_board": panel_left >= board_right,
            "clipped_labels": clipped, "move_table_clipped": table_clipped}
        self.layout_check["ok"] = (self.layout_check["side_panel_does_not_overlap_board"]
                                    and not clipped and not table_clipped)
        self.gui_checks_ok = (self.replay_test["left_moved_backward"]
                              and self.replay_test["right_moved_forward"]
                              and self.layout_check["ok"])
        self.exit_code = 0 if self.session_state.smoke_ok and self.gui_checks_ok else 1
        if self.exit_code:
            self.status.configure(text=f"GUI smoke failed: replay={self.replay_test}; layout={self.layout_check}")
        self.smoke_resize_checked = self.root.winfo_width() == 1100 and self.root.winfo_height() == 680
        self.closing = True
        self.stop_event.set()
        self.root.after(100, self.poll)

    def start(self):
        self.worker = threading.Thread(target=self.run_worker, args=(self,), daemon=True,
                                       name="videochess-live-episode")
        self.worker.start()
        self.root.mainloop()
        return self.exit_code
