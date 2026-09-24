from PyQt6.QtWidgets import QWidget,QHBoxLayout,QLabel
from PyQt6.QtCore import Qt
class SequenceWidget(QWidget):
    def __init__(self): super().__init__(); self.sequence=[]; self.step=0; self.refresh()
    def set_sequence(self,sequence,step=0): self.sequence=sequence; self.step=step; self.refresh()
    def refresh(self):
        if self.layout():
            while self.layout().count():
                i=self.layout().takeAt(0); i.widget() and i.widget().deleteLater()
        else: self.setLayout(QHBoxLayout())
        for n,name in enumerate(self.sequence):
            label=QLabel(("✓ " if n<self.step else "● " if n==self.step else "○ ")+name); label.setAlignment(Qt.AlignmentFlag.AlignCenter); label.setStyleSheet("color:"+("#19d66b" if n<self.step else "#f2b84b" if n==self.step else "#77828a")+";font-weight:700;padding:10px") ; self.layout().addWidget(label)
            if n<len(self.sequence)-1:self.layout().addWidget(QLabel("—"))
