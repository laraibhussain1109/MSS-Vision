"""Time-based candidate confirmation that never emits initialization events."""
from dataclasses import dataclass
from vision.roi import ROIState

@dataclass
class Transition:
    previous: ROIState
    current: ROIState
    timestamp_ms: int

class TemporalFilter:
    def __init__(self, presence_ms=300, absence_ms=700):
        self.presence_ms, self.absence_ms = presence_ms, absence_ms
        self.stable = ROIState.UNKNOWN
        self.candidate = ROIState.UNKNOWN
        self.candidate_since = 0
        self.baselined = False

    def update(self, candidate: ROIState, now_ms: int, occluded: bool = False):
        if occluded or candidate == ROIState.UNKNOWN:
            self.candidate = ROIState.UNKNOWN
            self.candidate_since = now_ms
            return None
        if candidate != self.candidate:
            self.candidate, self.candidate_since = candidate, now_ms
            return None
        delay = self.presence_ms if candidate == ROIState.PRESENT else self.absence_ms
        if now_ms - self.candidate_since < delay or candidate == self.stable:
            return None
        old = self.stable
        self.stable = candidate
        if not self.baselined:
            self.baselined = True
            return None
        return Transition(old, candidate, now_ms)

    def reset_baseline(self):
        self.stable = self.candidate = ROIState.UNKNOWN
        self.candidate_since = 0
        self.baselined = False
