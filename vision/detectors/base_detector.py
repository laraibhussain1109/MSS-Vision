"""Detector extension contract (HSV today; template/AI later)."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np
from vision.roi import ROIState

@dataclass
class DetectionResult:
    candidate: ROIState
    occupancy: float
    confidence: float
    raw_mask: np.ndarray | None = None
    processed_mask: np.ndarray | None = None

class BaseDetector(ABC):
    @abstractmethod
    def detect(self, frame: np.ndarray, roi):
        raise NotImplementedError
