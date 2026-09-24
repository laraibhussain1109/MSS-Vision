from PyQt6.QtWidgets import QDialog,QFormLayout,QComboBox,QLineEdit,QSpinBox,QDoubleSpinBox,QDialogButtonBox,QFileDialog,QHBoxLayout,QPushButton
class CameraSettingsDialog(QDialog):
    def __init__(self,settings,parent=None):
        super().__init__(parent);self.settings=dict(settings);self.setWindowTitle("Camera Settings");f=QFormLayout(self);self.source=QComboBox();self.source.setEditable(True);self.source.addItems([str(i) for i in range(6)]+["Video file / RTSP URL"]);self.source.setCurrentText(str(settings.get('source',0)));browse=QPushButton("Browse Video…");browse.clicked.connect(self.browse);row=QHBoxLayout();row.addWidget(self.source);row.addWidget(browse);f.addRow("Camera / video / URL",row)
        self.values={}
        for key,lo,hi,default in (("width",160,7680,1280),("height",120,4320,720),("fps",1,120,30),("exposure",-20,100,-1),("gain",0,255,0),("focus",0,255,0),("brightness",0,255,0),("contrast",0,255,0)):
            w=QSpinBox();w.setRange(lo,hi);w.setValue(int(settings.get(key,default)));f.addRow(key.title(),w);self.values[key]=w
        b=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);b.accepted.connect(self.accept);b.rejected.connect(self.reject);f.addRow(b)
    def browse(self):
        p,_=QFileDialog.getOpenFileName(self,"Select video","","Videos (*.mp4 *.avi *.mov);;All files (*)");p and self.source.setCurrentText(p)
    def result_settings(self):return {"source":self.source.currentText(),**{k:v.value() for k,v in self.values.items()}}
