"""Cycle state, traceability and snapshot coordination."""
from datetime import datetime, timezone
from process.sequence_engine import SequenceEngine, SequenceStatus

class CycleManager:
    def __init__(self, engine: SequenceEngine, database):
        self.engine, self.database = engine, database
        self.cycle_id = None
        self.started_at = None
        self.events = []

    def start(self, profile_name, initially_present=None):
        result = self.engine.start(initially_present)
        if result.status == SequenceStatus.RUNNING:
            self.started_at = datetime.now(timezone.utc)
            self.cycle_id = self.database.begin_cycle(profile_name, self.started_at, self.engine.expected_sequence)
        return result

    def event(self, event):
        result = self.engine.handle_event(event)
        self.events.append(event)
        if self.cycle_id: self.database.add_event(self.cycle_id, event)
        return result

    def finish(self, result, image_path=None):
        if self.cycle_id:
            self.database.finish_cycle(self.cycle_id, result.status.value, result.reason, self.engine.detected_sequence, image_path)
