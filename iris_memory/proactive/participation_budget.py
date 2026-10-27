"""Hard limits for accepted unsolicited reply attempts, independent of LLM output."""

import math
import time


class ParticipationBudget:
    def __init__(self):
        self.entries: dict[str, list[float]] = {}

    def load(self, data):
        if not isinstance(data, dict):
            return
        for key, values in list(data.items())[:1000]:
            if isinstance(key, str) and isinstance(values, list):
                self.entries[key] = [
                    float(t)
                    for t in values[-100:]
                    if type(t) in (int, float) and math.isfinite(t)
                ]

    def check(self, group, *, cooldown=90, window=900, limit=3, now=None):
        now = time.time() if now is None else now
        # Drop stale groups too, so old inactive groups cannot exhaust capacity.
        self.entries = {
            key: [t for t in values if now - t < 3600]
            for key, values in self.entries.items()
            if any(now - t < 3600 for t in values)
        }
        values = [
            t for t in self.entries.get(group, []) if now - t < max(window, cooldown)
        ]
        if values:
            self.entries[group] = values
        else:
            self.entries.pop(group, None)
        if group not in self.entries and len(self.entries) >= 1000:
            return "state_capacity"
        if values and now - max(values) < cooldown:
            return "cooldown"
        if sum(now - t < window for t in values) >= limit:
            return "rolling_limit"
        return "allowed"

    def reserve(self, group, now=None):
        self.entries.setdefault(group, []).append(time.time() if now is None else now)
        self.entries[group] = self.entries[group][-100:]
