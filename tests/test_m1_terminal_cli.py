from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.run_m1_terminal_experiment import validate_output_paths


class TerminalExperimentOutputPathTests(unittest.TestCase):
    def test_new_trace_and_frame_paths_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            trace = Path(temporary) / "run" / "trace.json"

            self.assertEqual(validate_output_paths(trace), trace.parent / "frames")

    def test_existing_trace_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            trace = Path(temporary) / "trace.json"
            trace.write_text("preserve this trace")

            with self.assertRaisesRegex(FileExistsError, "Refusing to overwrite"):
                validate_output_paths(trace)

            self.assertEqual(trace.read_text(), "preserve this trace")

    def test_existing_frames_directory_is_not_reused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            trace = Path(temporary) / "trace.json"
            frames = trace.parent / "frames"
            frames.mkdir()
            prior_frame = frames / "reset.png"
            prior_frame.write_bytes(b"prior evidence")

            with self.assertRaisesRegex(FileExistsError, "Refusing to overwrite"):
                validate_output_paths(trace)

            self.assertEqual(prior_frame.read_bytes(), b"prior evidence")

    def test_broken_trace_symlink_is_not_treated_as_a_new_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            trace = directory / "trace.json"
            trace.symlink_to(directory / "missing-target.json")

            with self.assertRaisesRegex(FileExistsError, "Refusing to overwrite"):
                validate_output_paths(trace)


if __name__ == "__main__":
    unittest.main()
