"""Deterministic generic finite-state sequence validator."""
from dataclasses import dataclass
from enum import Enum
from process.event import ProcessEvent

class SequenceStatus(str, Enum):
    IDLE="IDLE"; RUNNING="RUNNING"; PASS="PASS"; NG="NG"

@dataclass
class SequenceResult:
    status: SequenceStatus
    reason: str = ""
    expected: str | None = None
    detected: str | None = None

class SequenceEngine:
    def __init__(self, expected_sequence: list[str], simultaneous_window_ms: int = 300):
        self.expected_sequence = list(expected_sequence)
        self.simultaneous_window_ms = simultaneous_window_ms
        self.reset()

    def reset(self):
        self.status = SequenceStatus.IDLE
        self.current_step = 0
        self.detected_sequence: list[str] = []
        self.last_event: ProcessEvent | None = None
        self.reason = ""

    def start(self, initially_present: set[str] | None = None):
        self.reset()
        invalid = set(initially_present or ()) & set(self.expected_sequence)
        if invalid:
            self.status = SequenceStatus.NG
            self.reason = "PROCESS START INVALID: already present: " + ", ".join(sorted(invalid))
            return SequenceResult(self.status, self.reason, self.expected, None)
        self.status = SequenceStatus.RUNNING
        return SequenceResult(self.status, expected=self.expected)

    @property
    def expected(self):
        return self.expected_sequence[self.current_step] if self.current_step < len(self.expected_sequence) else None

    def handle_event(self, event: ProcessEvent):
        if self.status != SequenceStatus.RUNNING:
            return SequenceResult(self.status, self.reason, self.expected, event.roi_id)
        expected = self.expected
        if self.last_event and event.roi_id != self.last_event.roi_id and event.timestamp_ms - self.last_event.timestamp_ms <= self.simultaneous_window_ms:
            self.status = SequenceStatus.NG
            self.reason = f"MULTIPLE INSERTIONS: {self.last_event.roi_name} and {event.roi_name} within {event.timestamp_ms-self.last_event.timestamp_ms} ms; sequence could not be verified"
        elif event.roi_id != expected:
            self.status = SequenceStatus.NG
            self.reason = f"WRONG SEQUENCE: expected {expected}, detected {event.roi_name}"
        else:
            self.detected_sequence.append(event.roi_id)
            self.current_step += 1
            if self.current_step == len(self.expected_sequence):
                self.status = SequenceStatus.PASS
        self.last_event = event
        return SequenceResult(self.status, self.reason, expected, event.roi_id)
