"""Run the repository suite excluding only the unavailable Stockfish readiness smoke."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


EXCLUDED = "test_m0_smoke.M0EnvironmentSmokeTests.test_stockfish_answers_uci_readiness_without_searching"


def flatten(suite: unittest.TestSuite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


# Mirror `PYTHONPATH=. python -m unittest discover -s tests`: put this clone's
# repository root before any editable install path in the existing interpreter.
sys.path.insert(0, str(Path.cwd()))
all_tests = list(unittest.defaultTestLoader.discover("tests"))
cases = [case for group in all_tests for case in flatten(group)]
matches = [case for case in cases if case.id() == EXCLUDED]
if len(matches) != 1:
    print(f"Expected exactly one excluded test {EXCLUDED!r}; found {len(matches)}", file=sys.stderr)
    raise SystemExit(2)

selected = [case for case in cases if case.id() != EXCLUDED]
print(f"Excluded exactly one unavailable test: {EXCLUDED}")
result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(selected))
raise SystemExit(0 if result.wasSuccessful() else 1)
