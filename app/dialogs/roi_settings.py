from uuid import uuid4
from PyQt6.QtWidgets import QDialog,QFormLayout,QLineEdit,QComboBox,QCheckBox,QSpinBox,QDoubleSpinBox,QDialogButtonBox
from vision.roi import ROIConfig
class ROISettingsDialog(QDialog):
    def __init__(self,roi=None,parent=None):
        super().__init__(parent); self.roi=roi; self.setWindowTitle("ROI Properties"); f=QFormLayout(self)
        self.name=QLineEdit(roi.name if roi else ""); self.display=QLineEdit(roi.display_name if roi else ""); self.kind=QComboBox();self.kind.addItems(["Clip","Future type"])
        self.detector=QComboBox();self.detector.addItems(["hsv","reference","future_ai"]); self.seq=QCheckBox();self.seq.setChecked(roi.sequence_enabled if roi else True)
        self.order=QSpinBox();self.order.setRange(1,999);self.order.setValue(roi.sequence_position if roi else 1); self.required=QCheckBox();self.required.setChecked(roi.required if roi else True)
        self.removal=QCheckBox();self.removal.setChecked(roi.allow_removal if roi else False);self.threshold=QDoubleSpinBox();self.threshold.setRange(.001,1);self.threshold.setSingleStep(.01);self.threshold.setValue(roi.occupancy_threshold if roi else .08)
        self.presence=QSpinBox();self.presence.setRange(0,10000);self.presence.setValue(roi.presence_ms if roi else 300);self.absence=QSpinBox();self.absence.setRange(0,30000);self.absence.setValue(roi.absence_ms if roi else 700)
        for label,w in (("ROI name",self.name),("Display name",self.display),("ROI type",self.kind),("Detection method",self.detector),("Use in sequence",self.seq),("Sequence position",self.order),("Required",self.required),("Allow removal",self.removal),("Occupancy threshold",self.threshold),("Presence confirmation (ms)",self.presence),("Absence confirmation (ms)",self.absence)):f.addRow(label,w)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);f.addRow(buttons)
    def build(self,shape,points):
        r=self.roi or ROIConfig(str(uuid4()),self.name.text(),self.display.text() or self.name.text(),shape,points)
        r.name=self.name.text().strip() or "ROI";r.display_name=self.display.text().strip() or r.name;r.roi_type=self.kind.currentText();r.detector=self.detector.currentText();r.sequence_enabled=self.seq.isChecked();r.sequence_position=self.order.value();r.required=self.required.isChecked();r.allow_removal=self.removal.isChecked();r.occupancy_threshold=self.threshold.value();r.presence_ms=self.presence.value();r.absence_ms=self.absence.value();return r
