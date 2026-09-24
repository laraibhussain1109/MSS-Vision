"""OpenCV HSV occupancy detector with rectangle and polygon masking."""
import cv2
import numpy as np
from vision.detectors.base_detector import BaseDetector, DetectionResult
from vision.roi import ROIState

class HSVColorDetector(BaseDetector):
    def detect(self, frame, roi):
        h, w = frame.shape[:2]
        polygon = roi.pixel_polygon(w, h)
        if len(polygon) < 3:
            return DetectionResult(ROIState.UNKNOWN, 0.0, 0.0)
        x, y, rw, rh = cv2.boundingRect(polygon)
        x, y = max(0, x), max(0, y)
        rw, rh = min(rw, w - x), min(rh, h - y)
        if rw <= 1 or rh <= 1:
            return DetectionResult(ROIState.UNKNOWN, 0.0, 0.0)
        crop = frame[y:y+rh, x:x+rw]
        local = polygon - (x, y)
        valid = np.zeros((rh, rw), np.uint8)
        cv2.fillPoly(valid, [local], 255)
        hsv_img = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        s = roi.hsv
        raw = cv2.inRange(hsv_img, (s.h_min, s.s_min, s.v_min), (s.h_max, s.s_max, s.v_max))
        mask = cv2.bitwise_and(raw, valid)
        if s.open_kernel > 0:
            k = np.ones((s.open_kernel, s.open_kernel), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
        if s.close_kernel > 0:
            k = np.ones((s.close_kernel, s.close_kernel), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
        if s.erode: mask = cv2.erode(mask, None, iterations=s.erode)
        if s.dilate: mask = cv2.dilate(mask, None, iterations=s.dilate)
        valid_count = max(1, cv2.countNonZero(valid))
        occupancy = cv2.countNonZero(mask) / valid_count
        state = ROIState.PRESENT if occupancy >= roi.occupancy_threshold else ROIState.ABSENT
        confidence = min(1.0, occupancy / max(roi.occupancy_threshold, .001))
        return DetectionResult(state, occupancy, confidence, raw, mask)
