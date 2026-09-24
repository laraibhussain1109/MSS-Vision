from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class ProcessEvent:
    roi_id: str
    roi_name: str
    event_type: str = "INSERTED"
    occupancy: float = 0.0
    confidence: float = 0.0
    timestamp_ms: int = 0

    @property
    def iso_time(self):
        return datetime.fromtimestamp(self.timestamp_ms / 1000, tz=timezone.utc).isoformat()
