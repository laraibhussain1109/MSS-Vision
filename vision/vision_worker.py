"""Latest-frame vision worker: signals replace frame queues to prevent backlog."""
import time
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from vision.detectors.hsv_detector import HSVColorDetector
from vision.temporal_filter import TemporalFilter
from vision.roi import ROIState
from process.event import ProcessEvent

class VisionWorker(QObject):
    processed = pyqtSignal(object, object)
    insertion = pyqtSignal(object)
    def __init__(self, rois):
        super().__init__(); self.enabled=False; self.set_rois(rois)
    def set_rois(self, rois):
        self.rois=rois; self.filters={r.id:TemporalFilter(r.presence_ms,r.absence_ms) for r in rois}; self.detector=HSVColorDetector()
    @pyqtSlot(object)
    def process(self, frame):
        now=int(time.time()*1000); results={}
        for roi in self.rois:
            if not roi.enabled: continue
            d=self.detector.detect(frame,roi); transition=self.filters[roi.id].update(d.candidate,now)
            stable=self.filters[roi.id].stable
            results[roi.id]={"occupancy":d.occupancy,"confidence":d.confidence,"candidate":d.candidate.value,"stable":stable.value}
            if self.enabled and transition and transition.previous == ROIState.ABSENT and transition.current == ROIState.PRESENT:
                self.insertion.emit(ProcessEvent(roi.id,roi.display_name,"INSERTED",d.occupancy,d.confidence,now))
        self.processed.emit(frame,results)
