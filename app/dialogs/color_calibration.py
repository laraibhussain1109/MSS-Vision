import cv2, numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage,QPixmap
from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QSlider,QSpinBox,QLabel,QPushButton,QDialogButtonBox,QGroupBox
class ColorCalibrationDialog(QDialog):
    def __init__(self,roi,frame,parent=None):
        super().__init__(parent);self.roi=roi;self.frame=frame;self.setWindowTitle(f"Color Calibration — {roi.display_name}");self.resize(1050,700);root=QVBoxLayout(self); previews=QHBoxLayout();self.original=QLabel();self.mask=QLabel();self.result=QLabel()
        for title,w in (("ORIGINAL",self.original),("HSV MASK",self.mask),("FINAL DETECTION",self.result)):
            box=QGroupBox(title);l=QVBoxLayout(box);w.setMinimumSize(280,220);w.setAlignment(Qt.AlignmentFlag.AlignCenter);l.addWidget(w);previews.addWidget(box)
        root.addLayout(previews); controls=QHBoxLayout();form=QFormLayout();self.fields={}
        vals=(('h_min',0,179),('h_max',0,179),('s_min',0,255),('s_max',0,255),('v_min',0,255),('v_max',0,255),('erode',0,10),('dilate',0,10),('open_kernel',0,15),('close_kernel',0,15))
        for key,lo,hi in vals:
            row=QHBoxLayout();slider=QSlider(Qt.Orientation.Horizontal);spin=QSpinBox();slider.setRange(lo,hi);spin.setRange(lo,hi);value=getattr(roi.hsv,key);slider.setValue(value);spin.setValue(value);slider.valueChanged.connect(spin.setValue);spin.valueChanged.connect(slider.setValue);spin.valueChanged.connect(self.refresh);row.addWidget(slider);row.addWidget(spin);form.addRow(key.replace('_',' ').title(),row);self.fields[key]=spin
        controls.addLayout(form);side=QVBoxLayout();self.occupancy=QLabel();self.occupancy.setStyleSheet("font-size:22px;font-weight:700;color:#17c6e3");auto=QPushButton("AUTO SAMPLE COLOR");auto.clicked.connect(self.auto_sample);side.addWidget(self.occupancy);side.addWidget(auto);side.addStretch();controls.addLayout(side);root.addLayout(controls)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(self.save);buttons.rejected.connect(self.reject);root.addWidget(buttons);self.refresh()
    def crop(self):
        if self.frame is None:return None
        p=self.roi.pixel_polygon(self.frame.shape[1],self.frame.shape[0]);x,y,w,h=cv2.boundingRect(p);return self.frame[y:y+h,x:x+w]
    def pix(self,img):
        if len(img.shape)==2: q=QImage(img.data,img.shape[1],img.shape[0],img.strides[0],QImage.Format.Format_Grayscale8)
        else: rgb=cv2.cvtColor(img,cv2.COLOR_BGR2RGB);q=QImage(rgb.data,rgb.shape[1],rgb.shape[0],rgb.strides[0],QImage.Format.Format_RGB888)
        return QPixmap.fromImage(q.copy()).scaled(300,230,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
    def refresh(self):
        crop=self.crop()
        if crop is None or not crop.size:return
        hsv=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV);f={k:v.value() for k,v in self.fields.items()};raw=cv2.inRange(hsv,(f['h_min'],f['s_min'],f['v_min']),(f['h_max'],f['s_max'],f['v_max']));mask=raw
        for op,key in ((cv2.MORPH_OPEN,'open_kernel'),(cv2.MORPH_CLOSE,'close_kernel')):
            if f[key]>0:mask=cv2.morphologyEx(mask,op,np.ones((f[key],f[key]),np.uint8))
        if f['erode']:mask=cv2.erode(mask,None,iterations=f['erode'])
        if f['dilate']:mask=cv2.dilate(mask,None,iterations=f['dilate'])
        out=cv2.bitwise_and(crop,crop,mask=mask);self.original.setPixmap(self.pix(crop));self.mask.setPixmap(self.pix(mask));self.result.setPixmap(self.pix(out));occ=cv2.countNonZero(mask)/max(1,mask.size);self.occupancy.setText(f"Occupancy: {occ*100:.2f}%\nThreshold: {self.roi.occupancy_threshold*100:.2f}%")
    def auto_sample(self):
        crop=self.crop()
        if crop is None:return
        hsv=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV);pixels=hsv.reshape(-1,3);pixels=pixels[(pixels[:,1]>60)&(pixels[:,2]>40)]
        if not len(pixels):return
        lo=np.percentile(pixels,10,axis=0);hi=np.percentile(pixels,90,axis=0);margins=(8,35,35)
        for key,val in zip(('h_min','s_min','v_min'),lo-margins):self.fields[key].setValue(max(0,int(val)))
        for key,val,cap in zip(('h_max','s_max','v_max'),hi+margins,(179,255,255)):self.fields[key].setValue(min(cap,int(val)))
    def save(self):
        for k,v in self.fields.items():setattr(self.roi.hsv,k,v.value())
        self.accept()
