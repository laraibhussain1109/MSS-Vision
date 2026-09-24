"""Serializable region-of-interest definitions."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

class ROIShape(str, Enum):
    RECTANGLE = "rectangle"
    POLYGON = "polygon"

class ROIState(str, Enum):
    ABSENT = "ABSENT"
    PRESENT = "PRESENT"
    UNKNOWN = "UNKNOWN"

@dataclass
class HSVSettings:
    h_min: int = 90
    h_max: int = 135
    s_min: int = 100
    s_max: int = 255
    v_min: int = 60
    v_max: int = 255
    erode: int = 0
    dilate: int = 0
    open_kernel: int = 3
    close_kernel: int = 5

@dataclass
class ROIConfig:
    id: str
    name: str
    display_name: str
    shape: ROIShape = ROIShape.RECTANGLE
    points: list[list[float]] = field(default_factory=list)  # normalized frame coordinates
    roi_type: str = "Clip"
    detector: str = "hsv"
    sequence_enabled: bool = True
    sequence_position: int = 1
    required: bool = True
    enabled: bool = True
    allow_removal: bool = False
    occupancy_threshold: float = 0.08
    presence_ms: int = 300
    absence_ms: int = 700
    hsv: HSVSettings = field(default_factory=HSVSettings)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ROIConfig":
        copy = dict(data)
        copy["shape"] = ROIShape(copy.get("shape", "rectangle"))
        copy["hsv"] = HSVSettings(**copy.get("hsv", {}))
        return cls(**copy)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["shape"] = self.shape.value
        return result

    def pixel_polygon(self, width: int, height: int):
        import numpy as np
        return np.array([[round(x * width), round(y * height)] for x, y in self.points], dtype=np.int32)
