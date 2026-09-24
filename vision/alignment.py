"""Optional ArUco alignment service; NONE is the safe default."""
import cv2

class FrameAligner:
    def __init__(self, config): self.config = config
    def align(self, frame):
        if self.config.get("mode", "none") == "none": return frame, True
        if not hasattr(cv2, "aruco"): return frame, False
        # Marker reference homography can be expanded without changing processing callers.
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        corners, ids, _ = cv2.aruco.detectMarkers(frame, dictionary)
        required = set(self.config.get("marker_ids", []))
        return frame, bool(ids is not None and required.issubset(set(ids.flatten())))
