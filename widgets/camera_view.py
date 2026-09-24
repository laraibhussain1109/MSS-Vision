"""Aspect-correct camera renderer and normalized ROI coordinate editor."""
import cv2
from PyQt6.QtCore import Qt,QPointF,QRectF,pyqtSignal
from PyQt6.QtGui import QImage,QPainter,QPen,QColor,QFont
from PyQt6.QtWidgets import QWidget
from vision.roi import ROIShape

class CameraView(QWidget):
    roi_drawn=pyqtSignal(object)
    def __init__(self):
        super().__init__(); self.setMinimumSize(640,480); self.frame=None; self.rois=[]; self.results={}; self.editing=False; self.polygon_mode=False; self.start=None; self.preview=None; self.poly=[]; self.engineering=False; self.expected=None; self.completed=set(); self.wrong=None
    def set_frame(self,frame,results=None): self.frame=frame.copy(); self.results=results or {}; self.update()
    def set_rois(self,rois): self.rois=rois; self.update()
    def image_rect(self):
        if self.frame is None:return QRectF()
        ih,iw=self.frame.shape[:2]; scale=min(self.width()/iw,self.height()/ih); w,h=iw*scale,ih*scale; return QRectF((self.width()-w)/2,(self.height()-h)/2,w,h)
    def widget_to_normalized(self,p):
        r=self.image_rect(); return [max(0,min(1,(p.x()-r.x())/r.width())),max(0,min(1,(p.y()-r.y())/r.height()))] if r.contains(p) else None
    def normalized_to_widget(self,p):
        r=self.image_rect(); return QPointF(r.x()+p[0]*r.width(),r.y()+p[1]*r.height())
    def paintEvent(self,e):
        p=QPainter(self); p.fillRect(self.rect(),QColor("#050708"))
        if self.frame is None: p.setPen(QColor("#69757d")); p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,"NO CAMERA IMAGE"); return
        rgb=cv2.cvtColor(self.frame,cv2.COLOR_BGR2RGB); h,w,c=rgb.shape; q=QImage(rgb.data,w,h,c*w,QImage.Format.Format_RGB888); p.drawImage(self.image_rect(),q)
        p.setFont(QFont("Segoe UI",10,600))
        for roi in self.rois:
            pts=[self.normalized_to_widget(x) for x in roi.points]
            if len(pts)<3:continue
            color="#19d66b" if roi.id in self.completed else "#f2b84b" if roi.id==self.expected else "#ff3b4f" if roi.id==self.wrong else "#17c6e3"
            p.setPen(QPen(QColor(color),3)); p.drawPolygon(*pts)
            info=self.results.get(roi.id,{}); text=roi.display_name
            if self.engineering:text+=f"  {info.get('occupancy',0)*100:.1f}% | {info.get('candidate','?')} → {info.get('stable','?')}"
            p.fillRect(QRectF(pts[0].x(),pts[0].y()-25,max(130,len(text)*7),24),QColor(color)); p.setPen(QColor("#071012")); p.drawText(QPointF(pts[0].x()+5,pts[0].y()-7),text)
        if self.preview:
            p.setPen(QPen(QColor("#ffffff"),2,Qt.PenStyle.DashLine)); p.drawRect(self.preview)
        if self.poly:
            p.setPen(QPen(QColor("#ffffff"),2)); p.drawPolyline(*[self.normalized_to_widget(x) for x in self.poly])
    def mousePressEvent(self,e):
        if not self.editing:return
        n=self.widget_to_normalized(e.position())
        if not n:return
        if self.polygon_mode:self.poly.append(n); self.update()
        else:self.start=e.position(); self.preview=QRectF(self.start,self.start); self.update()
    def mouseMoveEvent(self,e):
        if self.editing and self.start:self.preview=QRectF(self.start,e.position()).normalized(); self.update()
    def mouseReleaseEvent(self,e):
        if self.editing and self.start:
            a=self.widget_to_normalized(self.preview.topLeft()); b=self.widget_to_normalized(self.preview.bottomRight()); self.start=None; self.preview=None
            if a and b and abs(b[0]-a[0])>.01 and abs(b[1]-a[1])>.01:self.roi_drawn.emit({"shape":ROIShape.RECTANGLE,"points":[a,[b[0],a[1]],b,[a[0],b[1]]]})
    def mouseDoubleClickEvent(self,e):
        if self.editing and self.polygon_mode and len(self.poly)>=3:self.roi_drawn.emit({"shape":ROIShape.POLYGON,"points":self.poly}); self.poly=[]; self.update()
