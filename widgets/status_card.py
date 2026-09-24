from PyQt6.QtWidgets import QFrame,QVBoxLayout,QLabel
from PyQt6.QtCore import Qt
class StatusCard(QFrame):
    COLORS={"PASS":"#19d66b","NG":"#ff3b4f","READY":"#e5ad23","IN PROCESS":"#13a8dc","PAUSED":"#69757d","CAMERA DISCONNECTED":"#ff3b4f","WAITING FOR PART RESET":"#e5ad23","INITIALIZING":"#69757d"}
    def __init__(self):
        super().__init__(); self.setObjectName("statusCard"); l=QVBoxLayout(self); self.title=QLabel("SYSTEM INITIALIZING"); self.title.setAlignment(Qt.AlignmentFlag.AlignCenter); self.title.setObjectName("statusTitle"); self.detail=QLabel("Loading station configuration…"); self.detail.setWordWrap(True); self.detail.setAlignment(Qt.AlignmentFlag.AlignCenter); l.addWidget(self.title); l.addWidget(self.detail); self.set_status("INITIALIZING")
    def set_status(self,status,detail=""):
        key=status.upper(); self.title.setText(key); self.detail.setText(detail); color=self.COLORS.get(key,"#13a8dc"); self.setStyleSheet(f"QFrame#statusCard{{background:{color}22;border:2px solid {color};border-radius:14px}} QLabel#statusTitle{{color:{color};font-size:30px;font-weight:800}}")
