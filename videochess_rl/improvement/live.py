"""Resizable local Tk viewer for real ALE frames and RGB-verified chess moves."""
from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
from pathlib import Path

import numpy as np

from videochess_rl.environment import ALEConfig, VideoChessEnv


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
                 run_worker, auto_smoke: bool = False):
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
        self.auto_smoke = auto_smoke
        self.frames: list[dict] = []
        self.verified_turns = 0
        self.replay_test = None
        self.trace_path = None
        self.finished_status = None
        self.smoke_resize_checked = False
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
        split = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        split.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        video = ttk.Frame(split, padding=4)
        panel = ttk.Frame(split, padding=8, width=330)
        split.add(video, weight=4)
        split.add(panel, weight=2)
        self.canvas = tk.Canvas(video, background="#111111", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda _event: self.render_frame())

        heading = ttk.Label(panel, text="LIVE ATARI VIDEOCHESS", font=("TkDefaultFont", 13, "bold"))
        heading.pack(anchor="w", pady=(0, 8))
        self.policy_label = ttk.Label(panel, text=f"Policy: {self.policy_name}\nFamily: {self.identity.policy_type}",
                                      justify=tk.LEFT, wraplength=310)
        self.policy_label.pack(anchor="w", fill=tk.X, pady=3)
        self.checkpoint_label = ttk.Label(panel,
            text=f"Checkpoint SHA-256\n{self.identity.checkpoint_sha256}\n"
                 f"Training decisions: {self.identity.valid_decisions if self.identity.valid_decisions is not None else 'not applicable'}",
            justify=tk.LEFT, wraplength=310, font=("TkFixedFont", 9))
        self.checkpoint_label.pack(anchor="w", fill=tk.X, pady=3)
        self.turn_label = ttk.Label(panel, text="Side to move: awaiting verified Atari reset", wraplength=310)
        self.turn_label.pack(anchor="w", fill=tk.X, pady=3)
        self.status = ttk.Label(panel, text="Initializing actual ALE/VideoChess-v5…", wraplength=310,
                                justify=tk.LEFT)
        self.status.pack(anchor="w", fill=tk.X, pady=6)
        ttk.Label(panel, text="Verified move history", font=("TkDefaultFont", 11, "bold")).pack(anchor="w", pady=(8, 2))
        history_box = ttk.Frame(panel)
        history_box.pack(fill=tk.BOTH, expand=True)
        self.history = tk.Text(history_box, width=38, height=18, wrap=tk.WORD, state=tk.DISABLED,
                               font=("TkFixedFont", 10))
        scrollbar = ttk.Scrollbar(history_box, orient=tk.VERTICAL, command=self.history.yview)
        self.history.configure(yscrollcommand=scrollbar.set)
        self.history.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        buttons = ttk.Frame(panel)
        buttons.pack(fill=tk.X, pady=(8, 2))
        self.back_button = ttk.Button(buttons, text="← Replay", command=self.step_back, state=tk.DISABLED)
        self.forward_button = ttk.Button(buttons, text="Replay →", command=self.step_forward, state=tk.DISABLED)
        self.back_button.pack(side=tk.LEFT, padx=(0, 5))
        self.forward_button.pack(side=tk.LEFT)
        self.replay_label = ttk.Label(panel, text="Replay is available after the session stops.", wraplength=310)
        self.replay_label.pack(anchor="w", fill=tk.X, pady=4)
        self.footer = ttk.Label(self.root, text=f"Actual ALE session • seed 20261103 • move cap {self.max_player_moves}",
                                anchor="w")
        self.footer.pack(fill=tk.X, padx=12, pady=(0, 8))
        self.root.update_idletasks()
        split.sashpos(0, max(420, self.root.winfo_width() - 365))

    def publish(self, event):
        if event.get("event") == "frame":
            # Coalesce high-rate emulator frames; the GUI renders only the newest.
            with self.frame_lock:
                self.latest_frame_event = event
        else:
            self.events.put(event)

    def append_history(self, text):
        self.history.configure(state=tk.NORMAL)
        self.history.insert(tk.END, text + "\n")
        self.history.see(tk.END)
        self.history.configure(state=tk.DISABLED)

    def record_replay(self, event):
        rgb = event.get("rgb")
        if rgb is None:
            return
        frame_no = event.get("frame_number")
        if self.frames and self.frames[-1]["frame_number"] == frame_no:
            self.frames[-1] = {"frame_number": frame_no, "rgb": np.array(rgb, copy=True),
                               "fen": event.get("fen"), "label": event.get("event")}
        else:
            self.frames.append({"frame_number": frame_no, "rgb": np.array(rgb, copy=True),
                                "fen": event.get("fen"), "label": event.get("event")})
        self.replay_index = len(self.frames) - 1

    def handle_event(self, event):
        kind = event.get("event")
        if kind == "frame":
            self.latest_rgb = event["rgb"]
            self.latest_frame_no = event["frame_number"]
            self.render_frame()
        elif kind == "reset_verified":
            self.record_replay(event)
            self.turn_label.configure(text="Side to move: White (RGB-verified standard reset)")
            self.status.configure(text=f"ALE reset verified at frame {event['frame_number']}; agent is ready.")
            self.render_frame(event["rgb"], event["frame_number"])
        elif kind == "move_selected":
            self.turn_label.configure(text="Side to move: White • selected action awaiting Atari verification")
            self.status.configure(text=f"Agent selected {event['san']} ({event['uci']}); Atari input and RGB confirmation in progress.")
        elif kind == "verified_turn":
            self.record_replay(event)
            self.verified_turns += 1
            self.append_history(f"{event['turn']:>2}. White  {event['player_san']} ({event['player_uci']})   ✓ RGB verified")
            self.append_history(f"    Black  {event['opponent_san']} ({event['opponent_uci']})   ✓ RGB verified")
            self.turn_label.configure(text="Side to move: White (verified opponent reply)")
            self.status.configure(text=f"Turn {event['turn']} complete; both moves confirmed against actual Atari RGB.")
            self.render_frame(event["rgb"], event["frame_number"])
        elif kind == "episode_finished":
            self.finished = True
            self.finished_status = event.get("status")
            term = event.get("terminal", {})
            result = "ALE game ended" if term.get("observed") else "Session incomplete; no terminal result observed"
            detail = event.get("failure") or term.get("runner_stop_reason") or event.get("status")
            self.status.configure(text=f"{result}. {detail or ''}")
            self.turn_label.configure(text=f"Session status: {event.get('status')} • frame {event['frame_number']}")
            self.back_button.configure(state=tk.NORMAL if len(self.frames) > 1 else tk.DISABLED)
            self.forward_button.configure(state=tk.NORMAL if len(self.frames) > 1 else tk.DISABLED)
            self.replay_label.configure(text=f"Replay {len(self.frames)} captured states; ←/→ keys step verified states.")
            if event.get("rgb") is not None:
                self.render_frame(event["rgb"], event.get("frame_number"))
        elif kind == "trace_saved":
            self.trace_path = event["path"]
            self.status.configure(text=f"Trace saved locally: {event['path']}")
            if self.auto_smoke:
                self.root.geometry("900x560")
                self.root.after(150, self._smoke_left)
        elif kind == "worker_error":
            self.finished = True
            self.status.configure(text=f"Session error: {event['error']}")
            self.back_button.configure(state=tk.NORMAL if len(self.frames) > 1 else tk.DISABLED)
            self.forward_button.configure(state=tk.NORMAL if len(self.frames) > 1 else tk.DISABLED)

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
        if self.worker and not self.worker.is_alive() and not self.finished:
            self.finished = True
            self.status.configure(text="Session stopped; trace may be available under the local artifact directory.")
        if getattr(self, "closing", False) and (self.worker is None or not self.worker.is_alive()):
            if self.auto_smoke:
                from .common import write
                write(self.artifact_dir / "demo-verification.json", {
                    "window_created": True, "policy_name": self.policy_name,
                    "policy_type": self.identity.policy_type,
                    "checkpoint_sha256": self.identity.checkpoint_sha256,
                    "captured_verified_state_count": len(self.frames),
                    "verified_atari_turns_displayed": self.verified_turns,
                    "replay_test": self.replay_test, "resized_900x560": self.smoke_resize_checked,
                    "finished_status": self.finished_status, "trace_path": self.trace_path,
                })
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
            self.turn_label.configure(text=f"Replay state (verified): {item['fen']}")

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
        self.root.event_generate("<Left>")
        self.root.after(100, lambda: self._smoke_right(before))

    def _smoke_right(self, before):
        left = self.replay_index
        self.root.event_generate("<Right>")
        self.root.after(100, lambda: self._smoke_finish(before, left))

    def _smoke_finish(self, before, left):
        self.replay_test = {"start_index": before, "after_left": left,
                            "after_right": self.replay_index,
                            "left_moved_backward": left < before,
                            "right_moved_forward": self.replay_index > left}
        self.smoke_resize_checked = self.root.winfo_width() == 900 and self.root.winfo_height() == 560
        self.closing = True
        self.stop_event.set()
        self.root.after(100, self.poll)

    def start(self):
        self.worker = threading.Thread(target=self.run_worker, args=(self,), daemon=True,
                                       name="videochess-live-episode")
        self.worker.start()
        self.root.mainloop()
