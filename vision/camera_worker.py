"""Reconnect-capable latest-frame capture worker."""
import time
import cv2
from PyQt6.QtCore import QThread, pyqtSignal

class CameraWorker(QThread):
    frame_ready = pyqtSignal(object)
    connection_changed = pyqtSignal(bool, str)
    def __init__(self, settings):
        super().__init__(); self.settings=settings; self.running=False
    def run(self):
        self.running=True; cap=None
        while self.running:
            if cap is None or not cap.isOpened():
                source=self.settings.get("source", 0)
                source=int(source) if str(source).isdigit() else source
                cap=cv2.VideoCapture(source)
                if cap.isOpened():
                    for key, prop in (("width",cv2.CAP_PROP_FRAME_WIDTH),("height",cv2.CAP_PROP_FRAME_HEIGHT),("fps",cv2.CAP_PROP_FPS),("exposure",cv2.CAP_PROP_EXPOSURE),("gain",cv2.CAP_PROP_GAIN),("focus",cv2.CAP_PROP_FOCUS),("brightness",cv2.CAP_PROP_BRIGHTNESS),("contrast",cv2.CAP_PROP_CONTRAST)):
                        if key in self.settings: cap.set(prop,float(self.settings[key]))
                    self.connection_changed.emit(True, str(source))
                else:
                    self.connection_changed.emit(False, str(source)); time.sleep(2); continue
            ok, frame=cap.read()
            if not ok:
                cap.release(); self.connection_changed.emit(False,"Frame unavailable"); time.sleep(.5); continue
            self.frame_ready.emit(frame)
            fps=max(1,float(self.settings.get("fps",30))); self.msleep(round(1000/fps))
        if cap is not None: cap.release()
    def stop(self): self.running=False; self.wait(2500)
