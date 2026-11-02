"""Improvement-only write guard; preserve the historical append operation."""
from videochess_rl.rl.replay import ReplayJournal


class SafeReplayJournal(ReplayJournal):
    def append(self,row):
        if not self._append_safe:
            raise ValueError('damaged journal tail; fork the verified checkpoint prefix before appending')
        try:
            return super().append(row)
        except BaseException:
            self._append_safe=False
            raise
